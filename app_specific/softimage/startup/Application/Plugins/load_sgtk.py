# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Shotgun Pipeline Toolkit bootstrap plugin for Softimage.
"""

import os

import win32com.client
from win32com.client import constants

false = 0
true = 1

def XSILoadPlugin(in_reg):
    """
    Plug-in Load
    """
    # setup registration details:
    in_reg.Author = "Shotgun"
    in_reg.Name = "Shotgun Pipeline Toolkit Loader"
    in_reg.Major = 1
    in_reg.Minor = 1

    # register our custom startup event to bootstrap sgtk
    in_reg.RegisterEvent("Load Shotgun Pipeline Toolkit", constants.siOnStartup)

    return true

def XSIUnloadPlugin(in_reg):
    """
    Plug-in Unload
    """
    Application.LogMessage(str(in_reg.Name) + str(" has been unloaded."),constants.siVerbose)
    return true

def LoadShotgunPipelineToolkit_OnEvent(in_ctxt):
    """
    Initialize event - this attempts to bootstrap the
    engine and load an initial file if specified
    """
    # Have to have some environment variables 
    # in order to start the engine: 
    if not "TANK_ENGINE" in os.environ:
        Application.LogMessage("Shotgun: Missing required environment variable TANK_ENGINE.", constants.siError)
        return
    
    if not "TANK_CONTEXT" in os.environ:
        Application.LogMessage("Shotgun: Missing required environment variable TANK_CONTEXT.", constants.siError)
        return
    
    # import sgtk:
    try:
        import sgtk
    except Exception, e:
        Application.LogMessage("Shotgun: Could not import sgtk! Disabling for now: %s" % e, constants.siError)
        return

    # parse environment for the engine name and context    
    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = sgtk.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        Application.LogMessage("Shotgun: Could not create context! Shotgun Pipeline Toolkit will be disabled. Details: %s" % e, constants.siError)
        return

    # start the engine:
    try:
        engine = sgtk.platform.start_engine(engine_name, context.sgtk, context)
    except Exception, e:
        Application.LogMessage("Shotgun: Could not start engine: %s" % e, constants.siError)
        return

    # load the file:
    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        # finally open the file
        Application.OpenScene(file_to_open, false, "")

    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]
