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
import traceback

import sgtk

from .base_launcher import BaseLauncher


class SoftwareEntityLauncher(BaseLauncher):
    """
    Launches a DCC application based on site Software entity entries.

    The following logic applies to the software entries in Shotgun:

    - If all three path fields for a software entity are set to None,
      the record is considered an "automatic" record and the launch app
      will automatically scan for suitable entries. When automatic mode
      is used, the software icon and software name defined in Shotgun are
      both ignored. The versions field in shotgun can however be used to
      *limit* the software versions returned by the automatic scan.

      The engine field needs to be set for any automatic entry.

      Please note that in the case of this automatic mode, one Software entity
      in Shotgun may result in multiple app commands being registered.

    - If a path (for any os platform) is set, the manual mode kicks in:

      - The icon will be downloaded from shotgun
      - The name defined in Shotgun will be used
      - The paths defined in Shotgun will be used.
        If the path for the current os is blank, the
        software entity will be skipped.
      - You can specify versions in the versions field
        for each version you specify, one launch entry will
        be generated. If you do this, you should also include
        the {version} token in the name field and the path fields
        and toolkit will automatically substitute it for each
        version number. (if you leave versions blank, one launch
        entry will be created and no substitutions will happen).

    - Groups and group defaults will be applied to both the manual
      and automatic entries. If an entry marked as a group default
      ends up registering more than one launch command, the command
      with the highest version number will be marked as the group
      default.

    """

    def register_launch_commands(self):
        """
        Determine what launch command(s) to register with the current TK engine.
        Multiple commands may be registered based on the number of retrieved
        Software entities and their corresponding 'versions' field.
        """
        # Retrieve the Software entities from SG and record how many were found.
        sw_entities = self._get_sg_software_entities()

        for sw_entity in sw_entities:

            self._tk_app.log_debug("-" * 20)
            self._tk_app.log_debug(
                "Parsing Software entity for launch commands:\n%s" %
                pprint.pformat(sw_entity, indent=4)
            )

            # Parse the Software `versions` field to determine the specific list of versions to
            # load. Assume the list of versions is stored as a comma-separated string in Shotgun.
            dcc_versions_str = sw_entity["version_names"] or ""
            dcc_versions = [v.strip() for v in dcc_versions_str.split(",") if v.strip()]

            # Parse the Software `products` field to determine the specific list
            # of product variations to load. Assume the list of products is
            # stored as a comma-separated string in Shotgun.
            dcc_products_str = sw_entity["products"] or ""
            dcc_products = [p.strip() for p in dcc_products_str.split(",") if p.strip()]

            # get the group settings
            app_group = sw_entity["group_name"]
            is_group_default = sw_entity["group_default"]

            # get associated engine (can be none)
            engine_str = sw_entity["engine"]

            # determine if we are in 'automatic' mode or manual
            if sw_entity.get("windows_path") is None and \
                    sw_entity.get("mac_path") is None and \
                    sw_entity.get("linux_path") is None:

                # all paths are none - we are in automatic mode
                self._tk_app.log_debug("All path fields are None. Automatic mode.")

                # make sure we have an engine defined when running in automatic mode
                # the engine implements the software discovery logic and is therefore required
                if engine_str is None:
                    self._tk_app.log_debug("No engine set. Skipping this software entity.")
                    continue

                # defer to the automatic DCC scan to enumerate and register DCCs
                self._scan_for_software_and_register(
                    engine_str,
                    dcc_versions,
                    dcc_products,
                    app_group,
                    is_group_default,
                    sw_entity["id"]
                )

            else:
                # one or more path fields are not none. This means manual mode.
                self._tk_app.log_debug("One or more path fields are not None. Manual mode.")

                # Resolve the app path and args field names for the current platform
                app_path_field = "%s_path" % self._platform_name
                app_args_field = "%s_args" % self._platform_name

                if sw_entity[app_path_field] is None:
                    # manual mode but nothing to do for our os
                    self._tk_app.log_debug(
                        "No path defined for current platform (field %s) - skipping." % app_path_field
                    )
                    continue

                app_path = sw_entity[app_path_field]
                app_display_name = sw_entity["code"]
                app_args = sw_entity[app_args_field] or ""

                # get icon
                icon_path = self._extract_thumbnail(
                    sw_entity["type"],
                    sw_entity["id"],
                    sw_entity["image"]
                )

                # manual mode!
                self._manual_register(
                    engine_str,
                    dcc_versions,
                    app_group,
                    is_group_default,
                    app_display_name,
                    app_path,
                    app_args,
                    icon_path,
                    sw_entity["id"]
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

        If the shotgun connection does not support software entities,
        an empty list is returned.

        :returns: A list of shotgun software entity dictionaries
        """

        # check that software entity is supported
        if self.__get_sg_server_version() < (7, 2, 0):
            self._tk_app.log_warning(
                "Your version of Shotgun does not support Software entity based launching."
            )
            return []

        scan_all_projects = self._tk_app.get_setting("scan_all_projects") or False

        # Determine the information to retrieve from Shotgun
        # Use filters to retrieve Software entities that match specified
        # Project, HumanUser, and Group restrictions. The filter specification
        # is broken up to allow for empty Project and or HumanUser values in
        # the current context. The resolved filter can be found in the log
        # files with "debug_logging" toggled on.

        # First, make sure to only include active entries.
        sw_filters = [["sg_status_list", "is", "act"]]

        # If we've been asked to register all software, then we don't want to
        # filter anything out based on user or project restrictions.
        if not scan_all_projects:
            # Next handle Project restrictions. Always include Software entities
            # that have no Project restrictions.
            project_filters = [["projects", "is", None]]
            current_project = self._tk_app.context.project
            if current_project:
                # If a Project is defined in the current context, retrieve
                # Software entities that have either no Project restrictions OR
                # include the context Project as a restriction.
                project_filters.append(
                    ["projects", "in", current_project],
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

        # No user restriction filter.
        user_group_filter = ["user_restrictions", "is", None]
        if current_user:
            # If a current User is defined, then retrieve Software
            # entities that either have A) no Group AND no User
            # restrictions OR B) current User is included in Group
            # OR User restrictions.
            sw_filters.append({
                "filter_operator": "or",
                "filters": [
                    user_group_filter,
                    {"filter_operator": "or",
                     "filters": [
                         ["user_restrictions", "in", current_user],
                         ["user_restrictions.Group.users", "in", current_user]
                     ]},
                ]
            })
        else:
            # If no User is defined, then only retrieve Software
            # entities that do not have any Group or User restrictions.
            sw_filters.append(user_group_filter)

        # The list of fields we need to retrieve in order to launch the app(s)
        # @todo: When the Software entity becomes native, these field names
        #        will need to be updated.
        # Expand Software field names that rely on the current platform
        sw_fields = [
            "code",
            "image",
            "engine",
            "version_names",
            "products",
            "group_name",
            "group_default",
            "linux_path",
            "mac_path",
            "windows_path",
            "linux_args",
            "mac_args",
            "windows_args",
        ]

        # Log the resolved filter.
        self._tk_app.log_debug(
            "Searching for Software entities matching filters:\n%s" %
            (pprint.pformat(sw_filters, indent=4),)
        )
        sw_entities = self._tk_app.shotgun.find("Software", sw_filters, sw_fields)
        if not sw_entities:
            # No Entities found matching filters, nothing to do.
            self._tk_app.log_debug(
                "No matching Shotgun Software entities found."
            )
        else:
            self._tk_app.log_debug(
                "Got software data from Shotgun:\n%s" % pprint.pformat(sw_entities)
            )

        return sw_entities

    def _scan_for_software_and_register(
        self, engine_str, dcc_versions, dcc_products, group, is_group_default, software_entity_id
    ):
        """
        Scan for installed software and register commands for all entries detected.

        This will call toolkit core and request that the given engine performs a
        software scan, returning versions, constrained by the dcc_versions and
        dcc_products parameters.

        Each version returned is registered as a command. If is_group_default is set
        to True and multiple versions are detected, the one with the highest version
        number will be the one that gets registered as the default.

        :param str engine_str: Engine instance to request software scanning for
        :param list dcc_versions: List of dcc versions to constrain the
            search to or None or [] if no constraint.
        :param list dcc_products: List of dcc products to constrain the
            search to or None or [] if no constraint.
        :param str group: String to group registered commands by
        :param bool is_group_default: If true, make the highest version match found
            by the scan the default.
        """
        # No application path was specified, triggering "auto discovery" mode. Attempt to
        # find relevant application path(s) from the engine launcher.
        self._tk_app.log_debug("Attempting to auto discover software for %s." % engine_str)
        software_versions = self._scan_for_software(engine_str, dcc_versions, dcc_products)

        self._tk_app.log_debug("Scan detected %d software versions" % len(software_versions))

        # sort the entries so that the highest version appears first
        sorted_versions = self._sort_versions(
            [software_version.version for software_version in software_versions]
        )

        if len(sorted_versions) > 1 and is_group_default:
            # there is more than one match and we have requested that this is the
            # group default. In this case make the highest version the group default.
            self._tk_app.log_debug(
                "Multiple matches for the group default. Will use the highest version "
                "number as the default."
            )

        for software_version in software_versions:
            # run before launch hook
            self._tk_app.log_debug("Running before register command hook...")
            launch_engine_str = self._tk_app.execute_hook_method(
                "hook_before_register_command",
                "determine_engine_instance_name",
                software_version=software_version,
                engine_instance_name=engine_str,
            )

            # If the engine name was transformed by the hook, then we need to
            # make sure that the new engine instance that's requested exists
            # in the environment. If it doesn't, then we don't register the
            # launcher command. The reason we do this here is because the same
            # verification will have occurred during the scan phase of
            # registration for the engine instance name defined in the associated
            # Software entity, but that occurs before the launch engine instance
            # is determined by the hook. We need to check for the same possible
            # issue here since the requested engine instance has changed.
            if launch_engine_str != engine_str:
                self._tk_app.logger.debug(
                    "The before_register_command hook changed the engine instance "
                    "to be %s.", launch_engine_str
                )

                try:
                    # We don't need the returned env and descriptor. We only
                    # care whether it raises or not.
                    sgtk.platform.engine.get_env_and_descriptor_for_engine(
                        launch_engine_str,
                        self._tk_app.sgtk,
                        self._tk_app.context,
                    )
                except sgtk.platform.TankMissingEngineError:
                    self._tk_app.logger.debug(
                        "The engine instance requested by before_register_command (%s) "
                        "does not exist in the current environment. The launcher will "
                        "not be registered as a result.", launch_engine_str
                    )
                    continue

            # We need to check to see if the engine instance associated with
            # the launch command is something we've been configured to skip.
            if launch_engine_str in self._tk_app.get_setting("skip_engine_instances"):
                self._tk_app.logger.debug(
                    "The %s engine instance has been configured to be skipped by way "
                    "of the skip_engine_instances app setting. The launcher command "
                    "for %r will not be registered.", launch_engine_str, software_version
                )
                continue

            # figure out if this is the group default
            if is_group_default and (software_version.version == sorted_versions[0]):
                group_default = True
            else:
                group_default = False

            # Use the product name if no group is defined in the Software
            # entity entry. This allows for smart grouping default display in
            # engine UIs.
            group_name = group or software_version.product

            # perform the registration
            self._register_launch_command(
                software_version.display_name,
                software_version.icon,
                launch_engine_str,
                software_version.path,
                " ".join(software_version.args or []),
                software_version.version,
                group_name,
                group_default,
                software_entity_id
            )

    def _manual_register(
        self, engine_str, dcc_versions, group, is_group_default,
        display_name, path, args, icon_path, software_entity_id
    ):
        """
        Parse manual software definition given by input params and register
        one or more commands.

        :param str engine_str: Engine instance to associate launching with or
            None for an engine-less launch workflow.
        :param list dcc_versions: List of dcc versions to constrain the
            search to or None or [] if no constraint.
        :param str group: String to group registered commands by
        :param bool is_group_default: If true, make the highest version match found
            by the scan the default.
        :param display_name: The name to give to launch command(s). If dcc_versions
            contains more than one item, this should contain a {version} token.
        :param path: Path to launch. If dcc_versions
            contains more than one item, this should contain a {version} token.
        :param args: Launch arguments.
        :param icon_path: Path to an icon thumbnail on disk.
        """
        if dcc_versions:
            # Construct a command for each version.
            # Sort entries by version number
            sorted_versions = self._sort_versions(dcc_versions)

            if len(sorted_versions) > 1 and is_group_default:
                # there is more than one match and we have requested that this is the
                # group default. In this case make the highest version the group default.
                self._tk_app.log_debug(
                    "Multiple matches for the group default. Will use the highest version "
                    "number as the default."
                )

            for version in dcc_versions:

                # figure out if this is the group default
                if is_group_default and (version == sorted_versions[0]):
                    group_default = True
                else:
                    group_default = False

                # perform the registration
                self._register_launch_command(
                    display_name,
                    icon_path,
                    engine_str,
                    path,
                    args,
                    version,
                    group,
                    group_default,
                    software_entity_id
                )

        else:
            # Construct a single, version-less command.
            self._register_launch_command(
                display_name,
                icon_path,
                engine_str,
                path,
                args,
                None,  # version
                group,
                is_group_default,
                software_entity_id
            )

    def _extract_thumbnail(self, entity_type, entity_id, sg_thumb_url):
        """
        Extracts the large size thumbnail from the given Shotgun entity.
        If no thumbnail can be found in Shotgun, a default one is returned.

        :param entity_type: The corresponding Shotgun entity type
        :param entity_id: The corresponding entity id
        :param sg_thumb_url: The thumbnail url for the given record
        :returns: path to local image
        """
        self._tk_app.log_debug(
            "Attempting to extract high res thumbnail from %s %s" % (entity_type, entity_id)
        )

        default_thumbnail_location = os.path.join(self._tk_app.disk_location, "icon_256.png")

        if sg_thumb_url is None:
            self._tk_app.log_debug("No thumbnail is set in Shotgun. Falling back on default.")
            # use the launch app icon
            return default_thumbnail_location

        if not self._tk_app.engine.has_ui:
            self._tk_app.log_debug("Runtime environment does not have Qt. Skipping extraction.")
            # use the launch app icon
            return default_thumbnail_location

        # all good to go - download the target icon

        # Import sgutils after ui has been confirmed because it has dependencies on Qt.
        shotgun_data = sgtk.platform.import_framework(
            "tk-framework-shotgunutils", "shotgun_data"
        )

        # Download the Software thumbnail source from Shotgun and cache for reuse.
        self._tk_app.log_debug("Downloading app icon from %s %s ..." % (entity_type, entity_id))

        try:
            icon_path = shotgun_data.ShotgunDataRetriever.download_thumbnail_source(
                entity_type,
                entity_id,
                self._tk_app
            )
        except Exception:
            self._tk_app.logger.exception("There was a problem downloading the thumbnail:")
            return default_thumbnail_location
        else:
            self._tk_app.log_debug("...download complete: %s" % icon_path)

        return icon_path

    def _scan_for_software(self, engine, versions, products):
        """
        Use the "auto discovery" feature of an engine launcher to scan the local
        environment for all related application paths. This information will in
        turn be used to construct launch commands for the current engine.

        :param str engine: Name of the Toolkit engine to construct a launcher for.
        :param list versions: Specific versions (as strings) to filter the auto
            discovery results by. If specified, launch commands will only be
            registered for executables that match one of the versions in the
            list, regardless of which executables were actually discovered.
        :param list products: Specific products (as strings) to filter the auto
            discovery results by. If specified, launch commands will only be
            registered for executables that match one of the products in the
            list, regardless of which exectuables were actually discovered.
            ex: Houdini FX, Houdini Apprentice, etc.

        :returns: List of SoftwareVersions related to the specified engine that meet the input
            requirements / restrictions.
        """
        # First try to construct the engine launcher for the specified engine.
        try:
            self._tk_app.log_debug("Initializing engine launcher for %s." % engine)
            engine_launcher = sgtk.platform.create_engine_launcher(
                self._tk_app.sgtk, self._tk_app.context, engine, versions, products
            )
            if not engine_launcher:
                self._tk_app.log_debug(
                    "Toolkit engine %s does not support scanning for local DCC "
                    "applications." % engine
                )
                return []
        except Exception, e:
            self._tk_app.log_debug(
                "Unable to construct engine launcher for %s. Cannot determine "
                "corresponding DCC application information:\n%s" % (engine, e)
            )
            return []

        # Next try to scan for available applications for this engine.
        try:
            self._tk_app.log_debug("Scanning for Toolkit engine %s local applications." % engine)
            software_versions = engine_launcher.scan_software()
        except Exception, e:
            self._tk_app.log_warning(
                "Caught unexpected error scanning for DCC applications corresponding "
                "to Toolkit engine %s:\n%s\n%s" % (engine, e, traceback.format_exc())
            )
            return []

        return software_versions

    def __get_sg_server_version(self):
        """
        Retrieves the shotgun server version
        from the currently connected Shotgun.

        :returns: Tuple of (major, minor, patch) versions.
        """
        sg_major_ver = self._tk_app.shotgun.server_info["version"][0]
        sg_minor_ver = self._tk_app.shotgun.server_info["version"][1]
        sg_patch_ver = self._tk_app.shotgun.server_info["version"][2]
        return sg_major_ver, sg_minor_ver, sg_patch_ver
