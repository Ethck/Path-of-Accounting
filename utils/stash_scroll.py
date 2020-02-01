# WARNING: DO NOT RUN THIS IN A DEBUGGER
# WARNING: Might trigger some anti-virus software (but we are open source so what?)


import os
from utils.config import STASHTAB_SCROLLING
if os.name == "nt" and STASHTAB_SCROLLING:

    import win32con
    import ctypes
    import atexit
    import sys
    from ctypes import *
    from ctypes.wintypes import DWORD, WPARAM, LPARAM, ULONG, POINT
    from multiprocessing import Process
    from utils.input import Keyboard


    class PoEScrollStash():
        def __init__(self):
            super(PoEScrollStash, self).__init__()
            self.daemon = True
            self.enabled = False
            self.keyboard_hook = None
            self.mouse_hook = None
            self.ctrl_pressed = False
        def enable(self, keyboard_callback, mouse_callback):
            if self.enabled:
                return
            self.enabled = True
            self.keyboard_hook = windll.user32.SetWindowsHookExA(win32con.WH_KEYBOARD_LL, keyboard_callback, windll.kernel32.GetModuleHandleW(None),0)
            self.mouse_hook = windll.user32.SetWindowsHookExA(win32con.WH_MOUSE_LL, mouse_callback, windll.kernel32.GetModuleHandleW(None),0)
            atexit.register(windll.user32.UnhookWindowsHookEx, self.keyboard_hook)
            atexit.register(windll.user32.UnhookWindowsHookEx, self.mouse_hook)
        def disable(self):
            if not self.enabled:
                return
            self.enabled = False
            windll.user32.UnhookWindowsHookEx(self.keyboard_hook)
            windll.user32.UnhookWindowsHookEx(self.mouse_hook)
            self.keyboard_hook = None
            self.mouse_hook = None
        def run(self):
            while self.enabled:
                try:
                    msg = ctypes.wintypes.MSG()
                    windll.user32.GetMessageA(byref(msg), 0, 0, 0)
                    windll.user32.TranslateMessage(msg)
                    windll.user32.DispatchMessageA(msg)
                except:
                    pass
            disable()
            
    class KBDLLHOOKSTRUCT(Structure): _fields_=[('vkCode',DWORD),('scanCode',DWORD),('flags',DWORD),('time',DWORD),('dwExtraInfo',ULONG)]

    scroll = PoEScrollStash()
    keyboard = Keyboard()
    def keyboard_callback(ncode, wparam, lparam):
        if ncode < 0:
            return windll.user32.CallNextHookEx(scroll.keyboard_hook, ncode, wparam, lparam)
        
        key = KBDLLHOOKSTRUCT.from_address(lparam)
        if key.vkCode == win32con.VK_LCONTROL:
            if wparam == win32con.WM_KEYDOWN:
                scroll.ctrl_pressed = True
            elif wparam == win32con.WM_KEYUP:
                scroll.ctrl_pressed = False
        return windll.user32.CallNextHookEx(scroll.keyboard_hook, ncode, wparam, lparam)



    class MSLLHOOKSTRUCT(Structure): _fields_=[('pt',POINT),('mouseData',DWORD),('flags',DWORD),('time',DWORD),('dwExtraInfo',ULONG)]

    def mouse_callback(ncode, wparam, lparam):
        if ncode < 0:
            return windll.user32.CallNextHookEx(scroll.keyboard_hook, ncode, wparam, lparam)
        if wparam == win32con.WM_MOUSEWHEEL:
            data = MSLLHOOKSTRUCT.from_address(lparam)
            a = ctypes.c_short(data.mouseData >> 16).value
            if a > 0: # up
                if scroll.ctrl_pressed:
                    keyboard.press_and_release("left")
                    return 1
            elif a < 0: # down
                if scroll.ctrl_pressed:
                    keyboard.press_and_release("right")
                    return 1 
        return windll.user32.CallNextHookEx(scroll.keyboard_hook, ncode, wparam, lparam)


    def setup():
        #                               (this, ncode, wparam, lparam)
        c_func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM)
        kc = c_func(keyboard_callback)
        mc = c_func(mouse_callback)
        scroll.enable(kc,mc)
        scroll.run()

if os.name == "nt" and STASHTAB_SCROLLING:
        p = Process(target=setup, args=())

def start_stash_scroll():
    if os.name == "nt" and STASHTAB_SCROLLING:
        p.daemon = True
        p.start()
def stop_stash_scroll():
    if os.name == "nt" and STASHTAB_SCROLLING:
        scroll.disable()
        p.terminate()

#Testing
if __name__ == '__main__':
    try:
        start_stash_scroll()
        while True:
            pass
    except KeyboardInterrupt:
            pass