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
        # Retrieve the TK Application from the current bundle
        self._tk_app = sgtk.platform.current_bundle()

        # Store the current platform value
        self._platform_name = {
            "linux2": "linux", "darwin": "mac", "win32": "windows"
        }[sys.platform]

        # Initialize DCC information used during the launch process
        self._set_app_info(None, None, None, None, None)

    def _set_app_info(self, menu_name, app_engine, app_path, app_args, app_version):
        """
        Register information required to successfully launch the DCC

        :param menu_name: Menu name displayed to launch this DCC.
        :param app_engine: The TK engine associated with the DCC to be launched.
        :param app_path: Full path to the DCC. May contain environment variables
                         and/or the locally supported {version}, {v0}, {v1}, ...
                         variables.
        :param app_args: Args string to pass to the DCC at launch time.
        :param app_version: Specific version of DCC to launch. Used to parse
                            {version}, {v0}, {v1}, ... information from.
        """
        self._menu_name = menu_name
        self._app_engine = app_engine
        self._app_path = app_path
        self._app_args = app_args
        self._app_version = app_version

    def _init_launch_command(self, app_menu_name, app_icon, app_engine, app_path, app_args, version=None):
        """
        Register a launch command with the current engine.

        :param app_menu_name: Menu name to display to launch this DCC. This is
                              also used to construct the associated command name.
        :param app_icon: Icon to display for this DCC
        :param app_engine: The TK engine associated with the DCC to be launched
        :param app_path: Full path name to the DCC. This may contain environment
                         variables and/or the locally supported {version}, {v0},
                         {v1}, ... variables
        :param app_args: Args string to pass to the DCC at launch time
        :param version: (Optional) Specific version of DCC to use.
        """
        # Resolve the input path to the application to launch. Verify that
        # it exists before creating a launch command.
        app_path = os.path.expandvars(
            _apply_version_to_setting(app_path, version)
        )
        if not os.path.exists(app_path):
            self._tk_app.log_warning("%s application path [%s] does not exist!" %
                (app_name, app_path)
            )
            return

        # do the {version} replacement if needed
        icon = _apply_version_to_setting(app_icon, version)
        menu_name = _apply_version_to_setting(app_menu_name, version)

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
        skip_environments = [
            "shotgun_tankpublishedfile",
            "shotgun_publishedfile",
            "shotgun_version",
        ]
        if self._tk_app.engine.environment.get("name") not in skip_environments:
            properties = { "title": menu_name,
                           "short_name": command_name,
                           "description": "Launches and initializes an application environment.",
                           "icon": icon,
                         }
            def launch_version():
                self.launch_app_from_entity(menu_name, app_engine, app_path, app_args, version)

            self._tk_app.engine.register_command(command_name, launch_version, properties)

    def _launch_app(self, context=None, file_to_open=None, version=None):
        """
        Launches an application. No environment variable change is
        leaked to the outside world.

        :param context: (Optional) Toolkit context to open the app in.
        :param file_to_open: (Optional) File to open when the app launches.
        :param version: (Optional) Version of the app to launch. Specifying
                        None means no {version} substitutions will take place.
        """
        # If no context has been specified, use the current TK Application's.
        context = context or self._tk_app.context

        # Record the new version, if specified.
        if version:
            self._app_version = version

        try:
            # Clone the environment variables
            environ_clone = os.environ.copy()
            sys_path_clone = list(sys.path)

            # Get the executable path path and args. Adjust according to
            # the relevant engine.
            app_path = _apply_version_to_setting(self._app_path, self._app_version)
            app_args = _apply_version_to_setting(self._app_args, self._app_version)
            if self._app_engine:
                (prepped_path, prepped_args) = prepare_launch_for_engine(
                    self._app_engine, app_path, app_args, context, file_to_open
                )
                # QUESTION: Since *some* of the "prep" methods may modify the app_path
                # and app_args values (e.g. _prepare_flame_flare_launch), should
                # they be reset here like this? (This is not what it does currently)
                app_path = prepped_path or app_path
                app_args = prepped_args or app_args

            version_string = _get_clean_version_string(self._app_version)

            # run before launch hook
            self._tk_app.log_debug("Running before app launch hook...")
            self._tk_app.execute_hook(
                "hook_before_app_launch", app_path=app_path,
                app_args=app_args, version=version_string
            )

            # Ticket 26741: Avoid having odd DLL loading issues on windows
            # Desktop PySide sets an explicit DLL path, which is getting
            # inherited by subprocess. The following undoes that to make
            # sure that apps depending on not having a DLL path are set
            # to work properly
            dll_directory_cache = _clear_dll_directory()
            try:
                # Launch the application
                self._tk_app.log_debug("Launching executable '%s' with args '%s'" %
                    (app_path, app_args)
                )
                result = self._tk_app.execute_hook(
                    "hook_app_launch", app_path=app_path, app_args=app_args, version=version_string
                )
                launch_cmd = result.get("command")
                return_code = result.get("return_code")
            finally:
                _restore_dll_directory(dll_directory_cache)

            self._tk_app.log_debug("Hook tried to launch '%s'" % launch_cmd)
            if return_code != 0:
                # some special logic here to decide how to display failure feedback
                if app_engine == "tk-shotgun":
                    # for the shotgun engine, use the log info in order to get the proper
                    # html formatting
                    self._tk_app.log_info(
                        "<b>Failed to launch application!</b> "
                        "This is most likely because the path is not set correctly."
                        "The command that was used to attempt to launch is '%s'. "
                        "<br><br><a href='%s' target=_new>Click here</a> to learn more about "
                        "how to setup your app launch configuration." %
                        (launch_cmd, self.HELP_DOC_URL)
                    )

                elif self._tk_app.engine.has_ui:
                    # got UI support. Launch dialog with nice message
                    not_found_dialog = self._tk_app.import_module("not_found_dialog")
                    not_found_dialog.show_path_error_dialog(self._tk_app, launch_cmd)

                else:
                    # traditional non-ui environment without any html support.
                    self._tk_app.log_error(
                        "Failed to launch application! This is most likely because the path "
                        "is not set correctly. The command that was used to attempt to launch "
                        "is '%s'. To learn more about how to set up your app launch "
                        "configuration, see the following documentation: %s" %
                        (launch_cmd, self.HELP_DOC_URL)
                    )

            else:
                # Write an event log entry
                self._register_event_log(context, launch_cmd)

        finally:
            # Clear the original structures and add into them so
            # that users who did from os import environ and from
            # sys import path get the restored values.
            os.environ.clear()
            os.environ.update(environ_clone)
            del sys.path[:]
            sys.path.extend(sys_path_clone)

    def _register_event_log(self, ctx, command_executed):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch

        :param ctx: TK context DCC was launched with
        :param command_executed: Command (including args) that was used to
                                 launch the DCC.
        """
        meta = {}
        meta["core"] = self._tk_app.sgtk.version
        meta["engine"] = "%s %s" % (self._tk_app.engine.name, self._tk_app.engine.version)
        meta["app"] = "%s %s" % (self._tk_app.name, self._tk_app.version)
        meta["launched_engine"] = self._app_engine
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc =  "%s %s: %s" % (self._tk_app.name, self._tk_app.version, self._menu_name)
        sgtk.util.create_event_log_entry(
            self._tk_app.sgtk, ctx, "Toolkit_App_Startup", desc, meta
        )

    def launch_app_from_entity(self, menu_name, app_engine, app_path, app_args, version=None):
        """
        Default method to launch DCC application command based on the current context.

        :param menu_name: Menu name displayed to launch this DCC.
        :param app_engine: The TK engine associated with the DCC to be launched.
        :param app_path: Full path to the DCC. May contain environment variables
                         and/or the locally supported {version}, {v0}, {v1}, ...
                         variables.
        :param app_args: Args string to pass to the DCC at launch time.
        :param version: Specific version of DCC to launch. Used to parse
                        {version}, {v0}, {v1}, ... information from.
        """
        # Verify a Project is defined in the context.
        if self._tk_app.context.project is None:
            raise TankError("Your context does not have a project defined. Cannot continue.")

        # Record input DCC info used throughout the launch process
        self._set_app_info(menu_name, app_engine, app_path, app_args, version)

        # Extract an entity type and id from the context.
        entity_type = self._tk_app.context.project["type"]
        entity_id = self._tk_app.context.project["id"]
        # if there is an entity then that takes precedence
        if self._tk_app.context.entity:
            entity_type = self._tk_app.context.entity["type"]
            entity_id = self._tk_app.context.entity["id"]
        # and if there is a task that is even better
        if self._tk_app.context.task:
            entity_type = self._tk_app.context.task["type"]
            entity_id = self._tk_app.context.task["id"]

        # Now do the folder creation.  If there is a specific defer keyword, this takes
        # precedence. Otherwise, use the engine name for the DCC application by default.
        defer_keyword = self._tk_app.get_setting("defer_keyword") or self._app_engine
        try:
            self._tk_app.log_debug("Creating folders for %s %s. Defer keyword: '%s'" %
                (entity_type, entity_id, defer_keyword)
            )
            self._tk_app.sgtk.create_filesystem_structure(entity_type, entity_id, engine=defer_keyword)
        except sgtk.TankError, err:
            raise TankError("Could not create folders on disk. Error reported: %s" % err)

        self._launch_app()

    def init_launch_commands(self):
        """
        Abstract method implemented by derived classes to envoke _init_launch_command()
        """
        raise NotImplementedError

    def launch_from_path(self, path, version=None):
        """
        Abstract method that can be optionally implemented by derived classes
        """
        raise NotImplementedError

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Abstract method that can be optionally implemented by derived classes
        """
        raise NotImplementedError


