"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

This file is loaded automatically by Nuke at startup, after init.py.
It sets up the tank context and prepares the Tank Nuke engine.


NOTE!

When opening a new scene in Nuke, Nuke launches a new process.

So a file->new operation is effectively equivalent to starting 
that very first session, again. Meaning that the bootstrap script will
run again. This is not what we want - we only want the bootstrap script
to run the very first time nuke starts. So therefore, we unset the env vars
once the engine has been created. 

"""


import os
import nuke

def bootstrap_tank():

    try:
        import tank
    except:
        nuke.warning("Could not import Tank! Disabling Tank for now.")
        return
    
    if not "TANK_NUKE_ENGINE" in os.environ:
        # key environment missing. This is usually when someone has done a file->new
        # and this menu.py is triggered but the env vars have been removed
        # because the boot strap is handled by the engine's callback system
        # rather than this startup script.
        return
    
    engine_name = os.environ.get("TANK_NUKE_ENGINE")
    file_to_open = os.environ.get("TANK_NUKE_FILE_TO_OPEN") 
    project_root = os.environ.get("TANK_NUKE_PROJECT_ROOT")
    entity_id = int(os.environ.get("TANK_NUKE_ENTITY_ID", "0"))
    entity_type = os.environ.get("TANK_NUKE_ENTITY_TYPE")

    try:
        tk = tank.Tank(project_root)
    except Exception, e:
         nuke.warning("The Tank API could not be initialized! Tank will be disabled. Details: %s" % e)
         return
    
    try:
        if file_to_open:
            ctx = tk.context_from_path(file_to_open)
        else:
            ctx = tk.context_from_entity(entity_type, entity_id)
    except Exception, e:
        nuke.warning("Could not determine the Tank Context! Disabling Tank for now. Details: %s" % e)
        return
    
    try:    
        engine = tank.platform.start_engine(engine_name, tk, ctx)
    except tank.TankEngineInitError, e:
        nuke.warning("The Tank Engine could not start! Tank will be disabled. Details: %s" % e)
    
    # remove from env so that they wont affect the nuke that is initalized on a
    # file->new. or file->open
    if "TANK_NUKE_ENGINE" in os.environ:
        del os.environ["TANK_NUKE_ENGINE"]
    
    if "TANK_NUKE_PROJECT_ROOT" in os.environ:
        del os.environ["TANK_NUKE_PROJECT_ROOT"]
    
    if "TANK_NUKE_ENTITY_ID" in os.environ:
        del os.environ["TANK_NUKE_ENTITY_ID"]
    
    if "TANK_NUKE_ENTITY_TYPE" in os.environ:
        del os.environ["TANK_NUKE_ENTITY_TYPE"]

    if "TANK_NUKE_FILE_TO_OPEN" in os.environ:
        del os.environ["TANK_NUKE_FILE_TO_OPEN"]
            


bootstrap_tank()
