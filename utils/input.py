import os
import traceback
from queue import Empty, Queue
from tkinter import TclError

import pyperclip
import keyboard

from utils.config import STASHTAB_SCROLLING

def get_clipboard():
    """Retrieves the current value in the clipboard

    :return: Value in clipboard
    """
    return pyperclip.paste()


class Keyboard:
    def __init__(self):
        self.hotkeys = {}
        self.queue = Queue()

    def poll(self):
        try:
            key = self.queue.get_nowait()
            self.hotkeys[key]()
        except Empty:
            return
        except Exception:
            # Do not fail
            print("Unexpected exception occurred while handling hotkey: ")
            traceback.print_exc()
        self.queue.task_done()

    def write(self, string):
        keyboard.write(string)

    def add_hotkey(self, key, func):
        self.hotkeys[key] = func
        keyboard.add_hotkey(key, lambda: self.queue.put(key))

    def press_and_release(self, key):
        keyboard.press_and_release(key)


if os.name == "nt" and STASHTAB_SCROLLING:
    import win32con
    import ctypes
    import atexit
    from ctypes import *
    from ctypes.wintypes import (
        DWORD,
        WPARAM,
        LPARAM,
        ULONG,
        POINT,
        HMODULE,
        LPCWSTR,
    )
    user32 = ctypes.WinDLL('user32', use_last_error=False)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=False)
    from threading import Thread
    from win32gui import GetWindowText, GetForegroundWindow
    import struct

    bits = struct.calcsize("P") * 8


    class MSLLHOOKSTRUCT(Structure):
        """ A structure representing a mouse input event on Windows
            used to convert the data pointed to by lparam
            into a easier readable format
            https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-msllhookstruct
        """

        _fields_ = [
            ("pt", POINT),  # mouse coordinates
            (
                "mouseData",
                DWORD,
            ),  # flags for which button and what state it entered
            ("flags", DWORD),  # flags for the event
            ("time", DWORD),  # time the event happened
            ("dwExtraInfo", ULONG),  # pointer to extra info
        ]

    class KBDLLHOOKSTRUCT(Structure):
        """ A structure representing a keyboard input event on Windows
            used to convert the data pointed to by lparam
            into a easier readable format
            https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-kbdllhookstruct
        """

        _fields_ = [
            ("vkCode", DWORD),  # virtual key-code
            ("scanCode", DWORD),  # hardware scan code
            ("flags", DWORD),  # flags for the event
            ("time", DWORD),  # time of message
            ("dwExtraInfo", ULONG),  # pointer to extra info
        ]

    # Helper to convert python function to a c function with args (this,ncode, wparam,lparam)
    c_func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM, use_errno=False, use_last_error=False)

    mouse_hook = None
    keyboard_hook = None

    def add_hook(hook_type, callback):
        GetModuleHandleW = kernel32.GetModuleHandleW
        GetModuleHandleW.restype = HMODULE
        GetModuleHandleW.argtypes = [LPCWSTR]
        # If we are running the program (Python interpreter)
        # in 64 bits mode, we need to handle 64 bit addresses
        if bits == 64:
            handle = ctypes.c_longlong(GetModuleHandleW(None))
        # Else 32 bit addresses
        else:
            handle = GetModuleHandleW(None)
        hook = user32.SetWindowsHookExA(
            hook_type, callback, handle, 0
        )
        atexit.register(user32.UnhookWindowsHookEx, hook)
        return hook

    def remove_hook(hook):
        if hook:
            user32.UnhookWindowsHookEx(hook)
            hook = None
        return hook


    ctrl_pressed = False


    def mouse_callback(ncode, wparam, lparam):
        """ Callback function windows calls
            when a mouse event is triggered

        :param ncode:
            Set by the os, if less than 0 call next hook immediately
            (Technically its always 0 for mouse callback)
        :param wparam:
            Identifies the mouse message
            can be WM_LBUTTONDOWN, WM_LBUTTONUP, WM_MOUSEMOVE,
            WM_MOUSEWHEEL, WM_MOUSEHWHEEL, WM_RBUTTONDOWN, or WM_RBUTTONUP.
        :param lparam:
            Pointer to a MSLLHOOKSTRUCT struct

        :return: CallNextHookEx(), or 1 if its blocking the input
        """
        global keyboard_hook, ctrl_pressed
        if (  # If we are in Path of Exile
            # and mouse wheel is scrolled
            # and ctrl is down
            ncode >= 0
            and ctrl_pressed
            and GetWindowText(GetForegroundWindow()) == "Path of Exile"
            and wparam == win32con.WM_MOUSEWHEEL
        ):
            data = MSLLHOOKSTRUCT.from_address(lparam)
            # get mouse wheel delta
            a = ctypes.c_short(data.mouseData >> 16).value
            if a > 0:  # mouse wheel up
                keyboard.press_and_release("left")
                return 1  # Block the input from going to PoE
            elif a < 0:  # mouse wheel down
                keyboard.press_and_release("right")
                return 1  # Block the input from going to PoE
        # If we are running on 64 bits, make sure we dont lose data
        if bits == 64:
            return user32.CallNextHookEx(
                ctypes.c_longlong(mouse_hook),
                ctypes.c_longlong(ncode),
                ctypes.c_longlong(wparam),
                ctypes.c_longlong(lparam),
            )
        else:
            return user32.CallNextHookEx(
                mouse_hook, ncode, wparam, lparam
            )


    def keyboard_callback(ncode, wparam, lparam):
        """ Callback function windows calls
            when a keyboard event is triggered

        :param ncode:
            Set by the os, if less than 0 call next hook immediately
            (Technically its always 0 for keyboard callback)
        :param wparam:
            Identifies the keyboard message
            can be WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, or WM_SYSKEYUP.
        :param lparam:
            Pointer to a KBDLLHOOKSTRUCT struct

        :return: CallNextHookEx()
        """
        global keyboard_hook, mouse_hook, ctrl_pressed
        if ncode >= 0:
            key = KBDLLHOOKSTRUCT.from_address(lparam)
            if key.vkCode == win32con.VK_LCONTROL:
                if wparam == win32con.WM_KEYDOWN:
                    # If PoE is in focus and ctrl is pressed down
                    ctrl_pressed = True
                else:
                    ctrl_pressed = False
        # If we are running on 64 bits, make sure we dont lose data
        if bits == 64:
            return user32.CallNextHookEx(
                ctypes.c_longlong(keyboard_hook),
                ctypes.c_longlong(ncode),
                ctypes.c_longlong(wparam),
                ctypes.c_longlong(lparam),
            )
        else:
            return user32.CallNextHookEx(
                keyboard_hook, ncode, wparam, lparam
            )


    class StashRunner(Thread):
        def __init__(self):
            super().__init__()
            self.isRunning = True
            self.pid = None

        def run(self):
            """ Registers the keyboard and mouse callbacks
                with the windows os and starts the message loop

            """
            global keyboard_hook, mouse_hook
            self.pid = kernel32.GetCurrentThreadId()
            # Convert keyboard and mouse callback
            kc = c_func(keyboard_callback)
            keyboard_hook = add_hook(win32con.WH_KEYBOARD_LL, kc)
            mc = c_func(mouse_callback)
            mouse_hook = add_hook(win32con.WH_MOUSE_LL, mc)

            while self.isRunning:
                try:
                    msg = ctypes.wintypes.MSG()
                    user32.GetMessageA(byref(msg), 0, 0, 0)
                except:
                    pass
            keyboard_hook = remove_hook(keyboard_hook)
            mouse_hook = remove_hook(mouse_hook)
            

    p = StashRunner()


def start_stash_scroll():
    """ Starts a new daemon thread and calls setup
    """
    if os.name == "nt" and STASHTAB_SCROLLING:
        p.start()


def stop_stash_scroll():
    """ Disables the hooks and stops the thread
    """
    global enabled, keyboard_hook, mouse_hook
    if os.name == "nt" and STASHTAB_SCROLLING:
        p.isRunning = False
        user32.PostThreadMessageW(p.pid, 0x0012, 0, 0)
        p.join()
