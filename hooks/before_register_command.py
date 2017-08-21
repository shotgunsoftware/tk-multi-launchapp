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
Before Register Command Hook

This hook is run prior to launchapp registering launcher commands with
the parent engine. Note: this hook is only run for Software entity 
launchers.
"""

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class BeforeRegisterCommand(HookBaseClass):
    """
    Hook to intercept SoftwareLauncher and engine instance name data prior to
    launcher command registration.
    """
    def execute(self, software_version, engine_instance_name):
        """
        Executed when the hook is run prior to launcher command registration.

        :param software_version: The software version instance constructed when
            the scan software routine was run.
        :type: :class:`sgtk.platform.SoftwareVersion`
        :param str engine_instance_name: The name of the engine instance that will
            be used when SGTK is bootstrapped during launch.

        :returns: A tuple containing a :class:`sgtk.platform.SoftwareVersion`
            instance followed by the engine instance name. These two items will
            be used when the launcher command is registered.
        :rtype: tuple
        """
        # The default implementation simply returns what it was given. Should
        # there be the need to tweak any data in the SoftwareVersion, a new
        # instance will need to be built using sgtk.platform.SoftwareVersion.
        return(software_version, engine_instance_name)