class SingleConfigLauncher(BaseLauncher):
    """
    Launches a DCC based on traditional configuration settings.
    """
    def __init__(self):
        BaseLauncher.__init__(self)

        # Store required information to launch the app as members.
        self._app_path = self._tk_app.get_setting("%s_path" % self._platform_name, "")
        self._app_args = self._tk_app.get_setting("%s_args" % self._platform_name, "")
        self._app_menu_name = self._tk_app.get_setting("menu_name")
        self._app_engine = self._tk_app.get_setting("engine")

    def init_launch_commands(self):
        """
        Determine what launch command(s) to register with the current TK engine.
        Multiple commands may be registered based on the app's 'version' setting.
        """
        if not self._app_path:
            # no application path defined for this os. So don't register a menu item!
            return

        # get icon value, replacing tokens if needed
        app_icon = self._tk_app.get_setting("icon")
        if app_icon.startswith("{target_engine}"):
            if self._app_engine:
                engine_path = sgtk.platform.get_engine_path(
                    self._app_engine, self._tk_app.sgtk, self._tk_app.context
                )
                if engine_path:
                    app_icon = app_icon.replace("{target_engine}", engine_path, 1)
                else:
                    # This can happen when an engine is configured in an environment that isn't
                    # supported on the current operating system.  Simply return an empty string.
                    app_icon = ""
            else:
                # This happens if there is no engine associated with the application being run.
                # Just return an empty string since using this syntax is invalid, but could
                # have been setup by running upgrades.
                app_icon = ""

        if app_icon.startswith("{config_path}"):
            config_path = self._tk_app.sgtk.pipeline_configuration.get_config_location()
            if not config_path:
                raise TankError(
                    "No pipeline configuration path found for '{config_path}' replacement."
                )
            app_icon = app_icon.replace("{config_path}", config_path, 1)

        # finally, correct the path separator
        app_icon = app_icon.replace("/", os.path.sep)

        # Initialize per version
        app_versions = self._tk_app.get_setting("versions") or []
        if app_versions:
            for version in app_versions:
                self._init_launch_command(
                    self._app_menu_name, app_icon, self._app_engine,
                    self._app_path, self._app_args, version
                )
        else:
            # No replacements defined, just register with the raw values
            self._init_launch_command(
                self._app_menu_name, app_icon, self._app_engine,
                self._app_path, self._app_args
            )

    def launch_from_path(self, path, version=None):
        """
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic
        which is external to this app.
        """
        context = self._tk_app.sgtk.context_from_path(path)
        self._launch_app(context, path, version)

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Extended version of launch_from_path. This method takes an additional
        context parameter which is useful if you want to seed the launch context
        with more context data than is available in the path itself. Typically
        paths may not contain a task, so this may need to be pushed through
        separately via the context.
        """
        if context is None:
            # this context looks sour. So fall back on to path-only launch.
            self.launch_from_path(path, version)
        else:
            # use given context to launch engine!
            self._launch_app(context, path, version)


class SoftwareEntityLauncher(BaseLauncher):
    """
    Launches a DCC based on site Software entity entries.
    """
    def init_launch_commands(self):
        """
        Determine what launch command(s) to register with the current TK engine.
        Multiple commands may be registered based on the number of retrieved
        Software entities and their corresponding 'versions' field.
        """
        # Expand Software field names that rely on the current platform
        app_path_field = "sg_%s_path" % self._platform_name
        app_args_field = "sg_%s_args" % self._platform_name

        # Determine the information to retrieve from SG
        sw_entity = self._tk_app.get_setting("sg_software_entity") or "Software"
        sw_filters = [
            ["sg_status_list", "is", "act"],
        ]
        sw_fields = [
            app_path_field,
            app_args_field,
            "code",
            "image",
            "sg_engine",
            "sg_group_restrictions",
            "sg_projects",
            "sg_versions",
            "sg_user_restrictions",
        ]

        # Get the list of Software apps that match the specified filters.
        sw_entities = self._tk_app.shotgun.find(
            sw_entity, sw_filters, sw_fields
        )
        if not sw_entities:
            # No Entities found matching filters, nothing to do.
            self._tk_app.log_debug("No SG %s entities found matching filters : %s" %
                (sw_entity, sw_filters)
            )
            return

        # Short-hand for a couple of useful context values
        ctx_user = self._tk_app.context.user
        ctx_project = self._tk_app.context.project

        for sw_app in sw_entities:
            app_menu_name = sw_app["code"]
            app_engine = sw_app["sg_engine"]
            app_path = sw_app[app_path_field]
            app_args = sw_app[app_args_field]
            app_projects = sw_app["sg_projects"] or []
            app_users = sw_app["sg_user_restrictions"] or []
            app_groups = sw_app["sg_group_restrictions"] or []
            app_icon = sw_app["image"]

            if not app_path:
                # If no path has been set for the app, we will eventually go look for one,
                # but for now, don't load the app.
                self._tk_app.log_warning("No path specified for app [%s]." % app_menu_name)
                continue

            if app_engine and app_engine not in self._tk_app.engine.get_env().get_engines():
                # If an engine name has been specified, make sure it has been loaded in
                # the current environment.
                self._tk_app.log_warning(
                    "%s is not loaded in the current environment." % app_engine
                )
                continue

            # If there are Project restrictions, check if the current Project is one of them.
            app_project_ids = [proj["id"] for proj in app_projects]
            if app_project_ids and (not ctx_project or ctx_project["id"] not in app_project_ids):
                self._tk_app.log_debug(
                    "Context Project %s not found in Project restrictions for app [%s]." %
                    (ctx_project, app_menu_name)
                )
                continue

            # If there are user restrictions, check if the current user is one of them.
            app_user_ids = [user["id"] for user in app_users]
            if app_user_ids and (not ctx_user or ctx_user["id"] not in app_user_ids):
                self._tk_app.log_debug(
                    "Context user %s not found in user restrictions for app [%s]." %
                    (ctx_user, app_menu_name)
                )
                continue

            # If there are group restrictions, check if the current user is in one of them.
            app_group_ids = [grp["id"] for grp in app_groups]
            usr_group_ids = _sg_user_group_ids(self._tk_app.shotgun, ctx_user)
            if app_group_ids and (not user_group_ids or
                    not set(user_group_ids).intersection(app_group_ids)):
                self._tk_app.log_debug(
                    "Context user %s is not a member of Group restrictions for app [%s]." %
                    (ctx_user, app_menu_name)
                )
                continue

            # Download the thumbnail to use as the app's icon.
            if app_icon:
                sg_icon = shotgun_data.ShotgunDataRetriever.download_thumbnail(
                    app_icon, self._tk_app
                )
                app_icon = sg_icon
                self._tk_app.log_debug("App icon from ShotgunDataRetriever : %s" % app_icon)

            # Parse the Software versions field to determine the specific list of
            # versions to load. Assume the list of versions is stored as comma-separated
            # in SG.
            app_versions = sw_app["sg_versions"]
            if app_versions:
                for app_version in [v.strip() for v in app_versions.split(",")]:
                    if not app_version :
                        continue
                    self._init_launch_command(
                        app_menu_name, app_icon, app_engine, app_path, app_args, app_version
                    )
            else:
                self._init_launch_command(
                    app_menu_name, app_icon, app_engine, app_path, app_args
                )


def _get_clean_version_string(version):
    """
    Returns version string used for current app launch stripped of any ()'s
    defining additional version tokens. For example, if the version
    setting is "(8.4)v6" this will return "8.4v6"

    :param version: version of the application being launched specified by
                    the value from 'versions' settings. If no 'versions'
                    were defined in the settings, then this will be None.
    """
    return re.sub('[()]', '', version) if version else None

def _translate_version_tokens(raw_string, version):
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
    clean_version = _get_clean_version_string(version)

    # do the substitution
    ver_string = raw_string.replace("{version}", clean_version)
    for i, token in enumerate(version_tokens):
        ver_string = ver_string.replace("{v%d}" % i, token)
    return ver_string

def _apply_version_to_setting(raw_string, version=None):
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

    :returns: string with version tokens replaced with their
              appropriate values
    """
    if version:
        return _translate_version_tokens(raw_string, version)
    return raw_string

