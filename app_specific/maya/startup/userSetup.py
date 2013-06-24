"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

This file is loaded automatically by Maya at startup
It sets up the tank context and prepares the Tank Maya engine.
"""


import os
import maya.OpenMaya as OpenMaya
import maya.cmds as cmds

def bootstrap_tank():
    
    try:
        import tank
    except Exception, e:
        OpenMaya.MGlobal.displayError("Shotgun: Could not import sgtk! Disabling for now: %s" % e)
        return
    
    if not "TANK_ENGINE" in os.environ:
        OpenMaya.MGlobal.displayError("Shotgun: Missing required environment variable TANK_ENGINE.")
        return
    
    engine_name = os.environ.get("TANK_ENGINE") 
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        OpenMaya.MGlobal.displayError("Shotgun: Could not create context! Shotgun pipeline toolkit will be disabled. Details: %s" % e)
        return
        
    try:    
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        OpenMaya.MGlobal.displayError("Shotgun: Could not start engine: %s" % e)
        return
    
    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        # finally open the file
        cmds.file(file_to_open, force=True, open=True)

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]


cmds.evalDeferred("bootstrap_tank()")

