"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

App that launches applications.

"""
import os
import re
import sys
import tank
from tank import TankError

class LaunchApplication(tank.platform.Application):
    """
    Multi App to launch applications.
    """
    
    def init_app(self):
        menu_name = self.get_setting("menu_name")

        # based on the app decide which platform to show up on
        engine_name = self.get_setting("engine")
        
        if engine_name == "tk-motionbuilder" or engine_name == "tk-3dsmax":
            if sys.platform in ["darwin", "linux2"]:
                return
            
        if engine_name == "tk-photoshop":
            if sys.platform == "linux2":
                return

        # the command name mustn't contain spaces and funny chars, so sanitize it.
        # Also, should be nice for the shell engine.
        
        # "Launch NukeX..." -> launch_nukex
        command_name = menu_name.lower().replace(" ", "_")
        if command_name.endswith("..."):
            command_name = command_name[:-3]

        # special case! todo: fix this. 
        # this is to allow this app to be loaded for sg entities of type publish
        # but not show up on the menu.
        # this is because typically, for published files, you want the app loaded
        # but you want to access it via the launch_from_path() method, normally
        # hooked up via a hook.
        if self.engine.environment.get("name") not in ["shotgun_tankpublishedfile", "shotgun_publishedfile"]:

            properties = { "title": menu_name,
                           "short_name": command_name,
                           "description": "Launches and initializes the %s environment." % engine_name }
                
            self.engine.register_command(command_name, self.launch_from_entity, properties)
        
        
    def launch_from_path_and_context(self, path, context):
        """
        Extended version of launch_from_path. This method takes an additional 
        context parameter which is useful if you want to seed the launch context
        with more context data than is available in the path itself. Typically
        paths may not contain a task, so this may need to be pushed through
        separately via the context.
        
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic 
        which is external to this app. 
        """
        if context is None:
            # this context looks sour. So fall back on to path-only launch.
            self.launch_from_path(path)
        else:
            # use given context to launch engine!
            self._launch_app(context, path)


    def launch_from_path(self, path):
        """
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic 
        which is external to this app. 
        """
        context = self.tank.context_from_path(path)
        self._launch_app(context, path)

    def launch_from_entity(self):
        """
        Default app command. Launches an app based on the current context and settings.
        """

        # extract a entity_type and id from the context.
        if self.context.project is None:
            raise TankError("Your context does not have a project defined. Cannot continue.")
        
        # make sure that we don't launch from tasks with no step - while this is not technically
        # incorrect, it can be confusing with any config that requires a step. 
        if self.engine.name == "tk-shotgun" and self.context.task and self.context.step is None:
            raise TankError("Looks like you are trying to launch from a Task that "
                            "does not have a Pipeline Step associated! ")  
        
        # first do project
        entity_type = self.context.project["type"]
        entity_id = self.context.project["id"]
        # if there is an entity then that takes precedence
        if self.context.entity:
            entity_type = self.context.entity["type"]
            entity_id = self.context.entity["id"]
        # and if there is a task that is even better
        if self.context.task:
            entity_type = self.context.task["type"]
            entity_id = self.context.task["id"]
        
        # Try to create path for the context.
        engine_name = self.get_setting("engine")
        try:
            self.log_debug("Creating folders for %s %s, %s" % (entity_type, entity_id, engine_name))
            self.tank.create_filesystem_structure(entity_type, entity_id, engine=engine_name)
        except tank.TankError, err:
            raise TankError("Could not create folders on disk. Error reported: %s" % err)            

        self._launch_app(self.context)
        

    def _launch_app(self, context, file_to_open=None):
        """
        Launches an app
        """
        # pass down the file to open into the startup script via env var.
        if file_to_open:
            os.environ["TANK_FILE_TO_OPEN"] = file_to_open
            self.log_debug("Setting TANK_FILE_TO_OPEN to '%s'" % file_to_open)
            
        # serialize the context into an env var
        os.environ["TANK_CONTEXT"] = tank.context.serialize(context)
        self.log_debug("Setting TANK_CONTEXT to '%r'" % context)

        # Set environment variables used by apps to prep Tank engine
        engine_name = self.get_setting("engine")
        os.environ["TANK_ENGINE"] = engine_name

        # get get path and args for the app
        try:
            system_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
            self._app_path = self.get_setting("%s_path" % system_name, "")
            self._app_args = self.get_setting("%s_args" % system_name, "")
            if not self._app_path:
                raise KeyError()
        except KeyError:
            raise TankError("Platform '%s' is not supported." % sys.platform)
        
        # Prep any application specific things
        if engine_name == "tk-nuke":
            self.prepare_nuke_launch(file_to_open)
        elif engine_name == "tk-maya":
            self.prepare_maya_launch()
        elif engine_name == "tk-softimage":
            self.prepare_softimage_launch()
        elif engine_name == "tk-motionbuilder":
            self.prepare_motionbuilder_launch()
        elif engine_name == "tk-3dsmax":
            self.prepare_3dsmax_launch()
        elif engine_name == "tk-hiero":
            self.prepare_hiero_launch()
        elif engine_name == "tk-photoshop":
            self.prepare_photoshop_launch(context)
        else:
            raise TankError("The %s engine is not supported!" % engine_name)

        # run before launch hook
        self.log_debug("Running before launch hook...")
        self.execute_hook("hook_before_app_launch")

        # Launch the application
        self.log_debug("Launching executable '%s' with args '%s'" % (self._app_path, self._app_args))
        result = self.execute_hook("hook_app_launch", app_path=self._app_path, app_args=self._app_args)
        
        cmd = result.get("command")
        return_code = result.get("return_code")

        self.log_debug("Hook tried to launch '%s'" % cmd)
        if return_code != 0:
            self.log_error(
                "Failed to launch application (return code: %s)! This is most likely because the path "
                "to the executable is not set to a correct value. The command used "
                "is '%s' - please double check that this command is valid and update "
                "as needed in this app's configuration or hook. If you have any "
                "questions, don't hesitate to contact support on sgtksupport@shotgunsoftware.com." %
                (return_code, cmd)
            )
            
        else:
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
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc =  "%s %s: Launched %s" % (self.name, self.version, self.get_setting("engine"))
        tank.util.create_event_log_entry(self.tank, ctx, "Tank_App_Startup", desc, meta)


    def prepare_nuke_launch(self, file_to_open):
        """
        Nuke specific pre-launch environment setup.
        """
        # Make sure Nuke can find the Tank menu
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("nuke"), "startup"))
        tank.util.append_path_to_env_var("NUKE_PATH", startup_path)
        
        # it's not possible to open a nuke script from within the initialization
        # scripts so if we have a path then we need to pass it through the start
        # up args:
        if file_to_open:
            if self._app_args:
                self._app_args = "%s %s" % (file_to_open, self._app_args)
            else:
                self._app_args = file_to_open


    def prepare_maya_launch(self):
        """
        Maya specific pre-launch environment setup.
        """
        # Make sure Maya can find the Tank menu
        app_specific_path = self._get_app_specific_path("maya")
        startup_path = os.path.abspath(os.path.join(app_specific_path, "startup"))
        tank.util.append_path_to_env_var("PYTHONPATH", startup_path)

        # Push our patched _ssl compiled module to the front of the PYTHONPATH for Windows
        # SSL Connection time fix.
        if sys.platform == "win32":
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


    def prepare_softimage_launch(self):
        """Softimage specific pre-launch environment setup."""
        xsi_plugins = os.path.abspath(os.path.join(self._get_app_specific_path("softimage"), "startup", "Application", "Plugins"))
        tank.util.append_path_to_env_var("XSI_PLUGINS", xsi_plugins)


    def prepare_motionbuilder_launch(self):
        """
        Maya specific pre-launch environment setup.
        """
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
            self._app_args = "%s %s" % (new_args, self._app_args)
        else:
            self._app_args = new_args


    def prepare_hiero_launch(self):
        """
        Hiero specific pre-launch environment setup.
        """
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("hiero"), "startup"))
        tank.util.append_path_to_env_var("HIERO_PLUGIN_PATH", startup_path)


    def prepare_photoshop_launch(self, context):
        """
        Photoshop specific pre-launch environment setup.
        """
        extra_configs = self.get_setting("extra", {})

        engine_path = tank.platform.get_engine_path("tk-photoshop", self.tank, context)        
        if engine_path is None:
            raise TankError("Path to photoshop engine (tk-photoshop) could not be found.")

        # Get the path to the python executable
        python_setting = {"darwin": "mac_python_path", "win32": "windows_python_path"}[sys.platform]
        python_path = extra_configs.get(python_setting)
        if not python_path:
            raise TankError("Your photoshop app launch config is missing the extra setting %s" % python_setting)

        # get the path to extension manager
        manager_setting = { "darwin": "mac_extension_manager_path",
                            "win32": "windows_extension_manager_path" }[sys.platform]
        manager_path = extra_configs.get(manager_setting)
        if not manager_path:
            raise TankError("Your photoshop app launch config is missing the extra setting %s!" % manager_setting)
        os.environ["TANK_PHOTOSHOP_EXTENSION_MANAGER"] = manager_path

        # make sure the extension is up to date
        sys.path.append(os.path.join(engine_path, "bootstrap"))
        try:
            import photoshop_extension_manager
            photoshop_extension_manager.update()
        except Exception, e:
            raise TankError("Could not run the Adobe Extension Manager. Please double check your "
                            "Shotgun Pipeline Toolkit Photoshop Settings. Error Reported: %s" % e)

        # Store data needed for bootstrapping Tank in env vars. Used in startup/menu.py
        os.environ["TANK_PHOTOSHOP_PYTHON"] = python_path
        os.environ["TANK_PHOTOSHOP_BOOTSTRAP"] = os.path.join(engine_path, "bootstrap", "engine_bootstrap.py")
        
        # unused values, but the photoshop engine code still looks for these...
        os.environ["TANK_PHOTOSHOP_ENGINE"] = "dummy_value"
        os.environ["TANK_PHOTOSHOP_PROJECT_ROOT"] = "dummy_value"

        # add our startup path to the photoshop init path
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("photoshop"), "startup"))
        tank.util.append_path_to_env_var("PYTHONPATH", startup_path)


    def _get_app_specific_path(self, app_dir):
        """
        Get the path for application specific files for a given application.
        """

        return os.path.join(self.disk_location, "app_specific", app_dir)
