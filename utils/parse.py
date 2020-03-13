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


def adv_search(text):
    item = parse_item_info(text)
    if not item:
        return
    if config.USE_GUI:
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
        print(f"[!] Limited Results, Removing some item stats")
        if config.USE_GUI:
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
    NINJA_BASES = get_ninja_bases(LEAGUE)
    real_item = parse_item_info(text)
    # logging.info(real_item.get_json())
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
