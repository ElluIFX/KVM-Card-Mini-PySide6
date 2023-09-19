import datetime
import os
import random
import re
import sys
import tempfile
import time
from typing import List, Tuple, Union

import hid_def
import pythoncom
import pyWinhook as pyHook
import yaml  # type: ignore
from loguru import logger
from PySide6 import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtMultimedia import *
from PySide6.QtMultimediaWidgets import *
from PySide6.QtWidgets import *
from server import KVM_Server, add_auth_user, count_auth_users
from ui import (
    device_setup_dialog_ui,
    indicator_ui,
    main_ui,
    numboard_ui,
    paste_board_ui,
    shortcut_key_ui,
)

"""
qdarktheme import after QT
"""
import qdarktheme

kb_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
mouse_buffer = [2, 0, 0, 0, 0, 0, 0, 0, 0]
shift_symbol = [
    ")","!","@","#","$","%",
    "^","&","*","(","~","_",
    "+","{","}","|",":",'"',
    "<",">","?",
]  # fmt: skip
PATH = os.path.dirname(os.path.abspath(__file__))
ARGV_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
dark_theme = True


class Fake_StdWriter:
    def __init__(self, *args, **kwargs):
        self.buffer = ""
        self.callback = None

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        self.buffer += data
        if self.callback is not None:
            self.callback(self.buffer)

    def flush(self):
        pass

    def clear(self):
        self.buffer = ""


fake_std = Fake_StdWriter()

# 屏蔽所有print
if sys.argv[-1] != "debug":

    def print(*args, **kwargs):
        pass

    sys.stdout = fake_std
    sys.stderr = fake_std

    logger.remove()
    logger.add(
        fake_std,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {name} - {message}",  #:{function}:{line}
    )
else:
    hid_def.set_verbose(True)


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


class MyDeviceSetupDialog(QDialog, device_setup_dialog_ui.Ui_Dialog):
    def __init__(self, parent=None):
        super(MyDeviceSetupDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)


class MyShortcutKeyDialog(QDialog, shortcut_key_ui.Ui_Dialog):
    def __init__(self, parent=None):
        super(MyShortcutKeyDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)


class MyPasteBoardDialog(QDialog, paste_board_ui.Ui_Dialog):
    def __init__(self, parent=None):
        super(MyPasteBoardDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)


class MyIndicatorDialog(QDialog, indicator_ui.Ui_Dialog):
    def __init__(self, parent=None):
        super(MyIndicatorDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)


