# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QStatusBar, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(842, 582)
        self.action_video_devices = QAction(MainWindow)
        self.action_video_devices.setObjectName(u"action_video_devices")
        self.action_video_device_connect = QAction(MainWindow)
        self.action_video_device_connect.setObjectName(u"action_video_device_connect")
        self.action_video_device_disconnect = QAction(MainWindow)
        self.action_video_device_disconnect.setObjectName(u"action_video_device_disconnect")
        self.actionexit = QAction(MainWindow)
        self.actionexit.setObjectName(u"actionexit")
        self.actionfullscreen = QAction(MainWindow)
        self.actionfullscreen.setObjectName(u"actionfullscreen")
        self.actionfullscreen.setCheckable(True)
        self.actionfullscreen.setChecked(False)
        self.actionfullscreen.setShortcutVisibleInContextMenu(False)
        self.actionScreen_recording = QAction(MainWindow)
        self.actionScreen_recording.setObjectName(u"actionScreen_recording")
        self.actionResize_window = QAction(MainWindow)
        self.actionResize_window.setObjectName(u"actionResize_window")
        self.actionResetKeyboard = QAction(MainWindow)
        self.actionResetKeyboard.setObjectName(u"actionResetKeyboard")
        self.actionResetMouse = QAction(MainWindow)
        self.actionResetMouse.setObjectName(u"actionResetMouse")
        self.action_quickkey_1 = QAction(MainWindow)
        self.action_quickkey_1.setObjectName(u"action_quickkey_1")
        self.action_quickkey_2 = QAction(MainWindow)
        self.action_quickkey_2.setObjectName(u"action_quickkey_2")
        self.actionMinimize = QAction(MainWindow)
        self.actionMinimize.setObjectName(u"actionMinimize")
        self.actionReload_Key_Mouse = QAction(MainWindow)
        self.actionReload_Key_Mouse.setObjectName(u"actionReload_Key_Mouse")
        self.actionRelease_mouse = QAction(MainWindow)
        self.actionRelease_mouse.setObjectName(u"actionRelease_mouse")
        self.actionDisplay_System_Mouse = QAction(MainWindow)
        self.actionDisplay_System_Mouse.setObjectName(u"actionDisplay_System_Mouse")
        self.actionCapture_mouse = QAction(MainWindow)
        self.actionCapture_mouse.setObjectName(u"actionCapture_mouse")
        self.actionCustomKey = QAction(MainWindow)
        self.actionCustomKey.setObjectName(u"actionCustomKey")
        self.actionq1 = QAction(MainWindow)
        self.actionq1.setObjectName(u"actionq1")
        self.actionq2 = QAction(MainWindow)
        self.actionq2.setObjectName(u"actionq2")
        self.actionq3 = QAction(MainWindow)
        self.actionq3.setObjectName(u"actionq3")
        self.actionq4 = QAction(MainWindow)
        self.actionq4.setObjectName(u"actionq4")
        self.actionq5 = QAction(MainWindow)
        self.actionq5.setObjectName(u"actionq5")
        self.actionq6 = QAction(MainWindow)
        self.actionq6.setObjectName(u"actionq6")
        self.actionq7 = QAction(MainWindow)
        self.actionq7.setObjectName(u"actionq7")
        self.actionq8 = QAction(MainWindow)
        self.actionq8.setObjectName(u"actionq8")
        self.actionq_8 = QAction(MainWindow)
        self.actionq_8.setObjectName(u"actionq_8")
        self.actionq9 = QAction(MainWindow)
        self.actionq9.setObjectName(u"actionq9")
        self.actionq10 = QAction(MainWindow)
        self.actionq10.setObjectName(u"actionq10")
        self.actionOn_screen_Keyboard = QAction(MainWindow)
        self.actionOn_screen_Keyboard.setObjectName(u"actionOn_screen_Keyboard")
        self.actionCalculator = QAction(MainWindow)
        self.actionCalculator.setObjectName(u"actionCalculator")
        self.actionSnippingTool = QAction(MainWindow)
        self.actionSnippingTool.setObjectName(u"actionSnippingTool")
        self.actionNotepad = QAction(MainWindow)
        self.actionNotepad.setObjectName(u"actionNotepad")
        self.actionIndicator_light = QAction(MainWindow)
        self.actionIndicator_light.setObjectName(u"actionIndicator_light")
        self.actionReload_MCU = QAction(MainWindow)
        self.actionReload_MCU.setObjectName(u"actionReload_MCU")
        self.action_fullscreen = QAction(MainWindow)
        self.action_fullscreen.setObjectName(u"action_fullscreen")
        self.action_Resize_window = QAction(MainWindow)
        self.action_Resize_window.setObjectName(u"action_Resize_window")
        self.actionKeep_ratio = QAction(MainWindow)
        self.actionKeep_ratio.setObjectName(u"actionKeep_ratio")
        self.actionKeep_on_top = QAction(MainWindow)
        self.actionKeep_on_top.setObjectName(u"actionKeep_on_top")
        self.actionPaste_board = QAction(MainWindow)
        self.actionPaste_board.setObjectName(u"actionPaste_board")
        self.actionHide_cursor = QAction(MainWindow)
        self.actionHide_cursor.setObjectName(u"actionHide_cursor")
        self.actionCaps_Lock = QAction(MainWindow)
        self.actionCaps_Lock.setObjectName(u"actionCaps_Lock")
        self.actionScroll_Lock = QAction(MainWindow)
        self.actionScroll_Lock.setObjectName(u"actionScroll_Lock")
        self.actionNum_Lock = QAction(MainWindow)
        self.actionNum_Lock.setObjectName(u"actionNum_Lock")
        self.actionDark_theme = QAction(MainWindow)
        self.actionDark_theme.setObjectName(u"actionDark_theme")
        self.actionCapture_frame = QAction(MainWindow)
        self.actionCapture_frame.setObjectName(u"actionCapture_frame")
        self.actionRGB = QAction(MainWindow)
        self.actionRGB.setObjectName(u"actionRGB")
        self.actionQuick_paste = QAction(MainWindow)
        self.actionQuick_paste.setObjectName(u"actionQuick_paste")
        self.actionWindows_Audio_Setting = QAction(MainWindow)
        self.actionWindows_Audio_Setting.setObjectName(u"actionWindows_Audio_Setting")
        self.actionWindows_Device_Manager = QAction(MainWindow)
        self.actionWindows_Device_Manager.setObjectName(u"actionWindows_Device_Manager")
        self.actionNum_Keyboard = QAction(MainWindow)
        self.actionNum_Keyboard.setObjectName(u"actionNum_Keyboard")
        self.actionRecord_video = QAction(MainWindow)
        self.actionRecord_video.setObjectName(u"actionRecord_video")
        self.actionOpen_Server_Manager = QAction(MainWindow)
        self.actionOpen_Server_Manager.setObjectName(u"actionOpen_Server_Manager")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.serverFrame = QFrame(self.centralwidget)
        self.serverFrame.setObjectName(u"serverFrame")
        self.serverFrame.setGeometry(QRect(40, 20, 691, 511))
        self.serverFrame.setFrameShape(QFrame.StyledPanel)
        self.serverFrame.setFrameShadow(QFrame.Plain)
        self.verticalLayout_6 = QVBoxLayout(self.serverFrame)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.serverSettingFrame = QFrame(self.serverFrame)
        self.serverSettingFrame.setObjectName(u"serverSettingFrame")
        self.serverSettingFrame.setFrameShape(QFrame.StyledPanel)
        self.serverSettingFrame.setFrameShadow(QFrame.Plain)
        self.verticalLayout_5 = QVBoxLayout(self.serverSettingFrame)
        self.verticalLayout_5.setSpacing(3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(-1, 3, 3, 3)
        self.label_4 = QLabel(self.serverSettingFrame)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignCenter)

        self.verticalLayout_5.addWidget(self.label_4)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_3)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(5, -1, 3, -1)
        self.label_2 = QLabel(self.serverSettingFrame)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.label = QLabel(self.serverSettingFrame)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.label_3 = QLabel(self.serverSettingFrame)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.kvmSetHostLine = QLineEdit(self.serverSettingFrame)
        self.kvmSetHostLine.setObjectName(u"kvmSetHostLine")
        self.kvmSetHostLine.setMaximumSize(QSize(70, 16777215))

        self.verticalLayout_2.addWidget(self.kvmSetHostLine)

        self.kvmSetPortSpin = QSpinBox(self.serverSettingFrame)
        self.kvmSetPortSpin.setObjectName(u"kvmSetPortSpin")
        self.kvmSetPortSpin.setMinimumSize(QSize(70, 0))
        self.kvmSetPortSpin.setMaximum(32768)
        self.kvmSetPortSpin.setValue(5000)

        self.verticalLayout_2.addWidget(self.kvmSetPortSpin)

        self.kvmSetQualitySpin = QSpinBox(self.serverSettingFrame)
        self.kvmSetQualitySpin.setObjectName(u"kvmSetQualitySpin")
        self.kvmSetQualitySpin.setMaximum(100)
        self.kvmSetQualitySpin.setValue(60)

        self.verticalLayout_2.addWidget(self.kvmSetQualitySpin)


        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(5, -1, 3, -1)
        self.label_5 = QLabel(self.serverSettingFrame)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout_3.addWidget(self.label_5)

        self.label_6 = QLabel(self.serverSettingFrame)
        self.label_6.setObjectName(u"label_6")

        self.verticalLayout_3.addWidget(self.label_6)

        self.label_7 = QLabel(self.serverSettingFrame)
        self.label_7.setObjectName(u"label_7")

        self.verticalLayout_3.addWidget(self.label_7)


        self.horizontalLayout.addLayout(self.verticalLayout_3)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.kvmSetDeviceCombo = QComboBox(self.serverSettingFrame)
        self.kvmSetDeviceCombo.setObjectName(u"kvmSetDeviceCombo")
        self.kvmSetDeviceCombo.setMinimumSize(QSize(100, 0))
        self.kvmSetDeviceCombo.setSizeIncrement(QSize(0, 0))
        self.kvmSetDeviceCombo.setBaseSize(QSize(0, 0))

        self.verticalLayout_4.addWidget(self.kvmSetDeviceCombo)

        self.kvmSetResCombo = QComboBox(self.serverSettingFrame)
        self.kvmSetResCombo.setObjectName(u"kvmSetResCombo")

        self.verticalLayout_4.addWidget(self.kvmSetResCombo)

        self.kvmSetFpsSpin = QSpinBox(self.serverSettingFrame)
        self.kvmSetFpsSpin.setObjectName(u"kvmSetFpsSpin")
        self.kvmSetFpsSpin.setMaximum(60)
        self.kvmSetFpsSpin.setValue(60)

        self.verticalLayout_4.addWidget(self.kvmSetFpsSpin)


        self.horizontalLayout.addLayout(self.verticalLayout_4)

        self.horizontalSpacer_8 = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_8)

        self.btnServerSwitch = QPushButton(self.serverSettingFrame)
        self.btnServerSwitch.setObjectName(u"btnServerSwitch")
        self.btnServerSwitch.setMinimumSize(QSize(60, 60))
        self.btnServerSwitch.setMaximumSize(QSize(60, 60))
        font = QFont()
        font.setBold(False)
        self.btnServerSwitch.setFont(font)
        self.btnServerSwitch.setIconSize(QSize(35, 35))

        self.horizontalLayout.addWidget(self.btnServerSwitch)

        self.horizontalSpacer_9 = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_9)

        self.btnServerSetAuth = QPushButton(self.serverSettingFrame)
        self.btnServerSetAuth.setObjectName(u"btnServerSetAuth")
        self.btnServerSetAuth.setMinimumSize(QSize(60, 60))
        self.btnServerSetAuth.setMaximumSize(QSize(60, 60))
        self.btnServerSetAuth.setFont(font)
        self.btnServerSetAuth.setIconSize(QSize(35, 35))

        self.horizontalLayout.addWidget(self.btnServerSetAuth)

        self.horizontalSpacer_10 = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_10)

        self.btnServerOpenBrowser = QPushButton(self.serverSettingFrame)
        self.btnServerOpenBrowser.setObjectName(u"btnServerOpenBrowser")
        self.btnServerOpenBrowser.setMinimumSize(QSize(60, 60))
        self.btnServerOpenBrowser.setMaximumSize(QSize(60, 60))
        self.btnServerOpenBrowser.setFont(font)
        self.btnServerOpenBrowser.setIconSize(QSize(35, 35))

        self.horizontalLayout.addWidget(self.btnServerOpenBrowser)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.verticalLayout_5.addLayout(self.horizontalLayout)


        self.verticalLayout_6.addWidget(self.serverSettingFrame)

        self.serverLogEdit = QTextEdit(self.serverFrame)
        self.serverLogEdit.setObjectName(u"serverLogEdit")
        self.serverLogEdit.setFocusPolicy(Qt.NoFocus)
        self.serverLogEdit.setFrameShadow(QFrame.Plain)
        self.serverLogEdit.setLineWidth(1)
        self.serverLogEdit.setAutoFormatting(QTextEdit.AutoAll)
        self.serverLogEdit.setReadOnly(True)

        self.verticalLayout_6.addWidget(self.serverLogEdit)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 842, 21))
        self.menu_video_menu = QMenu(self.menubar)
        self.menu_video_menu.setObjectName(u"menu_video_menu")
        self.menuKeyboard = QMenu(self.menubar)
        self.menuKeyboard.setObjectName(u"menuKeyboard")
        self.menuShortcut_key = QMenu(self.menuKeyboard)
        self.menuShortcut_key.setObjectName(u"menuShortcut_key")
        self.menuMouse = QMenu(self.menubar)
        self.menuMouse.setObjectName(u"menuMouse")
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName(u"menuTools")
        self.menuVideo = QMenu(self.menubar)
        self.menuVideo.setObjectName(u"menuVideo")
        self.menuServer = QMenu(self.menubar)
        self.menuServer.setObjectName(u"menuServer")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setSizeGripEnabled(False)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_video_menu.menuAction())
        self.menubar.addAction(self.menuVideo.menuAction())
        self.menubar.addAction(self.menuKeyboard.menuAction())
        self.menubar.addAction(self.menuMouse.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuServer.menuAction())
        self.menu_video_menu.addAction(self.action_video_devices)
        self.menu_video_menu.addAction(self.action_video_device_connect)
        self.menu_video_menu.addAction(self.action_video_device_disconnect)
        self.menu_video_menu.addSeparator()
        self.menu_video_menu.addAction(self.actionReload_MCU)
        self.menu_video_menu.addAction(self.actionReload_Key_Mouse)
        self.menu_video_menu.addSeparator()
        self.menu_video_menu.addAction(self.actionDark_theme)
        self.menu_video_menu.addAction(self.actionRGB)
        self.menu_video_menu.addSeparator()
        self.menu_video_menu.addAction(self.actionMinimize)
        self.menu_video_menu.addAction(self.actionexit)
        self.menuKeyboard.addAction(self.actionResetKeyboard)
        self.menuKeyboard.addSeparator()
        self.menuKeyboard.addAction(self.menuShortcut_key.menuAction())
        self.menuKeyboard.addAction(self.actionCustomKey)
        self.menuKeyboard.addSeparator()
        self.menuKeyboard.addAction(self.actionPaste_board)
        self.menuKeyboard.addAction(self.actionQuick_paste)
        self.menuKeyboard.addSeparator()
        self.menuKeyboard.addAction(self.actionIndicator_light)
        self.menuKeyboard.addAction(self.actionNum_Keyboard)
        self.menuMouse.addAction(self.actionResetMouse)
        self.menuMouse.addSeparator()
        self.menuMouse.addAction(self.actionCapture_mouse)
        self.menuMouse.addAction(self.actionRelease_mouse)
        self.menuMouse.addSeparator()
        self.menuMouse.addAction(self.actionHide_cursor)
        self.menuTools.addAction(self.actionWindows_Device_Manager)
        self.menuTools.addAction(self.actionWindows_Audio_Setting)
        self.menuTools.addAction(self.actionOn_screen_Keyboard)
        self.menuTools.addAction(self.actionCalculator)
        self.menuTools.addAction(self.actionSnippingTool)
        self.menuTools.addAction(self.actionNotepad)
        self.menuVideo.addAction(self.action_fullscreen)
        self.menuVideo.addAction(self.action_Resize_window)
        self.menuVideo.addAction(self.actionKeep_on_top)
        self.menuVideo.addSeparator()
        self.menuVideo.addAction(self.actionKeep_ratio)
        self.menuVideo.addAction(self.actionCapture_frame)
        self.menuVideo.addAction(self.actionRecord_video)
        self.menuServer.addAction(self.actionOpen_Server_Manager)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"USB KVM Client", None))
        self.action_video_devices.setText(QCoreApplication.translate("MainWindow", u"Video devices", None))
