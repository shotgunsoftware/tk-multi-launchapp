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

shotgun_data = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_data")

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
        # Determine the information to retrieve from Shotgun
        # @todo: The 'sg_software_entity' setting can be removed once the
        #        Software entity becomes native.
        sw_entity = self._tk_app.get_setting("sg_software_entity") or "Software"

        # Use filters to retrieve Software entities that match specified
        # Project, HumanUser, and Group restrictions.
        sw_filters = [["sg_status_list", "is", "act"]]

        current_project = self._tk_app.context.project
        # Always include Software entities that have no Project restrictions.
        project_filters = [["sg_projects", "is", None]]
        if current_project:
            # If a current Project is defined, retrieve Software
            # entities that have either no Project restrictions OR
            # include the current Project as a restriction.
            project_filters.append(
                ["sg_projects", "is", current_project],
            )
            sw_filters.append({
                "filter_operator": "or",
                "filters": project_filters,
            })
        else:
            # If no current Project is defined, then only retrieve
            # Software entities that do not have any Project restrictions.
            sw_filters.extend(project_filters)

        current_user = self._tk_app.context.user
        # Always include Software entities that have no Group
        # or User restrictions.
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
                        ["sg_user_restrictions", "is", current_user],
                        ["sg_group_restrictions.Group.users", "is", current_user],
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

        # Get the list of Software apps that match the specified filters.
        sw_entities = self._tk_app.shotgun.find(
            sw_entity, sw_filters, sw_fields
        )
        if not sw_entities:
            # No Entities found matching filters, nothing to do.
            self._tk_app.log_info("No Shotgun %s entities found matching filters : %s" %
                (sw_entity, pprint.pformat(sw_filters))
            )
            return

        self._tk_app.log_debug("Found (%d) %s entities matching filters %s: " %
            (len(sw_entities), sw_entity, pprint.pformat(sw_filters, indent=4))
        )
        for sw_entity in sw_entities:
            self._tk_app.log_debug(pprint.pformat(sw_entity, indent=4))

            app_menu_name = sw_entity["code"]
            app_icon = sw_entity["image"]
            app_engine = sw_entity["sg_engine"]
            app_path = sw_entity[app_path_field]
            app_args = sw_entity[app_args_field]

            if not app_path:
                # If no path has been set for the app, we will eventually go look for one,
                # but for now, don't load the app.
                self._tk_app.log_warning("No path specified for app [%s]." % app_menu_name)
                continue

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

            # Download the thumbnail to use as the app's icon.
            if app_icon:
                sg_icon = shotgun_data.ShotgunDataRetriever.download_thumbnail(
                    app_icon, self._tk_app
                )
                app_icon = sg_icon
                self._tk_app.log_debug("App icon from ShotgunDataRetriever : %s" % app_icon)

            # Parse the Software versions field to determine the specific list of
            # versions to load. Assume the list of versions is stored as comma-separated
            # in Shotgun.
            app_versions = sw_entity["sg_versions"]
            if app_versions:
                for app_version in [v.strip() for v in app_versions.split(",")]:
                    if not app_version :
                        continue
                    self._register_launch_command(
                        app_menu_name, app_icon, app_engine, app_path, app_args, app_version
                    )
            else:
                self._register_launch_command(
                    app_menu_name, app_icon, app_engine, app_path, app_args
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
