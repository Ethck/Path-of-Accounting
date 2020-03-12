import os
from queue import Empty, Queue
from tkinter import TclError

import pyperclip

from utils.config import STASHTAB_SCROLLING

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
    from multiprocessing import Process
    from win32gui import GetWindowText, GetForegroundWindow
    import struct

    bits = struct.calcsize("P") * 8

is_keyboard_module_available = False
try:
    # This will raise error in case user is not running as root
    import keyboard

    keyboard.add_hotkey("x", lambda: print())
    keyboard.remove_hotkey("x")
    is_keyboard_module_available = True
except Exception:
    is_keyboard_module_available = False

is_pyinput_module_available = False
if not is_keyboard_module_available:
    try:
        # This will raise error if there is no display environment
        from pynput.keyboard import GlobalHotKeys, Controller, Key

        is_pyinput_module_available = True
    except Exception:
        is_pyinput_module_available = False


def get_clipboard():
    """Retrieves the current value in the clipboard

    :return: Value in clipboard
    """
    return pyperclip.paste()


class HotkeyWatcher:
    """
    Watches for changes in hotkey queue and calls callback
    """

    def __init__(self, combination_to_function):
        self.queue = Queue()
        self.combination_to_function = combination_to_function

    def is_empty(self):
        return self.queue.unfinished_tasks == 0 and self.queue.qsize() == 0

    def push(self, hotkey):
        if self.is_empty():
            self.queue.put(hotkey)

    def poll(self):
        try:
            hotkey = self.queue.get_nowait()
            self.combination_to_function[hotkey]()
        except Empty:
            return
        #except Exception as e:
            # Do not fail
            #print(
            #    "Unexpected exception occurred while handling hotkey: "
            #    + str(e)
            #)

        self.queue.task_done()


class Keyboard:
    CLIPBOARD_HOTKEY = "<ctrl>+c"

    def __init__(self):
        self.combination_to_function = {}
        self.hotkey_watcher = None
        self.clipboard_watcher = None

        # For Stashtab Scrolling
        self.enabled = False
        self.keyboard_hook = None
        self.mouse_hook = None
        self.ctrl_pressed = False

        if is_pyinput_module_available:
            self.controller = Controller()
            self.listener = None

    def add_hotkey(self, hotkey, fun):
        self.combination_to_function[hotkey] = fun

    def start(self):
        # Create hotkey watcher with all our hotkey callbacks
        self.hotkey_watcher = HotkeyWatcher(self.combination_to_function)
        combination_to_queue = {}

        def to_watcher(watcher, hotkey):
            return lambda: watcher.push(hotkey)

        # Convert hotkey callbacks to proxy everything to hotkey watcher
        for h in self.combination_to_function:
            if h != "clipboard":
                combination_to_queue[h] = to_watcher(self.hotkey_watcher, h)

        if is_keyboard_module_available:
            for h in combination_to_queue:
                keyboard.add_hotkey(
                    h.replace("<", "").replace(">", ""),
                    combination_to_queue[h],
                )
        elif is_pyinput_module_available:
            self.listener = GlobalHotKeys(combination_to_queue)
            self.listener.daemon = True
            self.listener.start()

    def poll(self):
        self.hotkey_watcher.poll()

    def write(self, string):
        if is_keyboard_module_available:
            keyboard.write(string)
        elif is_pyinput_module_available:
            self.controller.type(string)

    def press_and_release(self, key):
        if is_keyboard_module_available:
            keyboard.press_and_release(key)
        elif is_pyinput_module_available:

            def safe_press(controller, k, press=True):
                try:
                    # Lazy way to try and convert special key to enum
                    k = Key[k]
                except Exception:
                    pass

                if press:
                    controller.press(k)
                else:
                    controller.release(k)

            keys = key.split("+")

            if len(keys) == 2:
                # Press first key, then second key, then release second key and finally release first key
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[1])
                safe_press(self.controller, keys[1], False)
                safe_press(self.controller, keys[0], False)
            elif len(keys) == 1:
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[0], False)

    def enable_hook(self, keyboard_callback, mouse_callback):
        """ Registers a keyboard callback and a mouse callback
            with windows os, if its not already enabled.
            
            Also unregisters the callbacks incase of program crash

            :param: keyboard_callback
                    callback function for keyboard events, 
                    must be in a c function format
            :param: mouse_callback
                    callback function for mouse events, 
                    must be in a c function format
        """
        if self.enabled:
            return
        self.enabled = True
        GetModuleHandleW = windll.kernel32.GetModuleHandleW
        GetModuleHandleW.restype = HMODULE
        GetModuleHandleW.argtypes = [LPCWSTR]
        # If we are running the program (Python interpreter)
        # in 64 bits mode, we need to handle 64 bit addresses
        if bits == 64:
            handle = ctypes.c_longlong(GetModuleHandleW(None))
        # Else 32 bit addresses
        else:
            handle = GetModuleHandleW(None)
        self.keyboard_hook = windll.user32.SetWindowsHookExA(
            win32con.WH_KEYBOARD_LL, keyboard_callback, handle, 0
        )
        self.mouse_hook = windll.user32.SetWindowsHookExA(
            win32con.WH_MOUSE_LL, mouse_callback, handle, 0
        )
        atexit.register(windll.user32.UnhookWindowsHookEx, self.keyboard_hook)
        atexit.register(windll.user32.UnhookWindowsHookEx, self.mouse_hook)

    def disable_hook(self):
        """ Removes the keyboard and mouse hooks / callbacks

        """
        if not self.enabled:
            return
        self.enabled = False
        windll.user32.UnhookWindowsHookEx(self.keyboard_hook)
        windll.user32.UnhookWindowsHookEx(self.mouse_hook)
        self.keyboard_hook = None
        self.mouse_hook = None

    def run_stash_macro(self):
        """ Loop that gets messages from windows os and dispatch them

        """
        while self.enabled:
            try:
                msg = ctypes.wintypes.MSG()
                windll.user32.GetMessageA(byref(msg), 0, 0, 0)
                windll.user32.TranslateMessage(msg)
                windll.user32.DispatchMessageA(msg)
            except:
                pass
        disable_hook()


