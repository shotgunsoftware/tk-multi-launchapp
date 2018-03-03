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
App Launch Hook

This hook is executed to launch the applications.
"""

import os
import re
import sys
import tank

class AppLaunch(tank.Hook):
    """
    Hook to run an application.
    """
    
    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute functon of the hook will be called to start the required application
        
        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.

        :returns: (dict) The two valid keys are 'command' (str) and 'return_code' (int).
        """
        system = sys.platform

        # We need to know whether we're launching one of the Flame family of
        # products. To do that, we have a few things to check:
        #
        # 1. If the launcher has an engine setting, we can look at that.
        # 2. If the tk-flame engine's app_launcher script is part of the args.
        # 3. If "flame" or "flare" is in the app path, and it's using the
        #    startApplication executable.
        #
        # Those three heuristics cover the use cases we have to be aware of:
        #
        # 1. A non-software entity launchers using tk-flame or tk-flare.
        # 2. A software entity launcher using the "classic" toolkit integration.
        # 3. A zero config launch that's using a new enough engine that the
        #    software entity launcher is built using the startApplication
        #    executable instead of the .app on OS X.
        #
        is_flame_family = (
            self.parent.get_setting("engine") in ["tk-flame", "tk-flare"] or \
            re.search(r"tk-flame/.*python/startup/app_launcher.py", app_args) or \
            (re.search(r"fla[mr]e", app_path) and app_path.endswith("startApplication"))
        )

        if system == "linux2":
            # on linux, we just run the executable directly
            cmd = "%s %s &" % (app_path, app_args)

        elif is_flame_family:
            cmd = "%s %s &" % (app_path, app_args)
            
        elif system == "darwin":
            # on the mac, the executable paths are normally pointing
            # to the application bundle and not to the binary file
            # embedded in the bundle, meaning that we should use the
            # built-in mac open command to execute it. The -n flag tells the OS
            # to launch a new instance even if one is already running. The -a
            # flag specifies that the path is an application and supports both
            # the app bundle form or the full executable form.
            cmd = "open -n -a \"%s\"" % (app_path)
            if app_args:
                cmd += " --args \"%s\"" % app_args.replace("\"", "\\\"")
        
        elif system == "win32":
            # on windows, we run the start command in order to avoid
            # any command shells popping up as part of the application launch.
            cmd = "start /B \"App\" \"%s\" %s" % (app_path, app_args)

        # run the command to launch the app
        exit_code = os.system(cmd)

        return {
            "command": cmd,
            "return_code": exit_code
        }
