import logging
import sys
import time

from colorama import Fore, deinit, init

from gui.gui import check_timeout_gui, close_all_windows, init_gui
from gui.windows import information
from item.generator import Currency, Weapon, parse_item_info
from utils import config
from utils.config import LEAGUE, USE_HOTKEYS
from utils.input import (
    Keyboard,
    get_clipboard,
    start_stash_scroll,
    stop_stash_scroll,
)
from utils.parse import (
    get_ninja_bases,
    get_response,
    price_item,
    search_ninja_base,
)
from utils.web import (
    find_latest_update,
    get_leagues,
    open_exchange_site,
    open_trade_site,
    wiki_lookup,
)


def hotkey_handler(keyboard, hotkey):
    """Based on the given hotkey, setup the logic for the triggered key

    :param keyboard: Keyboard object to determine status of keys
    :param hotkey: The triggered hotkey
    """
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
            if isinstance(item, Currency):
                open_exchange_site(response["id"], LEAGUE)
            else:
                open_trade_site(response["id"], LEAGUE)

    elif hotkey == "alt+w":
        item = parse_item_info(text)
        wiki_lookup(item)

    elif hotkey == "alt+c":
        search_ninja_base(text)

    elif hotkey == "alt+f":
        item = parse_item_info(text)
        if isinstance(item, Weapon):
            stats = item.get_weapon_stats()
            logging.info(stats)
            if config.USE_GUI:
                information.add_info(stats)
                information.create_at_cursor()

    else:  # alt+d, ctrl+c
        price_item(text)


def watch_keyboard(keyboard, use_hotkeys):
    """Add all of the hotkeys to watch over

    :param keyboard: Keyboard object to determine key status
    :param use_hotkeys: config to determine whether hotkeys are established
    """
    if use_hotkeys:
        # Use the "f5" key to go to hideout
        keyboard.add_hotkey("<f5>", lambda: keyboard.write("\n/hideout\n"))

        # Use the alt+d key as an alternative to ctrl+c
        keyboard.add_hotkey(
            "<alt>+d", lambda: hotkey_handler(keyboard, "alt+d")
        )

        # Open item in the Path of Exile Wiki
        keyboard.add_hotkey(
            "<alt>+w", lambda: hotkey_handler(keyboard, "alt+w")
        )

        # Open item search in pathofexile.com/trade
        keyboard.add_hotkey(
            "<alt>+t", lambda: hotkey_handler(keyboard, "alt+t")
        )

        # poe.ninja base check
        keyboard.add_hotkey(
            "<alt>+c", lambda: hotkey_handler(keyboard, "alt+c")
        )

        keyboard.add_hotkey(
            "<alt>+f", lambda: hotkey_handler(keyboard, "alt+f")
        )

    # Clipboard
    # keyboard.add_hotkey("clipboard", lambda: hotkey_handler(keyboard, "clipboard"))
    keyboard.add_hotkey(
        "<ctrl>+c", lambda: hotkey_handler(keyboard, "clipboard")
    )

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
    logging.info(
        f"If you wish to change the selected league you may do so in settings.cfg."
    )
    logging.info(
        f"Valid league values are {Fore.MAGENTA}{', '.join(valid_leagues)}{Fore.RESET}."
    )

    if LEAGUE not in valid_leagues:
        logging.info(
            f"Unable to locate {Fore.MAGENTA}{LEAGUE}{Fore.RESET}, please check settings.cfg."
        )
        logging.info(f"[!] Exiting, no valid league.")
    else:
        NINJA_BASES = get_ninja_bases(LEAGUE)
        logging.info(f"[*] Loaded {len(NINJA_BASES)} bases and their prices.")
        logging.info(
            f"All values will be from the {Fore.MAGENTA}{LEAGUE}{Fore.RESET} league"
        )
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