class MyNumKeyboardDialog(QDialog, numboard_ui.Ui_Dialog):
    def __init__(self, parent=None):
        super(MyNumKeyboardDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setFixedWidth(self.width())


class MyMainWindow(QMainWindow, main_ui.Ui_MainWindow):
    _disconnect_signal = Signal()
    _log_signal = Signal(str)
    _wheel_signal = Signal()

    def __init__(self, parent=None):
        self.ignore_event = False
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)

        self.camera = None
        self.camera_opened = False
        self.camera_info = None
        self.audio_opened = False
        self.device_connected = False

        # 子窗口
        self.device_setup_dialog = MyDeviceSetupDialog()
        self.shortcut_key_dialog = MyShortcutKeyDialog()
        self.paste_board_dialog = MyPasteBoardDialog()
        self.indicator_dialog = MyIndicatorDialog()
        self.numkeyboard_dialog = MyNumKeyboardDialog()

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

        for i in range(1, 28):
            getattr(self.numkeyboard_dialog, f"pushButton_{i}").pressed.connect(lambda x=i: self.numboard_func(x, True))
            getattr(self.numkeyboard_dialog, f"pushButton_{i}").released.connect(
                lambda x=i: self.numboard_func(x, False)
            )
        # 导入外部数据
        try:
            with open(os.path.join(ARGV_PATH, "data", "keyboard_hid2code.yaml"), "r") as load_f:
                self.keyboard_hid2code = yaml.safe_load(load_f)
            with open(os.path.join(ARGV_PATH, "data", "keyboard_scancode2hid.yml"), "r") as load_f:
                self.keyboard_scancode2hid = yaml.safe_load(load_f)
            with open(os.path.join(ARGV_PATH, "data", "keyboard.yaml"), "r") as load_f:
                self.keyboard_code = yaml.safe_load(load_f)
            with open(os.path.join(ARGV_PATH, "data", "config.yaml"), "r") as load_f:
                self.configfile = yaml.safe_load(load_f)
            self.config = self.configfile["config"]
            self.video_record_config = self.configfile["video_record_config"]
            self.video_config = self.configfile["video_config"]
            self.audio_config = self.configfile["audio_config"]
            self.fullscreen_key = getattr(Qt, f'Key_{self.config["fullscreen_key"]}')
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Import data error:\n {e}\n\nCheck the folder ./data and restart the program"
            )
            sys.exit(1)
        # 加载配置文件
        self.status = {
            "fullscreen": False,
            "topmost": False,
            "mouse_capture": False,
            "hide_cursor": False,
            "init_ok": False,
            "screen_height": 0,
            "screen_width": 0,
            "RGB_mode": False,
            "quick_paste": True,
        }
        global dark_theme
        dark_theme = self.config["dark_theme"]
        if dark_theme:
            self.set_font_bold(self.actionDark_theme, True)

        # 获取显示器分辨率大小
        self.desktop = QGuiApplication.primaryScreen()
        self.status["screen_height"] = self.desktop.availableGeometry().height()
        self.status["screen_width"] = self.desktop.availableGeometry().width()

        # 窗口图标
        self.setWindowIcon(QIcon(f"{PATH}/ui/images/icon.ico"))
        self.device_setup_dialog.setWindowIcon(load_icon("import", False))
        self.shortcut_key_dialog.setWindowIcon(load_icon("keyboard-settings-outline", False))
        self.paste_board_dialog.setWindowIcon(load_icon("paste", False))
        self.indicator_dialog.setWindowIcon(load_icon("capslock", False))
        self.numkeyboard_dialog.setWindowIcon(load_icon("numkey", False))

        # 状态栏图标
        self.statusbar_lable1 = QLabel()
        self.statusbar_lable2 = QLabel()
        self.statusbar_lable3 = QLabel()
        self.statusbar_lable4 = QLabel()
        font = QFont()
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
        self.statusbar_btn4 = MyPushButton()
        self.statusbar_btn1.setPixmap(load_pixmap("keyboard-settings-outline"))
        self.statusbar_btn2.setPixmap(load_pixmap("paste"))
        self.statusbar_btn3.setPixmap(load_pixmap("capslock"))
        self.statusbar_btn4.setPixmap(load_pixmap("numkey"))

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
        self.statusBar().addPermanentWidget(self.statusbar_btn4)
        self.statusBar().addPermanentWidget(self.statusbar_icon1)
        self.statusBar().addPermanentWidget(self.statusbar_icon2)
        self.statusBar().addPermanentWidget(self.statusbar_icon3)

        self.statusbar_btn1.clicked.connect(lambda: self.statusbar_func(1))
        self.statusbar_btn2.clicked.connect(lambda: self.statusbar_func(2))
        self.statusbar_btn3.clicked.connect(lambda: self.statusbar_func(3))
        self.statusbar_btn4.clicked.connect(lambda: self.statusbar_func(4))
        self.statusbar_icon1.clicked.connect(lambda: self.statusbar_func(5))
        self.statusbar_icon2.clicked.connect(lambda: self.statusbar_func(6))
        self.statusbar_icon3.clicked.connect(lambda: self.statusbar_func(7))

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
        self.actionRecord_video.setIcon(load_icon("record"))
        self.actionRGB.setIcon(load_icon("RGB"))
        self.actionQuick_paste.setIcon(load_icon("quick_paste"))
        self.actionWindows_Audio_Setting.setIcon(load_icon("audio"))
        self.actionWindows_Device_Manager.setIcon(load_icon("device"))
        self.actionNum_Keyboard.setIcon(load_icon("numkey"))
        self.actionOpen_Server_Manager.setIcon(load_icon("server"))
        self.actionSystem_hook.setIcon(load_icon("hook"))

        if self.video_config["keep_aspect_ratio"]:
            self.set_font_bold(self.actionKeep_ratio, True)
        self.set_font_bold(self.actionQuick_paste, True)

        # 初始化监视器
        self.setCentralWidget(self.serverFrame)
        self.serverFrame.setHidden(True)

        self.videoWidget = QVideoWidget()
        self.takeCentralWidget()
        self.setCentralWidget(self.videoWidget)
        self.videoWidget.setMouseTracking(True)
        self.videoWidget.children()[0].setMouseTracking(True)
        self.videoWidget.hide()

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
        self.action_video_device_connect.triggered.connect(lambda: self.set_device(True))
        self.action_video_device_disconnect.triggered.connect(lambda: self.set_device(False))
        self.action_video_devices.triggered.connect(self.device_config)
        self.actionCustomKey.triggered.connect(self.shortcut_key_func)
        self.actionReload_Key_Mouse.triggered.connect(lambda: self.reset_keymouse(4))
        self.actionMinimize.triggered.connect(self.window_minimized)
        self.actionexit.triggered.connect(sys.exit)

        self.device_setup_dialog.comboBox.currentIndexChanged.connect(self.update_device_info)

        self.action_fullscreen.triggered.connect(self.fullscreen_func)
        self.action_Resize_window.triggered.connect(self.resize_window_func)
        self.actionKeep_ratio.triggered.connect(self.keep_ratio_func)
        self.actionKeep_on_top.triggered.connect(self.topmost_func)
        self.actionCapture_frame.triggered.connect(self.capture_to_file)
        self.actionRecord_video.triggered.connect(self.record_video)

        self.actionRelease_mouse.triggered.connect(self.release_mouse)
        self.actionCapture_mouse.triggered.connect(self.capture_mouse)
        self.actionResetKeyboard.triggered.connect(lambda: self.reset_keymouse(1))
        self.actionResetMouse.triggered.connect(lambda: self.reset_keymouse(3))
        self.actionIndicator_light.triggered.connect(self.indicatorLight_func)
        self.actionReload_MCU.triggered.connect(lambda: self.reset_keymouse(2))

        self.actionPaste_board.triggered.connect(self.paste_board_func)
        self.actionHide_cursor.triggered.connect(self.hide_cursor_func)
        self.actionQuick_paste.triggered.connect(self.quick_paste_func)
        self.actionNum_Keyboard.triggered.connect(self.num_keyboard_func)
        self.actionSystem_hook.triggered.connect(self.system_hook_func)

        self.actionOn_screen_Keyboard.triggered.connect(lambda: self.menu_tools_actions(0))
        self.actionCalculator.triggered.connect(lambda: self.menu_tools_actions(1))
        self.actionSnippingTool.triggered.connect(lambda: self.menu_tools_actions(2))
        self.actionNotepad.triggered.connect(lambda: self.menu_tools_actions(3))
        self.actionWindows_Audio_Setting.triggered.connect(lambda: self.menu_tools_actions(4))
        self.actionWindows_Device_Manager.triggered.connect(lambda: self.menu_tools_actions(5))

        self.actionOpen_Server_Manager.triggered.connect(self.open_server_manager)

        self.actionDark_theme.triggered.connect(self.dark_theme_func)
        self.actionRGB.triggered.connect(self.RGB_func)
        self.paste_board_dialog.pushButtonFile.clicked.connect(self.paste_board_file_select)

        self.kvmSetDeviceCombo.currentTextChanged.connect(self.update_server_device_info)

        self.device_setup_dialog.checkBoxAudio.setChecked(self.audio_config["audio_support"])
        self.device_setup_dialog.checkBoxAudio.stateChanged.connect(self.audio_checkbox_switch)
        self.audio_checkbox_switch()

        self.paste_board_dialog.spinBox_ci.setValue(self.configfile["paste_board"]["click_interval"])
        self.paste_board_dialog.spinBox_ps.setValue(self.configfile["paste_board"]["packet_size"])
        self.paste_board_dialog.spinBox_pw.setValue(self.configfile["paste_board"]["packet_wait"])

        # 设置聚焦方式
        self.statusbar_btn1.setFocusPolicy(Qt.NoFocus)
        self.statusbar_btn2.setFocusPolicy(Qt.NoFocus)
        self.statusbar_btn3.setFocusPolicy(Qt.NoFocus)
        self.statusbar_btn4.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon1.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon2.setFocusPolicy(Qt.NoFocus)
        self.statusbar_icon3.setFocusPolicy(Qt.NoFocus)

        # self.camerafinder.setFocusPolicy(Qt.NoFocus)
        # self.statusBar().setFocusPolicy(Qt.NoFocus)
        # self.statusBar().setFocusPolicy(Qt.NoFocus)
        # self.setFocusPolicy(Qt.StrongFocus)

        self.mouse_action_timer = QTimer()
        self.mouse_action_timer.timeout.connect(self.mouse_action_timeout)
        self.indicator_timer = QTimer()
        self.indicator_timer.timeout.connect(self.update_indicatorLight)
        self.check_device_timer = QTimer()
        self.check_device_timer.timeout.connect(self.check_device_status)
        self.check_device_timer.start(1000)
        self._disconnect_signal.connect(lambda: self.check_device_status(camera=False))

        self.reset_keymouse(4)

        # self.setMouseTracking(True)

        self.mouse_scroll_timer = QTimer()
        self.mouse_scroll_timer.timeout.connect(self.mouse_scroll_stop)

        self._log_signal.connect(self.set_log_text)
        fake_std.callback = self._log_signal.emit
        self.server = KVM_Server(parent=self)
        self._wheel_signal.connect(self.mouse_wheel_act)

        self.hook_state = False
        self.hook_manager = pyHook.HookManager()
        self.hook_manager.KeyDown = self.hook_keyboard_down_event
        self.hook_manager.KeyUp = self.hook_keyboard_up_event
        self.pythoncom_timer = QTimer()
        self.pythoncom_timer.timeout.connect(lambda: pythoncom.PumpWaitingMessages())
        self.hook_pressed_keys = []

        self.status["init_ok"] = True

        self.camera_list_inited = False
        if self.video_config["auto_connect"]:
            self.device_setup_dialog.checkBoxAutoConnect.setChecked(True)
            QTimer().singleShot(1000, lambda: self.set_device(True, center=True))

    code_remap = {
        "Rcontrol": 0x011D,
        "Lwin": 0x015B,
        "Rwin": 0x015C,
    }

    def hook_keyboard_down_event(self, event):
        print(f"Hook: {event.Key} {event.ScanCode}")
        if event.Key in self.code_remap:
            scan_code = self.code_remap[event.Key]
        else:
            scan_code = event.ScanCode
        if scan_code not in self.hook_pressed_keys:
            self.hook_pressed_keys.append(scan_code)
            self.keyPress(scan_code)
        return False

    def hook_keyboard_up_event(self, event):
        if event.Key in self.code_remap:
            scan_code = self.code_remap[event.Key]
        else:
            scan_code = event.ScanCode
        self.keyRelease(scan_code)
        try:
            self.hook_pressed_keys.remove(scan_code)
        except ValueError:
            pass
        return False

    def statusbar_func(self, act):
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
            if self.numkeyboard_dialog.isVisible():
                self.numkeyboard_dialog.close()
            else:
                self.num_keyboard_func()
        elif act == 5:
            self.device_config()
        elif act == 6:
            self.reset_keymouse(4)
        elif act == 7:
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
        with open(os.path.join(ARGV_PATH, "data", "config.yaml"), "w", encoding="utf-8") as f:
            yaml.dump(self.configfile, f)

    def audio_checkbox_switch(self):
        if self.device_setup_dialog.checkBoxAudio.isChecked():
            self.device_setup_dialog.comboBox_4.show()
            self.device_setup_dialog.comboBox_5.show()
            self.device_setup_dialog.label_4.show()
            self.device_setup_dialog.label_5.show()
            self.device_setup_dialog.label_7.show()
            self.device_setup_dialog.setMaximumHeight(270)
            self.device_setup_dialog.setMinimumHeight(270)
            self.update_audio_devices()
        else:
            self.device_setup_dialog.comboBox_4.hide()
            self.device_setup_dialog.comboBox_5.hide()
            self.device_setup_dialog.label_4.hide()
            self.device_setup_dialog.label_5.hide()
            self.device_setup_dialog.label_7.hide()
            self.device_setup_dialog.setMaximumHeight(200)
            self.device_setup_dialog.setMinimumHeight(200)
        self.device_setup_dialog.adjustSize()

    def update_audio_devices(self):
        self.device_setup_dialog.comboBox_4.clear()
        self.device_setup_dialog.comboBox_5.clear()
        self.device_setup_dialog.comboBox_4.addItem("Default")
        self.device_setup_dialog.comboBox_5.addItem("Default")
        in_devices = QMediaDevices.audioInputs()
        out_devices = QMediaDevices.audioOutputs()
        devices = ["Default"]
        for i in in_devices:
            self.device_setup_dialog.comboBox_4.addItem(i.description())
            devices.append(i.description())
        if self.audio_config["audio_device_in"] in devices:
            self.device_setup_dialog.comboBox_4.setCurrentText(self.audio_config["audio_device_in"])
        else:
            self.device_setup_dialog.comboBox_4.setCurrentIndex(0)
        devices = ["Default"]
        for i in out_devices:
            self.device_setup_dialog.comboBox_5.addItem(i.description())
            devices.append(i.description())
        if self.audio_config["audio_device_out"] in devices:
            self.device_setup_dialog.comboBox_5.setCurrentText(self.audio_config["audio_device_out"])
        else:
            self.device_setup_dialog.comboBox_5.setCurrentIndex(0)

    # 弹出采集卡设备设置窗口，并打开采集卡设备
    def device_config(self):
        if self.serverFrame.isVisible():
            QMessageBox.critical(self, "Error", "Close KVM Server before local connection")
            return False

        self.device_setup_dialog.comboBox.clear()
        cameras = QMediaDevices.videoInputs()
        remember_name = self.video_config["device_name"]
        # self.video_config["device_name"] = ""
        devices = []
        for camera in cameras:
            self.device_setup_dialog.comboBox.addItem(camera.description())
            devices.append(camera.description())
        self.camera_list_inited = True
        if remember_name in devices:
            self.device_setup_dialog.comboBox.setCurrentText(remember_name)
            self.update_device_info()
            resolution_str = str(self.video_config["resolution_X"]) + "x" + str(self.video_config["resolution_Y"])
            self.device_setup_dialog.comboBox_2.setCurrentText(resolution_str)
            self.device_setup_dialog.comboBox_3.setCurrentText(self.video_config["format"])
        else:
            self.device_setup_dialog.comboBox.setCurrentIndex(0)
            self.update_device_info()
            self.device_setup_dialog.comboBox_2.setCurrentIndex(0)
            self.device_setup_dialog.comboBox_3.setCurrentIndex(0)
            try:
                self.video_config["resolution_X"] = self.device_setup_dialog.comboBox_2.currentText().split("x")[0]
                self.video_config["resolution_Y"] = self.device_setup_dialog.comboBox_2.currentText().split("x")[1]
            except:
                self.video_config["resolution_X"] = 0
                self.video_config["resolution_Y"] = 0
            self.video_config["format"] = self.device_setup_dialog.comboBox_3.currentText()

        if self.device_setup_dialog.checkBoxAudio.isChecked():
            self.update_audio_devices()

        wm_pos = self.geometry()
        wm_size = self.size()
        self.device_setup_dialog.move(
            wm_pos.x() + wm_size.width() / 2 - self.device_setup_dialog.width() / 2,
            wm_pos.y() + wm_size.height() / 2 - self.device_setup_dialog.height() / 2,
        )
        # 如果选择设备
        ret = self.device_setup_dialog.exec()

        if not ret:
            return
        try:
            self.video_config["device_name"] = self.device_setup_dialog.comboBox.currentText()
            self.video_config["resolution_X"] = int(self.device_setup_dialog.comboBox_2.currentText().split("x")[0])
            self.video_config["resolution_Y"] = int(self.device_setup_dialog.comboBox_2.currentText().split("x")[1])
            self.video_config["format"] = self.device_setup_dialog.comboBox_3.currentText()

            if self.device_setup_dialog.checkBoxAudio.isChecked():
                self.audio_config["audio_device_in"] = self.device_setup_dialog.comboBox_4.currentText()
                self.audio_config["audio_device_out"] = self.device_setup_dialog.comboBox_5.currentText()
        except:
            self.video_alert("Selected invalid device")
            return
        print(self.video_config)
        try:
            self.set_device(True, center=True)
            self.video_config["auto_connect"] = self.device_setup_dialog.checkBoxAutoConnect.isChecked()
            self.audio_config["audio_support"] = self.device_setup_dialog.checkBoxAudio.isChecked()
            self.save_config()
        except Exception as e:
            print(e)

    # 获取采集卡分辨率
    def update_device_info(self):
        self.device_setup_dialog.comboBox_2.clear()
        self.device_setup_dialog.comboBox_3.clear()
        cameras = QMediaDevices.videoInputs()
        if not self.camera_list_inited:
            for camera in cameras:
                if camera.description() == self.video_config["device_name"]:
                    self.camera_info = camera
                    break
            else:
                print("Target video device not found")
                self.camera_info = None
                return
        else:
            try:
                self.camera_info = cameras[self.device_setup_dialog.comboBox.currentIndex()]
            except IndexError:
                self.camera_info = None
                return
        res_list = []
        fmt_list = []
        for i in self.camera_info.videoFormats():
            resolutions_str = f"{i.resolution().width()}x{i.resolution().height()}"
            if resolutions_str not in res_list:
                res_list.append(resolutions_str)
                self.device_setup_dialog.comboBox_2.addItem(resolutions_str)
            fmt_str = i.pixelFormat().name.split("_")[1]
            if fmt_str not in fmt_list:
                fmt_list.append(fmt_str)
                self.device_setup_dialog.comboBox_3.addItem(fmt_str)

    # 初始化指定配置视频设备
    def setup_device(self):
        if self.serverFrame.isVisible():
            QMessageBox.critical(self, "Error", "Close KVM Server before local connection")
            return False
        if self.camera_info is None:
            self.update_device_info()
            if self.camera_info is None:
                self.video_alert("Target video device not found")
                return False
        self.camera = QCamera(self.camera_info)
        for i in self.camera_info.videoFormats():
            if (
                i.resolution().width() == self.video_config["resolution_X"]
                and i.resolution().height() == self.video_config["resolution_Y"]
                and i.pixelFormat().name.split("_")[1] == self.video_config["format"]
            ):
                self.camera.setCameraFormat(i)
                break
        else:
            self.video_alert("Unsupported combination of resolution and format")
            return False

        if self.device_setup_dialog.checkBoxAudio.isChecked():
            in_devices = QMediaDevices.audioInputs()
            out_devices = QMediaDevices.audioOutputs()
            in_device_name = self.audio_config["audio_device_in"]
            out_device_name = self.audio_config["audio_device_out"]
            if in_device_name == "Default":
                in_device = QMediaDevices.defaultAudioInput()
            else:
                for i in in_devices:
                    if i.description() == in_device_name:
                        in_device = i
                        break
                else:
                    in_device = None
            if out_device_name == "Default":
                out_device = QMediaDevices.defaultAudioOutput()
            else:
                for i in out_devices:
                    if i.description() == out_device_name:
                        out_device = i
                        break
                else:
                    out_device = None
            if in_device is None or out_device is None:
                self.video_alert("Audio device not found")
                return False
            self.audio_in_device = in_device
            self.audio_out_device = out_device

        self.camera.start()
        if not self.camera.isActive():
            self.video_alert("Video device connect failed")
            return False

        self.capture_session = QMediaCaptureSession()
        self.capture_session.setCamera(self.camera)
        self.capture_session.setVideoOutput(self.videoWidget)

        self.image_capture = QImageCapture(self.camera)
        self.capture_session.setImageCapture(self.image_capture)
        self.image_capture.setQuality(QImageCapture.Quality.VeryHighQuality)
        self.image_capture.setFileFormat(QImageCapture.FileFormat.PNG)
        self.image_capture.connect(self.image_capture, SIGNAL("imageCaptured(int,QImage)"), self.image_captured)

        self.video_record = QMediaRecorder(self.camera)
        self.capture_session.setRecorder(self.video_record)
        self.video_record.setQuality(getattr(QMediaRecorder.Quality, self.video_record_config["quality"]))
        self.video_record.setMediaFormat(QMediaFormat.FileFormat.MPEG4)
        self.video_record.setEncodingMode(
            getattr(QMediaRecorder.EncodingMode, self.video_record_config["encoding_mode"])
        )
        self.video_record.setVideoBitRate(self.video_record_config["encoding_bitrate"])
        self.video_record.setVideoFrameRate(self.video_record_config["framerate"])
        self.video_record.setVideoResolution(QSize())
        self.video_recording = False

        if self.device_setup_dialog.checkBoxAudio.isChecked():
            self.audio_input = QAudioInput(self.audio_in_device)
            self.audio_output = QAudioOutput(self.audio_out_device)
            self.audio_input.setVolume(1)
            self.audio_output.setVolume(1)
            self.audio_input.setMuted(False)
            self.audio_output.setMuted(False)
            self.capture_session.setAudioInput(self.audio_input)
            self.capture_session.setAudioOutput(self.audio_output)
            self.audio_opened = True
            # self.video_record.setAudioBitRate(16)
            # self.video_record.setAudioSampleRate(48000)
            # self.video_record.record()
            print("Audio device ok")
        return True

    # 保存当前帧到文件
    def capture_to_file(self):
        if not self.camera_opened:
            return
        self.image_capture.capture()
        print("capture_to_file ok")

    def record_video(self):
        if not self.camera_opened:
            return
        if self.video_record.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self.video_record.stop()
        if not self.video_recording:
            file_name = QFileDialog.getSaveFileName(
                self,
                "Video save location",
                "output.mp4",
                "Video (*.mp4)",
            )[0]
            if file_name == "":
                return
            self.video_record.setOutputLocation(QUrl.fromLocalFile(file_name))
            self.video_record.record()
            self.video_recording = True
            self.actionRecord_video.setText("Stop recording")
            self.statusBar().showMessage("Video recording started")
        else:
            self.video_record.stop()
            self.video_recording = False
            self.actionRecord_video.setText("Record video")
            self.statusBar().showMessage("Video recording stopped")

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
            self.statusBar().showMessage(f"Image saved to {file_name}")

    # 视频设备错误提示
    def video_alert(self, s):
        err = QMessageBox(self)
        err.setWindowTitle("Video device error")
        err.setText(s)
        err.exec()
        self.device_event_handle("video_error")
        print(s)
        print(err)

    # 启用和禁用视频设备
    def set_device(self, state, center=False):
        if self.serverFrame.isVisible():
            QMessageBox.critical(self, "Error", "Close KVM Server before local connection")
            return False
        if state:
            if not self.setup_device():
                return
            if not self.status["fullscreen"]:
                self.resize_window_func(center=center)
            fps = self.camera.cameraFormat().maxFrameRate()
            self.device_event_handle("video_ok")
            self.takeCentralWidget()
            self.setCentralWidget(self.videoWidget)
            self.disconnect_label.hide()
            self.videoWidget.show()
            self.setWindowTitle(
                f"USB KVM Client - {self.video_config['resolution_X']}x{self.video_config['resolution_Y']} @ {fps:.1f}"
            )
        else:
            if self.camera_opened:
                self.camera.stop()
                self.device_event_handle("video_close")
                self.takeCentralWidget()
                self.setCentralWidget(self.disconnect_label)
                self.videoWidget.hide()
                self.disconnect_label.show()
                self.setWindowTitle("USB KVM Client")
                del self.capture_session
                del self.camera
                del self.image_capture
                del self.video_record
                if self.audio_opened:
                    del self.audio_input
                    del self.audio_output
                    del self.audio_in_device
                    del self.audio_out_device
                    self.audio_opened = False

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
    def resize_window_func(self, center=True):
        if self.status["fullscreen"]:
            return
        if self.status["screen_height"] - self.video_config["resolution_Y"] < 100:
            self.showNormal()
            self.resize(
                int(
                    self.status["screen_height"]
                    * (2 / 3)
                    * self.video_config["resolution_X"]
                    / (self.video_config["resolution_Y"] + 66)
                ),
                int(self.status["screen_height"] * (2 / 3)),
            )
            self.showMaximized()
        else:
            self.showNormal()
            self.resize(self.video_config["resolution_X"], self.video_config["resolution_Y"] + 66)
            if center:
                qr = self.frameGeometry()
                cp = QGuiApplication.primaryScreen().availableGeometry().center()
                qr.moveCenter(cp)
                self.move(qr.topLeft())
        if self.video_config["keep_aspect_ratio"]:
            self.videoWidget.setAspectRatioMode(Qt.KeepAspectRatio)
        else:
            self.videoWidget.setAspectRatioMode(Qt.IgnoreAspectRatio)

    def keep_ratio_func(self):
        self.video_config["keep_aspect_ratio"] = not self.video_config["keep_aspect_ratio"]
        if self.video_config["keep_aspect_ratio"]:
            self.videoWidget.setAspectRatioMode(Qt.KeepAspectRatio)
            self.set_font_bold(self.actionKeep_ratio, True)
        else:
            self.videoWidget.setAspectRatioMode(Qt.IgnoreAspectRatio)
            self.set_font_bold(self.actionKeep_ratio, False)
        if not self.status["fullscreen"]:
            self.resize(self.width(), self.height() + 1)
        self.statusBar().showMessage("Keep aspect ratio: " + str(self.video_config["keep_aspect_ratio"]))
        self.save_config()

    # 最小化窗口
    def window_minimized(self):
        self.showMinimized()

    # 重置键盘鼠标
    def reset_keymouse(self, s):
        if s == 1:  # keyboard
            for i in range(2, len(kb_buffer)):
                kb_buffer[i] = 0
            hidinfo = hid_def.hid_report(kb_buffer)
            if hidinfo == 1 or hidinfo == 4:
                self.device_event_handle("hid_error")
            elif hidinfo == 0:
                self.device_event_handle("hid_ok")
            self.shortcut_status(kb_buffer)
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
            addheight += 34
        self.shortcut_key_dialog.move(
            wm_pos.x() + (wm_size.width() - self.shortcut_key_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.shortcut_key_dialog.height() - 30 - addheight),
        )
        self.shortcut_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        if self.shortcut_key_dialog.isVisible():
            self.shortcut_key_dialog.activateWindow()
            return
        self.shortcut_key_dialog.exec()
        for i in range(2, len(kb_buffer)):
            kb_buffer[i] = 0
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
            self.device_connected = False
        elif s == "video_error":
            self.statusBar().showMessage("Video device error")
            self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
            self.camera_opened = False
        elif s == "video_close":
            self.statusBar().showMessage("Video device close")
            self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
            self.camera_opened = False
            self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))
            self.status["mouse_capture"] = False
            self.set_ws2812b(30, 30, 0)
        elif s == "hid_init_error":
            self.statusBar().showMessage("Keyboard Mouse initialization error")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
            self.device_connected = False
        elif s == "hid_init_ok":
            self.statusBar().showMessage("Keyboard Mouse initialization done")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard"))
            self.device_connected = True
        elif s == "hid_ok":
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard"))
            self.device_connected = True
        elif s == "video_ok":
            self.statusBar().showMessage("Video device connected")
            self.statusbar_icon1.setPixmap(load_pixmap("video"))
            self.status["mouse_capture"] = True
            self.statusbar_icon3.setPixmap(load_pixmap("mouse"))
            self.camera_opened = True
            self.set_ws2812b(0, 30, 30)
        elif s == "device_disconnect":
            self.statusBar().showMessage("Device disconnect")
            self.statusbar_icon2.setPixmap(load_pixmap("keyboard-off"))
            self.statusbar_icon3.setPixmap(load_pixmap("mouse-off"))
            self.status["mouse_capture"] = False
            self.device_connected = False
        elif s == "video_disconnect":
            self.statusBar().showMessage("Device disconnect")
            self.statusbar_icon1.setPixmap(load_pixmap("video-off"))
            self.camera_opened = False

    # 检查连接状态
    def check_device_status(self):
        if self.device_connected:
            if not hid_def.check_connection():
                self.device_event_handle("device_disconnect")
        # if self.camera_opened:
        #     if self.camera.availability() != QMultimedia.Available:
        #         self.device_event_handle("video_disconnect")

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
        elif s == 4:
            os.popen("rundll32.exe shell32.dll, Control_RunDLL mmsys.cpl")
        elif s == 5:
            os.popen("devmgmt.msc")

    # 状态栏显示组合键状态
    def shortcut_status(self, s=[0, 0, 0]):
        if dark_theme:
            highlight_color = "color: white"
        else:
            highlight_color = "color: black"
        if (s[2] & 1) or (s[2] & 16):
            self.statusbar_lable1.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable1.setStyleSheet("color: grey")
        if (s[2] & 2) or (s[2] & 32):
            self.statusbar_lable2.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable2.setStyleSheet("color: grey")

        if (s[2] & 4) or (s[2] & 64):
            self.statusbar_lable3.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable3.setStyleSheet("color: grey")

        if (s[2] & 8) or (s[2] & 128):
            self.statusbar_lable4.setStyleSheet(highlight_color)
        else:
            self.statusbar_lable4.setStyleSheet("color: grey")

    def update_indicatorLight(self) -> None:
        reply = hid_def.hid_report([3, 0], True)
        if reply == 1 or reply == 2 or reply == 3 or reply == 4:
            self.device_event_handle("hid_error")
            self.indicator_timer.stop()
            print("hid error")
            return
        if reply[0] != 3:
            self.statusBar().showMessage("Indicator reply error")
            self.indicator_timer.stop()
            return
        self.indicator_dialog.pushButtonNum.setText("[" + ((reply[2] & (1 << 0)) and "*" or " ") + "] Num Lock")
        self.indicator_dialog.pushButtonCaps.setText("[" + ((reply[2] & (1 << 1)) and "*" or " ") + "] Caps Lock")
        self.indicator_dialog.pushButtonScroll.setText("[" + ((reply[2] & (1 << 2)) and "*" or " ") + "] Scroll Lock")
        if reply[2] & (1 << 0):
            self.numkeyboard_dialog.pushButton_1.setText("*Num\nLock")
        else:
            self.numkeyboard_dialog.pushButton_1.setText("Num\nLock")

    def indicatorLight_func(self):
        self.update_indicatorLight()
        if self.indicator_dialog.isVisible():
            self.indicator_dialog.activateWindow()
            return
        addheight = 0
        if not self.status["fullscreen"]:
            addheight += 34
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
        self.indicator_timer.start(500)
        self.indicator_dialog.exec()
        if not self.numkeyboard_dialog.isVisible():
            self.indicator_timer.stop()

    def num_keyboard_func(self):
        if self.numkeyboard_dialog.isVisible():
            self.numkeyboard_dialog.activateWindow()
            return
        wm_pos = self.geometry()
        wm_size = self.size()
        addheight = 0
        if not self.status["fullscreen"]:
            addheight += 34
        self.numkeyboard_dialog.move(
            wm_pos.x() + (wm_size.width() - self.numkeyboard_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.numkeyboard_dialog.height() - 30 - addheight),
        )
        self.indicator_timer.start(500)
        self.numkeyboard_dialog.exec()
        if not self.indicator_dialog.isVisible():
            self.indicator_timer.stop()

    num_hid_dict = {
        1: 0x53,2: 0x54,3: 0x55,
        4: 0x56,8: 0x57,17: 0x58,
        12: 0x59,13: 0x5A,14: 0x5B,
        9: 0x5C,10: 0x5D,11: 0x5E,
        5: 0x5F,6: 0x60,7: 0x61,
        15: 0x62,16: 0x63,
        18:0x4B,19:0x4A,20:0x4E,
        21:0x4D,22:0x46,23:0x48,
        24:0xE7,25:0x65,26:0x49,
        27:0x66
    }  # fmt:skip
    def numboard_func(self, x, state):
        self.update_kb_hid(self.num_hid_dict[x], state)

    def set_ws2812b(self, r: int, g: int, b: int):
        r = min(max(int(r), 0), 255)
        g = min(max(int(g), 0), 255)
        b = min(max(int(b), 0), 255)
        hidinfo = hid_def.hid_report([5, 0, r, g, b, 0])
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            print("hid error")
            return

    def quick_paste_func(self):
        self.status["quick_paste"] = not self.status["quick_paste"]
        self.set_font_bold(self.actionQuick_paste, self.status["quick_paste"])
        self.statusBar().showMessage("Quick paste (Ctrl+Shift+Alt+V): " + str(self.status["quick_paste"]))

    def system_hook_func(self):
        self.hook_state = not self.hook_state
        self.set_font_bold(self.actionSystem_hook, self.hook_state)
        self.statusBar().showMessage("System hook: " + str(self.hook_state))
        if self.hook_state:
            self.pythoncom_timer.start(500)
            self.hook_manager.HookKeyboard()
        else:
            self.hook_manager.UnhookKeyboard()
            self.pythoncom_timer.stop()

    # 粘贴板
    def paste_board_func(self):
        addheight = 0
        if self.shortcut_key_dialog.isVisible():
            addheight += self.shortcut_key_dialog.height() + 30
        if self.indicator_dialog.isVisible():
            addheight += self.indicator_dialog.height() + 30
        if not self.status["fullscreen"]:
            addheight += 34
        wm_pos = self.geometry()
        wm_size = self.size()
        self.paste_board_dialog.move(
            wm_pos.x() + (wm_size.width() - self.paste_board_dialog.width()),
            wm_pos.y() + (wm_size.height() - self.paste_board_dialog.height() - 30 - addheight),
        )
        self.paste_board_file_path = None
        self.paste_board_dialog.labelFile.setText("N/A")
        self.paste_board_dialog.spinBox_ci.setValue(self.configfile["paste_board"]["click_interval"])
        self.paste_board_dialog.spinBox_ps.setValue(self.configfile["paste_board"]["packet_size"])
        self.paste_board_dialog.spinBox_pw.setValue(self.configfile["paste_board"]["packet_wait"])
        if self.paste_board_dialog.isVisible():
            self.paste_board_dialog.activateWindow()
            return
        dialog_return = self.paste_board_dialog.exec()
        if dialog_return == 1:
            self.paste_board_send()
        self.configfile["paste_board"]["click_interval"] = self.paste_board_dialog.spinBox_ci.value()
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
            loop.exec()

    def send_char(self, c):
        char_buffer = [6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
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
                return
        mapcode = int(mapcode, 16)
        char_buffer[4] = mapcode
        if c in shift_symbol or shift:
            char_buffer[2] |= 2
        hidinfo = hid_def.hid_report(char_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            return 1
        self.qt_sleep(self.paste_board_dialog.spinBox_ci.value())
        return 0

    def paste_board_stop(self):
        self.paste_board_stop_flag = True

    def paste_board_send(self, text=None):
        if text is None:
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
        kb_buffer[2] = 0
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
        kb_buffer[2] = 0
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
        key_code = int(key_code, 16)
        self.update_kb_hid(key_code, True)
        self.qt_sleep(50)
        self.update_kb_hid(key_code, False)
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
    def fullscreen_func(self):
        self.status["fullscreen"] = not self.status["fullscreen"]
        if self.status["fullscreen"]:
            if not self.config["fullscreen_alert_showed"]:
                alert = QMessageBox(self)
                alert.setWindowTitle("Fullscreen")
                alert.setText(
                    f"Press Ctrl+Alt+Shift+{self.config['fullscreen_key']} to toggle fullscreen"
                    f"\n(Key {self.config['fullscreen_key']} can be changed in config.yaml)"
                    f"\nStay cursor at left top corner to show toolbar"
                )
                alert.Ok = alert.addButton("I know it, don't show again", QMessageBox.AcceptRole)
                alert.exec()
                self.config["fullscreen_alert_showed"] = True
                self.save_config()
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
        self.config["dark_theme"] = not dark_theme
        self.save_config()
        info = QMessageBox(self)
        info.setWindowTitle("Dark theme")
        info.setText(f"Theme change will take affect at next start")
        info.Ok = info.addButton("OK", QMessageBox.AcceptRole)
        info.exec()

    def mouseButton_to_int(self, s: Qt.MouseButton):
        if s == Qt.LeftButton:
            return 1
        elif s == Qt.RightButton:
            return 2
        elif s == Qt.MiddleButton:
            return 4
        elif s == Qt.XButton1:
            return 8
        elif s == Qt.XButton2:
            return 16
        else:
            return 0

    # 鼠标按下事件
    def mousePressEvent(self, event):
        if self.ignore_event:
            return
        if not self.status["mouse_capture"]:
            return
        mouse_buffer[2] = mouse_buffer[2] | self.mouseButton_to_int(event.button())

        hidinfo = hid_def.hid_report(mouse_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    # 鼠标松开事件
    def mouseReleaseEvent(self, event):
        if self.ignore_event:
            return
        if not self.status["mouse_capture"]:
            return
        mouse_buffer[2] = mouse_buffer[2] ^ self.mouseButton_to_int(event.button())

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
        p = event.position().toPoint()
        x, y = p.x(), p.y()
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
        if not (self.status["mouse_capture"]):
            self.setCursor(Qt.ArrowCursor)
            return
        if self.status["hide_cursor"]:
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        if not self.camera_opened:
            x_res = self.disconnect_label.width()
            y_res = self.disconnect_label.height()
            width = self.disconnect_label.width()
            height = self.disconnect_label.height()
            # x_pos = self.disconnect_label.pos().x()
            y_pos = self.disconnect_label.pos().y()
        else:
            x_res = self.video_config["resolution_X"]
            y_res = self.video_config["resolution_Y"]
            width = self.videoWidget.width()
            height = self.videoWidget.height()
            # x_pos = self.camerafinder.pos().x()
            y_pos = self.videoWidget.pos().y()
        x_diff = 0
        y_diff = 0
        if self.video_config["keep_aspect_ratio"]:
            cam_scale = y_res / x_res
            finder_scale = height / width
            if finder_scale > cam_scale:
                x_diff = 0
                y_diff = height - width * cam_scale
            elif finder_scale < cam_scale:
                x_diff = width - height / cam_scale
                y_diff = 0
        x_hid = (x - x_diff / 2) / (width - x_diff)
        y_hid = ((y - y_diff / 2 - y_pos)) / (height - y_diff)
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

    scan_to_b2 = {
        0x001D: 1,  # Left Control
        0x002A: 2,  # Left Shift
        0x0038: 4,  # Left Alt
        0x015B: 8,  # Left GUI
        0x011D: 16,  # Right Control
        0x0036: 32,  # Right Shift
        0x0138: 64,  # Right Alt
        0x015C: 128,  # Right GUI
    }

    hid_to_b2 = {
        0xE0: 1,  # Left Control
        0xE1: 2,  # Left Shift
        0xE2: 4,  # Left Alt
        0xE3: 8,  # Left GUI
        0xE4: 16,  # Right Control
        0xE5: 32,  # Right Shift
        0xE6: 64,  # Right Alt
        0xE7: 128,  # Right GUI
    }

    def update_kb(self, scancode: int, state: bool):
        if state:
            if scancode in self.scan_to_b2:
                kb_buffer[2] |= self.scan_to_b2[scancode]
            else:
                scancode2hid = self.keyboard_scancode2hid.get(scancode, 0)
                if scancode2hid == 0:
                    print(f"scancode2hid not found: {scancode}")
                    return
                for i in range(4, 10):
                    if kb_buffer[i] == scancode2hid:
                        return
                    if kb_buffer[i] == 0:
                        kb_buffer[i] = scancode2hid
                        break
                else:
                    print("Buffer overflow")
        else:
            if scancode in self.scan_to_b2:
                kb_buffer[2] &= ~self.scan_to_b2[scancode]
            else:
                scancode2hid = self.keyboard_scancode2hid.get(scancode, 0)
                if scancode2hid == 0:
                    print(f"scancode2hid not found: {scancode}")
                    return
                for i in range(4, 10):
                    if kb_buffer[i] == scancode2hid:
                        kb_buffer[i] = 0
                        break
                else:
                    print("Key not found in buffer")
        hidinfo = hid_def.hid_report(kb_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            return hidinfo
        return 0

    def update_kb_hid(self, hid: int, state: bool):
        if state:
            if hid in self.hid_to_b2:
                kb_buffer[2] |= self.hid_to_b2[hid]
            else:
                for i in range(4, 10):
                    if kb_buffer[i] == hid:
                        return
                    if kb_buffer[i] == 0:
                        kb_buffer[i] = hid
                        break
                else:
                    print("Buffer overflow")
        else:
            if hid in self.hid_to_b2:
                kb_buffer[2] &= ~self.hid_to_b2[hid]
            else:
                for i in range(4, 10):
                    if kb_buffer[i] == hid:
                        kb_buffer[i] = 0
                        break
                else:
                    print("Key not found in buffer")
        hidinfo = hid_def.hid_report(kb_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            return hidinfo
        return 0

    def update_kb_hid(self, hid: int, state: bool):
        if state:
            for i in range(4, 10):
                if kb_buffer[i] == hid:
                    return
                if kb_buffer[i] == 0:
                    kb_buffer[i] = hid
                    break
            else:
                print("Buffer overflow")
        else:
            for i in range(4, 10):
                if kb_buffer[i] == hid:
                    kb_buffer[i] = 0
                    break
            else:
                print("Key not found in buffer")
        hidinfo = hid_def.hid_report(kb_buffer)
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")
            return 1
        return 0

    # 键盘按下事件
    def keyPressEvent(self, event):
        if self.ignore_event:
            return
        if event.isAutoRepeat():
            return
        # Ctrl+Alt+Shift+F11 退出全屏
        if kb_buffer[2] == 7 and event.key() == self.fullscreen_key:
            self.fullscreen_func()
            return
        self.keyPress(event.nativeScanCode())

    def keyPress(self, scancode: int):
        # Ctrl+Alt+Shift+V quick paste
        if kb_buffer[2] == 7 and scancode == 0x002F and self.status["quick_paste"]:
            # 获取剪贴板内容
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if len(text) == 0:
                self.statusBar().showMessage("Clipboard is empty")
                return
            self.statusBar().showMessage(f"Quick pasting {len(text)} characters")
            self.paste_board_send(text)
            return
        if scancode == 285:  # Right Ctrl
            self.release_mouse()
            self.statusBar().showMessage("Mouse capture off")
        if self.status["RGB_mode"]:
            self.set_ws2812b(*hsv_to_rgb(random.random(), random.randint(6, 10) / 10, 0.4))
        self.update_kb(scancode, True)
        self.shortcut_status(kb_buffer)

    # 键盘松开事件
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if self.ignore_event:
            return
        self.keyRelease(event.nativeScanCode())

    def keyRelease(self, scancode: int):
        self.update_kb(scancode, False)
        self.shortcut_status(kb_buffer)

    def closeEvent(self, event):
        if self.paste_board_dialog.isVisible():
            self.paste_board_dialog.close()
        if self.shortcut_key_dialog.isVisible():
            self.shortcut_key_dialog.close()
        if self.device_setup_dialog.isVisible():
            self.device_setup_dialog.close()
        if self.indicator_dialog.isVisible():
            self.indicator_dialog.close()
        if self.numkeyboard_dialog.isVisible():
            self.numkeyboard_dialog.close()
        return super().closeEvent(event)

    @Slot()
    def on_btnServerSwitch_clicked(self):
        if self.server.running:
            self.server.stop_server()
            self.btnServerSwitch.setIcon(load_icon("Play"))
            logger.info("Server stopped")
            self.kvmSetPortSpin.setEnabled(True)
            self.kvmSetHostLine.setEnabled(True)
            self.kvmSetQualitySpin.setEnabled(True)
            self.kvmSetFpsSpin.setEnabled(True)
            self.kvmSetDeviceCombo.setEnabled(True)
            self.kvmSetResCombo.setEnabled(True)
        else:
            if self.kvmSetDeviceCombo.currentText() == "" or self.kvmSetResCombo.currentText() == "":
                QMessageBox.warning(self, "Warning", "Invalid device")
                return
            self.server.config["video"]["quality"] = self.kvmSetQualitySpin.value()
            # self.server.config["video"]["fps"] = self.kvmSetFpsSpin.value()
            width, height = self.kvmSetResCombo.currentText().split("x")
            self.server.config["video"]["width"] = int(width)
            self.server.config["video"]["height"] = int(height)
            self.server.command_callback = self.server_command_callback
            try:
                host = self.kvmSetHostLine.text()
                port = self.kvmSetPortSpin.value()
                self.server.start_server(
                    host=host,
                    device=self.kvmSetDeviceCombo.currentText(),
                    port=port,
                )
            except Exception as e:
                self.server.running = False
                logger.exception(f"Server start failed")
                return
            self.btnServerSwitch.setIcon(load_icon("Pause"))
            self.kvmSetPortSpin.setEnabled(False)
            self.kvmSetHostLine.setEnabled(False)
            self.kvmSetQualitySpin.setEnabled(False)
            self.kvmSetFpsSpin.setEnabled(False)
            self.kvmSetDeviceCombo.setEnabled(False)
            self.kvmSetResCombo.setEnabled(False)
            logger.info(f"Server hosting on {host}:{port}")

    @Slot()
    def on_btnServerSetAuth_clicked(self):
        # ask if auth is enabled
        box = QMessageBox(self)
        box.setWindowTitle("HTTP Authentication")
        if self.server.auth_required:
            box.setText(f"Authentication is enabled ({count_auth_users()} users)")
            box.b1 = box.addButton("Disable", QMessageBox.ActionRole)
        else:
            box.setText(f"Authentication is disabled")
            box.b1 = box.addButton("Enable", QMessageBox.ActionRole)
        box.b2 = box.addButton("Add User", QMessageBox.ActionRole)
        box.b3 = box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == box.b1:
            self.server.auth_required = not self.server.auth_required
            logger.info(f"Authentication {'enabled' if self.server.auth_required else 'disabled'}")
            if self.server.auth_required and not count_auth_users():
                logger.warning("No user found, remember to add one")
        elif box.clickedButton() == box.b2:
            username, ret = QInputDialog.getText(self, "Add User", "Username:", QLineEdit.Normal, "")
            if not ret:
                return
            password, ret = QInputDialog.getText(self, "Add User", "Password:", QLineEdit.Normal, "")
            if not ret:
                return
            add_auth_user(username, password)
            logger.info(f"User {username} added")

    def refresh_server_device_list(self):
        self.kvmSetDeviceCombo.clear()
        cameras = QMediaDevices.videoInputs()
        devices = []
        rmbd = self.video_config["device_name"]
        for camera in cameras:
            self.kvmSetDeviceCombo.addItem(camera.description())
            devices.append(camera.description())
        if rmbd in devices:
            self.kvmSetDeviceCombo.setCurrentText(rmbd)
        else:
            self.kvmSetDeviceCombo.setCurrentIndex(0)
        self.update_server_device_info()

    def update_server_device_info(self):
        self.kvmSetResCombo.clear()
        selected = self.kvmSetDeviceCombo.currentText()
        cameras = QMediaDevices.videoInputs()
        for camera in cameras:
            if camera.description() == selected:
                camera_info = camera
                break
        else:
            return
        res_list = []
        max_fps = 0
        min_fps = 999
        for i in camera_info.videoFormats():
            resolutions_str = f"{i.resolution().width()}x{i.resolution().height()}"
            if resolutions_str not in res_list:
                res_list.append(resolutions_str)
                self.kvmSetResCombo.addItem(resolutions_str)
            if i.maxFrameRate() > max_fps:
                max_fps = i.maxFrameRate()
            if i.minFrameRate() < min_fps:
                min_fps = i.minFrameRate()
        self.kvmSetFpsSpin.setMaximum(max_fps)
        self.kvmSetFpsSpin.setMinimum(min_fps)
        self.kvmSetFpsSpin.setValue(max_fps)

    def open_server_manager(self):
        if not self.serverFrame.isVisible():
            if self.camera_opened:
                ret = QMessageBox.warning(
                    self,
                    "Warning",
                    "Video device is opened, close it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ret == QMessageBox.Yes:
                    self.set_device(False)
                else:
                    return
            self.takeCentralWidget()
            self.setCentralWidget(self.serverFrame)
            self.disconnect_label.hide()
            self.serverFrame.show()
            self.actionOpen_Server_Manager.setText("Close Server Manager")
            self.refresh_server_device_list()
            self.btnServerSwitch.setIcon(load_icon("Play"))
            self.btnServerOpenBrowser.setIcon(load_icon("Safari"))
            self.btnServerSetAuth.setIcon(load_icon("Lock"))
        else:
            if self.server.running:
                ret = QMessageBox.warning(
                    self,
                    "Warning",
                    "Server is running, stop it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ret == QMessageBox.Yes:
                    self.on_btnServerSwitch_clicked()
                else:
                    return
            self.takeCentralWidget()
            self.setCentralWidget(self.disconnect_label)
            self.serverFrame.hide()
            self.disconnect_label.show()
            self.actionOpen_Server_Manager.setText("Open Server Manager")

    @Slot()
    def on_btnServerOpenBrowser_clicked(self):
        url = f"http://127.0.0.1:{self.kvmSetPortSpin.value()}"
        QDesktopServices.openUrl(QUrl(url))

    def set_log_text(self, text):
        self.serverLogEdit.setText(text)
        self.serverLogEdit.moveCursor(QTextCursor.End)

    def mouse_wheel_act(self):
        if self.mouse_scroll_timer.isActive():
            self.mouse_scroll_timer.stop()
        self.mouse_scroll_timer.start(100)

    def server_command_callback(self, data_type, data_payload):
        global mouse_buffer, kb_buffer
        if data_type == "mouse_wheel":
            if data_payload[0] > 0:
                mouse_buffer[7] = 0x01
            elif data_payload[0] < 0:
                mouse_buffer[7] = 0xFF
            else:
                mouse_buffer[7] = 0
            hidinfo = hid_def.hid_report(mouse_buffer)
            self._wheel_signal.emit()
        elif data_type == "mouse_btn":
            if data_payload[1] == 2:
                mouse_buffer[2] |= data_payload[0]
            elif data_payload[1] == 3:
                mouse_buffer[2] &= ~data_payload[0]
            else:
                mouse_buffer = [2, 0, 0, 0, 0, 0, 0, 0, 0]
            hidinfo = hid_def.hid_report(mouse_buffer)
        elif data_type == "mouse_pos":
            x, y = int(data_payload[0]) & 0x0FFF, int(data_payload[1]) & 0x0FFF
            mouse_buffer[3] = x & 0xFF
            mouse_buffer[4] = x >> 8
            mouse_buffer[5] = y & 0xFF
            mouse_buffer[6] = y >> 8
            hidinfo = hid_def.hid_report(mouse_buffer)
        elif data_type == "keyboard":
            state = data_payload[1]
            key = data_payload[0]
            if state == 3:  # release all
                kb_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                hidinfo = hid_def.hid_report(kb_buffer)
            else:
                self.update_kb_hid(key, state == 1)
                hidinfo = 0
        else:
            print(f"Unknown data type: {data_type}")
            return
        if hidinfo == 1 or hidinfo == 4:
            self.device_event_handle("hid_error")

    def focusInEvent(self, event):
        if self.hook_state:
            print("focusInEvent")
            self.pythoncom_timer.start(500)
            self.hook_manager.HookKeyboard()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if self.hook_state:
            print("focusOutEvent")
            self.hook_manager.UnhookKeyboard()
            self.pythoncom_timer.stop()
        super().focusOutEvent(event)


def clear_splash():
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(),
            "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
        )
        if os.path.exists(splash_filename):
            os.unlink(splash_filename)


def main():
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    qdarktheme.setup_theme(theme="dark" if dark_theme else "light")
    myWin.show()
    QTimer.singleShot(100, myWin.shortcut_status)
    clear_splash()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
