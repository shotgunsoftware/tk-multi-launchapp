# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog

def show_dialog(app_instance, cmd_line):
    """
    Shows the main dialog window, using the special Shotgun multi-select mode.
    """
    app_instance.engine.show_dialog("Error launching Application", app_instance, AppDialog, cmd_line)


class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """
    
    def __init__(self, cmd_line):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)
        
        # now load in the UI that was created in the UI designer
        self.ui = Ui_Dialog() 
        self.ui.setupUi(self)
        
        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        self._app = sgtk.platform.current_bundle()
        
        msg = ("<b style='color: orange'>Failed to launch application!</b> This is most likely because the path "
               "is not set correctly. The command that was used to attempt to launch is '%s'. "
               "<br><br>Click the button below to learn more about how to configure toolkit to launch "
               "applications." %  cmd_line)
        
        self.ui.message.setText(msg)
        
        self.ui.learn_more.clicked.connect(self._launch_docs)
        
    def _launch_docs(self):
        """
        Launches documentation describing how to configure the app launch
        """
        doc_url = "https://toolkit.shotgunsoftware.com/entries/93728833#Setting%20up%20Application%20Paths"
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(doc_url))
        self.close()
        
    @property
    def hide_tk_title_bar(self):
        """
        Tell the system to not show the std toolbar
        """
        return True
        
