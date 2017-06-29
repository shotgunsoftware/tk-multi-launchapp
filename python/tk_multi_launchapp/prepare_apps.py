# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys

import sgtk
from sgtk import TankError


def prepare_launch_for_engine(engine_name, app_path, app_args, context, file_to_open=None):
    """
    Prepares the environment to launch a DCC application in for the
    specified TK engine name.

    :param engine_name: Name of the TK engine to launch
    :param app_path: Path to DCC executable or launch script
    :param app_args: External app arguments
    :param context: The context that the application is being launched in
    :param file_to_open: (optional) File path to open once DCC finishes launching

    :returns: Tuple (app_path, app_args) Potentially modified app_path or
              app_args value, depending on preparation requirements for
              the specific DCC.
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    # Make sure this version of core supports the create_engine_launcher method, this was introduced
    # very recently, but we don't want to lock bugfixes to the legacy launch system behind a core upgrade.
    if hasattr(sgtk.platform, "create_engine_launcher"):
        # Use the TK engine to perform the necessary preparations
        # to launch the DCC. If launcher is None, then chances are the
        # installed version of the specified engine isn't up-to-date.
        launcher = sgtk.platform.create_engine_launcher(
            tk_app.sgtk, context, engine_name
        )
        if launcher:
            tk_app.log_debug("Created %s engine launcher : %s" % (engine_name, launcher))
            launch_info = launcher.prepare_launch(app_path, app_args, file_to_open)
            os.environ.update(launch_info.environment)
            tk_app.log_debug(
                "Engine launcher prepared launch info:\n  path : %s"
                "\n  args : %s\n  env  : %s" % (
                    launch_info.path, launch_info.args, launch_info.environment
                )
            )

            # There's nothing left to do at this point, simply return
            # the resolved app_path and args values.
            return (launch_info.path, launch_info.args)
        else:
            tk_app.log_debug(
                "Engine %s does not implement an application launch interface." %
                engine_name
            )
    else:
        tk_app.log_debug("'create_engine_launcher' method not found in sgtk.platform")

    tk_app.log_debug(
        "Using classic launchapp logic to prepare launch of '%s %s'" %
        (app_path, app_args)
    )

    # we have an engine we should start as part of this app launch
    # pass down the file to open into the startup script via env var.
    if file_to_open:
        os.environ["TANK_FILE_TO_OPEN"] = file_to_open
        tk_app.log_debug("Setting TANK_FILE_TO_OPEN to '%s'" % file_to_open)

    # serialize the context into an env var
    os.environ["TANK_CONTEXT"] = sgtk.context.serialize(context)
    tk_app.log_debug("Setting TANK_CONTEXT to '%r'" % context)

    # Set environment variables used by apps to prep Tank engine
    os.environ["TANK_ENGINE"] = engine_name

    # Prep any application specific things now that we know we don't
    # have an engine-specific bootstrap to use.
    if engine_name == "tk-maya":
        _prepare_maya_launch()
    elif engine_name == "tk-softimage":
        _prepare_softimage_launch()
    elif engine_name == "tk-motionbuilder":
        app_args = _prepare_motionbuilder_launch(app_args)
    elif engine_name == "tk-3dsmax":
        app_args = _prepare_3dsmax_launch(app_args)
    elif engine_name == "tk-3dsmaxplus":
        app_args = _prepare_3dsmaxplus_launch(context, app_args, app_path)
    elif engine_name == "tk-photoshop":
        _prepare_photoshop_launch(context)
    elif engine_name == "tk-houdini":
        _prepare_houdini_launch(context)
    elif engine_name == "tk-mari":
        _prepare_mari_launch(engine_name, context)
    elif engine_name in ["tk-flame", "tk-flare"]:
        (app_path, app_args) = _prepare_flame_flare_launch(
            engine_name, context, app_path, app_args,
        )
    else:
        # This should really be the first thing we try, but some of
        # the engines (like tk-3dsmaxplus, as an example) have bootstrapping
        # logic that doesn't properly stand alone and still requires
        # their "prepare" method here in launchapp to be run. As engines
        # are updated to handle all their own bootstrapping, they can be
        # pulled out from above and moved into the except block below in
        # the way that tk-nuke and tk-hiero have.
        try:
            (app_path, app_args) = _prepare_generic_launch(
                tk_app, engine_name, context, app_path, app_args,
            )
        except TankBootstrapNotFoundError:
            # Backwards compatibility here for earlier engine versions.
            if engine_name == "tk-nuke":
                app_args = _prepare_nuke_launch(file_to_open, app_args)
            elif engine_name == "tk-hiero":
                _prepare_hiero_launch()
            else:
                # We have neither an engine-specific nor launchapp-specific
                # bootstrap for this engine, so we have to bail out here.
                raise TankError(
                    "No bootstrap routine found for %s. The engine will not be started." %
                    (engine_name)
                )

    # Return resolved app path and args
    return (app_path, app_args)


def _prepare_generic_launch(tk_app, engine_name, context, app_path, app_args):
    """
    Generic engine launcher.

    This method will look for a bootstrap method in the engine's
    python/startup/bootstrap.py file if it exists.  That bootstrap will be
    called if possible.

    :param tk_app: Toolkit Application instance used for log messages
    :param engine_name: The name of the engine being launched
    :param context: The context that the application is being launched in
    :param app_path: Path to DCC executable or launch script
    :param app_args: External app arguments

    :returns: Tuple (app_path, app_args) Potentially modified app_path or
              app_args value, depending on preparation requirements for
              the specific DCC.
    """
    # find the path to the engine on disk where the startup script can be found:
    engine_path = sgtk.platform.get_engine_path(engine_name, tk_app.sgtk, context)
    if engine_path is None:
        raise TankError(
            "Could not find the path to the '%s' engine. It may not be configured "
            "in the environment for the current context ('%s')." % (engine_name, str(context))
        )

    # find bootstrap file located in the engine and load that up
    startup_path = os.path.join(engine_path, "python", "startup", "bootstrap.py")
    if not os.path.exists(startup_path):
        raise TankBootstrapNotFoundError(
            "Could not find the bootstrap for the '%s' engine at '%s'" %
            (engine_name, startup_path)
        )

    python_path = os.path.dirname(startup_path)

    # add our bootstrap location to the pythonpath
    sys.path.insert(0, python_path)
    try:
        import bootstrap
        extra_args = tk_app.get_setting("extra", {})

        # bootstrap should take kwargs in order to protect from changes in
        # this signature in the future.  For example:
        # def bootstrap(engine, context, app_path, app_args, **kwargs)
        (app_path, new_args) = bootstrap.bootstrap(
            engine_name=engine_name,
            context=context,
            app_path=app_path,
            app_args=app_args,
            extra_args=extra_args,
        )
    except Exception:
        tk_app.log_exception("Error executing engine bootstrap script.")
        raise TankError("Error executing bootstrap script. Please see log for details.")
    finally:
        # Remove bootstrap from sys.path
        sys.path.pop(0)

        # We also need to unload the bootstrap module so that any
        # subsequent launches that import a different bootstrap
        # will succeed.
        if "bootstrap" in sys.modules:
            tk_app.log_debug("Removing 'bootstrap' from sys.modules.")
            del sys.modules["bootstrap"]

    return (app_path, new_args)


def _prepare_nuke_launch(file_to_open, app_args):
    """
    Nuke specific pre-launch environment setup.

    :param file_to_open: File name to open when Nuke is launched.
    :param app_args: External app arguments

    :returns: (string) Command line arguments to launch DCC with.
    """
    # Make sure Nuke can find the Tank menu
    startup_path = _get_app_startup_path("nuke")
    sgtk.util.append_path_to_env_var("NUKE_PATH", startup_path)

    # it's not possible to open a nuke script from within the initialization
    # scripts so if we have a path then we need to pass it through the start
    # up args:
    if file_to_open:
        if app_args:
            app_args = "%s %s" % (file_to_open, app_args)
        else:
            app_args = file_to_open

    return app_args


def _prepare_hiero_launch():
    """
    Hiero specific pre-launch environment setup.
    """
    startup_path = _get_app_startup_path("hiero")
    sgtk.util.append_path_to_env_var("HIERO_PLUGIN_PATH", startup_path)


def _prepare_maya_launch():
    """
    Maya specific pre-launch environment setup.
    """
    # Make sure Maya can find the Tank menu
    startup_path = _get_app_startup_path("maya")
    sgtk.util.append_path_to_env_var("PYTHONPATH", startup_path)


def _prepare_softimage_launch():
    """
    Softimage specific pre-launch environment setup.
    """
    # add the startup plug-in to the XSI_PLUGINS path:
    xsi_plugins = os.path.abspath(os.path.join(
        _get_app_specific_path("softimage"), "startup", "Application", "Plugins"
    ))
    sgtk.util.append_path_to_env_var("XSI_PLUGINS", xsi_plugins)

    # On Linux, Softimage 2013 is missing libssl and sqlite3 libraries.  We have some that
    # we think will work so lets _append_ them to the LD_LIBRARY_PATH & PYTHONPATH before
    # launching Softimage.  Note, these can be overriden by specifying a location earlier
    # in the LD_LIBRARY_PATH & PYTHONPATH if needed
    if sys.platform == "linux2":
        # Note: we can't reliably check the version as the path on linux
        # is typically just 'xsi'.  This may become a problem if we start
        # to support 2014 and beyond...
        #
        # if "Softimage_2013" in app_path:
        lib_path = os.path.abspath(os.path.join(
            _get_app_specific_path("softimage"), "linux", "lib"
        ))
        sgtk.util.append_path_to_env_var("LD_LIBRARY_PATH", lib_path)
        sgtk.util.append_path_to_env_var("PYTHONPATH", lib_path)


def _prepare_motionbuilder_launch(app_args):
    """
    Motionbuilder specific pre-launch environment setup.

    :param app_args: External app arguments

    :returns: (string) Command line arguments to launch DCC with.
    """
    new_args = "\"%s\"" % os.path.join(
        _get_app_specific_path("motionbuilder"), "startup", "init_tank.py"
    )
    if app_args:
        app_args = "%s %s" % (app_args, new_args)
    else:
        app_args = new_args

    return app_args


def _prepare_3dsmax_launch(app_args):
    """
    3DSMax specific pre-launch environment setup.

    Make sure launch args include a maxscript to load the python engine:
    3dsmax.exe somefile.max -U MAXScript somescript.ms

    :param app_args: External app arguments

    :returns: (string) Command line arguments to launch DCC with.
    """
    startup_dir = _get_app_startup_path("3dsmax")
    os.environ["TANK_BOOTSTRAP_SCRIPT"] = os.path.join(startup_dir, "tank_startup.py")
    new_args = "-U MAXScript \"%s\"" % os.path.join(startup_dir, "init_tank.ms")
    if app_args:
        app_args = "%s %s" % (new_args, app_args)
    else:
        app_args = new_args

    return app_args


def _prepare_3dsmaxplus_launch(context, app_args, app_path):
    """
    3DSMax Plus specific pre-launch environment setup.

    Make sure launch args include a bootstrap to load the python engine:
    3dsmax.exe somefile.max -U PythonHost somescript.py

    :param context: The context that the application is being launched in
    :param app_args: External app arguments
    :param app_path: Path to DCC executable or launch script

    :returns: (string) Command line arguments to launch DCC with.
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    engine_path = sgtk.platform.get_engine_path("tk-3dsmaxplus", tk_app.sgtk, context)
    if engine_path is None:
        raise TankError("Path to 3dsmaxplus engine (tk-3dsmaxplus) could not be found.")

    # This is a fix for PySide problems in 2017+ versions of Max. Now that
    # Max ships with a full install of PySide, we need to ensure that dlls
    # for the native Max install are sourced. If we don't do this, we end
    # up with dlls loaded from SG Desktop's bin and we have a mismatch that
    # results in complete breakage.
    max_root = os.path.dirname(app_path)
    sgtk.util.prepend_path_to_env_var("PATH", max_root)

    startup_file = os.path.abspath(os.path.join(
        engine_path, "python", "startup", "bootstrap.py"
    ))
    new_args = "-U PythonHost \"%s\"" % startup_file
    if app_args:
        app_args = "%s %s" % (new_args, app_args)
    else:
        app_args = new_args

    return app_args


