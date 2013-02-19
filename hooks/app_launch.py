#
# Copyright (c) 2012 Shotgun Software, Inc
# ----------------------------------------------------
#
"""
Before App Launch Hook

This hook is executed to launch the applications.
"""

import os
import re
import tank

class AppLaunch(tank.Hook):
    
    def execute(self, **kwargs):
        # Arguments being passed in are:
        # system, app_path, app_args, project_path, entity_type, entity_id,
        # engine
        system = kwargs['system']
        app_path = kwargs['app_path']
        app_args = kwargs['app_args']
        engine = kwargs['engine']

        if system == "linux2":
            cmd = '%s %s &' % (app_path, app_args)
        elif system == "darwin":
            cmd = 'open -n "%s"' % (app_path)
            if app_args:
                cmd += ' --args "%s"' % (app_args)
        elif system == "win32":
            cmd = 'start /B "App" "%s" %s' % (app_path, app_args)

        # Run engine specific code
        # We're not using self.parent.engine because that is shotgun
        func = getattr(self, '_' + re.sub('\W+', '_', engine), None)
        if func and callable(func):
            func(kwargs)

        return cmd

    @classmethod
    def _tk_nuke(klass, args):
        """Nuke specific pre-launch environment setup."""

        # Make sure Nuke can find the Tank menu
        startup_path = os.path.abspath(os.path.join(klass._get_app_specific_path('nuke'), "startup"))
        tank.util.append_path_to_env_var("NUKE_PATH", startup_path)

        # Set environment variables used by Nuke to prep Tank engine
        os.environ["TANK_NUKE_ENGINE"] = args['engine']
        os.environ["TANK_NUKE_PROJECT_ROOT"] = args['project_path']
        os.environ["TANK_NUKE_ENTITY_TYPE"] = args['entity_type']
        os.environ["TANK_NUKE_ENTITY_ID"] = str(args['entity_id'])

    @classmethod
    def _tk_maya(klass, args):
        """Maya specific pre-launch environment setup."""

        # Make sure Maya can find the Tank menu
        app_specific_path = klass._get_app_specific_path('maya')
        startup_path = os.path.abspath(os.path.join(app_specific_path, "startup"))
        tank.util.append_path_to_env_var("PYTHONPATH", startup_path)

        # Store data needed for bootstrapping Tank in env vars. Used in startup/userSetup.mel
        os.environ["TANK_MAYA_ENGINE"] = args['engine']
        os.environ["TANK_MAYA_PROJECT_ROOT"] = args['project_path']
        os.environ["TANK_MAYA_ENTITY_TYPE"] = args['entity_type']
        os.environ["TANK_MAYA_ENTITY_ID"] = str(args['entity_id'])

        # Push our patched _ssl compiled module to the front of the PYTHONPATH for Windows
        # SSL Connection time fix.
        if args['system'] == "win32":
            # maps the maya version to the ssl maya version;  (maya 2011 can use the maya 2012 _ssl.pyd)
            # the ssl directory name is the version of maya it was compiled for.
            maya_version_to_ssl_maya_version = {
                "2011": "2012",
                "2012": "2012",
                "2013": "2013",
            }

            version_dir = None
            # From most recent to past version
            for year in sorted(maya_version_to_ssl_maya_version, reverse=True):
                # Test for the year in the path.
                # maya -v returns an empty line with maya 2013.
                if year in args['app_path']:
                    version_dir = maya_version_to_ssl_maya_version[year]
                    break

            # if there is an ssl lib for that current version of maya being used then
            # add it to the python path.
            if version_dir:
                ssl_path = os.path.abspath(os.path.join(app_specific_path, "ssl_patch", version_dir))
                tank.util.prepend_path_to_env_var('PYTHONPATH', ssl_path)

    @staticmethod
    def _get_app_specific_path(app_name):
        """Get the path for application specific files for a given application."""
        return os.path.join(os.path.dirname(__file__), "..", "app_specific", app_name)
