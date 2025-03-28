# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'usb_switch.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QLabel, QRadioButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.setWindowModality(Qt.WindowModal)
        Dialog.resize(375, 300)
        Dialog.setMaximumSize(QSize(443, 300))
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.graphics_label = QLabel(Dialog)
        self.graphics_label.setObjectName(u"graphics_label")

        self.verticalLayout.addWidget(self.graphics_label)

        self.radioButton_master = QRadioButton(Dialog)
        self.radioButton_master.setObjectName(u"radioButton_master")

        self.verticalLayout.addWidget(self.radioButton_master)

        self.radioButton_float = QRadioButton(Dialog)
        self.radioButton_float.setObjectName(u"radioButton_float")

        self.verticalLayout.addWidget(self.radioButton_float)

        self.radioButton_controlled = QRadioButton(Dialog)
        self.radioButton_controlled.setObjectName(u"radioButton_controlled")

        self.verticalLayout.addWidget(self.radioButton_controlled)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"USB Switch", None))
        self.graphics_label.setText(QCoreApplication.translate("Dialog", u"graphicsView", None))
        self.radioButton_master.setText(QCoreApplication.translate("Dialog", u"Master", None))
        self.radioButton_float.setText(QCoreApplication.translate("Dialog", u"Float", None))
        self.radioButton_controlled.setText(QCoreApplication.translate("Dialog", u"Controlled", None))
    # retranslateUi

