import keyboard
import parse

def watch_keyboard():
    keyboard.add_hotkey('f5', lambda: keyboard.write('\n/hideout\n'))

    keyboard.add_hotkey('alt+d', lambda: keyboard.press_and_release('ctrl+c'))

    #keyboard.add_hotkey('alt+w', parse.open_wiki())


if __name__ == "__main__":
    print("Please execute parse.py to interact with this script.")