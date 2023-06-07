import time

import hid

product_id = 0x2107
vendor_id = 0x413D
usage_page = 0xFF00

DEBUG = False


def set_debug(debug):
    global DEBUG
    DEBUG = debug


# 初始化HID设备
def init_usb(vendor_id, usage_page):
    if DEBUG:
        print(f"DEBUG: init_usb(vendor_id={vendor_id}, usage_page={usage_page})")
        return 0
    global h
    h = hid.device()
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
        print("Device not found")
        return "Device not found"
    h.open_path(device_path)
    h.set_nonblocking(1)  # enable non-blocking mode
    return 0


# 读写HID设备
def hid_report(buffer=[], r_mode=False, report=0):
    if DEBUG:
        print(f"DEBUG: hid_report(buffer={buffer}, r_mode={r_mode}, report={report})")
        return 0
    buffer = buffer[-1:] + buffer[:-1]
    buffer[0] = 0
    print("<", buffer)
    try:
        h.write(buffer)
    except (OSError, ValueError):
        print("Error writing data to device")
        return 1
    except NameError:
        print("Uninitialized device")
        return 4
    if r_mode:  # 读取回复
        time_start = time.time()
        while 1:
            try:
                d = h.read(64)
            except (OSError, ValueError):
                print("Error reading data from device")
                return 2
            if d:
                # print(">", d)
                break
            if time.time() - time_start > 2:
                print("Device response timeout")
                d = 3
                break
    else:
        d = 0
    return d
