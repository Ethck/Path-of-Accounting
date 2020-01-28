import time
from threading import Thread
from tkinter import TclError
import pyperclip

try:
    import keyboard
    keyboard.add_hotkey('c', lambda: print())
    keyboard.clear_all_hotkeys()
    is_keyboard_module_available = True
except Exception:
    is_keyboard_module_available = False


if not is_keyboard_module_available:
    try:
        from pynput.keyboard import GlobalHotKeys, Controller, Key
        is_pyinput_module_available = True
    except Exception:
        is_pyinput_module_available = False


def get_clipboard():
    return pyperclip.paste()


class ClipboardWatcher(Thread):
    def __init__(self, callback, pause=0.3):
        super(ClipboardWatcher, self).__init__()
        self.callback = callback
        self.pause = pause
        self.stopping = False

    def run(self):
        prev = ""

        while not self.stopping:
            try:
                text = get_clipboard()

                if text != prev:
                    self.callback(text)

                prev = text
                time.sleep(self.pause)
            except (TclError, UnicodeDecodeError):  # ignore non-text clipboard contents
                continue
            except KeyboardInterrupt:
                break

    def stop(self):
        self.stopping = True


class Keyboard:
    CLIPBOARD_HOTKEY = '<ctrl>+c'

    def __init__(self):
        self.combination_to_function = {}

        if is_pyinput_module_available:
            self.controller = Controller()
            self.listener = None
        elif not is_keyboard_module_available:
            self.clipboard_watcher = ClipboardWatcher(lambda text: self.combination_to_function[Keyboard.CLIPBOARD_HOTKEY](text))

    def add_hotkey(self, hotkey, fun):
        self.combination_to_function[hotkey] = fun

    def start(self):
        if is_keyboard_module_available:
            for h in self.combination_to_function:
                hotkey = h.replace('<', '').replace('>', '')
                keyboard.add_hotkey(hotkey, self.combination_to_function[h])
        elif is_pyinput_module_available:
            self.listener = GlobalHotKeys(self.combination_to_function)
            self.listener.start()
        else:
            self.clipboard_watcher.start()

    def wait(self):
        if is_keyboard_module_available:
            keyboard.wait()
        elif is_pyinput_module_available:
            self.listener.join()
        else:
            self.clipboard_watcher.join()

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
                    if press:
                        controller.press(k)
                    else:
                        controller.release(k)
                except ValueError:
                    k = Key[k]
                    if press:
                        controller.press(k)
                    else:
                        controller.release(k)

            keys = key.split('+')

            if len(keys) == 2:
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[1])
                safe_press(self.controller, keys[1], False)
                safe_press(self.controller, keys[0], False)
            elif len(keys) == 1:
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[0], False)
