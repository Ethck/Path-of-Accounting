import logging
import traceback
from datetime import datetime, timezone
from typing import Dict

from colorama import Fore

from gui.windows import (
    baseResults,
    information,
    notEnoughInformation,
    priceInformation,
)
from item.generator import *
from utils import config
from utils.config import LEAGUE, MIN_RESULTS, PROJECT_URL
from utils.exceptions import InvalidAPIResponseException
from utils.web import (
    exchange_currency,
    fetch,
    get_ninja_bases,
    open_exchange_site,
    open_trade_site,
    query_item,
)


def get_response(item):
    json = item.get_json()

    if isinstance(item, Currency):
        response = exchange_currency(json, LEAGUE)
    else:
        response = query_item(json, LEAGUE)

    return response


def get_trade_data(item):
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

    trade_info = None

    response = get_response(item)
    if not response:
        return {}

    if len(response["result"]) > 0:
        trade_info = fetch(response, isinstance(item, Currency))

    if trade_info:
        prev_account_name = ""
        # Modify data to usable status.
        times = []
        prices = []
        for trade in trade_info:  # Stop price fixers
            if trade["listing"]["price"]:
                if trade["listing"]["account"]["name"] != prev_account_name:
                    price = (
                        str(trade["listing"]["price"]["amount"])
                        + " "
                        + pretty_currency(
                            trade["listing"]["price"]["currency"]
                        )
                    )
                    prices.append(price)
                    times.append(
                        datetime.strptime(
                            trade["listing"]["indexed"], "%Y-%m-%dT%H:%M:%SZ"
                        )
                    )
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
            merged[key] = [
                count,
                datetime.fromtimestamp(combined, tz=timezone.utc),
            ]

        return merged
    return {}


def price_item(text):
    try:
        item = parse_item_info(text)
        if not item:
            return
        item.create_pseudo_mods()
        item.relax_modifiers()
        item.print()

        data = get_trade_data(item)

        if len(data) < MIN_RESULTS:
            print(f"[!] Limited Results, Removing some item stats")
            if config.USE_GUI:
                information.add_info(
                    "[!] Limited Results, Removing some item stats"
                )
                information.create_at_cursor()
            item.remove_bad_mods()
            data = get_trade_data(item)

        offline = False
        if len(data) <= 0:
            print(f"[!] No results, Checking offline sellers")
            if config.USE_GUI:
                information.add_info(
                    "[!] No results, Checking offline sellers"
                )
                information.create_at_cursor()
            item.set_offline()
            offline = True
            data = get_trade_data(item)

        if data:
            print_text = "[$] Prices: "
            for price, values in data.items():
                print_text += (
                    f"{Fore.YELLOW}{price}{Fore.RESET} x {values[0]}, "
                )

            print_text = print_text[:-2]
            logging.info(print_text)
            if len(data) < MIN_RESULTS:
                logging.info(
                    "[!] Not enough data to confidently price this item."
                )
            if config.USE_GUI:
                priceInformation.add_price_information(data, offline)
                priceInformation.create_at_cursor()

        else:
            logging.info("[!] No results!")
            if config.USE_GUI:
                notEnoughInformation.create_at_cursor()

    except InvalidAPIResponseException:
        logging.info(
            f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW =================={Fore.RESET}"
        )
        logging.info(
            f"[!] Failed to parse response from POE API. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        logging.info(
            f"{Fore.GREEN}================== START ISSUE DATA =================={Fore.RESET}"
        )
        logging.info(f"{Fore.GREEN}Title:{Fore.RESET}")
        logging.info("Failed to query item from trade API.")
        logging.info(f"{Fore.GREEN}Body:{Fore.RESET}")
        logging.info(
            "Macro failed to lookup item from POE trade API. Here is the item in question."
        )
        logging.info("====== ITEM DATA=====")
        logging.info(f"{text}")
        logging.info(
            f"{Fore.GREEN}================== END ISSUE DATA =================={Fore.RESET}"
        )
        logging.info(
            f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE =================={Fore.RESET}"
        )

    except Exception:
        exception = traceback.format_exc()
        logging.info(
            f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW =================={Fore.RESET}"
        )
        logging.info(
            f"[!] Something went horribly wrong. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        logging.info(
            f"{Fore.GREEN}================== START ISSUE DATA =================={Fore.RESET}"
        )
        logging.info(f"{Fore.GREEN}Title:{Fore.RESET}")
        logging.info("Failed to query item from trade API.")
        logging.info(f"{Fore.GREEN}Body:{Fore.RESET}")
        logging.info("Here is the item in question.")
        logging.info("====== ITEM DATA=====")
        logging.info(f"{text}")
        logging.info("====== TRACEBACK =====")
        logging.info(exception)
        logging.info(
            f"{Fore.GREEN}================== END ISSUE DATA =================={Fore.RESET}"
        )
        logging.info(
            f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE =================={Fore.RESET}"
        )


def search_ninja_base(text):
    NINJA_BASES = get_ninja_bases(LEAGUE)
    real_item = parse_item_info(text)
    if not isinstance(real_item, Item):
        return

    influences = real_item.influence
    ilvl = real_item.ilevel if real_item.ilevel >= 84 else 84
    base = real_item.base
    # base = info["itype"] if info["itype"] != None else info["base"]

    logging.info(
        f"[*] Searching for base {base}. Item Level: {ilvl}, Influences: {influences}"
    )
    result = None
    try:
        result = next(
            item
            for item in NINJA_BASES
            if (
                item["base"] == base
                and (
                    (not influences and item["influence"] is None)
                    or (
                        bool(influences)
                        and item["influence"] is not None
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

    if result is not None:
        price = result["exalt"] if result["exalt"] >= 1 else result["chaos"]
        currency = "ex" if result["exalt"] >= 1 else "chaos"
        logging.info(f"[$] Price: {price} {currency}")
        if config.USE_GUI:
            influence = influences[0] if bool(influences) else None
            baseResults.add_base_result(base, influence, ilvl, price, currency)
            baseResults.create_at_cursor()
