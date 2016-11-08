# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import re
import sys

import sgtk
from sgtk import TankError

from .prepare_apps import prepare_launch_for_engine

shotgun_data = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_data")

class BaseLauncher(object):
    # documentation explaining how to reconfigure app paths
    HELP_DOC_URL = "https://support.shotgunsoftware.com/entries/95443887#Setting%20up%20Application%20Paths"

    def __init__(self):
        # Retrieve the TK Application from the current bundle and
        # set some useful "shorthand" members.
        self._app = sgtk.platform.current_bundle()
        self._sgtk = self._app.sgtk
        self._engine = self._app.engine
        self._context = self._app.context
        self._sg = self._app.shotgun

        self._app_engine_name = None
        self._app_path = None
        self._app_args = None
        self._app_versions = None
        self._app_icon = None
        self._app_menu_name = None

    def _init_app_command(self, version=None):
        # do the {version} replacement if needed
        icon = self._apply_version_to_setting(self._app_icon, version)
        menu_name = self._apply_version_to_setting(self._app_menu_name, version)

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
                self.launch_from_entity(version)
            self._engine.register_command(command_name, launch_version, properties)

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
        Replace any version tokens contained in the raw_string with the 
        appropriate version value from the app settings. 

        If version is None, we return the raw_string since there's 
        no replacement to do.
        
        :param raw_string: the raw string potentially containing the 
                           version tokens (eg. {version}, {v0}, ...) we 
                           will be replacing. This string could represent 
                           a number of things including a path, an args 
                           string, etc. 
        :param version: version string to use for the token replacement. 

        :returns: string with version tokens replaced with their appropriate values
        """
        if version:
            return self._translate_version_tokens(raw_string, version)
        return raw_string

    def _launch_app(self, context, file_to_open=None, version=None):
        """
        Launches an application. No environment variable change is 
        leaked to the outside world.

        :param context: Toolkit context we will opening the app in.
        :param file_to_open: Optional file to open when the app 
                             launches. Can be None.
        :param version: Version of the app to launch. Specifying None 
                        means no {version} substitutions will take place.
        """
        try:
            # Clone the environment variables
            environ_clone = os.environ.copy()
            sys_path_clone = list(sys.path)

            # get the executable path
            app_path = self._apply_version_to_setting(self._app_path, version)
            # get the app args:
            app_args = self._apply_version_to_setting(self._app_args, version)

            if self._engine_name:
                prepare_launch_for_engine(
                    self._engine_name, context, file_to_open, app_path, app_args,
                )

            version_string = self._get_clean_version_string(version)

            # run before launch hook
            self._app.log_debug("Running before app launch hook...")
            self._app.execute_hook(
                "hook_before_app_launch", app_path=app_path, 
                app_args=app_args, version=version_string
            )

            # Ticket 26741: Avoid having odd DLL loading issues on windows
            # Desktop PySide sets an explicit DLL path, which is getting 
            # inherited by subprocess. The following undoes that to make 
            # sure that apps that depend on not having a DLL path are set 
            # work properly
            self._clear_dll_directory()

            try:
                # Launch the application
                self._app.log_debug("Launching executable '%s' with args '%s'" % 
                    (app_path, app_args)
                )
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
                    self._app.log_info(
                        "<b>Failed to launch application!</b> "
                        "This is most likely because the path is not set correctly."
                        "The command that was used to attempt to launch is '%s'. "
                        "<br><br><a href='%s' target=_new>Click here</a> to learn more about "
                        "how to setup your app launch configuration." % 
                        (cmd, self.HELP_DOC_URL)
                    )

                elif self._engine.has_ui:
                    # got UI support. Launch dialog with nice message
                    not_found_dialog = self._app.import_module("not_found_dialog")                
                    not_found_dialog.show_path_error_dialog(self._app, cmd)                

                else:
                    # traditional non-ui environment without any html support.
                    self._app.log_error(
                        "Failed to launch application! This is most likely because the path "
                        "is not set correctly. The command that was used to attempt to launch "
                        "is '%s'. To learn more about how to set up your app launch "
                        "configuration, see the following documentation: %s" % 
                        (cmd, self.HELP_DOC_URL)
                    )
                    
            else:
                # Write an event log entry
                self._register_event_log(context, cmd, version)

        finally:
            # Clear the original structures and add into them so 
            # that users who did from os import environ and from 
            # sys import path get the restored values.
            os.environ.clear()
            os.environ.update(environ_clone)
            del sys.path[:]
            sys.path.extend(sys_path_clone)

    def _clear_dll_directory(self):
        """
        Push current Dll Directory

        There are two cases that can happen related to setting a dll directory.
        
        1: Project is using different python then Desktop, in which case the 
           desktop will set the dll directory to none for the project's python 
           interpreter. In this case, the following code is redundant and not needed.
        2: Desktop is using same python as Project. In which case we need to keep 
           the desktop dll directory.
        """
        if sys.platform == "win32":
            # This 'try' block will fail silently if user is using a different 
            # python interpreter then Desktop, in which case it will be fine 
            # since the Desktop will have set the correct Dll folder for this 
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
            # This may fail silently, which is the correct behavior. Refer to the 
            # comments in _clear_dll_directory for additional information.
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
        meta["launched_engine"] = self._engine_name
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc =  "%s %s: %s" % (self._app.name, self._app.version, menu_name)
        sgtk.util.create_event_log_entry(self._sgtk, ctx, "Toolkit_App_Startup", desc, meta)

    def launch_app_from_entity(self, version=None):
        """
        Default method to launch DCC application command based on the current context
        and resolved settings.
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

        # Now do the folder creation.  If there is a specific defer keyword, this takes
        # precedence. Otherwise, use the engine name for the DCC application by default.
        defer_keyword = self._app.get_setting("defer_keyword") or self._engine_name

        try:
            self._app.log_debug("Creating folders for %s %s. Defer keyword: '%s'" % 
                (entity_type, entity_id, defer_keyword)
            )
            self._sgtk.create_filesystem_structure(entity_type, entity_id, engine=defer_keyword)
        except sgtk.TankError, err:
            raise TankError("Could not create folders on disk. Error reported: %s" % err)

        self._launch_app(self._context, version=version)


