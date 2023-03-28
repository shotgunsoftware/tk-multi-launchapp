import sys
import sgtk
from sgtk.platform.qt import QtCore, QtGui

# from .ui.launch_spinner import Ui_Dialog
from .ui.splash_new import Ui_Dialog

from .qtwidgets import overlay_widget
#from ..tk_multi_launchapp import overlay_widget
#from ..tk_multi_launchapp import base_launcher
#from ..tk_multi_launchapp import base_launcher

#overlay_widget = base_launcher.overlay


class TestSignals(QtCore.QObject):
    on_finished_timer = QtCore.Signal(str)


def populate_launch_widget(app_instance):
    """
    Shows a modal dialog with information about an invalid path

    :param app_instance: App instance to associate dialog with
    """

    dialog, widget = app_instance.engine._create_dialog_with_widget(
        "App Launcher widget",
        app_instance,
        LaunchDialog,
        app_instance=app_instance,
    )

    dialog.ui.top_group.setVisible(False)
    dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
    dialog.show()
    return widget, dialog


class LaunchDialog(QtGui.QDialog):
    """
    Not found UI dialog.
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

    @property
    def splash_look(self):
        """
        Splash screen look and feel.
        """
        return False
