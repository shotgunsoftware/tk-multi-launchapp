-- This is a wrapper around the Toolkit bootstrap python script for the tk-3dsmax
-- engine. It requires the Blur Python extensions and will raise an error if they
-- are not found.
if ( python != undefined ) then
(
    if ( _blurLibrary != undefined ) then
    (
        _blurLibrary.UnRegisterCallback callbackType:#filePostSave id:#blurGeneral
    )

    local bootstrap_script = systemTools.getEnvVariable "TANK_BOOTSTRAP_SCRIPT"

    if ( bootstrap_script != undefined ) then
    (
        -- Since 2015+ uses the native built-in Python, this Blur-specific function
        -- won't exist. This catches a common use-case where users upgrade to 2015+
        -- but don't update their Launcher to use the new tk-3dsmaxplus engine.
        try
        (
            python.run( bootstrap_script )
        )
        catch
        (
            error = getCurrentException()
            is_wrong_engine = (findString error "Unknown property: \"run\" in <Interface:python>")
            if ( is_wrong_engine != undefined ) then
                messageBox "Flow Production Tracking:\n\nYou are running a version of 3dsMax that is not supported by the tk-3dsmax engine.  If you intend to use 3dsMax's built-in Python support, please update your Launcher settings to use the tk-3dsmaxplus engine.\n\nIf you don't know how to update those settings, don't hesitate to contact us!. You can find us on https://knowledge.autodesk.com/contact-support"
            else
                throw
        )
    )
    else
    (
        print "Flow Production Tracking: Environment variable TANK_BOOTSTRAP_SCRIPT not set."
    )
)
else
(
    print "Flow Production Tracking: Could not find Blur Python interpreter in 3dsmax System."
)
