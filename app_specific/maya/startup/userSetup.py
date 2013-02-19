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
    except:
        OpenMaya.MGlobal.displayError("Could not import Tank! Disabling Tank for now.")
        return
    
    if not "TANK_MAYA_ENGINE" in os.environ:
        OpenMaya.MGlobal.displayError("Missing required environment variable TANK_MAYA_ENGINE")
        return
    
    engine_name = os.environ.get("TANK_MAYA_ENGINE")
    file_to_open = os.environ.get("TANK_MAYA_FILE_TO_OPEN") 
    project_root = os.environ.get("TANK_MAYA_PROJECT_ROOT")
    entity_id = int(os.environ.get("TANK_MAYA_ENTITY_ID", "0"))
    entity_type = os.environ.get("TANK_MAYA_ENTITY_TYPE")
    
    try:
        tk = tank.Tank(project_root)
    except Exception, e:
        OpenMaya.MGlobal.displayWarning("The Tank API could not be initialized! Tank will be disabled. Details: %s" % e)
        return
    
    try:
        if file_to_open:
            ctx = tk.context_from_path(file_to_open)
        else:
            ctx = tk.context_from_entity(entity_type, entity_id)
    except Exception, e:
        OpenMaya.MGlobal.displayWarning("Could not determine the Tank Context! Disabling Tank for now. Details: %s" % e)
        return
    
    try:    
        engine = tank.platform.start_engine(engine_name, tk, ctx)
    except tank.TankEngineInitError, e:
        OpenMaya.MGlobal.displayWarning("The Tank Engine could not start! Tank will be disabled. Details: %s" % e)
    
    # clean up temp env vars
    if "TANK_MAYA_ENGINE" in os.environ:
        del os.environ["TANK_MAYA_ENGINE"]
    
    if "TANK_MAYA_PROJECT_ROOT" in os.environ:
        del os.environ["TANK_MAYA_PROJECT_ROOT"]
    
    if "TANK_MAYA_ENTITY_ID" in os.environ:
        del os.environ["TANK_MAYA_ENTITY_ID"]
    
    if "TANK_MAYA_ENTITY_TYPE" in os.environ:
        del os.environ["TANK_MAYA_ENTITY_TYPE"]

    if "TANK_MAYA_FILE_TO_OPEN" in os.environ:
        del os.environ["TANK_MAYA_FILE_TO_OPEN"]
            
    if file_to_open:
        # finally open the file
        cmds.file(file_to_open, force=True, open=True)

cmds.evalDeferred("bootstrap_tank()")

