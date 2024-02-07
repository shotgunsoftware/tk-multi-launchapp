# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import datetime

# Required so that the SHOTGUN_HOME env var will be set
from tank_test.tank_test_base import setUpModule  # noqa

from launchapp_test_base import LaunchAppTestBase

from sgtk.platform import SoftwareVersion
from sgtk.util import pickle


class TestSoftwareEntity(LaunchAppTestBase):
    """
    Tests launching via a Software entity where the paths were automatically found, via the engine's startup.
    """

    def _create_software(self):
        """
        This will be called by the setup just before the engine is started, to allow creation of Software entities.
        """
        # additional custom args
        self._additional_args = "--test"
        # Create a Software entity with no paths provided so that it doesn't automatically scan for software.

        # Create one Software entity where the path is provided and one where it isn't.
        # This will test manual and automatic software path finding.

        def register_software(name, path=None, description=None):
            return self.mockgun.create(
                "Software",
                {
                    "code": name,
                    "engine": "tk-testengine",
                    "image": None,
                    "version_names": None,
                    "products": None,
                    "group_name": None,
                    "group_default": False,
                    "linux_path": path,
                    "mac_path": path,
                    "windows_path": path,
                    "linux_args": self._additional_args,
                    "mac_args": self._additional_args,
                    "windows_args": self._additional_args,
                    "description": description,
                    # This isn't a standard field that the launch app would normally request, but
                    # we are testing that the `software_entity_extra_fields` setting which is set to include
                    # the created_at field in the fixtures will actually fetch the field.
                    "created_at": datetime.datetime.now(),
                },
            )

        # Manual and Auto path SW entities
        self._manual_software_entity = register_software(
            "manual", "/path/to/software", "manual paths"
        )
        self._auto_software_entity = register_software("auto", description="auto paths")
        # No description entity, use a path so that we can have command name registered
        self._no_desc_software_entity = register_software(
            "no description", "/path/to/software"
        )

        # Provide the scan results to the tk-testengine startup scan software method via an environment variable.
        # We json serialize a list of lists. Each sub list must contain a value for the SoftwareEntity initialization
        # parameters in the following order: version, product, path, icon, args

        # These represent the standard args a specific engine might add to the list of launch args.
        self._engine_args = ["--engine --engine2"]
        scanned_software = [
            SoftwareVersion(
                "2020",
                "Auto",  # For auto path SW entities this becomes part of the command name + the version/year
                "path/to/software_2020.app",
                "",
                self._engine_args,
            )
        ]

        os.environ["SHOTGUN_SCAN_SOFTWARE_LIST"] = pickle.dumps(scanned_software)

    def _app_launch_hook_override_auto(
        self,
        hook,
        app_path,
        app_args,
        version,
        engine_name,
        software_entity=None,
        **kwargs
    ):
        # Check that the Software entity we created in _create_software matches exactly the software entity found
        # by the launchapp, including any extra fields we asked for (description)
        self.assertEqual(software_entity, self._auto_software_entity)

        # Make sure the args include the engine args and the additional ones we provided on the Software entity.
        self.assertEqual(
            app_args, " ".join(self._engine_args + [self._additional_args])
        )
        return {}

    def _app_launch_hook_override_manual(
        self,
        hook,
        app_path,
        app_args,
        version,
        engine_name,
        software_entity=None,
        **kwargs
    ):
        # Check that the Software entity we created in _create_software matches exactly the software entity found
        # by the launchapp, including any extra fields we asked for (description)
        self.assertEqual(software_entity, self._manual_software_entity)

        # Make sure the args include the engine args and the additional ones we provided on the Software entity.
        self.assertEqual(app_args, self._additional_args)
        return {}

    def test_launch_app_auto(self):
        """
        Test the Auto path finding Software entity, produces the correct args in app_launch hook
        """
        # The easiest way to test the result is to override the app_launch hook, and check that the passed args are
        # correct.
        self.engine.hook_overrides["execute"] = self._app_launch_hook_override_auto
        # Execute the app launch callback.
        self.engine.commands["auto_2020"]["callback"]()

    def test_launch_app_manual(self):
        """
        Test the Manual path finding Software entity, produces the correct args in app_launch hook
        """
        # The easiest way to test the result is to override the app_launch hook, and check that the passed args are
        # correct.
        self.engine.hook_overrides["execute"] = self._app_launch_hook_override_manual
        # test the Manual path finding Software entity (this generates a slightly different registered command name)
        self.engine.commands["manual"]["callback"]()

    def test_action_description(self):
        """
        Make sure that the description on the PTR entity matches that in the registered command properties.
        """
        # Test the manual path register (when a hard coded path is provided in the Software entity)
        self.assertEqual(
            self.engine.commands["manual"]["properties"]["description"],
            self._manual_software_entity["description"],
        )
        # Test the automatic path register.
        self.assertEqual(
            self.engine.commands["auto_2020"]["properties"]["description"],
            self._auto_software_entity["description"],
        )
        # Test that a default description is given when None is set on the Software entity.
        self.assertEqual(
            self.engine.commands["no_description"]["properties"]["description"],
            "Launches and initializes an application environment.",
        )
