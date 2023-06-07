import datetime
import os
import random
import re
import sys
import time
from typing import Tuple

import yaml  # type: ignore
from module import hid_def
from PyQt5 import QtGui
from PyQt5.QtCore import QEventLoop, QSize, Qt, QTimer
from PyQt5.QtGui import QCursor, QIcon, QImage, QPixmap
from PyQt5.QtMultimedia import (
    QCamera,
    QCameraImageCapture,
    QCameraInfo,
    QCameraViewfinderSettings,
    QImageEncoderSettings,
    QMultimedia,
    QVideoFrame,
)
from PyQt5.QtMultimediaWidgets import QCameraViewfinder
from PyQt5.QtWidgets import (
    QApplication,
    QDesktopWidget,
    QDialogButtonBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
)
from PyQt5.uic import loadUi
from ui import main_ui

"""
qdarktheme import after pyqt5
"""
import qdarktheme

buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
mouse_buffer = [2, 0, 0, 0, 0, 0, 0, 0, 0]
shift_symbol = [
    ")","!","@","#","$","%",
    "^","&","*","(","~","_",
    "+","{","}","|",":",'"',
    "<",">","?",
]  # fmt: skip
PATH = os.path.dirname(os.path.abspath(__file__))

dark_theme = True


# 屏蔽所有print
def print(*args, **kwargs):
    pass


