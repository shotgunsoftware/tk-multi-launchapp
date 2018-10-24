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

import sgtk
from sgtk import TankError

from .base_launcher import BaseLauncher

class SingleConfigLauncher(BaseLauncher):
    """
    Launches a DCC based on traditional configuration settings.
    """
    def __init__(self):
        """
        Initialize base class and member values
        """
        BaseLauncher.__init__(self)

        # Store required information to launch the app as members.
        self._app_path = self._tk_app.get_setting("%s_path" % self._platform_name, "")
        self._app_args = self._tk_app.get_setting("%s_args" % self._platform_name, "")
        self._app_menu_name = self._tk_app.get_setting("menu_name")
        self._app_engine = self._tk_app.get_setting("engine")
        self._app_group = self._tk_app.get_setting("group")
        self._is_group_default = self._tk_app.get_setting("group_default")

    def register_launch_commands(self):
        """
        Determine what launch command(s) to register with the current TK engine.
        Multiple commands may be registered based on the 'versions' configuration
        setting.
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
                    # This can happen when an engine is configured in an environment
                    # that isn't supported on the current operating system.
                    app_icon = ""
            else:
                # This happens if there is no engine associated with the application
                # being run. Just return an empty string since using this syntax is
                # invalid, but could have been setup by running upgrades.
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
            # If a list of versions has been specified, the "group_default" configuration
            # setting is invalid because it cannot be applied to each generated command.
            # Set the group default to the highest version in the list instead.
            sorted_versions = self._sort_versions(app_versions)
            self._tk_app.log_debug(
                "Unable to apply group '%s' group_default value to list of DCC versions : %s. "
                "Setting group '%s' default to highest version '%s' instead." %
                (self._app_group, sorted_versions, self._app_group, sorted_versions[0])
            )

            for version in app_versions:
                self._register_launch_command(
                    self._app_menu_name,
                    app_icon,
                    self._app_engine,
                    self._app_path,
                    self._app_args,
                    version,
                    self._app_group,
                    (version == sorted_versions[0])  # group_default
                    # We don't pass in a software entity id, since app is coming from
                    # the configuration.
                )
        else:
            # No replacements defined, just register with the raw values
            self._register_launch_command(
                self._app_menu_name,
                app_icon,
                self._app_engine,
                self._app_path,
                self._app_args,
                None,
                self._app_group,
                self._is_group_default,
                # We don't pass in a software entity id, since app is coming from
                # the configuration.
            )

    def launch_from_path(self, path, version=None):
        """
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic
        which is external to this app.

        :param path: File path DCC should open after launch.
        :param version: (Optional) Specific version of DCC to launch.
        """
        context = self._tk_app.sgtk.context_from_path(path)
        self._launch_app(
            self._app_menu_name,
            self._app_engine,
            self._app_path,
            self._app_args,
            context=context,
            version=version,
            file_to_open=path,
        )

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Extended version of launch_from_path. This method takes an additional
        context parameter which is useful if you want to seed the launch context
        with more context data than is available in the path itself. Typically
        paths may not contain a task, so this may need to be pushed through
        separately via the context.

        :param path: File path DCC should open after launch.
        :param context: Specific context to launch DCC with.
        :param version: (Optional) Specific version of DCC to launch.
        """
        if context is None:
            # this context looks sour. So fall back on to path-only launch.
            self.launch_from_path(path, version)
        else:
            # use given context to launch engine!
            self._launch_app(
                self._app_menu_name,
                self._app_engine,
                self._app_path,
                self._app_args,
                context=context,
                version=version,
                file_to_open=path,
            )