def _prepare_houdini_launch(context):
    """
    Houdini specific pre-launch environment setup.

    :param context: The context that the application is being launched in
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    engine_path = sgtk.platform.get_engine_path("tk-houdini", tk_app.sgtk, context)
    if engine_path is None:
        raise TankError("Path to houdini engine (tk-houdini) could not be found.")

    # let the houdini engine take care of initializing itself
    sys.path.append(os.path.join(engine_path, "python"))
    try:
        import tk_houdini
        tk_houdini.bootstrap.bootstrap(tk_app.sgtk, context)
    except:
        tk_app.log_exception("Error executing engine bootstrap script.")
        raise TankError("Error executing bootstrap script. Please see log for details.")


def _prepare_flame_flare_launch(engine_name, context, app_path, app_args):
    """
    Flame specific pre-launch environment setup.

    :param engine_name: The name of the engine being launched (tk-flame or tk-flare)
    :param context: The context that the application is being launched in
    :param app_path: Path to DCC executable or launch script
    :param app_args: External app arguments

    :returns: Tuple (app_path, app_args) Potentially modified app_path or
              app_args value, depending on preparation requirements for
              flame.
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    # find the path to the engine on disk where the startup script can be found:
    engine_path = sgtk.platform.get_engine_path(engine_name, tk_app.sgtk, context)
    if engine_path is None:
        raise TankError("Path to '%s' engine could not be found." % engine_name)

    # find bootstrap file located in the engine and load that up
    startup_path = os.path.join(engine_path, "python", "startup", "bootstrap.py")
    if not os.path.exists(startup_path):
        raise Exception("Cannot find bootstrap script '%s'" % startup_path)

    python_path = os.path.dirname(startup_path)

    # add our bootstrap location to the pythonpath
    sys.path.insert(0, python_path)
    try:
        import bootstrap
        (app_path, new_args) = bootstrap.bootstrap(engine_name, context, app_path, app_args)

    except Exception, e:
        tk_app.log_exception("Error executing engine bootstrap script.")

        if tk_app.engine.has_ui:
            # got UI support. Launch dialog with nice message
            not_found_dialog = tk_app.import_module("not_found_dialog")
            not_found_dialog.show_generic_error_dialog(tk_app, str(e))

        raise TankError("Error executing bootstrap script. Please see log for details.")
    finally:
        # remove bootstrap from sys.path
        sys.path.pop(0)

    return (app_path, new_args)


