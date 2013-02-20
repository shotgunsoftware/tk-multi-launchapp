#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#

import os

# Py3dsMax libs
from Py3dsMax import mxs

def bootstrap_tank():

    try:
        import tank
    except:
        mxs.messageBox("Could not import Tank! Disabling Tank for now.")
        return

    if not "TANK_ENGINE" in os.environ:
        # key environment missing. This is usually when someone has done a file->new
        # and this menu.py is triggered but the env vars have been removed
        # because the boot strap is handled by the engine's callback system
        # rather than this startup script.
        return

    engine_name = os.environ.get("TANK_ENGINE")
    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    project_root = os.environ.get("TANK_PROJECT_ROOT")
    entity_id = int(os.environ.get("TANK_ENTITY_ID", "0"))
    entity_type = os.environ.get("TANK_ENTITY_TYPE")

    try:
        tk = tank.Tank(project_root)
    except Exception, e:
        mxs.messageBox("The Tank API could not be initialized! Tank will be disabled. Details: %s" % e)
        return

    try:
        if file_to_open:
            ctx = tk.context_from_path(file_to_open)
        else:
            ctx = tk.context_from_entity(entity_type, entity_id)
    except Exception, e:
        mxs.messageBox("Could not determine the Tank Context! Disabling Tank for now. Details: %s" % e)
        return

    try:
        engine = tank.platform.start_engine(engine_name, tk, ctx)
    except tank.TankEngineInitError, e:
        mxs.messageBox("The Tank Engine could not start! Tank will be disabled. Details: %s" % e)

    # remove our tmp stuff from the env
    for var in ["TANK_ENGINE", "TANK_PROJECT_ROOT", "TANK_ENTITY_ID", "TANK_ENTITY_TYPE", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]


bootstrap_tank()
