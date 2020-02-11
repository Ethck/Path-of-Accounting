import logging
import traceback
from datetime import datetime, timezone
from typing import Dict

from colorama import Fore

# Local imports
from utils import config
from utils.config import LEAGUE, MIN_RESULTS, PROJECT_URL
from utils.exceptions import InvalidAPIResponseException
from utils.web import (
    exchange_currency,
    fetch,
    get_ninja_bases,
    query_item,
)
from utils.item import (
    #parse_item_info,
    InvalidItemError,
)
from models.item import (
    Exchangeable,
    Wearable,
)
from utils.mods import (
    create_pseudo_mods,
    relax_modifiers,
    remove_bad_mods,
)

from gui.windows import baseResults, notEnoughInformation, priceInformation
from item.generator import *

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


def get_response(item):
    json = item.get_json()

    if isinstance(item, Wearable):
        json = create_pseudo_mods(json)
        json = relax_modifiers(json)

    if isinstance(item, Exchangeable):
        response = exchange_currency(json, LEAGUE)
    else:
        response = query_item(json, LEAGUE)

    return response

def make_item(text):
    item = None
    try:
        item = parse_item_info(text)
        #item = item.deduce_specific_object()
        #item.sanitize_modifiers()
    except InvalidItemError:
        # This exception is only raised when we find that the text
        # being parsed is not actually a valid PoE item.
        pass
    return item

def get_trade_data(trade_info):
    """
    Returns a directory with price as key and value as list[time,count] or None if there where no items
    Returns dict{price: [count , time]}
    """
    def pretty_currency(curr):
        currency = curr
        # TODO: Add more currency types
        if "mir" in currency:
            currency = "Mirror"
        elif "exa" in currency:
            currency = "Exalt"
        elif "chaos" in currency:
            currency = "Chaos"
        elif "alch" in currency:
            currency = "Alch"
        elif "alt" in currency:
            currency = "Alt"
        elif "fuse" in currency:
            currency = "Fuse"
        return currency


    if trade_info and not result_prices_are_none(trade_info):
        prev_account_name = ""
        # Modify data to usable status.
        times = []
        prices = []
        for trade in trade_info:  # Stop price fixers
            if trade["listing"]["price"]:
                if trade["listing"]["account"]["name"] != prev_account_name:
                    price = str(trade["listing"]["price"]["amount"]) + " " + pretty_currency(trade["listing"]["price"]["currency"])
                    prices.append(price)
                    times.append(datetime.strptime(trade["listing"]["indexed"],"%Y-%m-%dT%H:%M:%SZ"))
                prev_account_name = trade["listing"]["account"]["name"]

        merged = {}
        count = 1
        for i in range(len(prices)):
            if i+1 < len(prices):
                if prices[i+1] == prices[i]:
                    count += 1
                    continue
                else:
                    start = i-count+1
                    s = 0
                    for y in range(start, i+1 ):
                        s += times[y].replace(tzinfo=timezone.utc).timestamp()
                    s = s / count
                    time = datetime.fromtimestamp(s, tz=timezone.utc)
                    merged[prices[i]] = [count,  time]
                    count = 1
            elif prices[i] != prices[i-1]:
                merged[prices[i]] = [1, times[i].replace(tzinfo=timezone.utc)]

            if count >= len(prices): # If theyre all the same price
                start = i-count+1
                s = 0
                for y in range(len(prices)):
                    s += times[y].replace(tzinfo=timezone.utc).timestamp()
                s = s / count
                time = datetime.fromtimestamp(s, tz=timezone.utc)
                merged[prices[0]] = [count,  time]

        return merged, len(prices)
    return None, 0


def print_item(item):
    print(f"{item.name}")
    print(f"{item.base}")
    print(f"{item.category}")
    print(f"{item.modifiers}")

def price_item(text):
    """
    Taking the text from the clipboard, parse the item, then price the item.
    Reads the results from pricing (from fetch) and lists the prices given
    for these similar items. Also calls the simple GUI if gui is enabled.
    No return.
    """
    
    try:
        item = make_item(text)
        if not item:
            return
        """
        print_item(item)
        response = get_response(item)
        if not response:
            return

        if len(response["result"]) < MIN_RESULTS:
            item = remove_bad_mods(item)
            response = get_response(item)
            if not response:
                return

        trade_info = None
        if len(response["result"]) > 0:
            fetched = fetch(response, isinstance(item, Exchangeable))
            trade_info = fetched

        # dict{price: [count , time]}
        data, length = get_trade_data(trade_info)

        if data:
            print_text = "[$] Prices: "
            for price, values in data.items():
                print_text += f"{Fore.YELLOW}{price}{Fore.RESET} x {values[0]}, "
            
            print_text = print_text[:-2]
            print(print_text)
            if length < MIN_RESULTS:
                logging.info("[!] Not enough data to confidently price this item.")
            if config.USE_GUI:
                priceInformation.add_price_information(data)
                priceInformation.create_at_cursor()

        else:
            logging.info("[!] No results!")
            if config.USE_GUI:
                notEnoughInformation.create_at_cursor()
        """


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
            baseResults.add_base_result(base, influence, ilvl, price, currency)
            baseResults.create_at_cursor()


