import logging
import traceback
from datetime import datetime, timezone
from typing import Dict

from colorama import Fore

from gui.advSearch import advancedSearch
from gui.windows import (
    baseResults,
    information,
    notEnoughInformation,
    priceInformation,
)
from item.generator import *
from utils import config
from utils.common import get_trade_data, price_item
from utils.config import MIN_RESULTS, PROJECT_URL
from utils.exceptions import InvalidAPIResponseException
from utils.web import (
    exchange_currency,
    fetch,
    get_ninja_bases,
    open_exchange_site,
    open_trade_site,
    query_item,
)


def adv_search(text):
    """Advanced pricing utiltity. User gets choice on values to search.

    User gets choice on inclusion and value of mods.

    :param text: The text of the item to be searched.
    """
    item = parse_item_info(text)
    if not item:
        return
    advancedSearch.add_item(item)
    advancedSearch.create_at_cursor()


def basic_search(text):
    """Pricing utility. Tries to price items by searching the API and gradually relaxing modifiers

    :param text: The raw text of the item to search
    """
    item = parse_item_info(text)
    if not item:
        return
    logging.debug(item.get_json())
    item.create_pseudo_mods()
    item.relax_modifiers()

    data, results = get_trade_data(item)

    if results < MIN_RESULTS:
        logging.info(f"[!] Limited Results, Removing some item stats")
        information.add_info(
            "[!] Limited Results, Removing some item stats"
        )
        information.create_at_cursor()
        item.remove_bad_mods()

    price_item(item)


def search_ninja_base(text):
    """Search the ninja_bases cache for a match for the given item.

    :param text: raw text of the item to be searched for
    """
    try:
        NINJA_BASES = get_ninja_bases(config.LEAGUE)
    except Exception:
        logging.info("Poe.ninja is unavailable right now.")
        return 0

    real_item = parse_item_info(text)
    if not real_item:
        return
    logging.debug(real_item.get_json())
    if not isinstance(real_item, Item):
        return

    influences = real_item.influence
    ilvl = real_item.ilevel if real_item.ilevel >= 84 else 84
    base = real_item.base

    logging.info(
        f"[*] Searching for base {base}. Item Level: {ilvl}, Influences: {influences}"
    )

    # This is just a really long generator expression to grab the first match
    # based on all of the variables.
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
        notEnoughInformation.create_at_cursor()

    if result is not None:
        price = result["exalt"] if result["exalt"] >= 1 else result["chaos"]
        currency = "ex" if result["exalt"] >= 1 else "chaos"
        logging.info(f"[$] Price: {price} {currency}")
        influence = influences[0] if bool(influences) else None
        baseResults.add_base_result(base, influence, ilvl, price, currency)
        baseResults.create_at_cursor()
