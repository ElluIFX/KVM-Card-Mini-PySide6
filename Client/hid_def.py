import time

import hid
from loguru import logger

product_id = 0x2107
vendor_id = 0x413D
usage_page = 0xFF00

DEBUG = False
VERBOSE = False


def set_debug(debug):
    global DEBUG
    DEBUG = debug


def set_verbose(verbose):
    global VERBOSE
    VERBOSE = verbose


h = hid.device()


# 初始化HID设备
def init_usb(vendor_id, usage_page):
    if DEBUG:
        logger.debug(f"init_usb(vendor_id={vendor_id}, usage_page={usage_page})")
        return 0
    global h
    h = hid.device()
    # h.close()
    hid_enumerate = hid.enumerate()
    device_path = 0
    for i in range(len(hid_enumerate)):
        # if (hid_enumerate[i]['usage_page'] == usage_page and hid_enumerate[i]['vendor_id'] == vendor_id):
        if (
            hid_enumerate[i]["usage_page"] == usage_page
            and hid_enumerate[i]["vendor_id"] == vendor_id
            and hid_enumerate[i]["product_id"] == product_id
        ):
            device_path = hid_enumerate[i]["path"]
            # print("Found target devicd:", hid_enumerate[i])
    if device_path == 0:
        logger.error("Device not found")
        return 1
    h.open_path(device_path)
    h.set_nonblocking(1)  # enable non-blocking mode
    return 0


def check_connection() -> bool:
    try:
        h.read(1)
        return True
    except Exception:
        return False
    return False


# 读写HID设备
def hid_report(buffer=[], r_mode=False, report=0):
    if DEBUG:
        logger.debug(f"hid_report(buffer={buffer}, r_mode={r_mode}, report={report})")
        return 0
    buffer = buffer[-1:] + buffer[:-1]
    buffer[0] = 0
    if VERBOSE:
        logger.debug(f"hid < {buffer}")
    try:
        h.write(buffer)
    except (OSError, ValueError):
        logger.error("Error writing data to device")
        return 1
    except NameError:
        logger.error("Uninitialized device")
        return 4
    if r_mode:  # 读取回复
        time_start = time.perf_counter()
        while 1:
            try:
                d = h.read(64)
            except (OSError, ValueError):
                logger.error("Error reading data from device")
                return 2
            if d:
                if VERBOSE:
                    logger.debug(f"hid > {d}")
                break
            if time.perf_counter() - time_start > 2:
                logger.error("Device response timeout")
                d = 3
                break
    else:
        d = 0
    return d
