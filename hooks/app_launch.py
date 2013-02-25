#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#
"""
Before App Launch Hook

This hook is executed to launch the applications.
"""

import os
import sys
import tank

class AppLaunch(tank.Hook):
    """
    Hook to run an application.
    """
    
    def execute(self, app_path, app_args, **kwargs):
        """
        The execute functon of the hook will be called to start the required application
        - app_path is the path of the application executable
        - app_args is any arguments the application may require
        """
        system = sys.platform
        if system == "linux2":
            cmd = "%s %s &" % (app_path, app_args)
        elif system == "darwin":
            cmd = "open -n \"%s\"" % (app_path)
            if app_args:
                cmd += " --args \"%s\"" % app_args.replace("\"", "\\\"")
        elif system == "win32":
            cmd = "start /B \"App\" \"%s\" %s" % (app_path, app_args)

        # run the command to launch the app
        exit_code = os.system(cmd)

        return {
            "command": cmd,
            "launch_error": bool(exit_code)
        }
