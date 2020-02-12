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
    open_trade_site,
    open_exchange_site
)

from gui.windows import baseResults, notEnoughInformation, priceInformation, information
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

    if isinstance(item, Currency):
        response = exchange_currency(json, LEAGUE)
    else:
        response = query_item(json, LEAGUE)

    return response

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

        for i in range(len(prices)):
            if prices[i] in merged:
                merged[prices[i]].append(times[i].replace(tzinfo=timezone.utc))
            else:
                merged[prices[i]] = [times[i].replace(tzinfo=timezone.utc)]

        for key, value in merged.items():
            combined = 0
            count = 0
            for t in value:
                combined += t.timestamp()
                count += 1
            combined = combined / count
            merged[key] = [count, datetime.fromtimestamp(combined, tz=timezone.utc)]

        return merged, len(prices)
    return None, 0


def price_item(text):
    try:
        item = parse_item_info(text)
        if not item:
            return
        item.create_pseudo_mods()
        item.relax_modifiers()
        item.print()

        response = get_response(item)
        if not response:
            return
    
        if len(response["result"]) < MIN_RESULTS:
            print(f"[!] Limited Results, Removing some item stats")
            if config.USE_GUI:
                information.add_info("[!] Limited Results, Removing some item stats")
                information.create_at_cursor()
            item.remove_bad_mods()
            response = get_response(item)
            if not response:
                return

        offline = False
        if len(response["result"]) <= 0:
            print(f"[!] No results, Checking offline sellers")
            if config.USE_GUI:
                information.add_info("[!] No results, Checking offline sellers")
                information.create_at_cursor()
            item.set_offline()
            offline = True
            response = get_response(item)
            if not response:
                return

        trade_info = None
        if len(response["result"]) > 0:
            fetched = fetch(response, isinstance(item, Currency))
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
                priceInformation.add_price_information(data, offline)
                priceInformation.create_at_cursor()

        else:
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
            baseResults.add_base_result(base, influence, ilvl, price, currency)
            baseResults.create_at_cursor()


