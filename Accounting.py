import logging
import sys
import time
from colorama import Fore, deinit, init
from utils.parse import price_item, search_ninja_base, get_response, get_ninja_bases
from item.generator import parse_item_info
from utils.input import Keyboard, start_stash_scroll, stop_stash_scroll, get_clipboard
from gui.gui import init_gui, close_all_windows, check_timeout_gui
from utils.web import find_latest_update, get_leagues, open_trade_site, wiki_lookup
from utils.config import LEAGUE, USE_HOTKEYS

def hotkey_handler(keyboard, hotkey):
    # Without this block, the clipboard's contents seem to always be from 1 before the current
    if hotkey != "clipboard":
        keyboard.press_and_release("ctrl+c")

    time.sleep(0.1)
    text = get_clipboard()

    if hotkey == "alt+t":
        item = parse_item_info(text)
        if not item:
            return
        item.create_pseudo_mods()
        item.relax_modifiers()

        response = get_response(item)
        if response:
            open_trade_site(response["id"], LEAGUE)

    elif hotkey == "alt+w":
        item = parse_item_info(text)
        wiki_lookup(item)

    elif hotkey == "alt+c":
        search_ninja_base(text)

    else:  # alt+d, ctrl+c
        price_item(text)

def watch_keyboard(keyboard, use_hotkeys):
    if use_hotkeys:
        # Use the "f5" key to go to hideout
        keyboard.add_hotkey("<f5>", lambda: keyboard.write("\n/hideout\n"))

        # Use the alt+d key as an alternative to ctrl+c
        keyboard.add_hotkey("<alt>+d", lambda: hotkey_handler(keyboard, "alt+d"))

        # Open item in the Path of Exile Wiki
        keyboard.add_hotkey("<alt>+w", lambda: hotkey_handler(keyboard, "alt+w"))

        # Open item search in pathofexile.com/trade
        keyboard.add_hotkey("<alt>+t", lambda: hotkey_handler(keyboard, "alt+t"))

        # poe.ninja base check
        keyboard.add_hotkey("<alt>+c", lambda: hotkey_handler(keyboard, "alt+c"))

    # Clipboard
    #keyboard.add_hotkey("clipboard", lambda: hotkey_handler(keyboard, "clipboard"))
    keyboard.add_hotkey("<ctrl>+c", lambda: hotkey_handler(keyboard, "clipboard"))

    # Fetch the item's approximate price
    logging.info("[*] Watching clipboard (Ctrl+C to stop)...")
    keyboard.start()

if __name__ == "__main__":
    loglevel = logging.INFO
    if len(sys.argv) > 1 and sys.argv[1] in ("-d", "--debug"):
        loglevel = logging.DEBUG
    logging.basicConfig(format="%(message)s", level=loglevel)

    find_latest_update()

    init(autoreset=True)  # Colorama
    # Get some basic setup stuff
    valid_leagues = get_leagues()


    # Inform user of choices
    logging.info(f"If you wish to change the selected league you may do so in settings.cfg.")
    logging.info(f"Valid league values are {Fore.MAGENTA}{', '.join(valid_leagues)}{Fore.RESET}.")

    if LEAGUE not in valid_leagues:
        logging.info(f"Unable to locate {Fore.MAGENTA}{LEAGUE}{Fore.RESET}, please check settings.cfg.")
        logging.info(f"[!] Exiting, no valid league.")
    else:
        NINJA_BASES = get_ninja_bases(LEAGUE)
        logging.info(f"[*] Loaded {len(NINJA_BASES)} bases and their prices.")
        logging.info(f"All values will be from the {Fore.MAGENTA}{LEAGUE}{Fore.RESET} league")
        keyboard = Keyboard()
        watch_keyboard(keyboard, USE_HOTKEYS)

        start_stash_scroll()

        init_gui()

        try:
            while True:
                keyboard.poll()
                check_timeout_gui()
        except KeyboardInterrupt:
            pass
        
        stop_stash_scroll()
        close_all_windows()
        logging.info(f"[!] Exiting, user requested termination.")

    # Apparently things go bad if we don't call this, so here it is!
    deinit()  # Colorama