def strB2Q(uchar):
    inside_code = ord(uchar)
    if inside_code == 0x3000:
        inside_code = 0x0020
    else:
        inside_code -= 0xFEE0
    if inside_code < 0x0020 or inside_code > 0x7E:  # 转完之后不是半角字符返回原来的字符
        return uchar
    return chr(inside_code)


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV color space to RGB color space.
    :param h: Hue, range in [0, 1)
    :param s: Saturation, range in [0, 1]
    :param v: Value, range in [0, 1]
    :return: RGB color space
    """
    if s == 0.0:
        return int(v * 255), int(v * 255), int(v * 255)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return int(v * 255), int(t * 255), int(p * 255)
    elif i == 1:
        return int(q * 255), int(v * 255), int(p * 255)
    elif i == 2:
        return int(p * 255), int(v * 255), int(t * 255)
    elif i == 3:
        return int(p * 255), int(q * 255), int(v * 255)
    elif i == 4:
        return int(t * 255), int(p * 255), int(v * 255)
    elif i == 5:
        return int(v * 255), int(p * 255), int(q * 255)
    return 0, 0, 0


def load_icon(name, dark_override=None) -> QIcon:
    if dark_override is not None:
        judge = dark_override
    else:
        judge = dark_theme
    if judge:
        return QIcon(f"{PATH}/ui/images/24_dark/{name}.png")
    else:
        return QIcon(f"{PATH}/ui/images/24_light/{name}.png")


def load_pixmap(name, dark_override=None) -> QPixmap:
    if dark_override is not None:
        judge = dark_override
    else:
        judge = dark_theme
    if judge:
        return QPixmap(f"{PATH}/ui/images/24_dark/{name}.png")
    else:
        return QPixmap(f"{PATH}/ui/images/24_light/{name}.png")


class MyPushButton(QPushButton):
    def __init__(self, parent=None):
        super(MyPushButton, self).__init__(parent)

    def setPixmap(self, pixmap):
        icon = QIcon(pixmap)
        self.setIcon(icon)
        self.setIconSize(QSize(18, 18))


class MyMainWindow(QMainWindow, main_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        self.ignore_event = False
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)

        self.camera = None
        self.camera_opened = False

        # 子窗口
        self.device_setup_dialog = loadUi(os.path.join(PATH, "ui", "device_setup_dialog.ui"))
        self.device_setup_dialog.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.device_setup_dialog.setWindowFlags(self.device_setup_dialog.windowFlags() | Qt.WindowStaysOnTopHint)

        self.shortcut_key_dialog = loadUi(os.path.join(PATH, "ui", "shortcut_key.ui"))
        self.shortcut_key_dialog.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.shortcut_key_dialog.setWindowFlags(self.shortcut_key_dialog.windowFlags() | Qt.WindowStaysOnTopHint)

        self.paste_board_dialog = loadUi(os.path.join(PATH, "ui", "paste_board.ui"))
        self.paste_board_dialog.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.paste_board_dialog.setWindowFlags(self.paste_board_dialog.windowFlags() | Qt.WindowStaysOnTopHint)

        self.indicator_dialog = loadUi(os.path.join(PATH, "ui", "indicator.ui"))
        self.indicator_dialog.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.indicator_dialog.setWindowFlags(self.indicator_dialog.windowFlags() | Qt.WindowStaysOnTopHint)

        self.shortcut_key_dialog.pushButtonSend.released.connect(lambda: self.shortcut_key_func(1))
        self.shortcut_key_dialog.pushButtonSend.pressed.connect(lambda: self.shortcut_key_func(2))
        self.shortcut_key_dialog.pushButtonSave.clicked.connect(lambda: self.shortcut_key_func(3))

        self.shortcut_key_dialog.pushButton_ctrl.clicked.connect(lambda: self.shortcut_key_handle(1))
        self.shortcut_key_dialog.pushButton_alt.clicked.connect(lambda: self.shortcut_key_handle(4))
        self.shortcut_key_dialog.pushButton_shift.clicked.connect(lambda: self.shortcut_key_handle(2))
        self.shortcut_key_dialog.pushButton_meta.clicked.connect(lambda: self.shortcut_key_handle(8))
        self.shortcut_key_dialog.pushButton_tab.clicked.connect(lambda: self.shortcut_key_handle(0x2B))
        self.shortcut_key_dialog.pushButton_prtsc.clicked.connect(lambda: self.shortcut_key_handle(0x46))
        self.shortcut_key_dialog.keySequenceEdit.keySequenceChanged.connect(lambda: self.shortcut_key_handle(0xFF))
        self.shortcut_key_dialog.pushButton_clear.clicked.connect(lambda: self.shortcut_key_handle(0xFE))

        self.paste_board_dialog.pushButtonSend.clicked.connect(lambda: self.paste_board_send())
        self.paste_board_dialog.pushButtonStop.clicked.connect(lambda: self.paste_board_stop())

        self.indicator_dialog.pushButtonNum.clicked.connect(lambda: self.lock_key_func(2))
        self.indicator_dialog.pushButtonCaps.clicked.connect(lambda: self.lock_key_func(1))
        self.indicator_dialog.pushButtonScroll.clicked.connect(lambda: self.lock_key_func(3))
        # 导入外部数据
        try:
            with open("./data/keyboard_hid2code.yaml", "r") as load_f:
                self.keyboard_hid2code = yaml.safe_load(load_f)
            with open("./data/keyboard_scancode2hid.yml", "r") as load_f:
                self.keyboard_scancode2hid = yaml.safe_load(load_f)
            with open("./data/keyboard.yaml", "r") as load_f:
                self.keyboard_code = yaml.safe_load(load_f)
            with open("./data/config.yaml", "r") as load_f:
                self.configfile = yaml.safe_load(load_f)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Import data error:\n {e}\n\nCheck the folder ./data and restart the program"
            )
            sys.exit(1)
        # 加载配置文件
        self.camera_config = self.configfile["camera_config"]
        self.config = self.configfile["config"]
        self.status = {
            "fullscreen": False,
            "topmost": False,
            "mouse_capture": False,
            "hide_cursor": False,
            "init_ok": False,
            "screen_height": 0,
            "screen_width": 0,
            "RGB_mode": False,
        }

        if self.configfile["config"]["debug"]:
            hid_def.set_debug(True)

        global dark_theme
        dark_theme = self.configfile["config"]["dark_theme"]
        if dark_theme:
            self.set_font_bold(self.actionDark_theme, True)

        # 获取显示器分辨率大小
        self.desktop = QApplication.desktop()
        self.status["screen_height"] = self.desktop.screenGeometry().height()
        self.status["screen_width"] = self.desktop.screenGeometry().width()

        # 窗口图标
        self.setWindowIcon(QtGui.QIcon(f"{PATH}/ui/images/icon.ico"))
        self.device_setup_dialog.setWindowIcon(load_icon("import", False))
        self.shortcut_key_dialog.setWindowIcon(load_icon("keyboard-settings-outline", False))
        self.paste_board_dialog.setWindowIcon(load_icon("paste", False))
        self.indicator_dialog.setWindowIcon(load_icon("capslock", False))

        # 状态栏图标
        self.statusbar_lable1 = QLabel()
        self.statusbar_lable2 = QLabel()
        self.statusbar_lable3 = QLabel()
        self.statusbar_lable4 = QLabel()
        font = QtGui.QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setBold(True)
        self.statusbar_lable1.setFont(font)
        self.statusbar_lable2.setFont(font)
        self.statusbar_lable3.setFont(font)
        self.statusbar_lable4.setFont(font)
        self.statusbar_lable1.setText("CTRL")
        self.statusbar_lable2.setText("SHIFT")
        self.statusbar_lable3.setText("ALT")
        self.statusbar_lable4.setText("META")
        self.statusbar_lable1.setStyleSheet("color: grey")
        self.statusbar_lable2.setStyleSheet("color: grey")
        self.statusbar_lable3.setStyleSheet("color: grey")
        self.statusbar_lable4.setStyleSheet("color: grey")

        self.statusbar_btn1 = MyPushButton()
        self.statusbar_btn2 = MyPushButton()
        self.statusbar_btn3 = MyPushButton()
        self.statusbar_btn1.setPixmap(load_pixmap("keyboard-settings-outline"))
        self.statusbar_btn2.setPixmap(load_pixmap("paste"))
        self.statusbar_btn3.setPixmap(load_pixmap("capslock"))

        self.statusbar_icon1 = MyPushButton()
        self.statusbar_icon2 = MyPushButton()
        self.statusbar_icon3 = MyPushButton()
        self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
        self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
        self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))

        self.statusBar().setStyleSheet("padding: 0px;")
        self.statusBar().addPermanentWidget(self.statusbar_lable1)
        self.statusBar().addPermanentWidget(self.statusbar_lable2)
        self.statusBar().addPermanentWidget(self.statusbar_lable3)
        self.statusBar().addPermanentWidget(self.statusbar_lable4)
        self.statusBar().addPermanentWidget(self.statusbar_btn1)
        self.statusBar().addPermanentWidget(self.statusbar_btn2)
        self.statusBar().addPermanentWidget(self.statusbar_btn3)
        self.statusBar().addPermanentWidget(self.statusbar_icon1)
        self.statusBar().addPermanentWidget(self.statusbar_icon2)
        self.statusBar().addPermanentWidget(self.statusbar_icon3)

        self.statusbar_btn1.clicked.connect(lambda: self.statusbar_func(1))
        self.statusbar_btn2.clicked.connect(lambda: self.statusbar_func(2))
        self.statusbar_btn3.clicked.connect(lambda: self.statusbar_func(3))
        self.statusbar_icon1.clicked.connect(lambda: self.statusbar_func(4))
        self.statusbar_icon2.clicked.connect(lambda: self.statusbar_func(5))
        self.statusbar_icon3.clicked.connect(lambda: self.statusbar_func(6))

        # 菜单栏图标
        self.action_video_devices.setIcon(load_icon("import"))
        self.action_video_device_connect.setIcon(load_icon("video"))
        self.action_video_device_disconnect.setIcon(load_icon("video-off"))
        self.actionMinimize.setIcon(load_icon("window-minimize"))
        self.actionexit.setIcon(load_icon("window-close"))
        self.actionReload_MCU.setIcon(load_icon("reload"))
        self.actionReload_Key_Mouse.setIcon(load_icon("reload"))
        self.action_fullscreen.setIcon(load_icon("fullscreen"))
        self.action_Resize_window.setIcon(load_icon("resize"))
        self.actionKeep_ratio.setIcon(load_icon("ratio"))
        self.actionResetKeyboard.setIcon(load_icon("reload"))
        self.actionResetMouse.setIcon(load_icon("reload"))
        self.menuShortcut_key.setIcon(load_icon("keyboard-outline"))
        self.actionCustomKey.setIcon(load_icon("keyboard-settings-outline"))
        self.actionCapture_mouse.setIcon(load_icon("mouse"))
        self.actionRelease_mouse.setIcon(load_icon("mouse-off"))
        self.actionOn_screen_Keyboard.setIcon(load_icon("keyboard-variant"))
        self.actionCalculator.setIcon(load_icon("calculator"))
        self.actionSnippingTool.setIcon(load_icon("monitor-screenshot"))
        self.actionNotepad.setIcon(load_icon("notebook-edit"))
        self.actionIndicator_light.setIcon(load_icon("capslock"))
        self.actionKeep_on_top.setIcon(load_icon("topmost"))
        self.actionPaste_board.setIcon(load_icon("paste"))
        self.actionHide_cursor.setIcon(load_icon("cursor"))
        self.actionDark_theme.setIcon(load_icon("night"))
        self.actionCapture_frame.setIcon(load_icon("capture"))
        self.actionRGB.setIcon(load_icon("RGB"))

        if self.configfile["camera_config"]["keep_aspect_ratio"]:
            self.set_font_bold(self.actionKeep_ratio, True)

        # 初始化监视器
        self.camerafinder = QCameraViewfinder()
        self.setCentralWidget(self.camerafinder)
        self.camerafinder.hide()

        self.disconnect_label = QLabel()
        self.disconnect_label.setPixmap(load_pixmap("disconnected"))
        self.disconnect_label.setAlignment(Qt.AlignCenter)
        self.disconnect_label.setMouseTracking(True)
        self.takeCentralWidget()
        self.setCentralWidget(self.disconnect_label)
        self.disconnect_label.show()

        # 快捷键菜单设置快捷键名称
        for i, name in enumerate(self.configfile["shortcut_key"]["shortcut_key_name"]):
            action = self.menuShortcut_key.addAction(name)
            action.triggered.connect(lambda checked, i=i: self.shortcut_key_action(i))

        # 按键绑定
        self.action_video_device_connect.triggered.connect(lambda: self.set_webcam(True))
        self.action_video_device_disconnect.triggered.connect(lambda: self.set_webcam(False))
        self.action_video_devices.triggered.connect(self.device_config)
        self.actionCustomKey.triggered.connect(self.shortcut_key_func)
        self.actionReload_Key_Mouse.triggered.connect(lambda: self.reset_keymouse(4))
        self.actionMinimize.triggered.connect(self.window_minimized)
        self.actionexit.triggered.connect(sys.exit)

        self.device_setup_dialog.comboBox.currentIndexChanged.connect(self.update_device_setup_resolutions)

        self.action_fullscreen.triggered.connect(self.fullscreen_func)
        self.action_Resize_window.triggered.connect(self.resize_window_func)
        self.actionKeep_ratio.triggered.connect(self.keep_ratio_func)
        self.actionKeep_on_top.triggered.connect(self.topmost_func)
        self.actionCapture_frame.triggered.connect(self.capture_to_file)

        self.actionRelease_mouse.triggered.connect(self.release_mouse)
        self.actionCapture_mouse.triggered.connect(self.capture_mouse)
        self.actionResetKeyboard.triggered.connect(lambda: self.reset_keymouse(1))
        self.actionResetMouse.triggered.connect(lambda: self.reset_keymouse(3))
        self.actionIndicator_light.triggered.connect(self.indicatorLight_func)
        self.actionReload_MCU.triggered.connect(lambda: self.reset_keymouse(2))

        self.actionPaste_board.triggered.connect(self.paste_board_func)
        self.actionHide_cursor.triggered.connect(self.hide_cursor_func)

        self.actionOn_screen_Keyboard.triggered.connect(lambda: self.menu_tools_actions(0))
        self.actionCalculator.triggered.connect(lambda: self.menu_tools_actions(1))
        self.actionSnippingTool.triggered.connect(lambda: self.menu_tools_actions(2))
        self.actionNotepad.triggered.connect(lambda: self.menu_tools_actions(3))

        self.actionDark_theme.triggered.connect(self.dark_theme_func)
        self.actionRGB.triggered.connect(self.RGB_func)
        self.paste_board_dialog.pushButtonFile.clicked.connect(self.paste_board_file_select)

        # 设置聚焦方式
        self.statusbar_btn1.setFocusPolicy(Qt.NoFocus)
        self.statusbar_btn2.setFocusPolicy(Qt.NoFocus)
        self.statusbar_btn3.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon1.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon2.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon3.setFocusPolicy(Qt.NoFocus)

        # self.camerafinder.setFocusPolicy(Qt.NoFocus)
        # self.statusBar().setFocusPolicy(Qt.NoFocus)
        # self.statusBar().setFocusPolicy(Qt.NoFocus)
        # self.setFocusPolicy(Qt.StrongFocus)

        self.fullscreen_alert_showed = False
        self.mouse_action_timer = QTimer()
        self.mouse_action_timer.timeout.connect(self.mouse_action_timeout)

        # 初始化hid设备
        self.reset_keymouse(4)
        # 创建指针对象
        self.cursor = QCursor()
        self.setMouseTracking(True)
        self.camerafinder.setMouseTracking(True)

        self.mouse_scroll_timer = QTimer()
        self.mouse_scroll_timer.timeout.connect(self.mouse_scroll_stop)

        self.status["init_ok"] = True

        if self.configfile["camera_config"]["auto_connect"]:
            self.device_setup_dialog.checkBoxAutoConnect.setChecked(True)
            QTimer().singleShot(1000, lambda: self.set_webcam(True))

    def statusbar_func(self, act):
        # print(f"action={act}")
        if act == 1:
            if self.shortcut_key_dialog.isVisible():
                self.shortcut_key_dialog.close()
            else:
                self.shortcut_key_func(0)
        elif act == 2:
            if self.paste_board_dialog.isVisible():
                self.paste_board_dialog.close()
            else:
                self.paste_board_func()
        elif act == 3:
            if self.indicator_dialog.isVisible():
                self.indicator_dialog.close()
            else:
                self.indicatorLight_func()
        elif act == 4:
            self.device_config()
        elif act == 5:
            self.reset_keymouse(4)
        elif act == 6:
            if self.status["mouse_capture"]:
                self.release_mouse()
                self.statusBar().showMessage("Mouse capture off")
            else:
                self.capture_mouse()

    def set_font_bold(self, attr, bold):
        font = attr.font()
        font.setBold(bold)
        attr.setFont(font)

    def save_config(self):
        # 保存配置文件
        with open("./data/config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(self.configfile, f)

    # 弹出采集卡设备设置窗口，并打开采集卡设备
    def device_config(self):
        self.device_setup_dialog.comboBox.clear()

        # 遍历相机设备
        cameras = QCameraInfo()
        remember_name = self.camera_config["device_name"][self.camera_config["device_No"]]
        self.camera_config["device_name"] = []
        for i in cameras.availableCameras():
            self.camera_config["device_name"].append(i.description())
            self.device_setup_dialog.comboBox.addItem(i.description())

        # 将设备设置为字典camera_config中指定的设备
        if remember_name in self.camera_config["device_name"]:
            self.camera_config["device_No"] = self.camera_config["device_name"].index(remember_name)
            self.device_setup_dialog.comboBox.setCurrentIndex(self.camera_config["device_No"])
            resolution_str = str(self.camera_config["resolution_X"]) + "x" + str(self.camera_config["resolution_Y"])
            self.device_setup_dialog.comboBox_2.setCurrentText(resolution_str)
            self.device_setup_dialog.comboBox_3.setCurrentText(self.camera_config["format"])
        else:
            self.device_setup_dialog.comboBox.setCurrentIndex(0)
            self.device_setup_dialog.comboBox_2.setCurrentIndex(0)
            self.device_setup_dialog.comboBox_3.setCurrentIndex(0)
            self.camera_config["device_No"] = 0
            try:
                self.camera_config["resolution_X"] = self.device_setup_dialog.comboBox_2.currentText().split("x")[0]
                self.camera_config["resolution_Y"] = self.device_setup_dialog.comboBox_2.currentText().split("x")[1]
            except:
                self.camera_config["resolution_X"] = 0
                self.camera_config["resolution_Y"] = 0
            self.camera_config["format"] = self.device_setup_dialog.comboBox_3.currentText()

        wm_pos = self.geometry()
        wm_size = self.size()
        self.device_setup_dialog.move(
            wm_pos.x() + wm_size.width() / 2 - self.device_setup_dialog.width() / 2,
            wm_pos.y() + wm_size.height() / 2 - self.device_setup_dialog.height() / 2,
        )
        # 如果选择设备
        info = self.device_setup_dialog.exec()

        if info == 1:
            print(self.device_setup_dialog.comboBox.currentIndex())
            print(self.device_setup_dialog.comboBox_2.currentText().split("x"))

            self.camera_config["device_No"] = self.device_setup_dialog.comboBox.currentIndex()
            try:
                self.camera_config["resolution_X"] = int(
                    self.device_setup_dialog.comboBox_2.currentText().split("x")[0]
                )
                self.camera_config["resolution_Y"] = int(
                    self.device_setup_dialog.comboBox_2.currentText().split("x")[1]
                )
                self.camera_config["format"] = self.device_setup_dialog.comboBox_3.currentText()
            except:
                self.alert("Selected invalid device")
                return
            print(self.camera_config)

            try:
                self.set_webcam(True)
                self.resize_window_func()
                self.configfile["camera_config"][
                    "auto_connect"
                ] = self.device_setup_dialog.checkBoxAutoConnect.isChecked()
                self.save_config()
            except Exception as e:
                print(e)

    # 获取采集卡分辨率
    def update_device_setup_resolutions(self):
        self.device_setup_dialog.comboBox_2.clear()
        self.device_setup_dialog.comboBox_3.clear()
        camera_info = QCamera(QCameraInfo.availableCameras()[self.device_setup_dialog.comboBox.currentIndex()])
        camera_info.load()
        for i in camera_info.supportedViewfinderResolutions():
            resolutions_str = f"{i.width()}x{i.height()}"
            self.device_setup_dialog.comboBox_2.addItem(resolutions_str)
        formats = [self.get_format(i) for i in camera_info.supportedViewfinderPixelFormats()]
        for i in formats:
            self.device_setup_dialog.comboBox_3.addItem(i)
        print(formats)
        print(camera_info.supportedViewfinderResolutions())
        camera_info.unload()

    def get_format(self, fmt: QVideoFrame.PixelFormat):
        for attr_name in dir(QVideoFrame):
            if attr_name.startswith("Format_"):
                if getattr(QVideoFrame, attr_name) == fmt:
                    return attr_name.replace("Format_", "")
        return "Unknown format"

    # 初始化指定配置视频设备
    def get_webcam(self, i, x, y, f, resize=True):
        self.camera = QCamera(QCameraInfo.availableCameras()[i])
        self.camera.error.connect(lambda: self.alert(self.camera.errorString()))
        self.camera.setViewfinder(self.camerafinder)
        self.camera.setCaptureMode(QCamera.CaptureViewfinder)
        # self.camera.setCaptureMode(QCamera.CaptureVideo)
        # self.camera.setCaptureMode(QCamera.CaptureStillImage)
        view_finder_settings = QCameraViewfinderSettings()
        view_finder_settings.setResolution(x, y)
        view_finder_settings.setPixelFormat(getattr(QVideoFrame, f"Format_{f}"))
        self.camera.setViewfinderSettings(view_finder_settings)

        self.capturer = QCameraImageCapture(self.camera)
        settings = QImageEncoderSettings()  # 拍照设置
        settings.setCodec("image/png")  # 设置抓图图形编码
        settings.setResolution(x, y)  # 分辨率
        settings.setQuality(QMultimedia.VeryHighQuality)  # 图片质量
        self.capturer.setEncodingSettings(settings)
        self.capturer.error.connect(lambda i, e, s: self.alert(s))
        self.capturer.imageCaptured.connect(self.image_captured)
        self.capturer.setCaptureDestination(QCameraImageCapture.CaptureToBuffer)
        print(f"capturer available: {self.capturer.isAvailable()}")
        if not self.status["fullscreen"] and resize:
            self.resize_window_func()
        # self.camera.start()

    # 保存当前帧到文件
    def capture_to_file(self):
        if not self.camera_opened:
            return
        # self.camera.setCaptureMode(QCamera.CaptureStillImage)
        # self.camera.searchAndLock()
        self.capturer.capture()
        # self.camera.unlock()
        # self.camera.setCaptureMode(QCamera.CaptureViewfinder)
        print("capture_to_file ok")

    def image_captured(self, id, preview):
        print("image_captured", id)
        file_name = QFileDialog.getSaveFileName(
            self,
            "Save Frame",
            "untitled.png",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )[0]
        if file_name != "":
            preview.save(file_name)
            self.statusBar().showMessage(f"Frame saved to {file_name}")

    # 视频设备错误提示
    def alert(self, s):
        err = QMessageBox(self)
        err.setWindowTitle("Video device error")
        err.setText(s)
        err.exec()
        self.device_event_handle("video_error")
        print(s)
        print(err)

    # 启用和禁用视频设备
    def set_webcam(self, s):
        if s:
            self.get_webcam(
                self.camera_config["device_No"],
                self.camera_config["resolution_X"],
                self.camera_config["resolution_Y"],
                self.camera_config["format"],
            )
            self.camera.start()
            if self.camera.availability() != QMultimedia.Available:
                self.statusBar().showMessage("Video device connect failed")
                return
            self.camera_opened = True
            fps = max([i.maximumFrameRate for i in self.camera.supportedViewfinderFrameRateRanges()])
            self.device_event_handle("video_ok")
            self.camerafinder.show()
            self.takeCentralWidget()
            self.setCentralWidget(self.camerafinder)
            self.disconnect_label.hide()
            self.disconnect_label.setMouseTracking(False)
            self.camerafinder.show()
            self.camerafinder.setMouseTracking(True)
            self.setWindowTitle(
                f"Simple USB KVM - {self.camera_config['resolution_X']}x{self.camera_config['resolution_Y']} @ {fps:.1f}"
            )
        else:
            if self.camera_opened:
                self.camera.stop()
                # print("video device disconnect")
                self.camera_opened = False
                self.device_event_handle("video_close")
                self.takeCentralWidget()
                self.setCentralWidget(self.disconnect_label)
                self.camerafinder.hide()
                self.camerafinder.setMouseTracking(False)
                self.disconnect_label.show()
                self.disconnect_label.setMouseTracking(True)
                self.setWindowTitle("Simple USB KVM")

    # 捕获鼠标功能
    def capture_mouse(self):
        self.status["mouse_capture"] = True
        self.statusbar_icon3.setPixmap(load_pixmap("mouse"))
        self.statusBar().showMessage("Mouse capture on (Press Right-Ctrl to release)")
        self.set_ws2812b(0, 30, 30)

    # 释放鼠标功能
    def release_mouse(self):
        self.status["mouse_capture"] = False
        hidinfo = hid_def.hid_report([2, 0, 0, 0, 0, 0, 0, 0, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
        self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))
        self.qt_sleep(10)
        self.set_ws2812b(30, 30, 0)

    # 通过视频设备分辨率调整窗口大小
    def resize_window_func(self):
        if self.status["fullscreen"]:
            return
        if self.status["screen_height"] - self.camera_config["resolution_Y"] < 100:
            self.showNormal()
            self.resize(
                int(
                    self.status["screen_height"]
                    * (2 / 3)
                    * self.camera_config["resolution_X"]
                    / (self.camera_config["resolution_Y"] + 66)
                ),
                int(self.status["screen_height"] * (2 / 3)),
            )
            self.showMaximized()
        else:
            self.showNormal()
            self.resize(self.camera_config["resolution_X"], self.camera_config["resolution_Y"] + 66)
            qr = self.frameGeometry()
            cp = QDesktopWidget().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        if self.configfile["camera_config"]["keep_aspect_ratio"]:
            self.camerafinder.setAspectRatioMode(Qt.KeepAspectRatio)
        else:
            self.camerafinder.setAspectRatioMode(Qt.IgnoreAspectRatio)

    def keep_ratio_func(self):
        self.configfile["camera_config"]["keep_aspect_ratio"] = not self.configfile["camera_config"][
            "keep_aspect_ratio"
        ]
        if self.configfile["camera_config"]["keep_aspect_ratio"]:
            self.camerafinder.setAspectRatioMode(Qt.KeepAspectRatio)
            self.set_font_bold(self.actionKeep_ratio, True)
        else:
            self.camerafinder.setAspectRatioMode(Qt.IgnoreAspectRatio)
            self.set_font_bold(self.actionKeep_ratio, False)
        if not self.status["fullscreen"]:
            self.resize(self.width(), self.height() + 1)
        self.statusBar().showMessage("Keep aspect ratio: " + str(self.configfile["camera_config"]["keep_aspect_ratio"]))
        self.save_config()

    # 最小化窗口
    def window_minimized(self):
        self.showMinimized()

    # 重置键盘鼠标
    def reset_keymouse(self, s):
        if s == 1:  # keyboard
            for i in range(2, len(buffer)):
                buffer[i] = 0
            hidinfo = hid_def.hid_report(buffer)
            if hidinfo == 1 or hidinfo == 4:
                self.device_event_handle("hid_error")
            elif hidinfo == 0:
                self.device_event_handle("hid_ok")
            self.shortcut_status(buffer)
        elif s == 2:  # MCU
            self.set_ws2812b(255, 0, 0)
            self.qt_sleep(100)
            hidinfo = hid_def.hid_report([4, 0])
            if hidinfo == 1 or hidinfo == 4:
                self.device_event_handle("hid_error")
            elif hidinfo == 0:
                self.device_event_handle("hid_ok")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
            self.status["mouse_capture"] = False
            self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))
        elif s == 3:  # mouse
            for i in range(2, len(mouse_buffer)):
                mouse_buffer[i] = 0
            hidinfo = hid_def.hid_report(mouse_buffer)
            if hidinfo == 1 or hidinfo == 4:
                self.device_event_handle("hid_error")
            elif hidinfo == 0:
                self.device_event_handle("hid_ok")
        elif s == 4:  # hid
            hid_code = hid_def.init_usb(hid_def.vendor_id, hid_def.usage_page)
            if hid_code == 0:
                self.device_event_handle("hid_init_ok")
                if self.status["mouse_capture"]:
                    self.set_ws2812b(0, 30, 30)
                else:
                    self.set_ws2812b(30, 30, 0)
            else:
                self.device_event_handle("hid_init_error")

    # 自定义组合键窗口
    def shortcut_key_func(self, s):
        if s == 1:  # release
            hid_return = hid_def.hid_report([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            if hid_return == 1 or hid_return == 4:
                self.device_event_handle("hid_error")
            return
        if s == 2:  # pressed
            hid_return = hid_def.hid_report(self.shortcut_buffer)
            if hid_return == 1 or hid_return == 4:
                self.device_event_handle("hid_error")
            return
        if s == 3:  # save
            text, ok = QInputDialog.getText(self, "Save shortcut key", "Enter name:")
            if ok:
                idx = len(self.configfile["shortcut_key"]["shortcut_key_name"])
                self.configfile["shortcut_key"]["shortcut_key_name"].append(text)
                self.configfile["shortcut_key"]["shortcut_key_hidcode"].append([_ for _ in self.shortcut_buffer])
                print(f"save {text}={self.shortcut_buffer}")
                action = self.menuShortcut_key.addAction(text)
                action.triggered.connect(lambda: self.shortcut_key_action(idx))
                self.save_config()
            return

        wm_pos = self.geometry()
        wm_size = self.size()
        addheight = 0
        if self.paste_board_dialog.isVisible():
            addheight += self.paste_board_dialog.height() + 30
        if self.indicator_dialog.isVisible():
            addheight += self.indicator_dialog.height() + 30
        if not self.status["fullscreen"]:
            addheight += 30
        self.shortcut_key_dialog.move(
            wm_pos.x() + (wm_size.width() - self.shortcut_key_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.shortcut_key_dialog.height() - 30 - addheight),
        )
        self.shortcut_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        if self.shortcut_key_dialog.isVisible():
            self.shortcut_key_dialog.activateWindow()
            return
        self.shortcut_key_dialog.exec()
        for i in range(2, len(buffer)):
            buffer[i] = 0
        self.shortcut_key_handle(0xFE)

    # 自定义组合键窗口按钮对应功能
    def shortcut_key_handle(self, s):
        if s == 0xFE:
            self.shortcut_key_dialog.pushButton_ctrl.setChecked(False)
            self.shortcut_key_dialog.pushButton_alt.setChecked(False)
            self.shortcut_key_dialog.pushButton_shift.setChecked(False)
            self.shortcut_key_dialog.pushButton_meta.setChecked(False)
            self.shortcut_key_dialog.pushButton_tab.setChecked(False)
            self.shortcut_key_dialog.pushButton_prtsc.setChecked(False)
            self.shortcut_key_dialog.keySequenceEdit.setKeySequence("")
            for i in range(2, len(self.shortcut_buffer)):
                self.shortcut_buffer[i] = 0

        if s == 0xFF:  # keySequenceChanged
            if self.shortcut_key_dialog.keySequenceEdit.keySequence().count() == 0:  # 去除多个复合键
                keysequence = ""
                return
            elif self.shortcut_key_dialog.keySequenceEdit.keySequence().count() == 1:
                keysequence = self.shortcut_key_dialog.keySequenceEdit.keySequence().toString()
            else:
                keysequence = self.shortcut_key_dialog.keySequenceEdit.keySequence().toString().split(",")
                self.shortcut_key_dialog.keySequenceEdit.setKeySequence(keysequence[0])
                keysequence = keysequence[0]

            if [s for s in shift_symbol if keysequence in s]:
                keysequence = "Shift+" + keysequence

            if len(re.findall("\+", keysequence)) == 0:  # 没有匹配到+号，不是组合键
                self.shortcut_key_dialog.keySequenceEdit.setKeySequence(keysequence)
            else:
                if keysequence != "+":
                    keysequence_list = keysequence.split("+").copy()  # 将复合键转换为功能键
                    if [s for s in keysequence_list if "Ctrl" in s]:
                        self.shortcut_key_dialog.pushButton_ctrl.setChecked(True)
                        self.shortcut_buffer[2] = self.shortcut_buffer[2] | 1
                    else:
                        self.shortcut_key_dialog.pushButton_ctrl.setChecked(False)

                    if [s for s in keysequence_list if "Alt" in s]:
                        self.shortcut_key_dialog.pushButton_alt.setChecked(True)
                        self.shortcut_buffer[2] = self.shortcut_buffer[2] | 4
                    else:
                        self.shortcut_key_dialog.pushButton_alt.setChecked(False)

                    if [s for s in keysequence_list if "Shift" in s]:
                        self.shortcut_key_dialog.pushButton_shift.setChecked(True)
                        self.shortcut_buffer[2] = self.shortcut_buffer[2] | 2
                    else:
                        self.shortcut_key_dialog.pushButton_shift.setChecked(False)

                    if [s for s in keysequence_list if "Meta" in s]:
                        self.shortcut_key_dialog.pushButton_meta.setChecked(True)
                        self.shortcut_buffer[2] = self.shortcut_buffer[2] | 8

                    self.shortcut_key_dialog.keySequenceEdit.setKeySequence(keysequence_list[-1])
                    keysequence = keysequence_list[-1]
            try:
                mapcode = self.keyboard_code[keysequence.upper()]
            except Exception as e:
                print(e)
                print("Hid query error")
                return

            if not mapcode:
                print("Hid query error")
            else:
                self.shortcut_buffer[4] = int(mapcode, 16)  # 功能位

        if self.shortcut_key_dialog.pushButton_ctrl.isChecked() and s == 1:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] | 1
        elif (self.shortcut_key_dialog.pushButton_ctrl.isChecked() is False) and s == 1:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] & 1 and self.shortcut_buffer[2] ^ 1

        if self.shortcut_key_dialog.pushButton_alt.isChecked() and s == 4:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] | 4
        elif (self.shortcut_key_dialog.pushButton_alt.isChecked() is False) and s == 4:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] & 4 and self.shortcut_buffer[2] ^ 4

        if self.shortcut_key_dialog.pushButton_shift.isChecked() and s == 2:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] | 2
        elif (self.shortcut_key_dialog.pushButton_shift.isChecked() is False) and s == 2:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] & 2 and self.shortcut_buffer[2] ^ 2

        if self.shortcut_key_dialog.pushButton_meta.isChecked() and s == 8:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] | 8
        elif (self.shortcut_key_dialog.pushButton_meta.isChecked() is False) and s == 8:
            self.shortcut_buffer[2] = self.shortcut_buffer[2] & 8 and self.shortcut_buffer[2] ^ 8

        if self.shortcut_key_dialog.pushButton_tab.isChecked() and s == 0x2B:
            self.shortcut_buffer[8] = 0x2B
        elif (self.shortcut_key_dialog.pushButton_tab.isChecked() is False) and s == 0x2B:
            self.shortcut_buffer[8] = 0

        if self.shortcut_key_dialog.pushButton_prtsc.isChecked() and s == 0x46:
            self.shortcut_buffer[9] = 0x46
        elif (self.shortcut_key_dialog.pushButton_prtsc.isChecked() is False) and s == 0x46:
            self.shortcut_buffer[9] = 0

    # 菜单快捷键发送hid报文
    def shortcut_key_action(self, s):
        try:
            get = self.configfile["shortcut_key"]["shortcut_key_hidcode"][s]
        except Exception as e:
            return
        hid_def.hid_report(get)
        # time.sleep(0.1)
        self.qt_sleep(10)
        hidinfo = hid_def.hid_report([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    # 设备事件处理
    def device_event_handle(self, s):
        if s == "hid_error":
            self.statusBar().showMessage("Keyboard Mouse connect error, try to <Reload Key/Mouse>")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
            self.status["mouse_capture"] = False
            self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))
        elif s == "video_error":
            self.statusBar().showMessage("Video device error")
            self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
        elif s == "video_close":
            self.statusBar().showMessage("Video device close")
            self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
        elif s == "hid_init_error":
            self.statusBar().showMessage("Keyboard Mouse initialization error")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
        elif s == "hid_init_ok":
            self.statusBar().showMessage("Keyboard Mouse initialization done")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard"))
        elif s == "hid_ok":
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard"))
            self.statusBar().addPermanentWidget(self.statusbar_icon2)
        elif s == "video_ok":
            self.statusBar().showMessage("Video device connected")
            self.statusbar_icon1.setPixmap(load_pixmap("video"))
            self.status["mouse_capture"] = True
            self.statusbar_icon3.setPixmap(load_pixmap("mouse"))
            self.set_ws2812b(0, 30, 30)

    # 菜单小工具
    def menu_tools_actions(self, s):
        if s == 0:
            os.popen("osk")
        elif s == 1:
            os.popen("calc")
        elif s == 2:
            os.popen("SnippingTool")
        elif s == 3:
            os.popen("notepad")

    # 状态栏显示组合键状态
    def shortcut_status(self, s=[0, 0, 0]):
        if dark_theme:
            highlight_color = "color: white"
        else:
            highlight_color = "color: black"
        if s[2] & 1:
            self.statusbar_lable1.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable1.setStyleSheet("color: grey")
        if s[2] & 2:
            self.statusbar_lable2.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable2.setStyleSheet("color: grey")

        if s[2] & 4:
            self.statusbar_lable3.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable3.setStyleSheet("color: grey")

        if s[2] & 8:
            self.statusbar_lable4.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable4.setStyleSheet("color: grey")

    def update_indicatorLight(self) -> None:
        reply = hid_def.hid_report([3, 0], True)
        print(reply)
        if reply == 1 or reply == 2 or reply == 3 or reply == 4:
            self.device_event_handle("hid_error")
            print("hid error")
            return

        if reply[0] != 3:
            self.statusBar().showMessage("Indicator reply error")
            return
        self.indicator_dialog.pushButtonNum.setText("[" + ((reply[2] & (1 << 0)) and "*" or " ") + "] Num Lock")
        self.indicator_dialog.pushButtonCaps.setText("[" + ((reply[2] & (1 << 1)) and "*" or " ") + "] Caps Lock")
        self.indicator_dialog.pushButtonScroll.setText("[" + ((reply[2] & (1 << 2)) and "*" or " ") + "] Scroll Lock")

    def indicatorLight_func(self):
        self.update_indicatorLight()
        if self.indicator_dialog.isVisible():
            self.indicator_dialog.activateWindow()
        addheight = 0
        if not self.status["fullscreen"]:
            addheight += 30
        wm_pos = self.geometry()
        wm_size = self.size()
        if self.paste_board_dialog.isVisible():
            addheight += self.paste_board_dialog.height() + 30
        if self.shortcut_key_dialog.isVisible():
            addheight += self.shortcut_key_dialog.height() + 30
        self.indicator_dialog.move(
            wm_pos.x() + (wm_size.width() - self.indicator_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.indicator_dialog.height() - 30 - addheight),
        )
        self.indicator_dialog.exec()

    def set_ws2812b(self, r: int, g: int, b: int):
        r = min(max(int(r), 0), 255)
        g = min(max(int(g), 0), 255)
        b = min(max(int(b), 0), 255)
        hidinfo = hid_def.hid_report([5, 0, r, g, b, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            print("hid error")
            return

    # 粘贴板
    def paste_board_func(self):
        addheight = 0
        if self.shortcut_key_dialog.isVisible():
            addheight += self.shortcut_key_dialog.height() + 30
        if self.indicator_dialog.isVisible():
            addheight += self.indicator_dialog.height() + 30
        if not self.status["fullscreen"]:
            addheight += 30
        wm_pos = self.geometry()
        wm_size = self.size()
        self.paste_board_dialog.move(
            wm_pos.x() + (wm_size.width() - self.paste_board_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.paste_board_dialog.height() - 30 - addheight),
        )
        self.paste_board_file_path = None
        self.paste_board_dialog.labelFile.setText("N/A")
        self.paste_board_dialog.spinBox_ci.setValue(self.configfile["paste_board"]["click_interval"])
        self.paste_board_dialog.spinBox_pi.setValue(self.configfile["paste_board"]["press_interval"])
        self.paste_board_dialog.spinBox_ps.setValue(self.configfile["paste_board"]["packet_size"])
        self.paste_board_dialog.spinBox_pw.setValue(self.configfile["paste_board"]["packet_wait"])
        if self.paste_board_dialog.isVisible():
            self.paste_board_dialog.activateWindow()
            return
        dialog_return = self.paste_board_dialog.exec()
        if dialog_return == 1:
            self.paste_board_send()
        self.configfile["paste_board"]["click_interval"] = self.paste_board_dialog.spinBox_ci.value()
        self.configfile["paste_board"]["press_interval"] = self.paste_board_dialog.spinBox_pi.value()
        self.configfile["paste_board"]["packet_size"] = self.paste_board_dialog.spinBox_ps.value()
        self.configfile["paste_board"]["packet_wait"] = self.paste_board_dialog.spinBox_pw.value()
        self.save_config()

    def paste_board_file_select(self):
        self.paste_board_dialog.hide()
        file_path = QFileDialog.getOpenFileName(self, "Select file", "", "All Files(*.*)")[0]
        self.paste_board_dialog.show()
        print(file_path)
        if os.path.isfile(file_path):
            file_size_kb = os.path.getsize(file_path) / 1024
            self.paste_board_file_path = file_path
            self.paste_board_dialog.labelFile.setText(os.path.basename(file_path) + f" ({file_size_kb:.2f} KB)")

    def qt_sleep(self, t):
        if (t := int(t)) > 0:
            loop = QEventLoop()
            QTimer.singleShot(t, loop.quit)
            loop.exec_()

    def send_char(self, c):
        CLICK_INTERVAL = self.paste_board_dialog.spinBox_ci.value()
        PRESS_INTERVAL = self.paste_board_dialog.spinBox_pi.value()
        temp_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        shift = False
        if c == "\n":
            mapcode = self.keyboard_code["ENTER"]
        elif c == "\t":
            mapcode = self.keyboard_code["TAB"]
        elif c == " ":
            mapcode = self.keyboard_code["SPACE"]
        else:
            try:
                cq = strB2Q(c)
                mapcode = self.keyboard_code[cq.upper()]
                if cq.isupper():
                    shift = True
            except KeyError:
                # print("Key not found:", c)
                return 0
        temp_buffer[4] = int(mapcode, 16)  # 功能位
        if c in shift_symbol or shift:
            temp_buffer[2] = 2
        else:
            temp_buffer[2] = 0
        hidinfo = 0
        hidinfo = hid_def.hid_report(temp_buffer)
        self.qt_sleep(PRESS_INTERVAL)
        hidinfo = hid_def.hid_report([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            print("hid error")
            return 1
        self.qt_sleep(CLICK_INTERVAL)
        return 0

    def paste_board_stop(self):
        self.paste_board_stop_flag = True

    def paste_board_send(self):
        idx = self.paste_board_dialog.tabWidget.currentIndex() + 1
        if idx == 10:
            print("paste_board_file_send call")
            self.paste_board_file_send()
            return
        if idx > 9:
            return
        text = getattr(self.paste_board_dialog, f"plainTextEdit_{idx}").toPlainText()
        text = text.replace("\r\n", "\n")
        total = len(text)
        if total == 0:
            return
        print("paste_board_send start")
        self.paste_board_dialog.pushButtonSend.setEnabled(False)
        self.ignore_event = True
        self.paste_board_stop_flag = False
        for i, c in enumerate(text):
            self.paste_board_dialog.setWindowTitle(f"Paste board - Sending {i/total:.0%}")
            if self.send_char(c) == 1:
                self.paste_board_dialog.setWindowTitle("Paste board - Error occurred")
                break
            if self.paste_board_stop_flag:
                self.paste_board_dialog.setWindowTitle("Paste board - Force stopped")
                break
        else:
            self.paste_board_dialog.setWindowTitle("Paste board - Finished")
        self.paste_board_dialog.pushButtonSend.setEnabled(True)
        self.ignore_event = False
        print("paste_board_send end")

    def paste_board_file_send(self):
        if self.paste_board_file_path is None:
            return
        echo_only = self.paste_board_dialog.checkBoxEcho.isChecked()
        PACKGE_SIZE = self.paste_board_dialog.spinBox_ps.value()
        PACKGE_WAIT = self.paste_board_dialog.spinBox_pw.value()
        if not echo_only:
            CMD_HEAD = "echo "
            CMD_TAIL0 = f" | xxd -r -p > ./{os.path.basename(self.paste_board_file_path)}\n"
            CMD_TAIL1 = f" | xxd -r -p >> ./{os.path.basename(self.paste_board_file_path)}\n"
        else:
            CMD_HEAD = 'echo -e -n "'
            CMD_TAIL0 = f'" > ./{os.path.basename(self.paste_board_file_path)}\n'
            CMD_TAIL1 = f'" >> ./{os.path.basename(self.paste_board_file_path)}\n'
        with open(self.paste_board_file_path, "rb") as f:
            data = f.read()
        data = data.hex()
        if echo_only:
            temp = ""
            for j, c in enumerate(data):
                if j % 2 == 0:
                    temp += "\\x"
                temp += c
            data = temp
        total = len(data)
        if total == 0:
            return
        print("paste_board_file_send start")
        self.paste_board_dialog.setWindowTitle(f"Paste board - Sending file")
        self.paste_board_dialog.pushButtonSend.setEnabled(False)
        self.ignore_event = True
        self.paste_board_dialog.progressBar.setValue(0)
        error = False
        self.paste_board_stop_flag = False
        cnt = 0
        PACKGE_SIZE -= len(CMD_HEAD) + max(len(CMD_TAIL0), len(CMD_TAIL1))
        for i in range(0, total, PACKGE_SIZE):
            part = data[i : i + PACKGE_SIZE]
            if i == 0:
                cmd = CMD_HEAD + part + CMD_TAIL0
            else:
                cmd = CMD_HEAD + part + CMD_TAIL1
            # print(cmd)
            cnt += len(part)
            print(i, cnt, total)
            self.paste_board_dialog.progressBar.setValue(int(i / total * 100))
            for c in cmd:
                if self.send_char(c) == 1:
                    self.paste_board_dialog.setWindowTitle("Paste board - Error occurred")
                    error = True
                    break
                if self.paste_board_stop_flag:
                    self.paste_board_dialog.setWindowTitle("Paste board - Force stopped")
                    error = True
                    break
            if error:
                break
            self.qt_sleep(PACKGE_WAIT)
        else:
            self.paste_board_dialog.setWindowTitle("Paste board - Finished")
            self.paste_board_dialog.progressBar.setValue(100)
        self.paste_board_dialog.pushButtonSend.setEnabled(True)
        self.ignore_event = False
        print("paste_board_file_send end")

    # 三个Lock键
    def lock_key_func(self, key):
        if key == 1:  # Caps Lock
            key_code = self.keyboard_code["CAPSLOCK"]
        elif key == 2:  # Num Lock
            key_code = self.keyboard_code["NUMLOCK"]
        elif key == 3:  # Scroll Lock
            key_code = self.keyboard_code["SCROLLLOCK"]
        temp_buffer = [1, 0, 0, 0, int(key_code, 16), 0, 0, 0, 0, 0, 0]
        hidinfo = hid_def.hid_report(temp_buffer)
        self.qt_sleep(50)
        hidinfo = hid_def.hid_report([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            print("hid error")
        self.qt_sleep(50)
        self.update_indicatorLight()

    def RGB_func(self):
        self.status["RGB_mode"] = not self.status["RGB_mode"]
        self.set_font_bold(self.actionRGB, self.status["RGB_mode"])
        self.statusBar().showMessage("RGB Led: " + str(self.status["RGB_mode"]))
        if not self.status["RGB_mode"]:
            if self.status["mouse_capture"]:
                self.set_ws2812b(0, 30, 30)
            else:
                self.set_ws2812b(30, 30, 0)

    # 全屏幕切换
    def fullscreen_func(self, skip_alert=False):
        self.status["fullscreen"] = not self.status["fullscreen"]
        if self.status["fullscreen"]:
            if not self.fullscreen_alert_showed and not skip_alert:
                alert = QMessageBox(self)
                alert.setWindowTitle("Fullscreen")
                alert.setText(
                    f"Press Ctrl+Alt+Shift+{self.config['fullscreen_key']} to toggle fullscreen"
                    f"\n(Key {self.config['fullscreen_key']} can be changed in config.yaml)"
                    f"\nStay cursor at left top corner to show toolbar"
                )
                alert.Ok = alert.addButton("I know it", QMessageBox.AcceptRole)
                alert.exec()
            self.fullscreen_alert_showed = True
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
            self.action_Resize_window.setEnabled(False)
            self.statusBar().hide()
            self.menuBar().hide()
            self.set_font_bold(self.action_fullscreen, True)
        else:
            self.showNormal()
            self.action_fullscreen.setChecked(False)
            self.action_Resize_window.setEnabled(True)
            self.statusBar().show()
            self.menuBar().show()
            self.set_font_bold(self.action_fullscreen, False)

    # 隐藏指针
    def hide_cursor_func(self):
        self.status["hide_cursor"] = not self.status["hide_cursor"]
        if self.status["hide_cursor"]:
            self.set_font_bold(self.actionHide_cursor, True)
        else:
            self.set_font_bold(self.actionHide_cursor, False)
        self.statusBar().showMessage("Hide cursor when capture mouse: " + str(self.status["hide_cursor"]))

    # 保持窗口在最前
    def topmost_func(self):
        self.status["topmost"] = not self.status["topmost"]
        self.setWindowFlags(Qt.WindowStaysOnTopHint if self.status["topmost"] else Qt.Widget)
        self.show()
        self.statusBar().showMessage("Window always on top: " + str(self.status["topmost"]))
        self.set_font_bold(self.actionKeep_on_top, self.status["topmost"])

    # 窗口失焦事件
    def changeEvent(self, event):
        try:  # 窗口未初始化完成时会触发一次事件
            if self.status is None:
                return
        except AttributeError:
            print("status Variable not initialized")
        except Exception as e:
            print(e)
        else:
            if not self.isActiveWindow() and self.status["init_ok"]:  # 窗口失去焦点时重置键盘，防止卡键
                # print("window not active")
                self.reset_keymouse(1)

    def dark_theme_func(self):
        self.configfile["config"]["dark_theme"] = not dark_theme
        self.save_config()
        # apply at next start
        info = QMessageBox(self)
        info.setWindowTitle("Dark theme")
        info.setText(f"Dark theme change will be applied at next start\nRestart now?")
        info.Ok = info.addButton("OK", QMessageBox.AcceptRole)
        info.Cancel = info.addButton("Cancel", QMessageBox.RejectRole)
        ret = info.exec()
        if ret == QMessageBox.AcceptRole:
            self.close()
            os.startfile(sys.argv[0])

    # 鼠标按下事件
    def mousePressEvent(self, event):
        if self.ignore_event:
            return
        if not self.status["mouse_capture"]:
            return
        mouse_buffer[2] = mouse_buffer[2] | int(event.button())

        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    # 鼠标松开事件
    def mouseReleaseEvent(self, event):
        if self.ignore_event:
            return
        if not self.status["mouse_capture"]:
            return
        mouse_buffer[2] = mouse_buffer[2] ^ int(event.button())

        if mouse_buffer[2] < 0 or mouse_buffer[2] > 7:
            mouse_buffer[2] = 0
        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    # 鼠标滚动事件
    def wheelEvent(self, event):
        if self.ignore_event:
            return
        if not self.status["mouse_capture"]:
            return
        if event.angleDelta().y() == 120:
            mouse_buffer[7] = 0x01
        elif event.angleDelta().y() == -120:
            mouse_buffer[7] = 0xFF
        else:
            mouse_buffer[7] = 0

        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
        if self.mouse_scroll_timer.isActive():
            self.mouse_scroll_timer.stop()
        self.mouse_scroll_timer.start(100)

    def mouse_scroll_stop(self):
        self.mouse_scroll_timer.stop()
        mouse_buffer[7] = 0
        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    def mouse_action_timeout(self):
        if self.mouse_action_target == "menuBar":
            self.menuBar().show()
        elif self.mouse_action_target == "statusBar":
            self.statusBar().show()
        self.mouse_action_timer.stop()

    # 鼠标移动事件
    def mouseMoveEvent(self, event):
        if self.ignore_event:
            return
        x, y = event.pos().x(), event.pos().y()
        if self.status["fullscreen"]:
            if (y < 2 and x < 2) or (x > self.width() - 2 and y > self.height() - 2):
                if (y < 2 and x < 2) and self.menuBar().isHidden() and not self.mouse_action_timer.isActive():
                    self.mouse_action_target = "menuBar"
                    self.mouse_action_timer.start(500)
                elif (
                    (x > self.width() - 2 and y > self.height() - 2)
                    and self.statusBar().isHidden()
                    and not self.mouse_action_timer.isActive()
                ):
                    self.mouse_action_target = "statusBar"
                    self.mouse_action_timer.start(500)
            else:
                if not self.menuBar().isHidden():
                    self.menuBar().hide()
                if not self.statusBar().isHidden():
                    self.statusBar().hide()
                if self.mouse_action_timer.isActive():
                    self.mouse_action_timer.stop()
        if not (self.status["mouse_capture"] and self.camera_opened):
            self.setCursor(Qt.ArrowCursor)
            return
        if self.status["hide_cursor"]:
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        x_diff = 0
        y_diff = 0
        x_res = self.camera_config["resolution_X"]
        y_res = self.camera_config["resolution_Y"]
        if self.configfile["camera_config"]["keep_aspect_ratio"]:
            cam_scale = y_res / x_res
            finder_scale = self.camerafinder.height() / self.camerafinder.width()
            if finder_scale > cam_scale:
                x_diff = 0
                y_diff = self.camerafinder.height() - self.camerafinder.width() * cam_scale
            elif finder_scale < cam_scale:
                x_diff = self.camerafinder.width() - self.camerafinder.height() / cam_scale
                y_diff = 0
        x_hid = (x - x_diff / 2) / (self.camerafinder.width() - x_diff)
        y_hid = ((y - y_diff / 2 - self.camerafinder.pos().y())) / (self.camerafinder.height() - y_diff)
        x_hid = max(min(x_hid, 1), 0)
        y_hid = max(min(y_hid, 1), 0)
        if self.status["RGB_mode"]:
            self.set_ws2812b(x_hid * 255, y_hid * 255, (1 - x_hid) * (1 - y_hid) * 255)
        self.statusBar().showMessage(f"X={x_hid*x_res:.0f}, Y={y_hid*y_res:.0f}")
        x_hid = int(x_hid * 0x7FFF)
        y_hid = int(y_hid * 0x7FFF)
        mouse_buffer[3] = x_hid & 0xFF
        mouse_buffer[4] = x_hid >> 8
        mouse_buffer[5] = y_hid & 0xFF
        mouse_buffer[6] = y_hid >> 8
        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    # 键盘按下事件
    def keyPressEvent(self, event):
        # print(f"keyPressEvent: {event.key()}")
        if self.ignore_event:
            return
        if event.nativeScanCode() == 285:  # Right Ctrl
            self.release_mouse()
            self.statusBar().showMessage("Mouse capture off")
        if event.isAutoRepeat():
            return
        if self.status["RGB_mode"]:
            self.set_ws2812b(*hsv_to_rgb(random.random(), random.randint(6, 10) / 10, 0.4))
        key = event.key()
        scancode = event.nativeScanCode()

        scancode2hid = self.keyboard_scancode2hid.get(scancode, 0)
        if scancode2hid != 0:
            buffer[4] = scancode2hid
        else:
            buffer[4] = 0

        if key == Qt.Key_Control:  # Ctrl 键被按下
            buffer[2] = buffer[2] | 1
        elif key == Qt.Key_Shift:  # Shift 键被按下
            buffer[2] = buffer[2] | 2
        elif key == Qt.Key_Alt:  # Alt 键被按下
            buffer[2] = buffer[2] | 4
        elif key == Qt.Key_Meta:  # Meta 键被按下
            buffer[2] = buffer[2] | 8

        # Ctrl+Alt+Shift+F11 退出全屏
        try:
            if buffer[2] == 7 and key == getattr(Qt, f'Key_{self.config["fullscreen_key"]}'):
                self.fullscreen_func(1)
                return
        except:
            pass

        if buffer[2] < 0 or buffer[2] > 16:
            buffer[2] = 0

        hidinfo = hid_def.hid_report(buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
        self.shortcut_status(buffer)

        """
        其它常用按键：
        Qt.Key_Escape,Qt.Key_Tab,Qt.Key_Backspace,Qt.Key_Return,Qt.Key_Enter,
        Qt.Key_Insert,Qt.Key_Delet###.Key_9,Qt.Key_Colon,Qt.Key_Semicolon,Qt.Key_Equal
        ...
        """

    # 键盘松开事件
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if self.ignore_event:
            return
        key = event.key()
        scancode = event.nativeScanCode()
        scancode2hid = self.keyboard_scancode2hid.get(scancode, 0)

        if scancode2hid != 0:
            buffer[4] = 0

        if key == Qt.Key_Control:  # Ctrl 键被释放
            if buffer[2] & 1:
                buffer[2] = buffer[2] ^ 1
        elif key == Qt.Key_Shift:  # Shift 键被释放
            if buffer[2] & 2:
                buffer[2] = buffer[2] ^ 2
        elif key == Qt.Key_Alt:  # Alt 键被释放
            if buffer[2] & 4:
                buffer[2] = buffer[2] ^ 4
        elif key == Qt.Key_Meta:  # Meta 键被释放
            if buffer[2] & 8:
                buffer[2] = buffer[2] ^ 8

        if buffer[2] < 0 or buffer[2] > 16:
            buffer[2] = 0

        hidinfo = hid_def.hid_report(buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

        self.shortcut_status(buffer)

    def closeEvent(self, event):
        if self.paste_board_dialog.isVisible():
            self.paste_board_dialog.close()
        if self.shortcut_key_dialog.isVisible():
            self.shortcut_key_dialog.close()
        if self.device_setup_dialog.isVisible():
            self.device_setup_dialog.close()
        if self.indicator_dialog.isVisible():
            self.indicator_dialog.close()
        return super().closeEvent(event)


def error_log(msg):
    with open("error.log", "a") as f:
        f.write(f"Error Occurred at {datetime.datetime.now()}:\n")
        f.write(f"{msg}\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    qdarktheme.setup_theme(theme="dark" if dark_theme else "light")
    myWin.show()
    QTimer.singleShot(100, myWin.shortcut_status)
    try:
        ret = app.exec_()
    except Exception as e:
        import traceback

        error_log(traceback.format_exc())
        ret = 1
    sys.exit(ret)
