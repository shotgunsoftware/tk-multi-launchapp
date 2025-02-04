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

from tank_test.tank_test_base import TankTestBase
from tank_test.tank_test_base import setUpModule  # noqa

from tk_testhook import get_test_hook_environment

import sgtk


class LaunchAppTestBase(TankTestBase):
    """ """

    def setUp(self):
        """
        Fixtures setup
        """
        _merge_into_environment_variables(get_test_hook_environment())

        super().setUp()

        self.setup_fixtures()

        self.mockgun.server_info = {"version": (7, 2, 0)}

        context = self.tk.context_from_entity(self.project["type"], self.project["id"])

        self._create_software()

        self.engine = sgtk.platform.start_engine("tk-testengine", self.tk, context)
        # This ensures that the engine will always be destroyed.
        self.addCleanup(self.engine.destroy)

        # patch the engine to define the hook_overrides attribute as a dictionary.
        # This will be looked for by tk-toolchain tk_testhook.
        self.engine.hook_overrides = {}

        self.app = self.engine.apps["tk-multi-launchapp"]

    def _create_software(self):
        """
        Override this method if you want to create Software entities and or provide the automatic software scan
        results, before the engine is started.
        """
        pass


def _merge_into_environment_variables(env):
    """
    Merge the passed in environment variables into the real
    environment.

    If an environment variable is already defined, the original
    value will remain.
    """
    for name, value in env.items():
        os.environ.setdefault(name, value)
