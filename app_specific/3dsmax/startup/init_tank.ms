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
                messageBox "Shotgun Pipeline Toolkit:\n\nYou are running a version of 3dsMax that is not supported by the tk-3dsmax engine.  If you intend to use 3dsMax's built-in Python support, please update your Launcher settings to use the tk-3dsmaxplus engine.\n\nIf you don't know how to update those settings, please email support@shotgunsoftware.com"
            else
                throw
        )
    )
    else
    ( 
        print "Shotgun: Environment variable TANK_BOOTSTRAP_SCRIPT not set." 
    )
)
else 
( 
    print "Shotgun: Could not find Blur Python interpreter in 3dsmax System." 
)

