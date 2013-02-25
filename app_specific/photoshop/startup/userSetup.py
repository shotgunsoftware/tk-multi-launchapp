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
        msgbox("Could not import Tank! Disabling Tank for now: Details: %s" % e)
        return

    if not "TANK_ENGINE" in os.environ:
        msgbox("Missing required environment variable TANK_ENGINE")
        return

    engine_name = os.environ.get("TANK_ENGINE")
    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    project_root = os.environ.get("TANK_PROJECT_ROOT")
    entity_id = int(os.environ.get("TANK_ENTITY_ID", "0"))
    entity_type = os.environ.get("TANK_ENTITY_TYPE")

    try:
        tk = tank.Tank(project_root)
    except Exception, e:
        msgbox("The Tank API could not be initialized! Tank will be disabled. Details: %s" % e)
        return

    try:
        if file_to_open:
            ctx = tk.context_from_path(file_to_open)
        else:
            ctx = tk.context_from_entity(entity_type, entity_id)
    except Exception, e:
        msgbox("Could not determine the Tank Context! Disabling Tank for now. Details: %s" % e)
        return

    try:
        tank.platform.start_engine(engine_name, tk, ctx)
    except tank.TankEngineInitError, e:
        msgbox("The Tank Engine could not start! Tank will be disabled. Details: %s" % e)

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_PROJECT_ROOT", "TANK_ENTITY_ID", "TANK_ENTITY_TYPE", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]

    if file_to_open:
        import photoshop
        f = photoshop.RemoteObject("flash.filesystem::File", file_to_open)
        photoshop.app.load(f)

bootstrap_tank()
