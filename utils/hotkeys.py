import keyboard

import parse


def watch_keyboard():
    # Use the "f5" key to go to hideout
    keyboard.add_hotkey("f5", lambda: keyboard.write("\n/hideout\n"))

    # Use the alt+d key as an alternative to ctrl+c
    keyboard.add_hotkey("alt+d", lambda: keyboard.press_and_release("ctrl+c"))

    keyboard.add_hotkey("alt+t", lambda: parse.open_trade_site())


if __name__ == "__main__":
    print("Please execute parse.py to interact with this script.")
