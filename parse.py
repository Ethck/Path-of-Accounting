import logging
import sys
import re
import time
import traceback
from datetime import datetime, timezone
from itertools import chain
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from colorama import Fore, deinit, init

# Local imports
from enums.item_modifier_type import ItemModifierType
from models.item_modifier import ItemModifier
from utils import config
from utils.config import LEAGUE, MIN_RESULTS, PROJECT_URL, USE_HOTKEYS
from utils.currency import (
    CATALYSTS,
    CURRENCY,
    DIV_CARDS,
    ESSENCES,
    FOSSILS,
    FRAGMENTS_AND_SETS,
    INCUBATORS,
    OILS,
    RESONATORS,
    SCARABS,
    VIALS,
)
from utils.exceptions import InvalidAPIResponseException, NotFoundException
from utils.input import Keyboard, get_clipboard, start_stash_scroll, stop_stash_scroll
from utils.trade import (
    exchange_currency,
    fetch,
    find_latest_update,
    get_item_modifiers,
    get_item_modifiers_by_text,
    get_item_modifiers_by_id,
    get_leagues,
    get_ninja_bases,
    query_item,
)
from utils.web import open_trade_site, wiki_lookup, open_exchange_site
from utils.item import (
    parse_item_info,
    InvalidItemError,
)
from models.item import (
    Exchangeable,
    Wearable,
)
from utils.mods import (
    create_pseudo_mods,
    relax_modifiers,
)

from gui.gui import init_gui, close_all_windows, check_timeout_gui
from gui.windows import baseResults, notEnoughInformation, priceInformation, BaseResults


def result_prices_are_none(j: Dict) -> bool:
    """
    Determine if all items in result are unpriced or not.

    Returns BOOLEAN
    """
    return all(x["listing"]["price"] == None for x in j)


def get_average_times(priceList):
    avg_times = []
    for tdList in priceList:
        avg_time = []
        days = 0
        seconds = 0
        num = 0
        for td in tdList:
            days += td.days
            seconds += td.seconds
            num += 1

        avg_time = [int(round(float(days) / float(num), 2)), int(round((float(seconds) / float(num)), 2))]
        avg_times.append(avg_time)

    return avg_times


