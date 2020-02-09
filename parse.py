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
from utils.web import open_trade_site, wiki_lookup
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

def search_item(j, league):
    """
    Based on j (JSON) and given league,
    search for similar items (with exact preferred).

    returns results
    """
    # Now search for similar items, if none found remove a stat and try again. TODO: Refactor and include more vars.
    if "stats" in j["query"]:
        num_stats_ignored = 0
        total_num_stats = len(j["query"]["stats"][0]["filters"])
        while len(j["query"]["stats"][0]["filters"]) > 0:

            # If we ignore more than half of the stats, it's not accurate
            if num_stats_ignored > (int(total_num_stats * 0.6)):
                logging.info(
                    f"[!] Take any values after this with a grain of salt. You should probably do a"
                    + Fore.RED
                    + " MANUAL search"
                    + Fore.RESET
                )

            # Make the actual request.
            res = query_item(j, league)

            # No results found. Trim the mod list until we find results.
            if "result" in res:
                if (len(res["result"])) == 0:

                    # Choose a non-priority mod
                    i = choose_bad_mod(j)

                    # Tell the user which mod we are deleting
                    logging.info(
                        "[-] Removing the"
                        + Fore.CYAN
                        + f" {stat_translate(i['id']).text}"
                        + Fore.RESET
                        + " mod from the list due to "
                        + Fore.RED
                        + "no results found."
                        + Fore.RESET
                    )

                    # Remove bad mod.
                    j["query"]["stats"][0]["filters"].remove(i)
                    num_stats_ignored += 1
                else:  # Found a result!
                    results = fetch(res)
                    logging.debug("Found results!")

                    if result_prices_are_none(results):
                        logging.debug("All resulting prices are none.")
                        # Choose a non-priority mod
                        i = choose_bad_mod(j)

                        # Tell the user which mod we are deleting
                        logging.info(
                            "[-] Removing the "
                            + Fore.CYAN
                            + f"{stat_translate(i['id']).text}"
                            + Fore.RESET
                            + " mod from the list due to "
                            + Fore.RED
                            + "no results found."
                            + Fore.RESET
                        )

                        # Remove bad mod.
                        j["query"]["stats"][0]["filters"].remove(i)
                        num_stats_ignored += 1
                    else:
                        return results
            else:
                raise InvalidAPIResponseException

        # If we have legitimately run out of stats...
        # Then this item can not be found.
        # TODO: Figure out why it can't find anything...
        raise NotFoundException

    else:  # Any time we ignore stats.
        res = query_item(j, league)
        results = fetch(res)
        return results

def choose_bad_mod(j):
    """
    Chooses a non-priority mod to delete.

    Returns modified JSON that lacks the chosen bad mod
    """
    # Good mod list
    priority = [
        "pseudo.pseudo_total_elemental_resistance",
        "pseudo.pseudo_total_chaos_resistance",
        "pseudo.pseudo_total_life",
    ]

    # Choose a non-priority mod to delete
    for i in j["query"]["stats"][0]["filters"]:
        if i["id"] not in priority:
            break

    return i


def result_prices_are_none(j: Dict) -> bool:
    """
    Determine if all items in result are unpriced or not.

    Returns BOOLEAN
    """
    return all(x["listing"]["price"] == None for x in j)


def query_exchange(qcur):
    """
    Build JSON for fetch request of wanted currency exchange.
    Fetch with the built JSON
    Return results of similar items.
    """

    logging.info(f"[*] All values will be reported as their chaos, exalt, or mirror equivalent.")
    IG_CURRENCY = [
        CURRENCY,
        OILS,
        CATALYSTS,
        FRAGMENTS_AND_SETS,
        INCUBATORS,
        SCARABS,
        RESONATORS,
        FOSSILS,
        VIALS,
        ESSENCES,
        DIV_CARDS,
    ]

    selection = "Exalt"
    if any(d.get(qcur, None) for d in IG_CURRENCY):
        for curr_type in IG_CURRENCY:
            if qcur in curr_type:
                selection = curr_type[qcur]

    # Default JSON
    for haveCurrency in ["chaos", "exa", "mir"]:
        def_json = {"exchange": {"have": [haveCurrency], "want": [selection], "status": {"option": "online"},}}

        res = exchange_currency(def_json, LEAGUE)
        logging.debug(def_json)

        if len(res["result"]) == 0:
            continue
        else:
            break

    results = fetch(res, exchange=True)
    return results


