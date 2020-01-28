import keyboard
import mouse

import parse
import os
if os.name == "nt":
    import win32gui

def is_PoE():
    if os.name == "nt":
        if  win32gui.GetWindowText(win32gui.GetForegroundWindow()) == "Path of Exile":
            return True
        return False
    else: #TODO Linux/mac support
        return True

def watch_keyboard():
    keyboard.add_hotkey("alt+d", copy_alt, suppress=False)
    keyboard.on_press_key("f5", goto_hideout, suppress=False)
    mouse.hook(tab_switch) # TODO SUPPRESS scroll wheel (zooming in and out)

    # keyboard.add_hotkey('alt+w', parse.open_wiki())



def goto_hideout(self):
    if is_PoE():
        keyboard.write("\n/hideout\n")

def copy_alt():
    if is_PoE():
        keyboard.press_and_release("ctrl+c")

def tab_switch(evn):
    if isinstance(evn, mouse.WheelEvent) and is_PoE():
        if keyboard.is_pressed("ctrl"):  # TODO SUPPRESS scroll wheel (zooming in and out)
            if evn.delta > 0:
                keyboard.press_and_release("left")
            if evn.delta < 0:
                keyboard.press_and_release("right")

if __name__ == "__main__":
    print("Please execute parse.py to interact with this script.")
