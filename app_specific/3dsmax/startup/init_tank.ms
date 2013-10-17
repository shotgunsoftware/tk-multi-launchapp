if ( python != undefined ) then 
(
    if ( _blurLibrary != undefined ) then
    (
        _blurLibrary.UnRegisterCallback callbackType:#filePostSave id:#blurGeneral
    )
    
    local bootstrap_script = systemTools.getEnvVariable "TANK_BOOTSTRAP_SCRIPT"

    if ( bootstrap_script != undefined ) then 
    (
        python.run( bootstrap_script )
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