def _clear_dll_directory():
    """
    Push current Dll Directory. There are two cases that
    can happen related to setting a dll directory:

    1: Project is using different python then Desktop, in
       which case the desktop will set the dll directory
       to none for the project's python interpreter. In this
       case, the following code is redundant and not needed.
    2: Desktop is using same python as Project. In which case
       we need to keep the desktop dll directory.
    """
    dll_directory = None
    if sys.platform == "win32":
        # This 'try' block will fail silently if user is using
        # a different python interpreter then Desktop, in which
        # case it will be fine since the Desktop will have set
        # the correct Dll folder for this interpreter. Refer to
        # the comments in the method's header for more information.
        try:
            import win32api

            # GetDLLDirectory throws an exception if none was set
            try:
                dll_directory = win32api.GetDllDirectory(None)
            except StandardError:
                dll_directory = None

            win32api.SetDllDirectory(None)
        except StandardError:
            pass

    return dll_directory

def _restore_dll_directory(dll_directory):
    """
    Pop the previously pushed DLL Directory

    :param dll_directory: The previously pushed DLL directory
    """
    if sys.platform == "win32":
        # This may fail silently, which is the correct behavior.
        # Refer to the comments in _clear_dll_directory() for
        # additional information.
        try:
            import win32api
            win32api.SetDllDirectory(dll_directory)
        except StandardError:
            pass

def _sg_user_group_ids(sg, sg_user):
    """
    Retrieve a list of Group ids the specified SG
    Person is a member of.

    :param sg: Connected Shotgun instance
    :param sg_user: SG Person entity to get Groups for

    :returns: List (int) of Group ids or empty list
    """
    if not sg_user:
        return []
    sg_user_groups = sg.find_one(
        sg_user["type"], [["id", "is", sg_user["id"]]], ["groups"]
    )
    return [group["id"] for group in (sg_user_groups["groups"] or [])]
