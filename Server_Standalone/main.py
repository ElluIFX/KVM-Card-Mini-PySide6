import argparse
import os
import subprocess
import sys
import time

import hid_def
import yaml
from loguru import logger
from server_us import KVM_Server, add_auth_user

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-ht", "--host", default="0.0.0.0", help="Host IP (default: 0.0.0.0)")
arg_parser.add_argument("-wp", "--web_port", default=5000, type=int, help="Web Interface Port (default: 5000)")
arg_parser.add_argument("-vp", "--video_port", default=5001, type=int, help="Video Port (default: 5001)")
arg_parser.add_argument("-d", "--device", default=None, type=str, help="Device Path")
arg_parser.add_argument("-r", "--res", default="1920x1080", type=str, help="Video Resolution (default: 1280x720)")
arg_parser.add_argument("-q", "--quality", default=60, type=int, help="Video Quality (default: 60)")
arg_parser.add_argument(
    "-f",
    "--format",
    default="MJPEG",
    type=str,
    choices=["YUYV", "UYVY", "RGB565", "RGB24", "MJPEG", "JPEG"],
    help="Video Format (default: MJPG)",
)
arg_parser.add_argument(
    "-e", "--encoder", default="CPU", type=str, choices=["CPU", "HW", "NOOP"], help="Video Encoder (default: CPU)"
)
arg_parser.add_argument(
    "--auth", default=None, type=str, help="HTTP Authentification (username:password) (default off)"
)
arg_parser.add_argument("--extra", default=None, type=str, help="Extra arguments passed to ustreamer")

args = arg_parser.parse_args()

if args.auth is not None:
    assert ":" in args.auth, "Authentification must be in format username:password"

# check if ustreamer is installed
cmd = "which ustreamer"
if subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
    logger.error("ustreamer is not installed, try to install it with `sudo apt install ustreamer`")
    sys.exit(1)

kb_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
mouse_buffer = [2, 0, 0, 0, 0, 0, 0, 0, 0]
shift_symbol = [
    ")","!","@","#","$","%",
    "^","&","*","(","~","_",
    "+","{","}","|",":",'"',
    "<",">","?",
]  # fmt: skip

PATH = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(PATH, "keyboard.yaml"), "r") as load_f:
    keyboard_code = yaml.safe_load(load_f)


def strB2Q(uchar):
    inside_code = ord(uchar)
    if inside_code == 0x3000:
        inside_code = 0x0020
    else:
        inside_code -= 0xFEE0
    if inside_code < 0x0020 or inside_code > 0x7E:  # 转完之后不是半角字符返回原来的字符
        return uchar
    return chr(inside_code)


def reset_keymouse(s):
    if s == 1:  # keyboard
        for i in range(2, len(kb_buffer)):
            kb_buffer[i] = 0
        hid_def.hid_report(kb_buffer)
    elif s == 2:  # MCU
        hid_def.hid_report([4, 0])
    elif s == 3:  # mouse
        for i in range(2, len(mouse_buffer)):
            mouse_buffer[i] = 0
        hid_def.hid_report(mouse_buffer)
    elif s == 4:  # hid
        hid_def.init_usb(hid_def.vendor_id, hid_def.usage_page)


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


def update_kb_hid(hid: int, state: bool):
    if state:
        if hid in hid_to_b2:
            kb_buffer[2] |= hid_to_b2[hid]
        else:
            for i in range(4, 10):
                if kb_buffer[i] == hid:
                    return
                if kb_buffer[i] == 0:
                    kb_buffer[i] = hid
                    break
            else:
                logger.error("Buffer overflow")
    else:
        if hid in hid_to_b2:
            kb_buffer[2] &= ~hid_to_b2[hid]
        else:
            for i in range(4, 10):
                if kb_buffer[i] == hid:
                    kb_buffer[i] = 0
                    break
            else:
                logger.error("Key not found in buffer")
    hidinfo = hid_def.hid_report(kb_buffer)
    return hidinfo


mouse_scroll_triggered = False
last_mouse_scroll = 0


def mouse_scroll_stop(self):
    global mouse_scroll_triggered, last_mouse_scroll
    while True:
        while (not mouse_scroll_triggered) or (time.perf_counter() - last_mouse_scroll < 0.1):
            time.sleep(0.01)
        mouse_scroll_triggered = False
        mouse_buffer[7] = 0
        hid_def.hid_report(mouse_buffer)


def send_char(c):
    char_buffer = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    shift = False
    if c == "\n":
        mapcode = keyboard_code["ENTER"]
    elif c == "\t":
        mapcode = keyboard_code["TAB"]
    elif c == " ":
        mapcode = keyboard_code["SPACE"]
    else:
        try:
            cq = strB2Q(c)
            mapcode = keyboard_code[cq.upper()]
            if cq.isupper():
                shift = True
        except KeyError:
            return 2
    mapcode = int(mapcode, 16)
    char_buffer[4] = mapcode
    if c in shift_symbol or shift:
        char_buffer[2] |= 2
    hid_def.hid_report(char_buffer)
    time.sleep(0.1)
    hid_def.hid_report([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.1)


def paste_board_send(text):
    text = text.replace("\r\n", "\n")
    total = len(text)
    if total == 0:
        return
    for c in text:
        send_char(c)


def server_command_callback(data_type, data_payload):
    global mouse_buffer, kb_buffer, mouse_scroll_triggered, last_mouse_scroll
    if data_type == "reset_mcu":
        reset_keymouse(2)
    elif data_type == "reset_hid":
        reset_keymouse(4)
    if data_type == "mouse_wheel":
        if data_payload[0] > 0:
            mouse_buffer[7] = 0x01
        elif data_payload[0] < 0:
            mouse_buffer[7] = 0xFF
        else:
            mouse_buffer[7] = 0
        hidinfo = hid_def.hid_report(mouse_buffer)
        last_mouse_scroll = time.perf_counter()
        mouse_scroll_triggered = True
    elif data_type == "mouse_btn":
        if data_payload[1] == 2:
            mouse_buffer[2] |= data_payload[0]
        elif data_payload[1] == 3:
            mouse_buffer[2] &= ~data_payload[0]
        else:
            mouse_buffer = [2, 0, 0, 0, 0, 0, 0, 0, 0]
        hidinfo = hid_def.hid_report(mouse_buffer)
    elif data_type == "mouse_pos":
        x, y = int(data_payload[0]) & 0x7FFF, int(data_payload[1]) & 0x7FFF
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
            hidinfo = update_kb_hid(key, state == 1)
            hidinfo = 0
    elif data_type == "paste":
        logger.debug(f"Received {len(data_payload)} bytes paste data")
        paste_board_send(data_payload)
        hidinfo = 0
    else:
        return
    if hidinfo == 1 or hidinfo == 4:
        logger.warning(f"HID Error {hidinfo}")


hid_def.init_usb()
server = KVM_Server()
server.command_callback = server_command_callback
if args.auth is not None:
    username = args.auth.split(":")[0]
    password = args.auth.split(":")[1]
    add_auth_user(username, password)
    logger.info(f"Added auth user {username}")
    server.auth_required = True
server.start_server(host=args.host, port=args.web_port, config= vars(args), block=True)
