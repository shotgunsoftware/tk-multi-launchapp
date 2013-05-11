#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#

import os

from pyfbsdk import FBMessageBox, FBApplication

def bootstrap_tank():

    try:
        import tank
    except Exception, e:
        FBMessageBox("Tank Error", 
                     "Could not import Tank! Disabling for now: %s" % e, 
                     "Ok")
        return

    if not "TANK_ENGINE" in os.environ:
        FBMessageBox("Tank Error", 
                     "Missing required environment variable TANK_ENGINE.", 
                     "Ok")
        return

    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        FBMessageBox("Tank Error",
                     "Could not create context! Tank will be disabled. Details: %s" % e,
                     "Ok")
        return

    try:
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        FBMessageBox(
            "Tank Error",
            "Could not start engine: %s" % e,
            "Ok"
        )
        return

    # if a file was specified, load it now
    file_to_open =  os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        FBApplication.FileOpen(file_to_open)

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]
        

bootstrap_tank()
