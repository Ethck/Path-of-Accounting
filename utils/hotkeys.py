import keyboard

import parse


def watch_keyboard():
    # Use the "f5" key to go to hideout
    keyboard.add_hotkey("f5", lambda: keyboard.write("\n/hideout\n"))

    # Use the alt+d key as an alternative to ctrl+c
    keyboard.add_hotkey("alt+d", lambda: parse.hotkey_handler("ctrl+c"))

    keyboard.add_hotkey("alt+t", lambda: parse.hotkey_handler("alt+t"))

    keyboard.add_hotkey("ctrl+c", lambda: parse.hotkey_handler("ctrl+c"))


if __name__ == "__main__":
    print("Please execute parse.py to interact with this script.")
