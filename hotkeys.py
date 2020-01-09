import keyboard 

def watch_keyboard():
    keyboard.add_hotkey('f5', lambda: keyboard.write('\n/hideout\n'))


if __name__ == "__main__":
    print("Please use parse.py to interact with this script.")