def _prepare_mari_launch(engine_name, context):
    """
    Mari specific pre-launch environment setup.

    :param engine_name: The name of the Mari engine being launched
    :param context:     The context that the application is being launched in
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    # find the path to the engine on disk where the startup script
    # can be found:
    engine_path = sgtk.platform.get_engine_path(engine_name, tk_app.sgtk, context)
    if engine_path is None:
        raise TankError("Path to '%s' engine could not be found." % engine_name)

    # add the location of our init.py script to the MARI_SCRIPT_PATH
    startup_folder = os.path.join(engine_path, "startup")
    sgtk.util.append_path_to_env_var("MARI_SCRIPT_PATH", startup_folder)


def _prepare_photoshop_launch(context):
    """
    Photoshop specific pre-launch environment setup.

    :param context: The context that the application is being launched in
    """
    # Retrieve the TK Application instance from the current bundle
    tk_app = sgtk.platform.current_bundle()

    engine_path = sgtk.platform.get_engine_path("tk-photoshop", tk_app.sgtk, context)
    if engine_path is None:
        raise TankError("Path to photoshop engine (tk-photoshop) could not be found.")

    # if the photoshop engine has the bootstrap logic with it, run it from there
    startup_path = os.path.join(engine_path, "bootstrap")
    env_setup = os.path.join(startup_path, "photoshop_environment_setup.py")
    if os.path.exists(env_setup):
        sys.path.append(startup_path)
        try:
            import photoshop_environment_setup
            photoshop_environment_setup.setup(tk_app, context)
        except:
            tk_app.log_exception("Error executing engine bootstrap script.")
            raise TankError("Error executing bootstrap script. Please see log for details.")
        return

    # no bootstrap logic with the engine, run the legacy version
    extra_configs = tk_app.get_setting("extra", {})

    # Get the path to the python executable
    python_setting = {
        "darwin": "mac_python_path",
        "win32": "windows_python_path"
    }[sys.platform]
    python_path = extra_configs.get(python_setting)
    if not python_path:
        raise TankError(
            "Your photoshop app launch config is missing the extra setting %s" %
            (python_setting)
        )

    # get the path to extension manager
    manager_setting = {
        "darwin": "mac_extension_manager_path",
        "win32": "windows_extension_manager_path"
    }[sys.platform]
    manager_path = extra_configs.get(manager_setting)
    if not manager_path:
        raise TankError(
            "Your photoshop app launch config is missing the extra setting %s!" %
            (manager_setting)
        )
    os.environ["TANK_PHOTOSHOP_EXTENSION_MANAGER"] = manager_path

    # make sure the extension is up to date
    sys.path.append(os.path.join(engine_path, "bootstrap"))
    try:
        import photoshop_extension_manager
        photoshop_extension_manager.update()
    except Exception, e:
        raise TankError(
            "Could not run the Adobe Extension Manager. Please double check your "
            "Shotgun Pipeline Toolkit Photoshop Settings. Error Reported: %s" % e
        )

    # Store data needed for bootstrapping Tank in env vars. Used in startup/menu.py
    os.environ["TANK_PHOTOSHOP_PYTHON"] = python_path
    os.environ["TANK_PHOTOSHOP_BOOTSTRAP"] = os.path.join(
        engine_path, "bootstrap", "engine_bootstrap.py"
    )

    # unused values, but the photoshop engine code still looks for these...
    os.environ["TANK_PHOTOSHOP_ENGINE"] = "dummy_value"
    os.environ["TANK_PHOTOSHOP_PROJECT_ROOT"] = "dummy_value"

    # add our startup path to the photoshop init path
    startup_path = _get_app_startup_path("photoshop")
    sgtk.util.append_path_to_env_var("PYTHONPATH", startup_path)


def _get_app_specific_path(app_dir):
    """
    Returns the path for application specific files for a given application.

    :param app_dir: (string) Sub directory name to append to
                    the current bundle's location.
    """
    # Retrieve the TK Application instance from the current bundle
    # to determine the bundle's disk location.
    tk_app = sgtk.platform.current_bundle()
    return os.path.join(tk_app.disk_location, "app_specific", app_dir)


def _get_app_startup_path(app_name):
    """
    Returns the standard 'startup' path for the given application.

    :param app_name: (string) Application name
    """
    return os.path.abspath(os.path.join(_get_app_specific_path(app_name), "startup"))


##########################################################################################
# Exceptions

class TankBootstrapNotFoundError(TankError):
    """
    Exception raised when an engine-specific bootstrap routine is not
    found.
    """
    pass
