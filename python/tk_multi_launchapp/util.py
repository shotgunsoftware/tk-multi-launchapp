# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import re

def _translate_version_tokens(raw_string, version):
    """
    Returns string with version tokens replaced by their values. Replaces
    {version} and {v0}, {v1}, etc. tokens in raw_string with their values.
    The {v} tokens are created by using groups defined by () within the
    version string. For example, if the version setting is "(9.0)v4(beta1)"
        {version} = "9.0v4"
        {v0} = "9.0"
        {v1} = "beta1"

    :param raw_string: raw string with un-translated tokens
    :param version: version string to use for replacement tokens

    :returns: (string) Version string resolved from inputs
    """
    # Verify there's something to replace.
    if not raw_string:
        return raw_string

    # split version string into tokens defined by ()s
    version_tokens = re.findall(r"\(([^\)]+)\)", version)

    # ensure we have a clean complete version string without ()s
    clean_version = get_clean_version_string(version)

    # do the substitution
    ver_string = raw_string.replace("{version}", clean_version)
    for i, token in enumerate(version_tokens):
        ver_string = ver_string.replace("{v%d}" % i, token)
    return ver_string

def get_clean_version_string(version):
    """
    Returns version string used for current app launch stripped of
    any ()'s defining additional version tokens. For example, if
    the version setting is "(8.4)v6" this will return "8.4v6"

    :param version: version of the application being launched
                    specified by the value from 'versions' settings.
                    If no 'versions' were defined in the settings,
                    then this will be None.

    :returns: Version string used to launch application.
    """
    return re.sub("[()]", "", version) if version else None

def apply_version_to_setting(raw_string, version=None):
    """
    Replace any version tokens contained in the raw_string with the
    appropriate version value from the app settings.

    If version is None, we return the raw_string since there's
    no replacement to do.

    :param raw_string: the raw string potentially containing the
                       version tokens (eg. {version}, {v0}, ...)
                       we will be replacing. This string could
                       represent a number of things including a
                       path, an args string, etc.
    :param version: version string to use for the token replacement.

    :returns: string with version tokens replaced with their
              appropriate values
    """
    if version:
        return _translate_version_tokens(raw_string, version)
    return raw_string

def clear_dll_directory():
    """
    Push current Dll Directory. There are two cases that
    can happen related to setting a dll directory:

    1: Project is using different python then Desktop, in
       which case the desktop will set the dll directory
       to none for the project's python interpreter. In this
       case, the following code is redundant and not needed.
    2: Desktop is using same python as Project. In which case
       we need to keep the desktop dll directory.
    """
    dll_directory = None
    if sys.platform == "win32":
        # This 'try' block will fail silently if user is using
        # a different python interpreter then Desktop, in which
        # case it will be fine since the Desktop will have set
        # the correct Dll folder for this interpreter. Refer to
        # the comments in the method's header for more information.
        try:
            import win32api

            # GetDLLDirectory throws an exception if none was set
            try:
                dll_directory = win32api.GetDllDirectory(None)
            except StandardError:
                dll_directory = None

            win32api.SetDllDirectory(None)
        except StandardError:
            pass

    return dll_directory

def restore_dll_directory(dll_directory):
    """
    Pop the previously pushed DLL Directory

    :param dll_directory: The previously pushed DLL directory
    """
    if sys.platform == "win32":
        # This may fail silently, which is the correct behavior.
        # Refer to the comments in _clear_dll_directory() for
        # additional information.
        try:
            import win32api
            win32api.SetDllDirectory(dll_directory)
        except StandardError:
            pass
