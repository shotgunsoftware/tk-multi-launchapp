#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#
"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
import sys
import tank

class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """
    
    def execute(self, **kwargs):
        """
        The execute functon of the hook will be called to start the required application        
        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > multi_publiish_app = self.parent
        # > current_entity = multi_publiish_app.context.entity
        
        # you can set environment variables like this:
        # os.environ["MY_SETTING"] = "foo bar"
        
        # if you are using a shared hook to cover multiple applications,
        # you can use the engine setting to figure out which application 
        # is currently being launched:
        #
        # > multi_publiish_app = self.parent
        # > if multi_publiish_app.get_setting("engine") == "tk-nuke":
        #       do_something()
        
        
        
        
        