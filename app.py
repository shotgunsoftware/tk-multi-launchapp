"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

App that launches applications.

"""
import os
import re
import sys
import tank


class LaunchApplication(tank.platform.Application):
    """Mutli App to launch applications."""

    def init_app(self):
        menu_name = self.get_setting("menu_name")

        p = {
            "title": menu_name,
            "entity_types": self.get_setting("entity_types"),
            "deny_permissions": self.get_setting("deny_permissions"),
            "deny_platforms": self.get_setting("deny_platforms"),
            "supports_multiple_selection": False
        }

        # the command name mustn't contain spaces and funny chars, so sanitize it before
        # passing it in...
        sanitized_menu_name = re.sub(r"\W+", "", menu_name)

        self.engine.register_command(sanitized_menu_name, self.launch_app, p)

    def launch_app(self, entity_type, entity_ids):
        if len(entity_ids) != 1:
            raise Exception("LaunchApp only accepts a single item in entity_ids.")

        entity_id = entity_ids[0]
        engine_name = self.get_setting("engine")

        # Try to create path for the context.
        try:
            self.tank.create_filesystem_structure(entity_type, entity_id, engine=engine_name)
        except tank.TankError, e:
            raise Exception("Could not create folders on disk. Error reported: %s" % e)            

        # get the setting
        system = sys.platform
        try:
            system_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[system]
            app_path = self.get_setting("%s_path" % system_name, "")
            app_args = self.get_setting("%s_args" % system_name, "")
            if not app_path: raise KeyError()
        except KeyError:
            raise Exception("Platform '%s' is not supported." % system)

        # Set environment variables used by apps to prep Tank engine
        os.environ["TANK_ENGINE"] = engine_name
        os.environ["TANK_PROJECT_ROOT"] = self.tank.project_path
        os.environ["TANK_ENTITY_TYPE"] = entity_type
        os.environ["TANK_ENTITY_ID"] = str(entity_id)

        # Prep any application specific things
        if engine_name == 'tk-nuke':
            _tk_nuke()
        elif engine_name == 'tk-maya':
            _tk_maya(system, app_path)
        elif engine_name == 'tk-motionbuilder':
            app_args = _tk_motionbuilder(app_args)
        elif engine_name == 'tk-3dsmax':
            app_args = _tk_3dsmax(app_args)

        # Launch the application
        self.log_debug("Launching executable '%s' with args '%s'" % (app_path, app_args))
        result = self.execute_hook("hook_app_launch", app_path=app_path, app_args=app_args)
        cmd = result.get('command')
        launch_error = result.get('launch_error')

        if cmd:
            self.log_debug("Hook tried to launch '%s'" % cmd)
            if launch_error:
                self.log_error(
                    "Failed to launch application! This is most likely because the path "
                    "to the executable is not set to a correct value. The command used "
                    "is '%s' - please double check that this command is valid and update "
                    "as needed in this app's configuration or hook. If you have any "
                    "questions, don't hesitate to contact support on tanksupport@shotgunsoftware.com." % result['command']
                )

        # Write an event log entry
        self._register_event_log(self.tank.context_from_entity(entity_type, entity_id), cmd, {})

    def _register_event_log(self, ctx, command_executed, additional_meta):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch
        """        
        meta = {}
        meta["engine"] = "%s %s" % (self.engine.name, self.engine.version) 
        meta["app"] = "%s %s" % (self.name, self.version) 
        meta["launched_engine"] = self.get_setting("engine")
        meta["command"] = command_executed or 'Unknown'
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        meta.update(additional_meta)
        desc =  "%s %s: Launched Application" % (self.name, self.version)
        tank.util.create_event_log_entry(self.tank, ctx, "Tank_App_Startup", desc, meta)


def _tk_nuke():
    """Nuke specific pre-launch environment setup."""

    # Make sure Nuke can find the Tank menu
    startup_path = os.path.abspath(os.path.join(_get_app_specific_path('nuke'), "startup"))
    tank.util.append_path_to_env_var("NUKE_PATH", startup_path)


def _tk_maya(system, app_path):
    """Maya specific pre-launch environment setup."""

    # Make sure Maya can find the Tank menu
    app_specific_path = _get_app_specific_path('maya')
    startup_path = os.path.abspath(os.path.join(app_specific_path, "startup"))
    tank.util.append_path_to_env_var("PYTHONPATH", startup_path)

    # Push our patched _ssl compiled module to the front of the PYTHONPATH for Windows
    # SSL Connection time fix.
    if system == "win32":
        # maps the maya version to the ssl maya version;  (maya 2011 can use the maya 2012 _ssl.pyd)
        # the ssl directory name is the version of maya it was compiled for.
        maya_version_to_ssl_maya_version = {
            "2011": "2012",
            "2012": "2012",
            "2013": "2013",
        }

        version_dir = None
        # From most recent to past version
        for year in sorted(maya_version_to_ssl_maya_version, reverse=True):
            # Test for the year in the path.
            # maya -v returns an empty line with maya 2013.
            if year in app_path:
                version_dir = maya_version_to_ssl_maya_version[year]
                break

        # if there is an ssl lib for that current version of maya being used then
        # add it to the python path.
        if version_dir:
            ssl_path = os.path.abspath(os.path.join(app_specific_path, "ssl_patch", version_dir))
            tank.util.prepend_path_to_env_var('PYTHONPATH', ssl_path)


def _tk_motionbuilder(app_args):
    """Maya specific pre-launch environment setup."""

    if app_args:
        app_args += ' '
    return app_args + '"%s"' % os.path.join(_get_app_specific_path('motionbuilder'), "startup", "init_tank.py")


def _tk_3dsmax(app_args):
    """
    3DSMax specific pre-launch environment setup.

    Make sure launch args include a maxscript to load the python engine:
    3dsmax.exe somefile.max -U MAXScript somescript.ms        
    """

    startup_dir = os.path.abspath(os.path.join(_get_app_specific_path('3dsmax'), "startup"))
    os.environ["TANK_BOOTSTRAP_SCRIPT"] = os.path.join(startup_dir, "tank_startup.py")
    new_args = '-U MAXScript "%s"' % os.path.join(startup_dir, "init_tank.ms")

    if app_args:
        app_args = ' ' + app_args
    return new_args + app_args


def _get_app_specific_path(app_dir):
    """Get the path for application specific files for a given application."""

    return os.path.join(os.path.dirname(__file__), "app_specific", app_dir)
