# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
App that launches applications.

"""
import os
import re
import sys

import sgtk
from sgtk import TankError

shotgun_data = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_data")

class InitAndLaunchApps(object):
    """
    Multi App to launch applications.
    """
    # documentation explaining how to reconfigure app paths
    HELP_DOC_URL = "https://support.shotgunsoftware.com/entries/95443887#Setting%20up%20Application%20Paths"

    def __init__(self):
        self._app = sgtk.platform.current_bundle()
        self._sgtk = self._app.sgtk
        self._engine = self._app.engine
        self._context = self._app.context
        self._sg = self._app.shotgun


    def init_app_from_settings(self):
        # get the path setting for this platform:
        platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
        app_path = self._app.get_setting("%s_path" % platform_name, "")
        if not app_path:
            # no application path defined for this os. So don't register a menu item!
            return

        versions = self._app.get_setting("versions")
        menu_name = self._app.get_setting("menu_name")

        # get icon value, replacing tokens if needed
        icon = self._app.get_setting("icon")
        if icon.startswith("{target_engine}"):
            engine_name = self._app.get_setting("engine")
            if engine_name:
                engine_path = sgtk.platform.get_engine_path(engine_name, self._sgtk, self._context)
                if engine_path:
                    icon = icon.replace("{target_engine}", engine_path, 1)
                else:
                    # This can happen when an engine is configured in an environment that isn't
                    # supported on the current operating system.  Simply return an empty string.
                    icon = ""

            else:
                # This happens if there is no engine associated with the application being run.
                # Just return an empty string since using this syntax is invalid, but could
                # have been setup by running upgrades.
                icon = ""

        if icon.startswith("{config_path}"):
            config_path = self._sgtk.pipeline_configuration.get_config_location()
            if not config_path:
                raise TankError("No pipeline configuration path found for '{config_path}' replacement.")

            icon = icon.replace("{config_path}", config_path, 1)

        # and correct the separator
        icon = icon.replace("/", os.path.sep)

        # Initialize per version
        if versions:
            for version in versions:
                self._init_app_internal(icon, menu_name, version)
        else:
            # No replacements defined, just register with the raw values
            self._init_app_internal(icon, menu_name)

    def init_sg_software_apps(self, sg_software_entity=None):
        # Expand Software field names that rely on the current platform
        platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
        platform_fields = ["sg_%s_path", "sg_%s_args"]
        for i, field in enumerate(platform_fields):
            platform_fields[i] = field % platform_name
        app_path_field = platform_fields[0]
        app_args_field = platform_fields[1]

        # Determine the information to retrieve from SG
        sw_entity = sg_software_entity or "Software"
        sw_filters = [
            ["sg_status_list", "is", "act"],
        ]
        sw_fields = [
            "code",
            "image",
            "sg_engine",
            "sg_group_restrictions",
            "sg_projects",
            "sg_versions",
            "sg_user_restrictions",
        ]
        sw_fields.extend(platform_fields)

        # Get the list of Software apps that match the specified filters.
        sg_softwares = self._sg.find(sw_entity, sw_filters, sw_fields)
        if not sg_softwares:
            # No apps found matching filters, nothing to do.
            self._app.log_debug("No SG %s entities found matching filters : %s" %
                (sw_entity, sw_filters)
            )
            return

        # Get the list of Software apps to initialize. Filter out apps
        # with project/group/user restrictions that are not relevant to
        # the current context.
        ctx_user = self._context.user
        ctx_user_group_ids = []
        if ctx_user:
            sg_user = self._sg.find_one(
                ctx_user["type"], [["id", "is", ctx_user["id"]]], ["groups"]
            )
            ctx_user_group_ids = [grp["id"] for grp in (sg_user["groups"] or [])]

        ctx_project = self._context.project
        for app in sg_softwares:
            app_name = app["code"]

            # If no path has been set for the app, we will eventually go look for one,
            # but for now, don't load the app.
            if not app[app_path_field]:
                self._app.log_warning("No path specified for app [%s]." % app_name)
                continue

            # Resolve any env vars in the app path string and verify it exists
            resolved_app_path = os.path.expandvars(app[app_path_field])
            if not os.path.exists(resolved_app_path):
                self._app.log_warning("%s application path [%s] does not exist!" %
                    (app_name, resolved_app_path)
                )
                continue

            # If an engine name has been specified, make sure it has been loaded in 
            # the current environment.
            engine_name = app["sg_engine"]
            if engine_name not in self._engine.get_env().get_engines():
                self._app.log_warning("App engine %s is not loaded in the current environment." %
                    (engine_name)
                )
                continue

            # If there are Project restrictions, check if the current Project is one of them.
            app_project_ids = [proj["id"] for proj in (app["sg_projects"] or [])]
            if app_project_ids and (not ctx_project or ctx_project["id"] not in app_project_ids):
                self._app.log_debug(
                    "Context Project %s not found in Project restrictions for app [%s]." %
                    (ctx_project, app_name)
                )
                continue

            # If there are user restrictions, check if the current user is one of them.
            app_user_ids = [user["id"] for user in (app["sg_user_restrictions"] or [])]
            if app_user_ids and (not ctx_user or ctx_user["id"] not in app_user_ids):
                self._app.log_debug(
                    "Context user %s not found in user restrictions for app [%s]." %
                    (ctx_user, app_name)
                )
                continue

            # If there are group restrictions, check if the current user is in one of them.
            app_group_ids = [grp["id"] for grp in (app["sg_group_restrictions"] or [])]
            if app_group_ids and (not ctx_user_group_ids or 
                    not set(ctx_user_group_ids).intersection(app_group_ids)):
                self._app.log_debug(
                    "Context user %s is not a member of Group restrictions for app [%s]." %
                    (ctx_user, app_name)
                )
                continue

            # Download the thumbnail to use as the app's icon. The Software entity
            # may need to be requeried for the thumbnail here, since the AWS urls
            # tend to timeout quickly.
            app_icon = None
            if app["image"]:
                app_icon = shotgun_data.ShotgunDataRetriever.download_thumbnail(app["image"], self._app)
                self._app.log_info("App icon from ShotgunDataRetriever : %s" % app_icon)

            # Parse the Software versions field to determine the specific list of 
            # versions to load. Assume the list of versions is stored as a comma-separated
            # list in SG.
            menu_name = app_name
            if not menu_name.lower().startswith("launch"):
                menu_name = "Launch %s" % menu_name
            app_versions = []
            if app["sg_versions"]:
                app_versions = app["sg_versions"].split(",")
            for app_version in app_versions:
                self._init_app_internal(
                    app_icon, menu_name, app_version.strip() or None, engine_name, 
                    resolved_app_path, app[app_args_field]
                )
            else:
                self._init_app_internal(
                    app_icon, menu_name, None, engine_name, 
                    resolved_app_path, app[app_args_field]
                )

    def _init_app_internal(self, raw_icon, raw_menu_name, version=None, engine_name=None, app_path=None, app_args=None):
        # do the {version} replacement if needed
        icon = self._apply_version_to_setting(raw_icon, version)
        menu_name = self._apply_version_to_setting(raw_menu_name, version)

        # the command name mustn't contain spaces and funny chars, so sanitize it.
        # Also, should be nice for the shell engine.
        # "Launch NukeX..." -> launch_nukex
        command_name = menu_name.lower().replace(" ", "_")
        if command_name.endswith("..."):
            command_name = command_name[:-3]

        # special case! todo: fix this.
        # this is to allow this app to be loaded for sg entities of type publish
        # but not show up on the menu.
        # this is because typically, for published files, and versions, you want the app loaded
        # but you want to access it via the launch_from_path() method, normally
        # hooked up via a hook.
        if self._engine.environment.get("name") not in ["shotgun_tankpublishedfile",
                                                       "shotgun_publishedfile",
                                                       "shotgun_version"]:
            properties = { "title": menu_name,
                           "short_name": command_name,
                           "description": "Launches and initializes an application environment.",
                           "icon": icon,
                         }

            def launch_version():
                self.launch_from_entity(version, engine_name, app_path, app_args)
            self._engine.register_command(command_name, launch_version, properties)


    def launch_from_path_and_context(self, path, context, version=None):
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
            self.launch_from_path(path, version)
        else:
            # use given context to launch engine!
            self._launch_app(context, path, version=version)

    def launch_from_path(self, path, version=None):
        """
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic
        which is external to this app.
        """
        context = self._sgtk.context_from_path(path)
        self._launch_app(context, path, version=version)

    def launch_from_entity(self, version=None, engine_name=None, app_path=None, app_args=None):
        """
        Default app command. Launches an app based on the current context and settings.
        """
        # extract a entity_type and id from the context.
        if self._context.project is None:
            raise TankError("Your context does not have a project defined. Cannot continue.")

        # first do project
        entity_type = self._context.project["type"]
        entity_id = self._context.project["id"]
        # if there is an entity then that takes precedence
        if self._context.entity:
            entity_type = self._context.entity["type"]
            entity_id = self._context.entity["id"]
        # and if there is a task that is even better
        if self._context.task:
            entity_type = self._context.task["type"]
            entity_id = self._context.task["id"]

        # Now do the folder creation. By default, use
        # the engine name as the defer keyword
        defer_keyword = engine_name or self._app.get_setting("engine")
        
        # if there is a specific defer keyword, this takes precedence
        if self._app.get_setting("defer_keyword"):
            defer_keyword = self._app.get_setting("defer_keyword")
        
        try:
            self._app.log_debug("Creating folders for %s %s. Defer keyword: '%s'" % (entity_type, entity_id, defer_keyword))
            self._sgtk.create_filesystem_structure(entity_type, entity_id, engine=defer_keyword)
        except sgtk.TankError, err:
            raise TankError("Could not create folders on disk. Error reported: %s" % err)

        self._launch_app(
            self._context, version=version, engine_name=engine_name, 
            app_path=app_path, app_args=app_args
        )

    def _get_clean_version_string(self, version):
        """
        Returns version string used for current app launch stripped of any ()'s defining 
        additional version tokens. For example, if the version setting is "(8.4)v6" this will 
        return "8.4v6"

        :param version: version of the application being launched specified by the value from 
                        'versions' settings. If no 'versions' were defined in the settings, then 
                        this will be None.
        """
        if version is None:
            return None
        clean_version = re.sub('[()]', '', version)
        return clean_version

    def _translate_version_tokens(self, raw_string, version):
        """
        Returns string with version tokens replaced by their values. Replaces 
        {version} and {v0}, {v1}, etc. tokens in raw_string with their values. The {v} 
        tokens are created by using groups defined by () within the version string.
        For example, if the version setting is "(9.0)v4(beta1)"
            {version} = "9.0v4"
            {v0} = "9.0"
            {v1} = "beta1" 
        :param raw_string: raw string with un-translated tokens 
        :param version: version string to use for replacement tokens
        """
        # split version string into tokens defined by ()s
        version_tokens = re.findall(r"\(([^\)]+)\)", version)
        # ensure we have a clean complete version string without ()s
        clean_version = self._get_clean_version_string(version)
        # do the substitution
        string = raw_string.replace("{version}", clean_version)
        for i, token in enumerate(version_tokens):
            string = string.replace("{v%d}" % i, token)
        return string

    def _apply_version_to_setting(self, raw_string, version=None):
        """
        Replace any version tokens  contained in the raw_string with the appropriate version value from 
        the app settings. 

        If version is None, then no version has been specified and we will return the first version 
        from the versions list in the settings. If no versions have been defined in the settings, then 
        we return the raw_string since there's no replacement to do.
        
        :param raw_string: the raw string potentially containing the version tokens (eg. {version}, 
                           {v0}, ...) we will be replacing. This string could represent a number of 
                           things including a path, an args string, etc. 
        :param version: version string to use for the token replacement. 
        :returns: string with version tokens replaced with their appropriate values
        """
        if version is None:
            # there are two reasons version could be None
            # 1. if versions have not been configured, the raw string is assumed valid
            # 2. if versions has been configured, but no specific version was requested, then we 
            #    expand with the first element in the versions list, and use it as the default
            versions = self._app.get_setting("versions")
            if versions:
                return self._translate_version_tokens(raw_string, versions[0])
            else:
                return raw_string
        else:
            return self._translate_version_tokens(raw_string, version)

    def _get_app_path(self, version=None, raw_app_path=None):
        """ Return the platform specific app path, performing version substitution. """
        if not raw_app_path:
            platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
            raw_app_path = self._app.get_setting("%s_path" % platform_name, "")
        
        return self._apply_version_to_setting(raw_app_path, version)

    def _get_app_args(self, version=None, raw_app_args=None):
        """ Return the platform specific app path, performing version substitution. """
        if not raw_app_args:
            platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
            raw_app_args = self._app.get_setting("%s_args" % platform_name, "")
        
        return self._apply_version_to_setting(raw_app_args, version)

    def _launch_app(self, context, file_to_open=None, version=None, engine_name=None, app_path=None, app_args=None):
        """
        Launches an application. No environment variable change is leaked to the outside world.
        :param context: Toolkit context we will opening the app in.
        :param file_to_open: Optional file to open when the app launches. Can be None.
        :param version: Version of the app to launch. Specifying None means the default version will
                        be picked.
        """
        try:
            # Clone the environment variables
            environ_clone = os.environ.copy()
            sys_path_clone = list(sys.path)
            self._launch_app_internal(context, file_to_open, version, engine_name, app_path, app_args)
        finally:
            # Clear the original structures and add into them so that users who did
            # from os import environ and from sys import path get the restored values.
            os.environ.clear()
            os.environ.update(environ_clone)
            del sys.path[:]
            sys.path.extend(sys_path_clone)

    def _launch_app_internal(self, context, file_to_open=None, version=None, engine_name=None, app_path=None, app_args=None):
        """
        Launches an application. This method may have side-effects in the environment variables table.
        Call the _launch_app method instead.
        :param context: Toolkit context we will opening the app in.
        :param file_to_open: Optional file to open when the app launches. Can be None.
        :param version: Version of the app to launch. Specifying None means the default version will
                        be picked.
        """
        # get the executable path
        app_path = self._get_app_path(version, app_path)
        # get the app args:
        app_args = self._get_app_args(version, app_args)

        engine_name = engine_name or self._app.get_setting("engine")
        if engine_name:

            # we have an engine we should start as part of this app launch
            # pass down the file to open into the startup script via env var.
            if file_to_open:
                os.environ["TANK_FILE_TO_OPEN"] = file_to_open
                self._app.log_debug("Setting TANK_FILE_TO_OPEN to '%s'" % file_to_open)

            # serialize the context into an env var
            os.environ["TANK_CONTEXT"] = sgtk.context.serialize(context)
            self._app.log_debug("Setting TANK_CONTEXT to '%r'" % context)

            # Set environment variables used by apps to prep Tank engine
            os.environ["TANK_ENGINE"] = engine_name

            # Prep any application specific things now that we know we don't
            # have an engine-specific bootstrap to use.
            if engine_name == "tk-maya":
                self.prepare_maya_launch(app_path)
            elif engine_name == "tk-softimage":
                self.prepare_softimage_launch()
            elif engine_name == "tk-motionbuilder":
                app_args = self.prepare_motionbuilder_launch(app_args)
            elif engine_name == "tk-3dsmax":
                app_args = self.prepare_3dsmax_launch(app_args)
            elif engine_name == "tk-3dsmaxplus":
                app_args = self.prepare_3dsmaxplus_launch(context, app_args, app_path)
            elif engine_name == "tk-photoshop":
                self.prepare_photoshop_launch(context)
            elif engine_name == "tk-houdini":
                self.prepare_houdini_launch(context)
            elif engine_name == "tk-mari":
                self.prepare_mari_launch(engine_name, context)
            elif engine_name in ["tk-flame", "tk-flare"]:
                (app_path, app_args) = self.prepare_flame_flare_launch(
                    engine_name,
                    context,
                    app_path,
                    app_args,
                )
            else:
                # This should really be the first thing we try, but some of
                # the engines (like tk-3dsmaxplus, as an example) have bootstrapping
                # logic that doesn't properly stand alone and still requires
                # their "prepare" method here in launchapp to be run. As engines
                # are updated to handle all their own bootstrapping, they can be
                # pulled out from above and moved into the except block below in
                # the way that tk-nuke and tk-hiero have.
                try:
                    (app_path, app_args) = self.prepare_generic_launch(
                        engine_name,
                        context,
                        app_path,
                        app_args,
                    )
                except TankBootstrapNotFoundError:
                    # Backwards compatibility here for earlier engine versions.
                    if engine_name == "tk-nuke":
                        app_args = self.prepare_nuke_launch(file_to_open, app_args)
                    elif engine_name == "tk-hiero":
                        self.prepare_hiero_launch()
                    else:
                        # We have neither an engine-specific nor launchapp-specific
                        # bootstrap for this engine, so we have to bail out here.
                        raise TankError(
                            "No bootstrap routine found for %s. The engine will not be started." % engine_name
                        )

        version_string = self._get_clean_version_string(version)
        # run before launch hook
        self._app.log_debug("Running before app launch hook...")
        self._app.execute_hook("hook_before_app_launch", app_path=app_path, app_args=app_args, 
                               version=version_string)

        # Ticket 26741: Avoid having odd DLL loading issues on windows
        # Desktop PySide sets an explicit DLL path, which is getting inherited by subprocess. 
        # The following undoes that to make sure that apps that depend on not having a DLL path are set work properly
        self._clear_dll_directory()

        try:
            # Launch the application
            self._app.log_debug("Launching executable '%s' with args '%s'" % (app_path, app_args))
            result = self._app.execute_hook(
                "hook_app_launch", app_path=app_path, app_args=app_args, version=version_string
            )
            cmd = result.get("command")
            return_code = result.get("return_code")
        finally:
            self._restore_dll_directory()

        self._app.log_debug("Hook tried to launch '%s'" % cmd)
        if return_code != 0:
            
            # some special logic here to decide how to display failure feedback 
            
            if self._engine.name == "tk-shotgun":
                # for the shotgun engine, use the log info in order to get the proper
                # html formatting
                self._app.log_info("<b>Failed to launch application!</b> "
                              "This is most likely because the path "
                              "is not set correctly. The command that was used to attempt to launch is '%s'. "
                              "<br><br><a href='%s' target=_new>Click here</a> to learn more about how to set "
                              "up your app launch configuration." % (cmd, self.HELP_DOC_URL))
            
            
            elif self._engine.has_ui:
                # got UI support. Launch dialog with nice message
                not_found_dialog = self._app.import_module("not_found_dialog")                
                not_found_dialog.show_path_error_dialog(self, cmd)                
            
            else:
                # traditional non-ui environment without any html support.
                self._app.log_error("Failed to launch application! This is most likely because the path "
                              "is not set correctly. The command that was used to attempt to launch is '%s'. "
                              "To learn more about how to set up your app launch configuration, "
                              "see the following documentation: %s" % (cmd, self.HELP_DOC_URL))
                

        else:
            # Write an event log entry
            self._register_event_log(context, cmd, version)

    def _clear_dll_directory(self):
        """
        Push current Dll Directory

        There are two cases that can happen related to setting a dll directory.
        
        1: Project is using different python then Desktop, in which case the desktop will set the dll 
           directory to none for the project's python interpreter. In this case, the following code is
           redundant and not needed.
        2: Desktop is using same python as Project. In which case we need to keep the desktop dll directory.
        """
        if sys.platform == "win32":
            # This 'try' block will fail silently if user is using a different python interpreter then Desktop,
            # in which case it will be fine since the Desktop will have set the correct Dll folder for this 
            # interpreter. Refer to the comments in the method's header for more information.
            try:
                import win32api

                # GetDLLDirectory throws an exception if none was set
                try:
                    self._previous_dll_directory = win32api.GetDllDirectory(None)
                except StandardError:
                    self._previous_dll_directory = None
                
                win32api.SetDllDirectory(None)
            except StandardError:
                pass
            
    def _restore_dll_directory(self):
        """
        Pop the previously pushed DLL Directory
        """
        if sys.platform == "win32":
            # This may fail silently, which is the correct behavior. Refer to the comments in 
            # _clear_dll_directory for additional information.
            try:
                import win32api
                win32api.SetDllDirectory(self._previous_dll_directory)
            except StandardError:
                pass

    def _register_event_log(self, ctx, command_executed, version=None):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch
        """
        menu_name = self._app.get_setting("menu_name")
        if version is not None:
            menu_name = menu_name.replace("{version}", version)

        meta = {}
        meta["core"] = self._sgtk.version
        meta["engine"] = "%s %s" % (self._engine.name, self._engine.version)
        meta["app"] = "%s %s" % (self._app.name, self._app.version)
        meta["launched_engine"] = self._app.get_setting("engine")
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc =  "%s %s: %s" % (self._app.name, self._app.version, menu_name)
        sgtk.util.create_event_log_entry(self._sgtk, ctx, "Toolkit_App_Startup", desc, meta)

    def prepare_generic_launch(self, engine_name, context, app_path, app_args):
        """
        Generic engine launcher.

        This method will look for a bootstrap method in the engine's
        python/startup/bootstrap.py file if it exists.  That bootstrap will be
        called if possible.

        :param engine_name: The name of the engine being launched
        :param context: The context that the application is being launched in
        :param app_path: Path to DCC executable or launch script
        :param app_args: External app arguments

        :returns: extra arguments to pass to launch
        """
        # find the path to the engine on disk where the startup script can be found:
        engine_path = sgtk.platform.get_engine_path(engine_name, self._sgtk, context)
        if engine_path is None:
            raise TankError(
                "Could not find the path to the '%s' engine. It may not be configured "
                "in the environment for the current context ('%s')." % (engine_name, str(context)))

        # find bootstrap file located in the engine and load that up
        startup_path = os.path.join(engine_path, "python", "startup", "bootstrap.py")

        if not os.path.exists(startup_path):
            raise TankBootstrapNotFoundError(
                "Could not find the bootstrap for the '%s' engine at '%s'" % (
                    engine_name, startup_path
                )
            )

        python_path = os.path.dirname(startup_path)

        # add our bootstrap location to the pythonpath
        sys.path.insert(0, python_path)
        try:
            import bootstrap
            extra_args = self._app.get_setting("extra", {})

            # bootstrap should take kwargs in order to protect from changes in
            # this signature in the future.  For example:
            # def bootstrap(engine, context, app_path, app_args, **kwargs)
            (app_path, new_args) = bootstrap.bootstrap(
                engine_name=engine_name,
                context=context,
                app_path=app_path,
                app_args=app_args,
                extra_args=extra_args,
            )
        except Exception:
            self._app.log_exception("Error executing engine bootstrap script.")
            raise TankError("Error executing bootstrap script. Please see log for details.")
        finally:
            # Remove bootstrap from sys.path
            sys.path.pop(0)

            # We also need to unload the bootstrap module so that any
            # subsequent launches that import a different bootstrap
            # will succeed.
            if "bootstrap" in sys.modules:
                self._app.log_debug("Removing 'bootstrap' from sys.modules.")
                del sys.modules["bootstrap"]

        return (app_path, new_args)

    def prepare_nuke_launch(self, file_to_open, app_args):
        """
        Nuke specific pre-launch environment setup.
        """
        # Make sure Nuke can find the Tank menu
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("nuke"), "startup"))
        sgtk.util.append_path_to_env_var("NUKE_PATH", startup_path)

        # it's not possible to open a nuke script from within the initialization
        # scripts so if we have a path then we need to pass it through the start
        # up args:
        if file_to_open:
            if app_args:
                app_args = "%s %s" % (file_to_open, app_args)
            else:
                app_args = file_to_open

        return app_args

    def prepare_hiero_launch(self):
        """
        Hiero specific pre-launch environment setup.
        """
        startup_path = os.path.abspath(os.path.join(self._get_app_specific_path("hiero"), "startup"))
        sgtk.util.append_path_to_env_var("HIERO_PLUGIN_PATH", startup_path)

    def prepare_maya_launch(self, app_path):
        """
        Maya specific pre-launch environment setup.
        """
        # Make sure Maya can find the Tank menu
        app_specific_path = self._get_app_specific_path("maya")
        startup_path = os.path.abspath(os.path.join(app_specific_path, "startup"))
        sgtk.util.append_path_to_env_var("PYTHONPATH", startup_path)

    def prepare_softimage_launch(self):
        """
        Softimage specific pre-launch environment setup.
        """
        # add the startup plug-in to the XSI_PLUGINS path:
        xsi_plugins = os.path.abspath(os.path.join(self._get_app_specific_path("softimage"), "startup", "Application", "Plugins"))
        sgtk.util.append_path_to_env_var("XSI_PLUGINS", xsi_plugins)

        # On Linux, Softimage 2013 is missing libssl and sqlite3 libraries.  We have some that
        # we think will work so lets _append_ them to the LD_LIBRARY_PATH & PYTHONPATH before
        # launching Softimage.  Note, these can be overriden by specifying a location earlier
        # in the LD_LIBRARY_PATH & PYTHONPATH if needed
        if sys.platform == "linux2":
            # Note: we can't reliably check the version as the path on linux
            # is typically just 'xsi'.  This may become a problem if we start
            # to support 2014 and beyond...
            #
            # if "Softimage_2013" in self._app_path:
            lib_path = os.path.abspath(os.path.join(self._get_app_specific_path("softimage"), "linux", "lib"))
            sgtk.util.append_path_to_env_var("LD_LIBRARY_PATH", lib_path)
            sgtk.util.append_path_to_env_var("PYTHONPATH", lib_path)

    def prepare_motionbuilder_launch(self, app_args):
        """
        Maya specific pre-launch environment setup.
        """
        new_args = "\"%s\"" % os.path.join(self._get_app_specific_path("motionbuilder"), "startup", "init_tank.py")

        if app_args:
            app_args = "%s %s" % (app_args, new_args)
        else:
            app_args = new_args

        return app_args

    def prepare_3dsmax_launch(self, app_args):
        """
        3DSMax specific pre-launch environment setup.

        Make sure launch args include a maxscript to load the python engine:
        3dsmax.exe somefile.max -U MAXScript somescript.ms
        """
        startup_dir = os.path.abspath(os.path.join(self._get_app_specific_path("3dsmax"), "startup"))
        os.environ["TANK_BOOTSTRAP_SCRIPT"] = os.path.join(startup_dir, "tank_startup.py")

        new_args = "-U MAXScript \"%s\"" % os.path.join(startup_dir, "init_tank.ms")

        if app_args:
            app_args = "%s %s" % (new_args, app_args)
        else:
            app_args = new_args

        return app_args


    def prepare_3dsmaxplus_launch(self, context, app_args, app_path):
        """
        3DSMax Plus specific pre-launch environment setup.

        Make sure launch args include a bootstrap to load the python engine:
        3dsmax.exe somefile.max -U PythonHost somescript.py
        """
        engine_path = sgtk.platform.get_engine_path("tk-3dsmaxplus", self._sgtk, context)

        if engine_path is None:
            raise TankError("Path to 3dsmaxplus engine (tk-3dsmaxplus) could not be found.")

        # This is a fix for PySide problems in 2017+ versions of Max. Now that
        # Max ships with a full install of PySide, we need to ensure that dlls
        # for the native Max install are sourced. If we don't do this, we end
        # up with dlls loaded from SG Desktop's bin and we have a mismatch that
        # results in complete breakage.
        max_root = os.path.dirname(app_path)
        sgtk.util.prepend_path_to_env_var("PATH", max_root)

        startup_file = os.path.abspath(os.path.join(engine_path, "python", "startup", "bootstrap.py"))
        new_args = "-U PythonHost \"%s\"" % startup_file

        if app_args:
            app_args = "%s %s" % (new_args, app_args)
        else:
            app_args = new_args

        return app_args

    def prepare_houdini_launch(self, context):
        """
        Houdini specific pre-launch environment setup.
        """
        engine_path = sgtk.platform.get_engine_path("tk-houdini", self._sgtk, context)
        if engine_path is None:
            raise TankError("Path to houdini engine (tk-houdini) could not be found.")

        # let the houdini engine take care of initializing itself
        sys.path.append(os.path.join(engine_path, "python"))
        try:
            import tk_houdini
            tk_houdini.bootstrap.bootstrap(self._sgtk, context)
        except:
            self._app.log_exception("Error executing engine bootstrap script.")
            raise TankError("Error executing bootstrap script. Please see log for details.")

    def prepare_flame_flare_launch(self, engine_name, context, app_path, app_args):
        """
        Flame specific pre-launch environment setup.

        :param engine_name: The name of the engine being launched (tk-flame or tk-flare)
        :param context: The context that the application is being launched in
        :param app_path: Path to DCC executable or launch script
        :param app_args: External app arguments
        
        :returns: extra arguments to pass to launch
        """
        # find the path to the engine on disk where the startup script can be found:
        engine_path = sgtk.platform.get_engine_path(engine_name, self._sgtk, context)
        if engine_path is None:
            raise TankError("Path to '%s' engine could not be found." % engine_name)
        
        # find bootstrap file located in the engine and load that up
        startup_path = os.path.join(engine_path, "python", "startup", "bootstrap.py")
        
        if not os.path.exists(startup_path):
            raise Exception("Cannot find bootstrap script '%s'" % startup_path)        
        
        python_path = os.path.dirname(startup_path)
        
        # add our bootstrap location to the pythonpath
        sys.path.insert(0, python_path)
        try:
            import bootstrap
            (app_path, new_args) = bootstrap.bootstrap(engine_name, context, app_path, app_args)            
            
        except Exception, e:
            self._app.log_exception("Error executing engine bootstrap script.")
            
            if self._engine.has_ui:
                # got UI support. Launch dialog with nice message
                not_found_dialog = self._app.import_module("not_found_dialog")                
                not_found_dialog.show_generic_error_dialog(self, str(e))
            
            raise TankError("Error executing bootstrap script. Please see log for details.")
        finally:
            # remove bootstrap from sys.path
            sys.path.pop(0)
        
        return (app_path, new_args)

    def prepare_mari_launch(self, engine_name, context):
        """
        Mari specific pre-launch environment setup.

        :param engine_name: The name of the Mari engine being launched
        :param context:     The context that the application is being launched in
        """
        # find the path to the engine on disk where the startup script
        # can be found:
        engine_path = sgtk.platform.get_engine_path(engine_name, self._sgtk, context)
        if engine_path is None:
            raise TankError("Path to '%s' engine could not be found." % engine_name)
        
        # add the location of our init.py script to the MARI_SCRIPT_PATH
        startup_folder = os.path.join(engine_path, "startup")
        sgtk.util.append_path_to_env_var("MARI_SCRIPT_PATH", startup_folder)
        
    def prepare_photoshop_launch(self, context):
        """
        Photoshop specific pre-launch environment setup.
        """
        engine_path = sgtk.platform.get_engine_path("tk-photoshop", self._sgtk, context)
        if engine_path is None:
            raise TankError("Path to photoshop engine (tk-photoshop) could not be found.")

        # if the photoshop engine has the bootstrap logic with it, run it from there
        startup_path = os.path.join(engine_path, "bootstrap")
        env_setup = os.path.join(startup_path, "photoshop_environment_setup.py")
        if os.path.exists(env_setup):
            sys.path.append(startup_path)
            try:
                import photoshop_environment_setup
                photoshop_environment_setup.setup(self, context)
            except:
                self._app.log_exception("Error executing engine bootstrap script.")
                raise TankError("Error executing bootstrap script. Please see log for details.")

            return

        # no bootstrap logic with the engine, run the legacy version
        extra_configs = self._app.get_setting("extra", {})

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
        sgtk.util.append_path_to_env_var("PYTHONPATH", startup_path)


    def _get_app_specific_path(self, app_dir):
        """
        Get the path for application specific files for a given application.
        """

        return os.path.join(self._app.disk_location, "app_specific", app_dir)


##########################################################################################
# Exceptions

class TankBootstrapNotFoundError(TankError):
    """
    Exception raised when an engine-specific bootstrap routine is not
    found.
    """
    pass
