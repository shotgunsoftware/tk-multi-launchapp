"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

App that launches applications.

"""
import os
import re
import sys
import tank

class LaunchApplication(tank.platform.Application):
    def init_app(self):
        entity_types = self.get_setting("entity_types")
        deny_permissions = self.get_setting("deny_permissions")
        deny_platforms = self.get_setting("deny_platforms")
        menu_name = self.get_setting("menu_name")

        p = {
            "title": menu_name,
            "entity_types": entity_types,
            "deny_permissions": deny_permissions,
            "deny_platforms": deny_platforms,
            "supports_multiple_selection": False
        }

        # the command name mustn't contain spaces and funny chars, so sanitize it before
        # passing it in...
        sanitized_menu_name = re.sub(r"\W+", "", menu_name)

        self.engine.register_command(sanitized_menu_name, self.launch_app, p)

    def launch_app(self, entity_type, entity_ids):
        if len(entity_ids) != 1:
            raise Exception("LaunchApp only accepts a single item in entity_ids.")

        entity_id = entity_ids[0]

        # Try to create path for the context.
        try:
            self.tank.create_filesystem_structure(entity_type, entity_id, engine=self.get_setting("engine"))
        except tank.TankError, e:
            raise Exception("Could not create folders on disk. Error reported: %s" % e)            

        # get the setting
        system = sys.platform
        try:
            path_key = r"%s_path"
            args_key = r"%s_args"
            system_name = {"linux2": "linux", "darwin": "mac", "win32": "windows"}[system]
            app_path = self.get_setting(path_key % system_name, "")
            app_args = self.get_setting(args_key % system_name, "")
            if not app_path: raise KeyError()
        except KeyError:
            raise Exception("Platform '%s' is not supported." % system)

        # Get the command to execute
        kwargs = {
            'system': system,
            'app_path': app_path,
            'app_args': app_args,
            'project_path': self.tank.project_path,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'engine': self.get_setting("engine"),
        }
        cmd = self.execute_hook("hook_app_launch", **kwargs)

        # run the command to launch the app
        self.log_debug("Executing launch command '%s'" % cmd)
        exit_code = os.system(cmd)
        if exit_code != 0:
            self.log_error("Failed to launch application! This is most likely because the path "
                          "to the executable is not set to a correct value. The "
                          "current value is '%s' - please double check that this path "
                          "is valid and update as needed in this app's configuration. "
                          "If you have any questions, don't hesitate to contact support "
                          "on tanksupport@shotgunsoftware.com." % app_path)
        
        # write an event log entry
        ctx = self.tank.context_from_entity(entity_type, entity_id)
        self._register_event_log(ctx, cmd, {})

    def _register_event_log(self, ctx, command_executed, additional_meta):
        """
        Writes an event log entry to the shotgun event log, informing
        about the app launch
        """        
        meta = {}
        meta["engine"] = "%s %s" % (self.engine.name, self.engine.version) 
        meta["app"] = "%s %s" % (self.name, self.version) 
        meta["command"] = command_executed
        meta["platform"] = sys.platform
        if ctx.task:
            meta["task"] = ctx.task["id"]
        meta.update(additional_meta)
        desc =  "%s %s: Launched Application" % (self.name, self.version)
        tank.util.create_event_log_entry(self.tank, ctx, "Tank_App_Startup", desc, meta)