def price_item(text):
    """
    Taking the text from the clipboard, parse the item, then price the item.
    Reads the results from pricing (from fetch) and lists the prices given
    for these similar items. Also calls the simple GUI if gui is enabled.
    No return.
    """
    try:
        item = parse_item_info(text)
        item = item.deduce_specific_object()
        item.sanitize_modifiers()

        json = item.get_json()
        print(json)
        # pseudo what we can
        if isinstance(item, Wearable):
            json = create_pseudo_mods(json)
            logging.debug("json query: %s" % str(json))

            json = relax_modifiers(json)
            logging.debug("relaxed query: %s" % str(json))


        if isinstance(item, Exchangeable):
            response = exchange_currency(json, LEAGUE)
            open_exchange_site(response["id"], LEAGUE)
        else:
            response = query_item(json, LEAGUE)
            open_trade_site(response["id"], LEAGUE)

        logging.debug("json response: %s" % str(response))


        if len(response["result"]) == 0:
            raise NotFoundException

        fetched = fetch(response, isinstance(item, Exchangeable))
        logging.debug("Fetched: %s" % str(fetched))

        trade_info = fetched
        logging.debug("Found %d items" % len(trade_info))

        # If results found
        if trade_info:
            prev_account_name = ""
            # Modify data to usable status.
            prices = []
            for trade in trade_info:  # Stop price fixers
                if trade["listing"]["account"]["name"] != prev_account_name:
                    prices.append(trade["listing"]["price"])

                prev_account_name = trade["listing"]["account"]["name"]

            prices = ["%(amount)s%(currency)s" % x for x in prices if x != None]

            prices = {x: prices.count(x) for x in prices}
            print_string = ""
            total_count = 0

            # Make pretty strings.
            for price_dict in prices:
                pretty_price = " ".join(re.split(r"([0-9.]+)", price_dict)[1:])
                print_string += f"{prices[price_dict]} x " + Fore.YELLOW + f"{pretty_price}" + Fore.RESET + ", "
                total_count += prices[price_dict]

            # Print the pretty string, ignoring trailing comma
            logging.info(f"[$] Price: {print_string[:-2]}\n\n")
            if len(trade_info) < MIN_RESULTS:
                logging.info("[!] Not enough data to confidently price this item.")
            if config.USE_GUI:
                priceList = prices
                # Get difference between current time and posted time in timedelta format
                times = [
                    (
                        datetime.now(timezone.utc)
                        - datetime.replace(
                            datetime.strptime(time["listing"]["indexed"], "%Y-%m-%dT%H:%M:%SZ"),
                            tzinfo=timezone.utc,
                        )
                    )
                    for time in trade_info
                ]
                # Assign times to proper price values (for getting average later.)
                priceTimes = []
                total = 0
                for price in priceList:
                    num = priceList[price]
                    priceTimes.append(times[total : num + total])
                    total += num

                avg_times = get_average_times(priceTimes)

                price = [re.findall(r"([0-9.]+)", tprice)[0] for tprice in prices.keys()]

                currency = None  # TODO If a single result shows a higher tier, it currently presents only that value in the GUI.
                if "mir" in print_string:
                    currency = "mirror"
                elif "exa" in print_string:
                    currency = "exalt"
                elif "chaos" in print_string:
                    currency = "chaos"
                elif "alch" in print_string:
                    currency = "alchemy"

                price.sort()

                # Fastest method for calculating average as seen here:
                # https://stackoverflow.com/questions/21230023/average-of-a-list-of-numbers-stored-as-strings-in-a-python-list
                # TODO average between multiple currencies...
                L = [float(n) for n in price if n]
                average = str(round(sum(L) / float(len(L)) if L else "-", 2))

                price = [
                    round(float(price[0]), 2),
                    average,
                    round(float(price[-1]), 2),
                ]

                priceInformation.add_price_information(price, prices, avg_times, len(trade_info) < MIN_RESULTS)
                priceInformation.create_at_cursor()

        else:
            logging.info(f"[$] Price: {Fore.YELLOW}None{Fore.RESET} \n\n")
            logging.info("[!] Not enough data to confidently price this item.")
            if config.USE_GUI:
                notEnoughInformation.create_at_cursor()

    except InvalidItemError:
        # This exception is only raised when we find that the text
        # being parsed is not actually a valid PoE item.
        pass

    except NotFoundException as e:
        logging.info("[!] No results!")
        if config.USE_GUI:
            notEnoughInformation.create_at_cursor()

    except InvalidAPIResponseException as e:
        logging.info(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW =================={Fore.RESET}")
        logging.info(
            f"[!] Failed to parse response from POE API. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        logging.info(f"{Fore.GREEN}================== START ISSUE DATA =================={Fore.RESET}")
        logging.info(f"{Fore.GREEN}Title:{Fore.RESET}")
        logging.info("Failed to query item from trade API.")
        logging.info(f"{Fore.GREEN}Body:{Fore.RESET}")
        logging.info("Macro failed to lookup item from POE trade API. Here is the item in question.")
        logging.info("====== ITEM DATA=====")
        logging.info(f"{text}")
        logging.info(f"{Fore.GREEN}================== END ISSUE DATA =================={Fore.RESET}")
        logging.info(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE =================={Fore.RESET}")

    except Exception as e:
        exception = traceback.format_exc()
        logging.info(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW =================={Fore.RESET}")
        logging.info(
            f"[!] Something went horribly wrong. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        logging.info(f"{Fore.GREEN}================== START ISSUE DATA =================={Fore.RESET}")
        logging.info(f"{Fore.GREEN}Title:{Fore.RESET}")
        logging.info("Failed to query item from trade API.")
        logging.info(f"{Fore.GREEN}Body:{Fore.RESET}")
        logging.info("Here is the item in question.")
        logging.info("====== ITEM DATA=====")
        logging.info(f"{text}")
        logging.info("====== TRACEBACK =====")
        logging.info(exception)
        logging.info(f"{Fore.GREEN}================== END ISSUE DATA =================={Fore.RESET}")
        logging.info(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE =================={Fore.RESET}")


def search_ninja_base(text):
    NINJA_BASES = get_ninja_bases(LEAGUE)
    real_item = parse_item_info(text)

    influences = real_item.influence
    ilvl = real_item.ilevel if real_item.ilevel >= 84 else 84
    base = real_item.base
    # base = info["itype"] if info["itype"] != None else info["base"]

    logging.info(f"[*] Searching for base {base}. Item Level: {ilvl}, Influences: {influences}")
    result = None
    try:
        result = next(
            item
            for item in NINJA_BASES
            if (
                item["base"] == base
                and (
                    (not influences and item["influence"] == None)
                    or (
                        bool(influences)
                        and item["influence"] != None
                        and influences[0] == item["influence"].lower()
                    )
                )
                and ilvl == item["ilvl"]
            )
        )
    except StopIteration:
        logging.error("[!] Could not find the requested item.")
        if config.USE_GUI:
            notEnoughInformation.create_at_cursor()

    if result != None:
        price = result["exalt"] if result["exalt"] >= 1 else result["chaos"]
        currency = "ex" if result["exalt"] >= 1 else "chaos"
        logging.info(f"[$] Price: {price} {currency}")
        if config.USE_GUI:
            influence = influences[0] if bool(influences) else None
            baseGUI = BaseResults()
            baseGUI.add_base_result(base, influence, ilvl, price, currency)
            baseGUI.create_at_cursor()



def hotkey_handler(keyboard, hotkey):
    # Without this block, the clipboard's contents seem to always be from 1 before the current
    if hotkey != "clipboard":
        keyboard.press_and_release("ctrl+c")
        time.sleep(0.1)
    text = get_clipboard()

    if hotkey == "alt+t":
        item = parse_item_info(text)
        item = item.deduce_specific_object()
        item.sanitize_modifiers()
        json = item.get_json()

        # if not isinstance(item, Exchangeable):
        response = requests.post(item.query_url(LEAGUE), json=json)
        response_json = response.json()
        logging.debug("response json: %s" % str(response_json))
        open_trade_site(response_json["id"], LEAGUE)

    elif hotkey == "alt+w":
        item = parse_item_info(text)
        item = item.deduce_specific_object()
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
        keyboard.add_hotkey("clipboard", lambda: hotkey_handler(keyboard, "clipboard"))

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
        """
        data = {
            "exchange": {
                "status": {
                    "option": "online"
                },
                "have": ["chaos"],
                "want": ["splinter-esh"]
            }
        }
        response = exchange_currency(data, LEAGUE)
        open_exchange_site(response["id"], LEAGUE)
        """

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
        
