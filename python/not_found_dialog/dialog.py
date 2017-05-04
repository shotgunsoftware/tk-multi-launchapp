# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog

def show_path_error_dialog(app_instance, cmd_line):
    """
    Shows a modal dialog with information about an invalid path

    :param app_instance: App instance to associate dialog with
    :param cmd_line: Launch command line that should be displayed
                     to the user as part of the message
    """
    widget = app_instance.engine.show_dialog(
        "Error launching Application", app_instance, AppDialog,
        app_instance=app_instance
    )
    widget.show_path_error_message(cmd_line)


def show_generic_error_dialog(app_instance, error_message):
    """
    Shows a modal dialog with information about a generic
    launch error.

    :param app_instance: App instance to associate dialog with
    :param cmd_line: Error message to present to the user
    """
    widget = app_instance.engine.show_dialog(
        "Error launching Application", app_instance, AppDialog,
        app_instance=app_instance
    )
    widget.show_generic_error_message(error_message)


class AppDialog(QtGui.QWidget):
    """
    Not found UI dialog.
    """

    def __init__(self, app_instance=None):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        # Capture the input TK Application instance
        self._app = app_instance

        # now load in the UI that was created in the UI designer
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.learn_more.clicked.connect(self._launch_docs)

    def show_path_error_message(self, cmd_line):
        """
        Display an error message that explains to the user that
        the app launch path is incorrect.

        :param cmd_line: Launch command line that should be displayed
                         to the user as part of the message
        """
        msg = ("<b style='color: rgb(252, 98, 70)'>Failed to launch "
               "application!</b> This is most likely because the path "
               "is not set correctly. The command that was used to "
               "attempt to launch is '%s'. <br><br>Click the button below "
               "to learn more about how to configure Toolkit to launch "
               "applications." %  cmd_line)

        self.ui.message.setText(msg)

    def show_generic_error_message(self, error_message):
        """
        Display a generic launch error message to the user.

        :param error_message: Error message to present to the user.
        """
        msg = ("<b style='color: rgb(252, 98, 70)'>Failed to launch "
               "application!</b><br><br>The following error was reported: "
               "<b>%s</b><br><br>Click the button below to learn more about "
               "how to configure Toolkit to launch applications." %
                error_message)

        self.ui.message.setText(msg)

    def _launch_docs(self):
        """
        Launches documentation describing how to configure the app launch
        """
        if self._app:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._app.HELP_DOC_URL))
        self.close()

    @property
    def hide_tk_title_bar(self):
        """
        Tell the system to not show the std toolbar
        """
        return True
