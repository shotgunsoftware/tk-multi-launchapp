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
            messageBox "Shotgun Pipeline Toolkit:\n\nYou are running a version of 3dsMax that is not supported by the tk-3dsmax engine.  If you intend to use 3dsMax's built-in Python support, please update your launcher settings to use the tk-3dsmaxplus engine."
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

