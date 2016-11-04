# Copyright (c) 2013 Shotgun Software Inc.
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

    def init_app(self):
        app_payload = self.import_module("tk_multi_launchapp")
        if self.get_setting("use_software_entity"):
            app_payload.init_apps_from_shotgun()
        else:
            app_payload.init_apps_from_settings()

    def launch_from_path_and_context(self, path, context, version=None):
        """
        Extended version of launch_from_path. This method takes an additional
        context parameter which is useful if you want to seed the launch context
        with more context data than is available in the path itself. Typically
        paths may not contain a task, so this may need to be pushed through
        separately via the context.

        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic
        which is external to this app.
        """
        app_payload = self.import_module("tk_multi_launchapp")
        app_payload.launch_app_from_path_and_context(path, context, version)

    def launch_from_path(self, path, version=None):
        """
        Entry point if you want to launch an app given a particular path.
        Note that there are no checks that the path passed is actually compatible
        with the app that is being launched. This should be handled in logic
        which is external to this app.
        """
        app_payload = self.import_module("tk_multi_launchapp")
        app_payload.launch_app_from_path(path, version)
