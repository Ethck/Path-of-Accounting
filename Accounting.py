import logging
import sys
import time

from colorama import Fore, deinit, init

from gui.gui import check_timeout_gui, close_all_windows, init_gui
from gui.windows import gearInformation, information
from item.generator import Currency, Item, parse_item_info
from utils import config
from utils.common import get_response
from utils.config import (
    ADV_SEARCH,
    BASE_SEARCH,
    BASIC_SEARCH,
    HIDEOUT,
    OPEN_TRADE,
    OPEN_WIKI,
    SHOW_INFO,
    EXIT,
)
from utils.input import (
    Keyboard,
    get_clipboard,
    set_clipboard,
    start_stash_scroll,
    stop_stash_scroll,
)
from utils.parse import (
    adv_search,
    basic_search,
    get_ninja_bases,
    search_ninja_base,
)
from utils.web import (
    find_latest_update,
    get_leagues,
    open_exchange_site,
    open_trade_site,
    wiki_lookup,
    get_item_modifiers,
)


def hotkey_handler(keyboard, hotkey):
    """Based on the given hotkey, setup the logic for the triggered key

    :param keyboard: Keyboard object to determine status of keys
    :param hotkey: The triggered hotkey
    """

    old_clipboard = get_clipboard()

    keyboard.press_and_release("ctrl+c")
    time.sleep(0.1)
    text = get_clipboard()

    set_clipboard(old_clipboard)

    close_all_windows()

    if hotkey == "Trade":
        item = parse_item_info(text)
        if not item:
            return
        item.create_pseudo_mods()
        item.relax_modifiers()

        response = get_response(item)
        if response:
            if isinstance(item, Currency):
                open_exchange_site(response["id"], config.LEAGUE)
            else:
                open_trade_site(response["id"], config.LEAGUE)

    elif hotkey == "Wiki":
        item = parse_item_info(text)
        wiki_lookup(item)

    elif hotkey == "Base":
        search_ninja_base(text)

    elif hotkey == "Adv":
        adv_search(text)

    elif hotkey == "Info":
        item = parse_item_info(text)
        if isinstance(item, Item):
            stats = item.get_item_stats()
            if stats != "":
                logging.info(stats)
            else:
                logging.info("[!] No extra info yet!")
            gearInformation.add_info(item)
            gearInformation.create_at_cursor()

    elif hotkey == "Basic":  # alt+d, ctrl+c
        basic_search(text)


def watch_keyboard(keyboard):
    """Add all of the hotkeys to watch over

    :param keyboard: Keyboard object to determine key status
    :param use_hotkeys: config to determine whether hotkeys are established
    """

    # Use the "f5" key to go to hideout
    keyboard.add_hotkey(HIDEOUT, lambda: keyboard.write("\n/hideout\n"))

    # Basic search
    keyboard.add_hotkey(
        BASIC_SEARCH, lambda: hotkey_handler(keyboard, "Basic")
    )

    # Open item in the Path of Exile Wiki
    keyboard.add_hotkey(
        OPEN_WIKI, lambda: hotkey_handler(keyboard, "Wiki")
    )

    # Open item search in pathofexile.com/trade
    keyboard.add_hotkey(
        OPEN_TRADE, lambda: hotkey_handler(keyboard, "Trade")
    )

    # poe.ninja base check
    keyboard.add_hotkey(
        BASE_SEARCH, lambda: hotkey_handler(keyboard, "Base")
    )

    # Show item info
    keyboard.add_hotkey(
        SHOW_INFO, lambda: hotkey_handler(keyboard, "Info")
    )

    # Adv Search
    keyboard.add_hotkey(
        ADV_SEARCH, lambda: hotkey_handler(keyboard, "Adv")
    )

    # Exit
    keyboard.add_hotkey(
        EXIT, lambda: hotkey_handler(keyboard, "Exit")
    )


def check_league():
    valid_leagues = get_leagues()

    if valid_leagues:
        # Inform user of choices
        logging.info(
            f"If you wish to change the selected league you may do so in settings.cfg."
        )
        logging.info(
            f"Valid league values are {Fore.MAGENTA}{', '.join(valid_leagues)}{Fore.RESET}."
        )
        if config.LEAGUE == "League" or config.LEAGUE == "League-Hardcore":
            for league in valid_leagues:
                if league != "Standard" and league != "Hardcore":
                    if config.LEAGUE == "League-Hardcore":
                        if "Hardcore" in league:
                            config.LEAGUE = league
                    if config.LEAGUE == "League":
                        if "Hardcore" not in league:
                            config.LEAGUE = league

        if config.LEAGUE not in valid_leagues:
            logging.info(
                f"Unable to locate {Fore.MAGENTA}{config.LEAGUE}{Fore.RESET}, please check settings.cfg."
            )
            logging.info(f"[!] Exiting, no valid league.")
            return False
        else:
            logging.info(
                f"All values will be from the {Fore.MAGENTA}{config.LEAGUE}{Fore.RESET} league"
            )
        return True
    logging.info("[!] Pathofexile.com seems to be down!")
    logging.info("[!] Please restart the program when website is back up")
    return True


if __name__ == "__main__":
    loglevel = logging.INFO
    if len(sys.argv) > 1 and sys.argv[1] in ("-d", "--debug"):
        loglevel = logging.DEBUG
    logging.basicConfig(format="%(message)s", level=loglevel)

    find_latest_update()

    init(autoreset=True)  # Colorama

    # Get some basic setup stuff
    valid_league = check_league()
    if valid_league:
        NINJA_BASES = get_ninja_bases(config.LEAGUE)
        if NINJA_BASES:
            logging.info(
                f"[*] Loaded {len(NINJA_BASES)} bases and their prices."
            )

        get_item_modifiers()

        keyboard = Keyboard()
        watch_keyboard(keyboard)

        start_stash_scroll()

        init_gui()

        logging.info(
            f"[{(BASIC_SEARCH)}]:".rjust(15) + " For simple search.\n" +
            f"[{(ADV_SEARCH)}]:".rjust(15) + " For advanced search.\n" +
            f"[{(BASE_SEARCH)}]:".rjust(15) + " For item base price\n" +
            f"[{(OPEN_WIKI)}]:".rjust(15) + " To open the item on wiki.\n" +
            f"[{(OPEN_TRADE)}]:".rjust(15) + " To open the item on trade site.\n" +
            f"[{(SHOW_INFO)}]:".rjust(15) + " To see item stats (Does not work with all items).\n" +
            f"[{(HIDEOUT)}]:".rjust(15) + " To go to hideout.\n" +
            "[*] Hotkeys can be changed in settings.cfg\n" +
            f"[*] Watching hotkeys ({EXIT} to stop) ..."
        )

        while True:
            try:
                check_timeout_gui()
                time.sleep(0.2)
                _exit = keyboard.poll()
                if _exit:
                    break
            except KeyboardInterrupt:
                pass

        stop_stash_scroll()
        close_all_windows()
        logging.info(f"[!] Exiting, user requested termination.")

    # Apparently things go bad if we don't call this, so here it is!
    deinit()  # Colorama
