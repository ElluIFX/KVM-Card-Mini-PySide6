import pythoncom
import win32com
import pyWinhook as pyHook
import threading as thd
import time
def onKeyboardEvent(event):
    print('MessageName: %s' % event.MessageName)
    print('Message: %s' % event.Message)
    print('Time: %s' % event.Time)
    print('Window: %s' % event.Window)
    print('WindowName: %s' % event.WindowName)
    print('Ascii: %s' %  event.Ascii, chr(event.Ascii))
    print('Key: %s' %  event.Key)
    print('KeyID: %s' %  event.KeyID)
    print('ScanCode: %s' %  event.ScanCode)
    print('Extended: %s' %  event.Extended)
    print('Injected: %s' %  event.Injected)
    print('Alt %s' %  event.Alt)
    print('Transition %s' %  event.Transition)
    print('---')
    return True

def main():
	# 创建管理器
    hm = pyHook.HookManager()
    # 监听键盘
    hm.KeyDown = onKeyboardEvent
    hm.HookKeyboard()
    # hm.UnhookKeyboard()
    # 循环监听
    while True:
        time.sleep(0.01)
        pythoncom.PumpWaitingMessages()

if __name__ == "__main__":
    main()
