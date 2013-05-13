if( python != undefined ) then 
(
    _blurLibrary.UnRegisterCallback callbackType:#filePostSave id:#blurGeneral
    
    local bootstrap_script = systemTools.getEnvVariable "TANK_BOOTSTRAP_SCRIPT"

    if( bootstrap_script != undefined ) then 
    (
        python.run( bootstrap_script )
    )
    else
    ( 
        print "Tank: Environment variable TANK_BOOTSTRAP_SCRIPT not set." 
    )
)
else 
( 
    print "Tank: Could not find Blur Python interpreter in 3dsmax System." 
)

