#
# Copyright (c) 2013 Shotgun Software, Inc
# ----------------------------------------------------
#
"""
This file is loaded automatically by Photoshop at startup
It sets up the tank context and prepares the Tank Photoshop engine.
"""
import os
import sys


def msgbox(msg):
    if sys.platform == "win32":
        import ctypes
        MessageBox = ctypes.windll.user32.MessageBoxA
        MessageBox(None, msg, "Tank", 0)
    elif sys.platform == "darwin":
        os.system("""osascript -e 'tell app "Finder" to display dialog "%s"'""" % msg)


def bootstrap_tank():
    try:
        import tank
    except Exception, e:
        msgbox("Tank: Could not import Tank! Disabling for now: %s" % e)
        return

    if not "TANK_ENGINE" in os.environ:
        msgbox("Tank: Missing required environment variable TANK_ENGINE.")
        return

    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        msgbox("Tank: Could not create context! Tank will be disabled. Details: %s" % e)
        return
        
    try:    
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        msgbox("Tank: Could not start engine: %s" % e)
        return

    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        import photoshop
        f = photoshop.RemoteObject("flash.filesystem::File", file_to_open)
        photoshop.app.load(f)
        
    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]
        

bootstrap_tank()
