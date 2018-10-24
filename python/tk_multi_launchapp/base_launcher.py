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
import sys
from distutils.version import LooseVersion

import sgtk
from sgtk import TankError

from .util import apply_version_to_setting, get_clean_version_string
from .util import clear_dll_directory, restore_dll_directory
from .prepare_apps import prepare_launch_for_engine


class BaseLauncher(object):
    """
    Functionality to register engine commands that launch DCC
    applications, as well as the business logic to perform the launch.
    Subclasses of this class are responsible for parsing the
    information required to launch an application from a variety
    of sources.
    """
    def __init__(self):
        """
        Initialize members
        """
        # Retrieve the TK Application from the current bundle
        self._tk_app = sgtk.platform.current_bundle()

        # Store the current platform value
        self._platform_name = {
            "linux2": "linux", "darwin": "mac", "win32": "windows"
        }[sys.platform]

    def _register_launch_command(
        self,
        app_menu_name,
        app_icon,
        app_engine,
        app_path,
        app_args,
        version=None,
        group=None,
        group_default=True,
        software_entity_id=None
    ):
        """
        Register a launch command with the current engine.

        Also handles replacement of {version} tokens.

        :param str app_menu_name: Menu name to display to launch this DCC. This is also
                                  used to construct the associated command name.
        :param str app_icon: Icon to display for this DCC
        :param str app_engine: The TK engine associated with the DCC to be launched
        :param str app_path: Full path name to the DCC. This may contain environment
                             variables and/or the locally supported {version}, {v0},
                             {v1}, ... variables
        :param str app_args: Args string to pass to the DCC at launch time
        :param str version: (Optional) Specific version of DCC to use.
        :param str group: (Optional) Group name this command belongs to. This value is
                          interpreted by the engine the command is registered with.
        :param bool group_default: (Optional) If this command is one of a group of commands,
                                   indicate whether to launch this command if the group is
                                   selected instead of an individual command. This value is
                                   also interpreted by the engine the command is registered with.
        :param int software_entity_id: If set, this is the entity id of the software entity that
                                       is associated with this launch command.
        """
        # do the {version} replacement if needed
        icon = apply_version_to_setting(app_icon, version)
        menu_name = apply_version_to_setting(app_menu_name, version)

        # Resolve any env variables in the specified path to the application to launch.
        app_path = os.path.expandvars(
            apply_version_to_setting(app_path, version)
        )

        # the command name mustn't contain spaces and funny chars, so sanitize it.
        # Also, should be nice for the shell engine.
        # "Launch NukeX..." -> launch_nukex
        command_name = menu_name.lower().replace(" ", "_")
        if command_name.endswith("..."):
            command_name = command_name[:-3]

        # special case! @todo: fix this.
        # this is to allow this app to be loaded for sg entities of
        # type publish but not show up on the Shotgun menu. The
        # launch_from_path() and launch_from_path_and_context()
        # methods for this app should be used for these environments
        # instead. These methods are normally accessed via a hook.
        skip_environments = [
            "shotgun_tankpublishedfile",
            "shotgun_publishedfile",
            "shotgun_version",
        ]
        if self._tk_app.engine.environment.get("name") not in skip_environments:
            properties = {
                "title": menu_name,
                "short_name": command_name,
                "description": "Launches and initializes an application environment.",
                "icon": icon,
                "group": group,
                "group_default": group_default,
                "engine_name": app_engine
            }

            properties["software_entity_id"] = software_entity_id

            def launch_version(*args, **kwargs):
                self._launch_callback(
                    menu_name,
                    app_engine,
                    app_path,
                    app_args,
                    version,
                    *args, **kwargs
                )

            self._tk_app.log_debug(
                "Registering command %s to launch %s with args %s for engine %s" %
                (command_name, app_path, app_args, app_engine)
            )
            self._tk_app.engine.register_command(
                command_name, launch_version, properties
            )

    def _launch_app(
        self, menu_name, app_engine, app_path, app_args, context,
        version=None, file_to_open=None
    ):
        """
        Launches an application. No environment variable change is
        leaked to the outside world.

        :param menu_name: Menu name to display to launch this DCC. This is
                          also used to construct the associated command name.
        :param app_engine: The TK engine associated with the DCC to be launched
        :param app_path: Full path name to the DCC. This may contain environment
                         variables and/or the locally supported {version}, {v0},
                         {v1}, ... variables
        :param app_args: Args string to pass to the DCC at launch time
        :param context: Toolkit context to open the app in.
        :param version: (Optional) Version of the app to launch. Specifying
                        None means no {version} substitutions will take place.
        :param file_to_open: (Optional) File to open when the app launches.
        """
        try:
            # Clone the environment variables
            environ_clone = os.environ.copy()
            sys_path_clone = list(sys.path)

            # Get the executable path path and args. Adjust according to
            # the relevant engine.
            app_path = apply_version_to_setting(app_path, version)
            app_args = apply_version_to_setting(app_args, version)
            if app_engine:
                (prepped_path, prepped_args) = prepare_launch_for_engine(
                    app_engine, app_path, app_args, context, file_to_open
                )
                # QUESTION: Since *some* of the "prep" methods may modify
                # the app_path and app_args values (e.g. _prepare_flame_flare_launch),
                # should they be reset here like this?
                # (This is not what it does currently)
                app_path = prepped_path or app_path
                app_args = prepped_args or app_args

            version_string = get_clean_version_string(version)

            # run before launch hook
            self._tk_app.log_debug("Running before app launch hook...")
            self._tk_app.execute_hook(
                "hook_before_app_launch",
                app_path=app_path,
                app_args=app_args,
                version=version_string,
                engine_name=app_engine,
            )

            # Ticket 26741: Avoid having odd DLL loading issues on windows
            # Desktop PySide sets an explicit DLL path, which is getting
            # inherited by subprocess. The following undoes that to make
            # sure that apps depending on not having a DLL path are set
            # to work properly
            dll_directory_cache = clear_dll_directory()
            try:
                # Launch the application
                self._tk_app.log_debug(
                    "Launching executable '%s' with args '%s'" %
                    (app_path, app_args)
                )
                result = self._tk_app.execute_hook(
                    "hook_app_launch",
                    app_path=app_path,
                    app_args=app_args,
                    version=version_string,
                    engine_name=app_engine,
                )
                launch_cmd = result.get("command")
                return_code = result.get("return_code")
            finally:
                restore_dll_directory(dll_directory_cache)

            self._tk_app.log_debug("Hook tried to launch '%s'" % launch_cmd)
            if return_code != 0:
                # some special logic here to decide how to display failure feedback
                if app_engine == "tk-shotgun":
                    # for the shotgun engine, use the log info in order to
                    # get the proper html formatting
                    self._tk_app.log_info(
                        "<b>Failed to launch application!</b> "
                        "This is most likely because the path is not set correctly."
                        "The command that was used to attempt to launch is '%s'. "
                        "<br><br><a href='%s' target=_new>Click here</a> to learn "
                        "more about how to setup your app launch configuration." %
                        (launch_cmd, self._tk_app.HELP_DOC_URL)
                    )

                elif self._tk_app.engine.has_ui:
                    # got UI support. Launch dialog with nice message
                    from ..not_found_dialog import show_path_error_dialog
                    show_path_error_dialog(self._tk_app, launch_cmd)

                else:
                    # traditional non-ui environment without any html support.
                    self._tk_app.log_error(
                        "Failed to launch application! This is most likely because "
                        "the path is not set correctly. The command that was used "
                        "to attempt to launch is '%s'. To learn more about how to "
                        "set up your app launch configuration, see the following "
                        "documentation: %s" % (launch_cmd, self._tk_app.HELP_DOC_URL)
                    )

            else:
                # Emit a launched software metric
                try:
                    # Dedicated try/except block: we wouldn't want a metric-related
                    # exception to prevent execution of the remaining code.
                    engine = sgtk.platform.current_engine()
                    engine.log_metric("Launched Software")

                except Exception:
                    pass

                # Write an event log entry
                self._register_event_log(menu_name, app_engine, context, launch_cmd)

        finally:
            # Clear the original structures and add into them so
            # that users who did from os import environ and from
            # sys import path get the restored values.
            os.environ.clear()
            os.environ.update(environ_clone)
            del sys.path[:]
            sys.path.extend(sys_path_clone)

    def _register_event_log(self, menu_name, app_engine, ctx, command_executed):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch

        :param menu_name: Menu name displayed to launch a DCC.
        :param app_engine: The TK engine associated with the launched DCC.
        :param ctx: TK context DCC was launched with
        :param command_executed: Command (including args) that was used to
                                 launch the DCC.
        """
        meta = {}
        meta["core"] = self._tk_app.sgtk.version
        meta["engine"] = "%s %s" % (self._tk_app.engine.name, self._tk_app.engine.version)
        meta["app"] = "%s %s" % (self._tk_app.name, self._tk_app.version)
        meta["launched_engine"] = app_engine
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        desc = "%s %s: %s" % (self._tk_app.name, self._tk_app.version, menu_name)
        sgtk.util.create_event_log_entry(
            self._tk_app.sgtk, ctx, "Toolkit_App_Startup", desc, meta
        )

    def _launch_callback(self, menu_name, app_engine, app_path, app_args, version=None, file_to_open=None):
        """
        Default method to launch DCC application command based on the current context.

        :param menu_name: Menu name displayed to launch this DCC.
        :param app_engine: The TK engine associated with the DCC to be launched.
        :param app_path: Full path to the DCC. May contain environment variables
                         and/or the locally supported {version}, {v0}, {v1}, ...
                         variables.
        :param app_args: Args string to pass to the DCC at launch time.
        :param version: (Optional) Specific version of DCC to launch. Used to
                        parse {version}, {v0}, {v1}, ... information from.
        """
        # Verify a Project is defined in the context.
        if self._tk_app.context.project is None:
            raise TankError(
                "Your context does not have a project defined. Cannot continue."
            )

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

        if len(self._tk_app.sgtk.roots) == 0:
            # configuration doesn't have any filesystem roots defined
            self._tk_app.log_debug(
                "Configuration does not have any filesystem roots defined. "
                "Skipping folder creation."
            )

        else:
            # Do the folder creation. If there is a specific defer keyword,
            # this takes precedence. Otherwise, use the engine name for the
            # DCC application by default.
            defer_keyword = self._tk_app.get_setting("defer_keyword") or app_engine
            try:
                self._tk_app.log_debug(
                    "Creating folders for %s %s. Defer keyword: '%s'" %
                    (entity_type, entity_id, defer_keyword)
                )
                self._tk_app.sgtk.create_filesystem_structure(
                    entity_type, entity_id, engine=defer_keyword
                )
            except sgtk.TankError, err:
                raise TankError(
                    "Could not create folders on disk. Error reported: %s" % err
                )

        # Launch the DCC
        self._launch_app(
            menu_name,
            app_engine,
            app_path,
            app_args,
            self._tk_app.context,
            version,
            file_to_open,
        )

    def register_launch_commands(self):
        """
        Abstract method implemented by derived classes to
        envoke _register_launch_command()
        """
        raise NotImplementedError

    def launch_from_path(self, path, version=None):
        """
        Abstract method that can optionally be implemented by
        derived classes

        :param path: File path DCC should open after launch.
        :param version: (optional) Specific version of DCC
                        to launch.
        """
        raise NotImplementedError

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Abstract method that can optionally be implemented by derived classes

        :param path: File path DCC should open after launch.
        :param context: Specific context to launch DCC with.
        :param version: (Optional) Specific version of DCC to launch.
        """
        raise NotImplementedError

    def _sort_versions(self, versions):
        """
        Uses standard python modules to determine how to sort arbitrary version numbers.
        A version number consists of a series of numbers, separated by either periods or
        strings of letters. When comparing version numbers, the numeric components will
        be compared numerically, and the alphabetic components lexically. For example:

            1.1 < 1.2 < 1.3
            1.2 < 1.2a < 1.2ab < 1.2b

        The input list of versions is not modified.

        :param list versions: List of version "numbers" (may be strings)
        :returns: List of sorted versions in descending order. The highest version is
                  at index 0.
        """
        # Cast the incoming version strings as LooseVersion instances to sort using
        # the LooseVersion.__cmp__ method.
        sort_versions = [LooseVersion(version) for version in versions]
        sort_versions.sort(reverse=True)

        # Convert the LooseVersions back to strings on return.
        return [str(version) for version in sort_versions]
