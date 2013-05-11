"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Set up the tank context and prepares the Tank Hiero engine.

"""

import os
import hiero.core

def bootstrap_tank():
    
    try:
        import tank
    except Exception, e:
        hiero.core.error("Tank: Could not import Tank! Disabling for now: %s" % e)
        return
    
    if not "TANK_ENGINE" in os.environ:
        # todo: should we display a warning message here?
        return
    
    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
         hiero.core.error("Tank: Could not create context! Tank will be disabled. Details: %s" % e)
         return
        
    try:    
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        hiero.core.error("Tank: Could not start engine: %s" % e)
        return
    
    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]
    
    # todo: add support for opening a file!

bootstrap_tank()
