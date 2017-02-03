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
import pprint

import sgtk

from .base_launcher import BaseLauncher

class SoftwareEntityLauncher(BaseLauncher):
    """
    Launches a DCC application based on site Software entity entries.
    """
    def register_launch_commands(self):
        """
        Determine what launch command(s) to register with the current TK engine.
        Multiple commands may be registered based on the number of retrieved
        Software entities and their corresponding 'versions' field.
        """
        # Retrieve the Software entities from SG and record how many were found.
        sw_entities = self._get_sg_software_entities()
        self._tk_app.log_debug("Found (%d) Software entities to generate launch commands for." %
            len(sw_entities)
        )
        if not sw_entities:
            # No commands to register if no entities were found.
            return

        # Resolve the app path and args field names for the current platform
        app_path_field = "sg_%s_path" % self._platform_name
        app_args_field = "sg_%s_args" % self._platform_name

        # Collect a list of dictionaries that contain the information required
        # to register a command with the current engine to launch a DCC.
        register_cmd_data = []
        for sw_entity in sw_entities:
            self._tk_app.log_debug(
                "Parsing Software entity for launch commands:\n%s" %
                pprint.pformat(sw_entity, indent=4)
            )

            # Set some local variables for the Software data used here.
            app_path = sw_entity[app_path_field]
            app_display_name = sw_entity["code"]
            app_args = sw_entity[app_args_field] or ""
            app_icon = sw_entity["image"]
            app_versions = sw_entity["sg_versions"] or ""
            app_engine = sw_entity["sg_engine"]

            # Parse the Software `versions` field to determine the specific list of versions to
            # load. Assume the list of versions is stored as a comma-separated string in Shotgun.
            ver_strings = [v.strip() for v in app_versions.split(",") if v.strip()]
            app_versions = ver_strings

            # Try to retrieve the path to the specified engine. If nothing is returned, then this
            # engine hasn't been loaded in the current environment and there's not much more to do.
            if app_engine:
                app_engine_path = sgtk.platform.get_engine_path(
                    app_engine, self._tk_app.sgtk, self._tk_app.context
                )
                if not app_engine_path:
                    self._tk_app.log_warning(
                        "Software engine %s is not loaded in the current environment. "
                        "Setting Software %s 'engine' to None." % (app_engine, app_display_name)
                    )
                    app_engine = None

            # Get the list of command data dictionaries from the information provided by this
            # Software entity
            register_cmd_data.extend(self._build_register_command_data(
                app_display_name, app_icon, app_engine, app_path, app_args, app_versions,
                sw_entity["type"], sw_entity["id"]
            ))

        # Use the BaseLauncher._register_launch_command() to register command
        # data with the current engine.
        for register_cmd in register_cmd_data:
            self._register_launch_command(
                register_cmd["display_name"],
                register_cmd["icon"],
                register_cmd["engine"],
                register_cmd["path"],
                register_cmd["args"],
                register_cmd["version"]
            )

    def launch_from_path(self, path, version=None):
        """
        Entry point if you want to launch an app given a particular path.

        :param path: File path DCC should open after launch.
        :param version: (Optional) Specific version of DCC to launch.
        """
        # This functionality is not supported for Software entities.
        self._tk_app.log_error(
            "launch_from_path() is not supported by SoftwareEntityLauncher. "
            "Please register individual application launch commands in your "
            "Project's configuration to use this functionality."
        )

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Entry point if you want to launch an app given a particular path
        and context.

        :param path: File path DCC should open after launch.
        :param context: Specific context to launch DCC with.
        :param version: (Optional) Specific version of DCC to launch.
        """
        # This functionality is not supported for Software entities.
        self._tk_app.log_error(
            "launch_from_path_and_context() is not supported by "
            "SoftwareEntityLauncher. Please register individual application "
            "launch commands in your Project's configuration to use this "
            "functionality."
        )

    def _get_sg_software_entities(self):
        """
        Retrieve a list of Software entities from Shotgun that
        are active for the current project and user.
        """
        # Determine the information to retrieve from Shotgun
        # @todo: The 'sg_software_entity' setting can be removed once the
        #        Software entity becomes native.
        sw_entity = self._tk_app.get_setting("sg_software_entity") or "Software"

        # Use filters to retrieve Software entities that match specified
        # Project, HumanUser, and Group restrictions. The filter specification
        # is broken up to allow for empty Project and or HumanUser values in
        # the current context. The resolved filter can be found in the log
        # files with "debug_logging" toggled on.

        # First, make sure to only include active entries.
        sw_filters = [["sg_status_list", "is", "act"]]

        # Next handle Project restrictions. Always include Software entities
        # that have no Project restrictions.
        project_filters = [["sg_projects", "is", None]]
        current_project = self._tk_app.context.project
        if current_project:
            # If a Project is defined in the current context, retrieve
            # Software entities that have either no Project restrictions OR
            # include the context Project as a restriction.
            project_filters.append(
                ["sg_projects", "in", current_project],
            )
            sw_filters.append({
                "filter_operator": "or",
                "filters": project_filters,
            })
        else:
            # If no context Project is defined, then only retrieve
            # Software entities that do not have any Project restrictions.
            sw_filters.extend(project_filters)

        # Now Group and User restrictions. Always retrieve Software entities
        # that have no Group or User restrictions.
        current_user = self._tk_app.context.user
        user_group_filters = [
            ["sg_user_restrictions", "is", None],
            ["sg_group_restrictions", "is", None],
        ]
        if current_user:
            # If a current User is defined, then retrieve Software
            # entities that either have A) no Group AND no User
            # restrictions OR B) current User is included in Group
            # OR User restrictions.
            sw_filters.append({
                "filter_operator": "or",
                "filters": [
                    {"filter_operator": "and",
                     "filters": user_group_filters},
                    {"filter_operator": "or",
                     "filters": [
                        ["sg_user_restrictions", "in", current_user],
                        ["sg_group_restrictions.Group.users", "in", current_user],
                     ]},
                ]
            })
        else:
            # If no User is defined, then only retrieve Software
            # entities that do not have any Group or User restrictions.
            sw_filters.extend(user_group_filters)

        # The list of fields we need to retrieve in order to launch the app(s)
        # @todo: When the Software entity becomes native, these field names
        #        will need to be updated.
        # Expand Software field names that rely on the current platform
        app_path_field = "sg_%s_path" % self._platform_name
        app_args_field = "sg_%s_args" % self._platform_name
        sw_fields = [
            app_path_field,
            app_args_field,
            "code",
            "image",
            "sg_engine",
            "sg_versions",
        ]

        # Log the resolved filter.
        self._tk_app.log_debug("Searching for %s entities matching filters:\n%s" %
            (sw_entity, pprint.pformat(sw_filters, indent=4))
        )
        sw_entities = self._tk_app.shotgun.find(sw_entity, sw_filters, sw_fields)
        if not sw_entities:
            # No Entities found matching filters, nothing to do.
            self._tk_app.log_info("No Shotgun %s entities found matching filters : %s" %
                (sw_entity, pprint.pformat(sw_filters, indent=4))
            )
        return sw_entities

    def _build_register_command_data(
            self, display_name, icon, engine, path, args, versions=None,
            sg_software_type=None, sg_software_id=None
        ):
        """
        Determine the list of command data to register based on the input
        path and versions information.

        :param str display_name: Label for the registered command.
        :param str icon: Path to icon to load for the registered command.
        :param str engine: Name of the Toolkit engine this command will run
        :param str path: Path to the DCC executable to register a launch command for.
        :param str args: Args to pass to the DCC executable when launched.
        :param list versions: (optional) Specific versions (as strings) to
                              register launch commands for.
        :param str sg_software_type: (optional) Software entity type to use when retrieving
                                     thumbnail source files to use as command icons. This param
                                     will be deprecated once the Software entity is adopted natively.
        :param str sg_software_id: (optional) Software entity id to download thumbnail source file
                                   from. The downloaded thumbnail will be used as an icon for the
                                   relevant comands. This will not be used if all command icons are
                                   retrieved from the corresponding Toolkit engine instead.

        :returns: List of dictionaries containing required information to register
                  a command with the current engine.
        """
        # Keep track of the list of launch commands that should use the Software source
        # thumbnail downloaded from Shotgun. If all of the commands use icons from the engine
        # instead, then nothing needs to be downloaded, saving considerable time.
        # commands use icons from the engine instead.
        download_icon_for_commands = []

        # List of command data to return
        commands = []
        if path:
            # A custom application path has been specified in the Software data. If an icon
            # has also been specified, it will need to be downloaded. Otherwise, attempt to
            # retrieve the icon from the associated Toolkit engine launcher and use that instead.
            download_icon = True if icon else False
            if not icon and engine:
                software_versions = self._scan_for_software(
                    engine, display_name, icon, versions
                )
                if software_versions:
                    self._tk_app.log_debug("Using icon %s from SoftwareVersion for %s." %
                        ((software_versions[0].icon), display_name)
                    )
                    icon = software_versions[0].icon
                else:
                    self._tk_app.log_debug("No SoftwareVersions found for Toolkit engine %s. "
                        "Cannot determine icon to display for %s." % (engine, display_name)
                    )

            if versions:
                # Construct a command for each version.
                for version in versions:
                    commands.append({
                        "display_name": display_name, "icon": icon, "engine": engine,
                        "path": path, "args": args, "version": version,
                    })
            else:
                # Construct a single, version-less command.
                commands.append({
                    "display_name": display_name, "icon": icon, "engine": engine,
                    "path": path, "args": args, "version": None,
                })

            if download_icon:
                # The icon field for these commands will need to be updated with the cached file
                # downloaded from Shotgun.
                download_icon_for_commands.extend(commands)

        elif engine:
            # No application path was specified, triggering "auto discovery" mode. Attempt to
            # find relevant application path(s) from the engine launcher.
            self._tk_app.log_debug("Using %s engine launcher to find application paths for %s." %
                (engine, display_name)
            )
            software_versions = self._scan_for_software(
                engine, display_name, icon, versions
            ) or []
            for software_version in software_versions:
                # Construct a command for each SoftwareVersion found.
                commands.append({
                    "display_name": software_version.display_name, "icon": software_version.icon,
                    "engine": engine, "path": software_version.path, "args": args,
                    "version": software_version.version
                })

                # If the resolved SoftwareVersion icon is empty or does not exist
                # locally, use the Software icon instead.
                if not software_version.icon or not os.path.exists(software_version.icon):
                    download_icon_for_commands.append(command_data)

        else:
            # No application path(s), no launch command(s) ....
            self._tk_app.log_warning(
                "No application path or Toolkit engine specified for Software %s. "
                "Cannot create launch commands associated with this entity." % display_name
            )

        # Check if there are icons to download and whether we're in an appropriate
        # environment to do so.
        if download_icon_for_commands and self._tk_app.engine.has_ui:
            if sg_software_type and sg_software_id:
                # Import sgutils after ui has been confirmed because it has dependencies on Qt.
                shotgun_data = sgtk.platform.import_framework(
                    "tk-framework-shotgunutils", "shotgun_data"
                )

                # Download the Software thumbnail source from Shotgun and cache for reuse.
                self._tk_app.log_debug("Downloading app icon for %s from %s %s ..." %
                    (display_name, sg_software_type, sg_software_id)
                )
                local_icon = shotgun_data.ShotgunDataRetriever.download_thumbnail_source(
                    sg_software_type, sg_software_id, self._tk_app
                )
                self._tk_app.log_debug("... download complete: %s" % local_icon)

                # Update the launch commands with the local icon value.
                [cmd.update({"icon": local_icon}) for cmd in download_icon_for_commands]

            else:
                self._tk_app.log_warning(
                    "Missing entity information to download source thumbnails. Expecting "
                    "valid values for entity type (got %s) and id (got %s). Related icons "
                    "may not display correctly." % (sg_software_type, sg_software_id)
                )

        return commands

    def _scan_for_software(self, engine, default_name, default_icon, versions=None):
        """
        Use the "auto discovery" feature of an engine launcher to scan the local environment
        for all related application paths. This information will in turn be used to construct
        launch commands for the current engine.

        :param str engine: Name of the Toolkit engine to construct a launcher for.
        :param str default_name: Passed to the engine launcher as a 'display_name' to use if one
                                 cannot be determined locally.
        :param str default_icon: Passed to the engine launcher as an 'icon' to use if one cannot
                                 be determined locally.
        :param list versons: (optional) Specific versions (as strings) to filter the auto
                             discovery results by. If specified, launch commands will only be
                             registered for applications that match one of the versions in the
                             list, regardless of which applications were actually discovered.

        :returns: List of SoftwareVersions related to the specified engine that meet the input
                  requirements / restrictions.
        """
        software_versions = []
        # First try to construct the engine launcher for the specified engine.
        try:
            self._tk_app.log_debug("Initializing engine launcher for %s." % engine)
            engine_launcher = sgtk.platform.create_engine_launcher(
                self._tk_app.sgtk, self._tk_app.context, engine
            )
            if not engine_launcher:
                self._tk_app.log_info(
                    "Toolkit engine %s does not support scanning for local DCC "
                    "applications." % engine
                )
                return None
        except:
            self._tk_app.log_info(
                "Unable to construct engine launcher for %s. Cannot determine "
                "corresponding DCC application information." % engine
            )
            return None

        # Next try to scan for available applications for this engine.
        try:
            self._tk_app.log_debug("Scanning for Toolkit engine %s local applications." % engine)
            software_versions = engine_launcher.scan_software(versions, default_name, default_icon)
        except Exception, e:
            self._tk_app.log_warning(
                "Caught unexpected error scanning for DCC applications corresponding "
                "to Toolkit engine %s :\n%s" % (engine, e)
            )
            return None

        return software_versions
