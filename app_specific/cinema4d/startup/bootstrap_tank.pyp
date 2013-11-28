import os


def bootstrap_tank():

    try:
        import tank
    except Exception as e:
        print "Could not import Tank! Disabling Tank for now. Details: %s" % e
        return

    if not "TANK_ENGINE" in os.environ:
        # key environment missing. This is usually when someone has done a
        # file->new
        # and this menu.py is triggered but the env vars have been removed
        # because the boot strap is handled by the engine's callback system
        # rather than this startup script.
        return

    engine_name = os.environ.get("TANK_ENGINE")

    try:
        context = tank.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        print("Shotgun: Could not create context! Shotgun Pipeline Toolkit ",
              "will be disabled. Details: %s" % e)
        return

    try:
        tank.platform.start_engine(engine_name, context.tank, context)
    except tank.TankEngineInitError, e:
        print("The Tank Engine could not start! Tank will be disabled. ",
              "Details: %s" % e)

    # check if we should open a file
    file_to_open = os.environ.get("TANK_FILE_TO_OPEN")
    if file_to_open:
        import c4d
        c4d.documents.LoadDocument(file_to_open, c4d.SCENEFILTER_0)

    # remove our tmp stuff from the env
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]


if __name__ == '__main__':
    bootstrap_tank()