class SingleConfigLauncher(BaseLauncher):
    """
    Originally from _apply_version_to_setting:
        if version is None:
            # there are two reasons version could be None
            # 1. if versions have not been configured, the raw string is 
            #    assumed valid
            # 2. if versions has been configured, but no specific version 
            #    was requested, then we expand with the first element in 
            #    the versions list, and use it as the default
            versions = self._app.get_setting("versions")
            if versions:
                return self._translate_version_tokens(raw_string, versions[0])
            else:
                return raw_string

    Originally from _get_app_args:
        if not raw_app_args:
            platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
            raw_app_args = self._app.get_setting("%s_args" % platform_name, "")
    """

    def init_from_settings(self):
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


class SoftwareEntityLauncher(BaseLauncher):

    def init_from_shotgun(self):
        # Expand Software field names that rely on the current platform
        platform_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[sys.platform]
        platform_fields = ["sg_%s_path", "sg_%s_args"]
        for i, field in enumerate(platform_fields):
            platform_fields[i] = field % platform_name
        app_path_field = platform_fields[0]
        app_args_field = platform_fields[1]

        # Determine the information to retrieve from SG
        sg_software_entity = self._app.get_setting("sg_software_entity")
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

        # Record what Groups the current context user is a member of
        ctx_user = self._context.user
        ctx_user_group_ids = []
        if ctx_user:
            sg_user = self._sg.find_one(
                ctx_user["type"], [["id", "is", ctx_user["id"]]], ["groups"]
            )
            ctx_user_group_ids = [grp["id"] for grp in (sg_user["groups"] or [])]

        ctx_project = self._context.project
        for app in sg_softwares:
            # Get the list of Software apps to initialize. Filter out apps
            # with project/group/user restrictions that are not relevant to
            # the current context.
            app_name = app["code"]

            # If no path has been set for the app, we will eventually go look for one,
            # but for now, don't load the app.
            if not app[app_path_field]:
                self._app.log_warning("No path specified for app [%s]." % app_name)
                continue

            # Resolve any env vars in the app path string and verify it exists
            resolved_app_path = app[app_path_field] 
            #resolved_app_path = os.path.expandvars(app[app_path_field])
            #if not os.path.exists(resolved_app_path):
            #    self._app.log_warning("%s application path [%s] does not exist!" %
            #        (app_name, resolved_app_path)
            #    )
            #    continue

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
                app_icon = shotgun_data.ShotgunDataRetriever.download_thumbnail(
                    app["image"], self._app
                )
                self._app.log_debug("App icon from ShotgunDataRetriever : %s" % app_icon)

            # Prepend "Launch" to the application name to produce a familiar
            # menu/command name
            menu_name = app_name
            if not menu_name.lower().startswith("launch"):
                menu_name = "Launch %s" % menu_name

            # Parse the Software versions field to determine the specific list of
            # versions to load. Assume the list of versions is stored as comma-separated
            # in SG.
            app_versions = []
            if app["sg_versions"]:
                app_versions = app["sg_versions"].split(",")
            for app_version in app_versions:
                app_version = app_version.strip()
                if not app_version : continue
                use_menu_name = menu_name
                if app_version not in menu_name:
                    use_menu_name = "%s %s" % (menu_name, app_version)
                use_app_path = resolved_app_path.replace("{version}", app_version)

                self._app.log_info("\n\nuse menu name : %s" % use_menu_name)
                self._app.log_info("app version : %s" % app_version)
                self._app.log_info("use app path : %s" % use_app_path)
                self._init_app_internal(
                    app_icon, use_menu_name, app_version or None, engine_name, 
                    use_app_path, app[app_args_field]
                )
            else:
                self._app.log_info("\n\nmenu name : %s" % menu_name)
                self._app.log_info("resolved app path : %s" % resolved_app_path)
                if "{version}" not in resolved_app_path:
                    self._init_app_internal(
                        app_icon, menu_name, None, engine_name, 
                        resolved_app_path, app[app_args_field]
                    )
