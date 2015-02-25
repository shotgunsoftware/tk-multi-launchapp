if ( python != undefined ) then 
(
    if ( _blurLibrary != undefined ) then
    (
        _blurLibrary.UnRegisterCallback callbackType:#filePostSave id:#blurGeneral
    )
    
    local bootstrap_script = systemTools.getEnvVariable "TANK_BOOTSTRAP_SCRIPT"

    if ( bootstrap_script != undefined ) then 
    (
        try
        (
            python.run( bootstrap_script )
        )
        catch
        (
            error = getCurrentException()
            is_wrong_engine = (findString error "Unknown property: \"run\" in <Interface:python>") 
            if ( is_wrong_engine != undefined ) then
                messageBox "Shotgun Pipeline Toolkit:\n\nYou are running a version of 3dsMax that is not supported by the tk-3dsmax engine.  If you intend to use 3dsMax's built-in Python support, please update your Launcher settings to use the tk-3dsmaxplus engine.\n\nIf you don't know how to update those settings, please email toolkitsupport@shotgunsoftware.com"
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

