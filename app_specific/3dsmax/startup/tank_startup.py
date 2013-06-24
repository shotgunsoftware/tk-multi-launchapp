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
    except Exception, e:
        mxs.messageBox("Shotgun: Could not import sgtk! Disabling for now: %s" % e)
        return

    if not "TANK_ENGINE" in os.environ:
        mxs.messageBox("Shotgun: Missing required environment variable TANK_ENGINE.")
        return

    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        mxs.messageBox("Shotgun: Could not create context! Shotgun pipeline toolkit will be disabled. Details: %s" % e)
        return

    try:
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        mxs.messageBox("Shotgun: Could not start engine: %s" % e)
        return

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]


bootstrap_tank()