def affix_equals(text, affix) -> Optional[int]:
    """
    Clean up the affix to match the given text so we can find the correct id to search with.

    returns tuple (BOOLEAN, value)
    """
    value = 0
    match = re.findall(r"\d+", affix)

    if len(match) > 0:
        value = match[0]

    # Replace numbers with # and remove + signs to have simple searches
    query = re.sub(r"\d+", "#", affix)
    query = re.sub(r"\+", "", query)

    # Remove (implicit) from the search
    if query.endswith(r" (implicit)"):
        text = text + r" (implicit)"

    # Remove (crafted) from the search
    if query.endswith(r" (crafted)"):
        text = text + r" (crafted)"

    # Remove (pseudo) from the search
    if query.endswith(r" (pseudo)"):
        text = text + r" (pseudo)"
        query = r"+" + query

    # Remove (Local) from the search
    if text.endswith("(Local)"):
        query = query + r" (Local)"

    # At this point all numbers and other special characters have been minimized
    # So if the mod is the same, this catches it.
    if text == query:
        logging.info(
            "[+] Found mod " + Fore.GREEN + f"{text[0:]}: {value}" + Fore.RESET
        )  # TODO: support "# to # damage to attacks" type mods and other similar
        return value

    return None


def find_affix_match(affix: str) -> Tuple[str, int]:
    """
    Search for the proper id to return the correct results.

    returns tuple (id of the affix requested, value)
    """
    # Get all modifiers of a certian type
    def get_mods_by_type(type: ItemModifierType) -> Iterable[ItemModifier]:
        return (x for x in ITEM_MODIFIERS if x.type == type)

    logging.debug("AFFIX:", affix)

    if re.search(r"\((pseudo|implicit|crafted)\)", affix):
        # Search for these special modifiers first
        # Order does not matter
        search_order = [
            ItemModifierType.PSEUDO,
            ItemModifierType.IMPLICIT,
            ItemModifierType.CRAFTED,
        ]

        # Unpack all special mods into search_mods
        search_mods = chain(*(get_mods_by_type(x) for x in search_order))
        # Search every special mod for a match
        for mod in search_mods:
            value = affix_equals(mod.text, affix)
            if value is not None:
                return (mod.id, value)

    else:
        # Check all explicit for a match
        for explicit in (x for x in ITEM_MODIFIERS if x.type is ItemModifierType.EXPLICIT):
            value = affix_equals(explicit.text, affix)
            if value is not None:
                return (explicit.id, value)

        # Check all enchants for a match if nothing else matched.
        for enchant in (x for x in ITEM_MODIFIERS if x.type is ItemModifierType.ENCHANT):
            value = affix_equals(enchant.text, affix)
            if value is not None:
                return (enchant.id, value)

    raise NotImplementedError("Unable to find matching affix.")