if os.name == "nt" and STASHTAB_SCROLLING:

    class KBDLLHOOKSTRUCT(Structure):
        """ A structure representing a keyboard input event on Windows
            used to convert the data pointed to by lparam
            into a easier readable format
            https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-kbdllhookstruct
        """
        _fields_ = [
            ("vkCode", DWORD), # virtual key-code
            ("scanCode", DWORD), # hardware scan code
            ("flags", DWORD), # flags for the event
            ("time", DWORD), # time of message
            ("dwExtraInfo", ULONG), # pointer to extra info
        ]

    kb_macro = Keyboard()

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
        if (
            ncode >= 0
        ):
            key = KBDLLHOOKSTRUCT.from_address(lparam)
            if key.vkCode == win32con.VK_LCONTROL:
                if (
                    wparam == win32con.WM_KEYDOWN
                    ):
                    # If PoE is in focus and ctrl is pressed down
                    kb_macro.ctrl_pressed = True
                else:
                    kb_macro.ctrl_pressed = False
        # If we are running on 64 bits, make sure we dont lose data
        if bits == 64:
            return windll.user32.CallNextHookEx(
                ctypes.c_longlong(kb_macro.keyboard_hook),
                ctypes.c_longlong(ncode),
                ctypes.c_longlong(wparam),
                ctypes.c_longlong(lparam),
            )
        else:
            return windll.user32.CallNextHookEx(
                kb_macro.keyboard_hook, ncode, wparam, lparam
            )

    class MSLLHOOKSTRUCT(Structure):
        """ A structure representing a mouse input event on Windows
            used to convert the data pointed to by lparam
            into a easier readable format
            https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-msllhookstruct
        """
        _fields_ = [
            ("pt", POINT), # mouse coordinates
            ("mouseData", DWORD), # flags for which button and what state it entered
            ("flags", DWORD), # flags for the event
            ("time", DWORD), # time the event happened
            ("dwExtraInfo", ULONG), # pointer to extra info
        ]

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
        if ( # If we are in Path of Exile 
            # and mouse wheel is scrolled
            # and ctrl is down
            ncode >= 0
            and kb_macro.ctrl_pressed
            and GetWindowText(GetForegroundWindow()) == "Path of Exile"
            and wparam == win32con.WM_MOUSEWHEEL
        ):
            data = MSLLHOOKSTRUCT.from_address(lparam)
            # get mouse wheel delta
            a = ctypes.c_short(data.mouseData >> 16).value
            if a > 0:  # mouse wheel up
                kb_macro.press_and_release("left")
                return 1 # Block the input from going to PoE
            elif a < 0:  # mouse wheel down
                kb_macro.press_and_release("right")
                return 1 # Block the input from going to PoE
        # If we are running on 64 bits, make sure we dont lose data
        if bits == 64:
            return windll.user32.CallNextHookEx(
                ctypes.c_longlong(kb_macro.mouse_hook),
                ctypes.c_longlong(ncode),
                ctypes.c_longlong(wparam),
                ctypes.c_longlong(lparam),
            )
        else:
            return windll.user32.CallNextHookEx(
                kb_macro.mouse_hook, ncode, wparam, lparam
            )

    def setup():
        """ Registers the keyboard and mouse callbacks
            with the windows os and starts the message loop

        """
        # Helper to convert python function to a c function with args (this,ncode, wparam,lparam)
        c_func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM)
        # Convert keyboard and mouse callback
        kc = c_func(keyboard_callback)
        mc = c_func(mouse_callback)
        # Set the hooks, register callback with os
        kb_macro.enable_hook(kc, mc)
        # Handle message loop
        kb_macro.run_stash_macro()

    p = Process(target=setup, args=())


def start_stash_scroll():
    """ Starts a new daemon thread and calls setup
    """
    if os.name == "nt" and STASHTAB_SCROLLING:
        p.daemon = True
        p.start()


def stop_stash_scroll():
    """ Disables the hooks and stops the thread
    """
    if os.name == "nt" and STASHTAB_SCROLLING:
        kb_macro.disable_hook()
        p.terminate()
