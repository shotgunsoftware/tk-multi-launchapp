#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#

import os

from pyfbsdk import FBMessageBox, FBApplication

def bootstrap_tank():

    try:
        import tank
    except:
        FBMessageBox("Tank Error", "Could not import Tank! Disabling Tank for now.", "Ok")
        return

    engine_name =   os.environ.get("TANK_ENGINE")
    file_to_open =  os.environ.get("TANK_FILE_TO_OPEN")
    project_root =  os.environ.get("TANK_PROJECT_ROOT")
    entity_id = int(os.environ.get("TANK_ENTITY_ID", "0"))
    entity_type =   os.environ.get("TANK_ENTITY_TYPE")

    try:
        tk = tank.Tank(project_root)
    except Exception, e:
        FBMessageBox("Tank Error",
                     "The Tank API could not be initialized! Tank will be disabled. Details: %s" % e,
                     "Ok")
        return

    try:
        if file_to_open:
            ctx = tk.context_from_path(file_to_open)
        elif entity_type:
            ctx = tk.context_from_entity(entity_type, entity_id)
        else:
            ctx = tk.context_from_path(project_root)
    except Exception, e:
        # Need to figure out how to show details
        FBMessageBox(
            "Tank Error",
            "Could not determine the Tank Context! Disabling Tank for now. Details: %s" % e,
            "Ok"
        )
        return

    try:
        engine = tank.platform.start_engine(engine_name, tk, ctx)
    except tank.TankEngineInitError, e:
        # Need to figure out how to show details
        FBMessageBox(
            "Tank Error",
            "The Tank Engine could not start! Tank will be disabled. Details: %s" % e,
            "Ok"
        )

    # if a file was specified, load it now
    if file_to_open:
        FBApplication.FileOpen(file_to_open)
        
    # clean up any environment variables we have set.
    for var in ["TANK_ENGINE", "TANK_PROJECT_ROOT", "TANK_ENTITY_ID", "TANK_ENTITY_TYPE", "TANK_FILE_TO_OPEN"]
        if var in os.environ:
            del os.environ[var]


bootstrap_tank()
