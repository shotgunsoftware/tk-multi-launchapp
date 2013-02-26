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
    def __init__(self, *args, **kwargs):
        super(LaunchApplication, self).__init__(*args, **kwargs)
        self._app_path = None           # Path to the application executable
        self._app_args = None           # Executable arguments (str)
        self._engine_path = None        # Path to the engine to use
        self._extra_configs = {}        # Extra per engine
        self._system = sys.platform     # Platform this app is running on (should be in tank.platform.Application?)

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
        context = self.tank.context_from_entity(entity_type, entity_id)
        engine_name = self.get_setting("engine")
        self._engine_path = tank.platform.get_engine_path(engine_name, self.tank, context)

        # Try to create path for the context.
        try:
            self.tank.create_filesystem_structure(entity_type, entity_id, engine=engine_name)
        except tank.TankError, e:
            raise Exception("Could not create folders on disk. Error reported: %s" % e)            

        # get the setting
        try:
            system_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[self._system]
            self._app_path = self.get_setting("%s_path" % system_name, "")
            self._app_args = self.get_setting("%s_args" % system_name, "")
            if not self._app_path: raise KeyError()
        except KeyError:
            raise Exception("Platform '%s' is not supported." % self._system)

        # Set environment variables used by apps to prep Tank engine
        os.environ["TANK_ENGINE"] = engine_name
        os.environ["TANK_PROJECT_ROOT"] = self.tank.project_path
        os.environ["TANK_ENTITY_TYPE"] = entity_type
        os.environ["TANK_ENTITY_ID"] = str(entity_id)

        # Prep any application specific things
        self._extra_configs = self.get_setting("extra", {})
        if engine_name == "tk-nuke":
            self.prepare_nuke_launch()
        elif engine_name == "tk-maya":
            self.prepare_maya_launch()
        elif engine_name == "tk-motionbuilder":
            self.prepare_motionbuilder_launch()
        elif engine_name == "tk-3dsmax":
            self.prepare_3dsmax_launch()
        elif engine_name == "tk-hiero":
            self.prepare_hiero_launch()
        elif engine_name == "tk-photoshop":
            self.prepare_photoshop_launch()

        # Launch the application
        self.log_debug("Launching executable '%s' with args '%s'" % (self._app_path, self._app_args))
        result = self.execute_hook("hook_app_launch", app_path=self._app_path, app_args=self._app_args)
        cmd = result.get("command")
        return_code = result.get("launch_error")

        if cmd:
            self.log_debug("Hook tried to launch '%s'" % cmd)
            if return_code != 0:
                self.log_error(
                    "Failed to launch application (return code: %d)! This is most likely because the path "
                    "to the executable is not set to a correct value. The command used "
                    "is '%s' - please double check that this command is valid and update "
                    "as needed in this app's configuration or hook. If you have any "
                    "questions, don't hesitate to contact support on tanksupport@shotgunsoftware.com." %
                    (return_code, cmd)
                )

        # Write an event log entry
        self._register_event_log(context, cmd)

    def _register_event_log(self, ctx, command_executed):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch
        """        
        meta = {}
        meta["engine"] = "%s %s" % (self.engine.name, self.engine.version) 
        meta["app"] = "%s %s" % (self.name, self.version) 
        meta["launched_engine"] = self.get_setting("engine")
        meta["command"] = command_executed or "Unknown"
        meta["platform"] = self._system
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc =  "%s %s: Launched Application" % (self.name, self.version)
        tank.util.create_event_log_entry(self.tank, ctx, "Tank_App_Startup", desc, meta)


    def prepare_nuke_launch(self):
        """Nuke specific pre-launch environment setup."""

        # Make sure Nuke can find the Tank menu
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("nuke"), "startup"))
        tank.util.append_path_to_env_var("NUKE_PATH", startup_path)


    def prepare_maya_launch(self):
        """Maya specific pre-launch environment setup."""

        # Make sure Maya can find the Tank menu
        app_specific_path = self._get_app_specific_path("maya")
        startup_path = os.path.abspath(os.path.join(app_specific_path, "startup"))
        tank.util.append_path_to_env_var("PYTHONPATH", startup_path)

        # Push our patched _ssl compiled module to the front of the PYTHONPATH for Windows
        # SSL Connection time fix.
        if self._system == "win32":
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
                if year in self._app_path:
                    version_dir = maya_version_to_ssl_maya_version[year]
                    break

            # if there is an ssl lib for that current version of maya being used then
            # add it to the python path.
            if version_dir:
                ssl_path = os.path.abspath(os.path.join(app_specific_path, "ssl_patch", version_dir))
                tank.util.prepend_path_to_env_var("PYTHONPATH", ssl_path)


    def prepare_motionbuilder_launch(self):
        """Maya specific pre-launch environment setup."""

        new_args = "\"%s\"" % os.path.join(self._get_app_specific_path("motionbuilder"), "startup", "init_tank.py")

        if self._app_args:
            self._app_args += " "
        self._app_args += new_args


    def prepare_3dsmax_launch(self):
        """
        3DSMax specific pre-launch environment setup.

        Make sure launch args include a maxscript to load the python engine:
        3dsmax.exe somefile.max -U MAXScript somescript.ms        
        """

        startup_dir = os.path.abspath(os.path.join(self._get_app_specific_path("3dsmax"), "startup"))
        os.environ["TANK_BOOTSTRAP_SCRIPT"] = os.path.join(startup_dir, "tank_startup.py")
        new_args = "-U MAXScript \"%s\"" % os.path.join(startup_dir, "init_tank.ms")

        if self._app_args:
            self._app_args = " " + self._app_args
        return new_args + self._app_args


    def prepare_hiero_launch(self):
        """Hiero specific pre-launch environment setup."""

        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("hiero"), "startup"))
        tank.util.append_path_to_env_var("HIERO_PLUGIN_PATH", startup_path)


    def prepare_photoshop_launch(self):
        """Photoshop specific pre-launch environment setup."""

        if self._engine_path is None:
            raise ValueError("Path to photoshop engine (tk-photoshop) could not be found.")

        # Get the path to the python executable
        try:
            python_setting = {"darwin": "mac_python_path", "win32": "windows_python_path"}[self._system]
        except KeyError:
            raise Exception("Platform '%s' is not supported." % self._system)
        python_path = self._extra_configs.get(python_setting)
        if not python_path:
            raise Exception("Missing extra setting %s" % python_setting)

        # get the path to extension manager
        try:
            manager_setting = {
                "darwin": "mac_extension_manager_path",
                "win32": "windows_extension_manager_path"
            }[self._system]
        except KeyError:
            raise Exception("Platform '%s' is not supported." % self._system)
        manager_path = self._extra_configs.get(manager_setting)
        if not manager_path:
            raise Exception("Missing extra setting %s" % manager_setting)
        os.environ["TANK_PHOTOSHOP_EXTENSION_MANAGER"] = manager_path

        # make sure the extension is up to date
        sys.path.append(os.path.join(self._engine_path, "bootstrap"))
        import photoshop_extension_manager
        photoshop_extension_manager.update()

        # Store data needed for bootstrapping Tank in env vars. Used in startup/menu.py
        os.environ["TANK_PHOTOSHOP_PYTHON"] = python_path
        os.environ["TANK_PHOTOSHOP_BOOTSTRAP"] = os.path.join(self._engine_path, "bootstrap", "engine_bootstrap.py")
        os.environ["TANK_PHOTOSHOP_ENGINE"] = os.environ["TANK_ENGINE"]
        os.environ["TANK_PHOTOSHOP_PROJECT_ROOT"] = os.environ["TANK_PROJECT_ROOT"]
        os.environ["TANK_PHOTOSHOP_ENTITY_TYPE"] = os.environ["TANK_ENTITY_TYPE"]
        os.environ["TANK_PHOTOSHOP_ENTITY_ID"] = os.environ["TANK_ENTITY_ID"]

        # add our startup path to the photoshop init path
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("photoshop"), "startup"))
        tank.util.append_path_to_env_var("PYTHONPATH", startup_path)


    def _get_app_specific_path(self, app_dir):
        """Get the path for application specific files for a given application."""

        return os.path.join(self.disk_location, "app_specific", app_dir)
