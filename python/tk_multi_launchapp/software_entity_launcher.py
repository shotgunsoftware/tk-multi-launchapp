# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
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
        self._tk_app.log_debug("Found (%d) Software entities." % len(sw_entities))
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
            self._tk_app.log_debug("Software Entity:\n%s" % pprint.pformat(sw_entity, indent=4))

            # Parse the Software versions field to determine the specific list
            # of versions to load. Assume the list of versions is stored as
            # a comma-separated string in Shotgun.
            app_versions = sw_entity["sg_versions"] or ""
            ver_strings = [v.strip() for v in app_versions.split(",") if v.strip()]
            app_versions = ver_strings

            # Download the thumbnail to use as the app's icon.
            app_icon_url = sw_entity["image"]
            # thumb will be none if it cannot be resolved for whatever reason
            local_thumb_path = None
            # now attempt to resolve a thumbnail path
            if app_icon_url:
                if self._tk_app.engine.has_ui:
                    # import sgutils locally as this has dependencies on QT
                    shotgun_data = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_data")
                    # download thumbnail from shotgun
                    self._tk_app.log_debug("Download app icon...")
                    local_thumb_path = shotgun_data.ShotgunDataRetriever.download_thumbnail_source(
                        sw_entity["type"], sw_entity["id"], self._tk_app
                    )
                    self._tk_app.log_debug("...download complete: %s" % local_thumb_path)

            app_engine = sw_entity["sg_engine"]
            app_path = sw_entity[app_path_field]
            if app_engine:
                # Try to retrieve the path to the specified engine. If nothing is
                # returned, then this engine hasn't been loaded in the current
                # environment, and there's not much more we can do.
                app_engine_path = sgtk.platform.get_engine_path(
                    app_engine, self._tk_app.sgtk, self._tk_app.context
                )
                if not app_engine_path:
                    self._tk_app.log_warning(
                        "Software engine %s is not loaded in the current environment. "
                        "Cannot launch %s" % (app_engine, app_path)
                    )
                    continue

            app_display_name = sw_entity["code"]
            app_args = sw_entity[app_args_field] or ""
            register_cmd_data.extend(
                self._build_register_command_data(
                    app_display_name,
                    local_thumb_path,
                    app_engine,
                    app_path,
                    app_args,
                    app_versions
                )
            )

        registered_cmds = []
        for register_cmd in register_cmd_data:
            if register_cmd in registered_cmds:
                # Don't register the same command data more than once.
                continue
            self._register_launch_command(
                register_cmd["display_name"],
                register_cmd["icon"],
                register_cmd["engine"],
                register_cmd["path"],
                register_cmd["args"],
                register_cmd["version"]
            )
            registered_cmds.append(register_cmd)

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

    def _build_register_command_data(self, display_name, icon, engine, path, args, versions=None):
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

        :returns: List of dictionaries containing required information to register
                  a command with the current engine.
        """
        # List of command data to return
        commands = []
        if path:
            if versions:
                for version in versions:
                    # Register a command for each version for the path specified.
                    commands.append({
                        "display_name": display_name, "icon": icon,
                        "engine": engine, "path": path, "args": args,
                        "version": version,
                    })
            else:
                # Register a launch command for the specified path
                commands.append({
                    "display_name": display_name, "icon": icon,
                    "engine": engine, "path": path, "args": args,
                    "version": None,
                })
        else:
            try:
                # Instantiate a SoftwareLauncher for the requested engine
                # to see if it can determine a list of executable paths to
                # register launch commands for.
                launcher = sgtk.platform.create_engine_launcher(
                    self._tk_app.sgtk, self._tk_app.context, engine
                )
                if launcher:
                    # Get a list of SoftwareVersions for this engine and use that
                    # data to construct a launch command to register.
                    sw_versions = launcher.scan_software(versions, display_name, icon)
                    for swv in sw_versions:
                        commands.append({
                            "display_name": swv.display_name, "icon": swv.icon,
                            "engine": engine, "path": swv.path, "args": args,
                            "version": swv.version
                        })
                else:
                    self._tk_app.log_error(
                        "Engine %s does not support scanning for software versions." %
                        engine
                    )
            except Exception, e:
                self._tk_app.log_warning(
                    "Cannot determine executable paths for %s: %s" %
                    (engine, e)
                )

        return commands