#if QT_CONFIG(shortcut)
        self.action_video_devices.setShortcut("")
#endif // QT_CONFIG(shortcut)
        self.action_video_device_connect.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.action_video_device_disconnect.setText(QCoreApplication.translate("MainWindow", u"Disconnect", None))
        self.actionexit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.actionfullscreen.setText(QCoreApplication.translate("MainWindow", u"Full screen", None))
        self.actionScreen_recording.setText(QCoreApplication.translate("MainWindow", u"Screen recording", None))
        self.actionResize_window.setText(QCoreApplication.translate("MainWindow", u"Resize window", None))
        self.actionResetKeyboard.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.actionResetMouse.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.action_quickkey_1.setText(QCoreApplication.translate("MainWindow", u"Ctrl+Alt+Del", None))
        self.action_quickkey_2.setText(QCoreApplication.translate("MainWindow", u"Alt+Tab", None))
        self.actionMinimize.setText(QCoreApplication.translate("MainWindow", u"Minimize", None))
        self.actionReload_Key_Mouse.setText(QCoreApplication.translate("MainWindow", u"Reload Key/Mouse", None))
        self.actionRelease_mouse.setText(QCoreApplication.translate("MainWindow", u"Release mouse", None))
        self.actionDisplay_System_Mouse.setText(QCoreApplication.translate("MainWindow", u"Display system mouse", None))
        self.actionCapture_mouse.setText(QCoreApplication.translate("MainWindow", u"Capture mouse", None))
        self.actionCustomKey.setText(QCoreApplication.translate("MainWindow", u"Custom key", None))
        self.actionq1.setText(QCoreApplication.translate("MainWindow", u"q1", None))
        self.actionq2.setText(QCoreApplication.translate("MainWindow", u"q2", None))
        self.actionq3.setText(QCoreApplication.translate("MainWindow", u"q3", None))
        self.actionq4.setText(QCoreApplication.translate("MainWindow", u"q4", None))
        self.actionq5.setText(QCoreApplication.translate("MainWindow", u"q5", None))
        self.actionq6.setText(QCoreApplication.translate("MainWindow", u"q6", None))
        self.actionq7.setText(QCoreApplication.translate("MainWindow", u"q7", None))
        self.actionq8.setText(QCoreApplication.translate("MainWindow", u"q8", None))
        self.actionq_8.setText(QCoreApplication.translate("MainWindow", u"q8", None))
        self.actionq9.setText(QCoreApplication.translate("MainWindow", u"q9", None))
        self.actionq10.setText(QCoreApplication.translate("MainWindow", u"q10", None))
        self.actionOn_screen_Keyboard.setText(QCoreApplication.translate("MainWindow", u"On-screen Keyboard", None))
        self.actionCalculator.setText(QCoreApplication.translate("MainWindow", u"Calculator", None))
        self.actionSnippingTool.setText(QCoreApplication.translate("MainWindow", u"SnippingTool", None))
        self.actionNotepad.setText(QCoreApplication.translate("MainWindow", u"Notepad", None))
        self.actionIndicator_light.setText(QCoreApplication.translate("MainWindow", u"Indicator light", None))
        self.actionReload_MCU.setText(QCoreApplication.translate("MainWindow", u"Reload MCU", None))
        self.action_fullscreen.setText(QCoreApplication.translate("MainWindow", u"Full screen", None))
        self.action_Resize_window.setText(QCoreApplication.translate("MainWindow", u"Resize window", None))
        self.actionKeep_ratio.setText(QCoreApplication.translate("MainWindow", u"Keep aspect ratio", None))
        self.actionKeep_on_top.setText(QCoreApplication.translate("MainWindow", u"Always on top", None))
        self.actionPaste_board.setText(QCoreApplication.translate("MainWindow", u"Paste board", None))
        self.actionHide_cursor.setText(QCoreApplication.translate("MainWindow", u"Hide cursor", None))
        self.actionCaps_Lock.setText(QCoreApplication.translate("MainWindow", u"Caps Lock", None))
        self.actionScroll_Lock.setText(QCoreApplication.translate("MainWindow", u"Scroll Lock", None))
        self.actionNum_Lock.setText(QCoreApplication.translate("MainWindow", u"Num Lock", None))
        self.actionDark_theme.setText(QCoreApplication.translate("MainWindow", u"Dark theme", None))
        self.actionCapture_frame.setText(QCoreApplication.translate("MainWindow", u"Capture frame", None))
        self.actionRGB.setText(QCoreApplication.translate("MainWindow", u"RGB Led", None))
        self.actionQuick_paste.setText(QCoreApplication.translate("MainWindow", u"Quick paste", None))
        self.actionWindows_Audio_Setting.setText(QCoreApplication.translate("MainWindow", u"Windows Audio Settings", None))
        self.actionWindows_Device_Manager.setText(QCoreApplication.translate("MainWindow", u"Windows Device Manager", None))
        self.actionNum_Keyboard.setText(QCoreApplication.translate("MainWindow", u"Num Keyboard", None))
        self.actionRecord_video.setText(QCoreApplication.translate("MainWindow", u"Record video", None))
        self.actionOpen_Server_Manager.setText(QCoreApplication.translate("MainWindow", u"Open Server Manager", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"KVM Server Settings", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Host:", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Port:", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Quality:", None))
        self.kvmSetHostLine.setText(QCoreApplication.translate("MainWindow", u"0.0.0.0", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Video device:", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Resolution:", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"FPS(prefer):", None))
        self.btnServerSwitch.setText("")
        self.btnServerSetAuth.setText("")
        self.btnServerOpenBrowser.setText("")
        self.serverLogEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"No log output", None))
        self.menu_video_menu.setTitle(QCoreApplication.translate("MainWindow", u"Device", None))
        self.menuKeyboard.setTitle(QCoreApplication.translate("MainWindow", u"Keyboard", None))
        self.menuShortcut_key.setTitle(QCoreApplication.translate("MainWindow", u"Shortcut key", None))
        self.menuMouse.setTitle(QCoreApplication.translate("MainWindow", u"Mouse", None))
        self.menuTools.setTitle(QCoreApplication.translate("MainWindow", u"Tools", None))
        self.menuVideo.setTitle(QCoreApplication.translate("MainWindow", u"Video", None))
        self.menuServer.setTitle(QCoreApplication.translate("MainWindow", u"Server", None))
    # retranslateUi