def stat_translate(jaffix: str) -> ItemModifier:
    """
    Translate id to the equivalent stat.
    Returns the ItemModifier equivalent to requested id
    """
    return get_item_modifiers_by_id(jaffix)


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

        # pseudo what we can
        if isinstance(item, Wearable):
            json = create_pseudo_mods(json)
            logging.debug("json query: %s" % str(json))

            json = relax_modifiers(json)
            logging.debug("relaxed query: %s" % str(json))

        query_url = item.query_url(LEAGUE)
        response = requests.post(query_url, json=json)
        logging.debug("json response: %s" % str(response.json()))

        response_json = response.json()
        if len(response_json["result"]) == 0:
            raise NotFoundException

        fetched = fetch(response_json, isinstance(item, Exchangeable))
        logging.debug("Fetched: %s" % str(fetched))

        trade_info = fetched
        logging.debug("Found %d items" % len(trade_info))
        '''
        if info:
            # Uniques, only search by corrupted status, links, and name.

            if info["itype"] == "Currency":
                logging.info(f'[-] Found currency {info["name"]} in clipboard')
                trade_info = query_exchange(info["name"])

            elif info["itype"] == "Divination Card":
                logging.info(f'[-] Found Divination Card {info["name"]}')
                trade_info = query_exchange(info["name"])

            else:

                # Do intensive search.
                if info["itype"] != info["name"] and info["itype"] != None:
                    logging.info(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {info['itype']}", flush=True)
                else:
                    extra_strings = ""
                    if info["rarity"] == "Gem":
                        extra_strings += f"Level: {info['gem_level']}+, "

                    if "corrupted" in info:
                        if info["corrupted"]:
                            extra_strings += "Corrupted: True, "

                    if info["quality"] != 0:
                        extra_strings += f"Quality: {info['quality']}+"

                    logging.info(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {extra_strings}")

                json = build_json_official(
                    **{
                        k: v
                        for k, v in info.items()
                        if k
                        in (
                            "name",
                            "itype",
                            "ilvl",
                            "links",
                            "corrupted",
                            "influenced",
                            "stats",
                            "rarity",
                            "gem_level",
                            "quality",
                            "maps",
                        )
                    },
                )
                
            if json != None:
                trade_info = search_item(json, LEAGUE)
        '''
        # If results found
        if trade_info:
            # If more than 1 result, assemble price list.
            if len(trade_info) > 1:
                # print(trade_info[0]['item']['extended']) #TODO search this for bad mods
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

                    if config.USE_GUI:
                        gui.show_price(price, list(prices), avg_times, len(trade_info) < MIN_RESULTS)
            else:
                price = trade_info[0]["listing"]["price"]
                if price != None:
                    price_val = price["amount"]
                    price_curr = price["currency"]
                    price = f"{price_val} x {price_curr}"
                    logging.info(f"[$] Price: {Fore.YELLOW}{price}{Fore.RESET} \n\n")
                    time = datetime.now(timezone.utc) - datetime.replace(
                        datetime.strptime(trade_info[0]["listing"]["indexed"], "%Y-%m-%dT%H:%M:%SZ"),
                        tzinfo=timezone.utc,
                    )
                    time = [[time.days, time.seconds]]
                    price_vals = [[str(price_val) + price_curr]]

                    logging.info("[!] Not enough data to confidently price this item.")
                    if config.USE_GUI:
                        gui.show_price(price, price_vals, time, True)
                else:
                    logging.info(f"[$] Price: {Fore.YELLOW}None{Fore.RESET} \n\n")
                    logging.info("[!] Not enough data to confidently price this item.")
                    if config.USE_GUI:
                        gui.show_not_enough_data()

        elif trade_info is not None:
            logging.info("[!] No results!")
            if config.USE_GUI:
                gui.show_not_enough_data()

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

    # Fetch the item's approximate price
    logging.info("[*] Watching clipboard (Ctrl+C to stop)...")
    keyboard.clipboard_callback = lambda _: hotkey_handler(keyboard, "clipboard")
    keyboard.start()


def search_ninja_base(text):
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
            gui.show_base_result(base, influence, ilvl, price, currency)

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
        print(f"Unable to locate {LEAGUE}, please check settings.cfg.")
        print(f"[!] Exiting, no valid league.")
    else:
        NINJA_BASES = get_ninja_bases(LEAGUE)
        print(f"[*] Loaded {len(NINJA_BASES)} bases and their prices.")
        print(f"All values will be from the {Fore.MAGENTA}{LEAGUE} league")
        keyboard = Keyboard()
        watch_keyboard(keyboard, USE_HOTKEYS)

        start_stash_scroll()
        
        if config.USE_GUI:
            init_gui()

        try:
            while True:
                keyboard.poll()
                
                if config.USE_GUI:
                    check_timeout_gui()
        except KeyboardInterrupt:
            pass
        
        stop_stash_scroll()
        print(f"[!] Exiting, user requested termination.")

        close_all_windows()
    # Apparently things go bad if we don't call this, so here it is!
    deinit()  # Colorama
        
