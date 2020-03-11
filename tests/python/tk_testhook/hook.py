# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# TODO: This should ideally be merged into tk-toolchain once we are confident it is working and
#  can be useful in other situations.


def _get_callable(hook, item):
    # TODO: Ideally we would be able to tell/register interest in which hook we are overriding
    #  in the situation where we are overriding multiple with the same method names.
    engine = sgtk.platform.current_engine()
    return engine.hook_overrides[item]


class TestHook(HookBaseClass):
    def __getattribute__(self, item):
        try:
            hook_method_override = _get_callable(self, item)

            def _callback(*args, **kwargs):
                return hook_method_override(self, *args, **kwargs)

        except (AttributeError, KeyError):
            _callback = getattr(super(TestHook, self), item)

        return _callback
