# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
App that launches applications.

"""

import sgtk

class LaunchApplication(sgtk.platform.Application):
    """
    Multi App to launch applications.
    """

    # documentation explaining how to reconfigure app paths
    HELP_DOC_URL = "https://support.shotgunsoftware.com/entries/95443887#Setting%20up%20Application%20Paths"

    def init_app(self):
        """
        Called as app is being initialized
        """
        # Use the Launchers defined in the tk_multi_launchapp payload
        # to do all of the heavy lifting for this app
        app_payload = self.import_module("tk_multi_launchapp")
        if self.get_setting("use_software_entity"):
            # For zero config type setups
            self._launcher = app_payload.SoftwareEntityLauncher()
        else:
            # For traditional setups
            self._launcher = app_payload.SingleConfigLauncher()

        # Register the appropriate DCC launch commands
        self._launcher.register_launch_commands()

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Launch an app with the specified path and context. The context can
        contain more information than is available from the path itself,
        such as Task information.
        """
        self._launcher.launch_from_path_and_context(path, context, version)

    def launch_from_path(self, path, version=None):
        """
        Launch an app to open the specified file path. Also derive the
        context from this path. Note that there are no checks that the
        input path is actually compatible with the app that is being launched.
        This should be handled in logic which is external to this app.
        """
        self._launcher.launch_from_path(path, version)
