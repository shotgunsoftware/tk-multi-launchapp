"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Tank bootstrap plugin for Softimage.
"""

import os

import win32com.client
from win32com.client import constants

null = None
false = 0
true = 1


def XSILoadPlugin(in_reg):
    in_reg.Author = "Shotgun"
    in_reg.Name = "SgtkInit"
    in_reg.Major = 1
    in_reg.Minor = 0

    in_reg.RegisterEvent("Sgtk_OnStartup", constants.siOnStartup)
    #RegistrationInsertionPoint - do not remove this line

    return true


def XSIUnloadPlugin(in_reg):
    Application.LogMessage(str(in_reg.Name) + str(" has been unloaded."),constants.siVerbose)
    return true


def Sgtk_OnStartup_OnEvent(in_ctxt):
    try:
        import tank
    except Exception, e:
        Application.LogMessage("Shotgun: Could not import sgtk! Disabling for now: %s" % e, constants.siError)
        return

    if not "TANK_ENGINE" in os.environ:
        Application.LogMessage("Shotgun: Missing required environment variable TANK_ENGINE.", constants.siError)
        return

    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        Application.LogMessage("Shotgun: Could not create context! Shotgun Pipeline Toolkit will be disabled. Details: %s" % e, constants.siError)
        return

    try:
        engine = tank.platform.start_engine(engine_name, context.tank, context)
    except Exception, e:
        Application.LogMessage("Shotgun: Could not start engine: %s" % e, constants.siError)
        return

    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        # finally open the file
        Application.OpenScene(file_to_open, false, "")

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]
