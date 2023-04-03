# Copyright (c) 2023 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import sgtk
from sgtk.platform.qt import QtCore, QtGui
from .ui.splash_new import Ui_Dialog
from .qtwidgets import overlay_widget


def populate_launch_dialog(app_instance):
    """
    Shows a modal dialog inheriting from QTankDialog.

    :param app_instance: App instance to associate dialog with
    """

    dialog, widget = app_instance.engine._create_dialog_with_widget(
        "App Launcher dialog",
        app_instance,
        LaunchDialog,
        app_instance=app_instance,
    )
    dialog.ui.top_group.setVisible(False)
    # Add a frameless look and force the dialog to
    # be on top of other dialogs
    dialog.setWindowFlags(
        QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint
    )
    dialog.show()
    return widget, dialog


class LaunchDialog(QtGui.QDialog):
    """
    Launcher indicator UI dialog.
    """

    def __init__(self, app_instance=None):
        """
        Constructor
        """

        # first, call the base class and let it do its thing.
        QtGui.QDialog.__init__(self)
        # Capture the input TK Application instance
        self._app = app_instance
        self._parent = None
        # now load in the UI that was created in the UI designer
        self._ui = Ui_Dialog()
        self._ui.setupUi(self)

        self._overlay = overlay_widget.ShotgunOverlayWidget(self)
        self._overlay.setMargin(20)

    def start_progress(self):
        """
        Starts the progress reporting.
        """
        # Reset the message
        self._show_progress_widgets(True)
        self._ui.sg_spinning_wid.start_progress()

    def _show_progress_widgets(self, show=False):
        """
        Shows or hides the widgets in the UI.

        :param show: If True, shows all the widgets in the UI. Hides them on False.
        """
        self._ui.sg_spinning_wid.setVisible(show)

    def report_progress(self, pct, msg=None):
        """
        Updates the widget's progress indicator and detailed area.

        :param float pct: Current progress. Must be between 0 and 1.
        :param str msg: Message to add to the detailed area.
        """
        self._ui.sg_spinning_wid.report_progress(pct)
        if msg:
            self._ui.message.setText(msg)

    @property
    def hide_tk_title_bar(self):
        """
        Tell the system to not show the std toolbar
        """
        return False
