# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash_new.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from tank.platform.qt import QtCore
for name, cls in QtCore.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls

from tank.platform.qt import QtGui
for name, cls in QtGui.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls


from ..qtwidgets import ShotgunSpinningWidget

from  . import resources_rc

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(446, 156)
        Dialog.setStyleSheet(u"background-color: rgb(41, 41, 41);")
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalSpacer = QSpacerItem(20, 11, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(12)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(128, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.sg_spinning_wid = ShotgunSpinningWidget(Dialog)
        self.sg_spinning_wid.setObjectName(u"sg_spinning_wid")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sg_spinning_wid.sizePolicy().hasHeightForWidth())
        self.sg_spinning_wid.setSizePolicy(sizePolicy)
        self.sg_spinning_wid.setMinimumSize(QSize(0, 83))

        self.horizontalLayout.addWidget(self.sg_spinning_wid)

        self.horizontalSpacer = QSpacerItem(128, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.message = QLabel(Dialog)
        self.message.setObjectName(u"message")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.message.sizePolicy().hasHeightForWidth())
        self.message.setSizePolicy(sizePolicy1)
        self.message.setMaximumSize(QSize(16777215, 18))
        self.message.setAlignment(Qt.AlignHCenter|Qt.AlignTop)
        self.message.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.message)

        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        self.message.setText("")
        pass
    # retranslateUi
