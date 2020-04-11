import base64
import logging
import os
import pathlib
import re
import subprocess
import sys
import traceback
import webbrowser
import time
import zipfile
from itertools import chain

import requests
from tqdm import tqdm

from item.itemModifier import ItemModifier, ItemModifierType
from utils import config
from utils.config import RELEASE_URL, VERSION
from utils.exceptions import InvalidAPIResponseException

ninja_bases = []

item_cache = []
map_cache = set()

mod_list = []
mod_list_dict_id = {}
mod_list_dict_text = {}

# contains all mods there exist more than 1 off
dup_mod_list_text = {}


def search_url(league: str) -> str:
    """Returns the URL needed to make the POST request to the API"""
    return f"https://www.pathofexile.com/api/trade/search/{league}"


def exchange_url(league: str) -> str:
    """Returns the URL needed to make the POST request to the Exchange API"""
    return f"https://www.pathofexile.com/api/trade/exchange/{league}"


def post_request(addr: str, timeout: int, max_tries: int, json=None):
    try:
        r = requests.post(addr, timeout=timeout, json=json)

        if r.status_code != 200:
            logging.error(
                f"[!] Trade result retrieval failed: HTTP {r.status_code}! "
                f'Message: {r.json().get("error", "unknown error")}'
            )

        return r
    except Exception:
        site = ""
        x = addr.rfind(".")
        y = addr.find("/", x)
        site += addr[:y]
        if max_tries > 0:
            logging.info(
                site
                + " is not responding, trying "
                + str(max_tries)
                + " more times"
            )
            return post_request(addr, timeout, max_tries - 1, json)
        else:
            logging.info("Could not connect to: " + site + ".")
            return None
    return None


def get_request(addr: str, timeout: int, max_tries: int, stream=False):
    try:
        r = requests.get(addr, timeout=timeout, stream=stream)

        if r.status_code != 200:
            logging.error(
                f"[!] Trade result retrieval failed: HTTP {r.status_code}! "
                f'Message: {r.json().get("error", "unknown error")}'
            )

        return r
    except Exception:
        site = ""
        x = addr.rfind(".")
        y = addr.find("/", x)
        site += addr[:y]
        if max_tries > 0:
            logging.info(
                site
                + " is not responding, trying "
                + str(max_tries)
                + " more times"
            )
            return get_request(addr, timeout, max_tries - 1, stream)
        else:
            logging.info("Could not connect to: " + site + ".")
            return None


def exchange_currency(query: dict, league: str) -> dict:
    """Queries the Exchange API and returns the results

    :param query: A JSON query to send to the currency trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = post_request(exchange_url(league), 10, 2, query).json()
    if "error" in results.keys():
        msg = results["error"]["message"]
        logging.info(f"[Error] {msg}")
        return None
    return results


def query_item(query: dict, league: str) -> dict:
    """Queries the API and returns the results

    :param query: A JSON query to send to the trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = post_request(search_url(league), 10, 2, query).json()

    if "error" in results.keys():
        msg = results["error"]["message"]
        logging.info(f"[Error] {msg}")
        return None
    return results


def fetch(q_res: dict, exchange: bool = False) -> dict:
    """Based on results of the POST requests construct the GET request(s)

    :param q_res: Results of the POST request
    :param exchange: Whether or not to use the exchange API
    :return results: Results of the GET request
    """

    results = []
    # Limited to crawling by 10 results at a time due to API restrictions
    DEFAULT_CAP = 10
    DEFAULT_INTERVAL = 10
    cap = DEFAULT_CAP
    interval = DEFAULT_INTERVAL

    # If there's less than 10 results, change to the number there is.
    if len(q_res) < DEFAULT_CAP:
        cap = int((len(q_res) / 10) * 10)

    # Find all the results
    if "result" in q_res:
        for i in range(0, cap, interval):
            url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(q_res["result"][i:i+10])}?query={q_res["id"]}'

            if exchange:
                url += "exchange=true"
            res = get_request(url, 10, 2).json()
            # Return the results from our fetch (this has who to whisper, prices, and more!)
            if res:
                if "result" in res:
                    results += res["result"]

    else:
        raise InvalidAPIResponseException()

    return results


def get_leagues() -> tuple:
    """Query the API to get all current running leagues

    :return: Tuple of league ids
    """
    try:
        leagues = get_request(
            "https://www.pathofexile.com/api/trade/data/leagues", 10, 2
        ).json()
        return tuple(x["id"] for x in leagues["result"])
    except Exception:
        return None


def get_item_modifiers_by_text(element: tuple) -> ItemModifier:
    """Search all available ItemModifier objects by their text attribute.

    If this is the first time being used, construct a cache so that we
    can search faster on subsequent versions

    :param element: (text, type) of the requested ItemModifier
    :return: ItemModifier that matches
    """
    global mod_list_dict_text
    global dup_mod_list_text
    if len(mod_list_dict_text) == 0:
        item_modifiers = get_item_modifiers()
        found = {}
        for mod in item_modifiers:
            if "Allocates # (Additional)" in mod.text:  # Gives no results ATM
                continue
            if (mod.text, mod.type) in mod_list_dict_text:
                if not (mod.text, mod.type) in found:
                    found[(mod.text, mod.type)] = {}
                found[(mod.text, mod.type)][mod.id] = ""
                found[(mod.text, mod.type)][
                    mod_list_dict_text[(mod.text, mod.type)].id
                ] = ""

            mod_list_dict_text[(mod.text, mod.type)] = mod
        for key, value in found.items():
            dup_mod_list_text[key] = ""
    if element in mod_list_dict_text:
        return mod_list_dict_text[element]


def is_duplicate_mod_type(mod):
    """
    Checks if a mod exist in the duplicate mod list
    Return True if it does, false if it does not
    """
    global dup_mod_list_text
    if (mod.text, mod.type) in dup_mod_list_text:
        return True
    return False


def get_item_modifiers_by_id(element: str) -> ItemModifier:
    """Search all available ItemModifier objects by their id attribute.

    If this is the first time being used, construct a cache so that we
    can search faster on subsequent versions

    :param element: id of the requested ItemModifier
    :return: ItemModifier that matches
    """
    global mod_list_dict_id
    if len(mod_list_dict_id) == 0:
        item_modifiers = get_item_modifiers()
        mod_list_dict_id = {e.id: e for e in item_modifiers}
    if element in mod_list_dict_id:
        return mod_list_dict_id[element]


def build_from_json(blob: dict) -> ItemModifier:
    """From the stats API construct ItemModifier objects for given entry

    :param blob: A modifier found in the stats API
    :return: ItemModifier object for the given modifier
    """
    if "option" in blob:
        # If the given modifier has an option section, add it.
        # This is necessary for the "Allocates #" modifier that
        # is present on Annointed items
        if "options" in blob["option"]:
            options = {}
            for i in blob["option"]["options"]:
                options[i["text"]] = i["id"]

            t = blob["text"].rstrip()
            if not "(Local)" in t:
                t = re.sub(r"\(([^)]*)\)", "", t)
            t = t.rstrip()
            return ItemModifier(
                id=blob["id"],
                text=t,
                options=options,
                type=ItemModifierType(blob["type"].lower()),
            )

    t = blob["text"].rstrip()
    if not "(Local)" in t:
        t = re.sub(r"\(([^)]*)\)", "", t)
    t = t.rstrip()

    return ItemModifier(
        id=blob["id"],
        text=t,
        type=ItemModifierType(blob["type"].lower()),
        options={},
    )


def get_item_modifiers() -> tuple:
    """Query the stats API to retrieve all current stats

    :return: tuple of all available modifiers
    """
    global mod_list
    if mod_list:
        return mod_list
    else:
        json_blob = get_request(
            "https://www.pathofexile.com/api/trade/data/stats", 10, 3
        ).json()
        try:
            for modType in json_blob["result"]:
                for mod in modType["entries"]:
                    mod_list.append(build_from_json(mod))

            logging.info(f"[*] Loaded {len(mod_list)} item mods.")
            return mod_list
        except Exception:
            logging.info(f"[!] Something went wrong getting item mods!")
            return None


def find_latest_update():
    """Search both local and remote versions, if different, prompt for update."""
    try:
        # Get the list of releases from github, choose newest (even pre-release)
        remote = get_request(RELEASE_URL, 10, 2).json()[0]

        if not remote:
            logging.error("[!] Could not check for new update!")
            return

        # local version
        local = VERSION
        # Check if the same-
        # print(remote["tag_name"], local)
        if float(local.replace("v", "")) < float(
            remote["tag_name"].replace("v", "")
        ):
            url = remote["html_url"]
            logging.info(
                f"[!] You are not running the latest version of Path of Accounting.\nNew Version available at: {url}"
            )

              # Keep going till user makes a valid choice
            if os.name == "nt":

                logging.info(
                    f"[!] Do you want to download the new version? (y/n)"
                )

                while True:
                    user_choice = input()
                    if user_choice.lower() == "y":
                        # Get the sole zip url
                        url = remote["assets"][0]["browser_download_url"]
                        r = get_request(url, 10, 2, True)
                        # Set up a progress bar
                        total_size = int(r.headers.get("content-length", 0))
                        block_size = 1024
                        timer = tqdm(
                            total=total_size, unit="iB", unit_scale=True
                        )

                        # Write the file
                        with open("Path-of-Accounting.zip", "wb") as f:
                            for data in r.iter_content(block_size):
                                timer.update(len(data))
                                f.write(data)
                        timer.close()
                        f.close()

                        # This means data got lost somewhere...
                        if total_size != 0 and timer.n != total_size:
                            logging.error(
                                "[!] Error, something went wrong while downloading the file.\n" +
                                "[!] Please try download manually"
                            )
                        else:
                            logging.info(
                                f"[*] Zip file downloaded to: {pathlib.Path().absolute()}\n" +
                                "[*] Please extract it manually\n" +
                                "[*] Program will automaticly exit in 10 seconds.."
                            )
                            time.sleep(10)
                            sys.exit()
                        break

                    elif user_choice.lower() == "n":
                        break
                    else:
                        logging.error(
                            "I did not understand your response. Please user either y or n."
                        )
    except Exception:
        logging.error("[!] Could not check for new update!")


def get_ninja_bases(league: str):
    """Retrieve all of the bases and their respective prices listed on poe.ninja

    :return ninja_bases: list of all availabe bases and their properties
    """
    global ninja_bases
    if not ninja_bases:
        try:
            addr = f"https://poe.ninja/api/data/itemoverview?league={league}&type=BaseType&language=en"
            tbases = get_request(addr, 10, 2).json()

            ninja_bases = [
                {
                    "base": b["baseType"],
                    "ilvl": b["levelRequired"],
                    "influence": b["variant"],
                    "corrupted": b["corrupted"],
                    "exalt": b["exaltedValue"],
                    "chaos": b["chaosValue"],
                    "type": b["itemType"],
                }
                for b in tbases["lines"]
            ]
        except Exception:
            logging.info("poe.ninja is not available.")
            return None
        # unique_ninja_bases = [e for e in ninja_bases if not e["influence"]]

    return ninja_bases


def get_items() -> dict:
    """Query item API to find all current items.

    If this is the first time being used, construct a cache so that we
    can search faster on subsequent versions

    :return: cache that contains all items
    """
    global item_cache
    if not item_cache:
        try:
            items = get_request(
                "https://www.pathofexile.com/api/trade/data/items", 10, 3
            ).json()
            item_cache = items["result"]
            for i in item_cache:
                i["entries"].sort(key=lambda x: len(x["type"]), reverse=True)
        except Exception:
            return None
    return item_cache


def get_base(category, name):
    """Find the base type of a given item.

    :param category: cateogory of given item (Belt, Flask, etc.)
    :param name: name of the given item
    :return: Found base type, or None
    """
    items = get_items()
    try:
        for i in items:
            if i["label"] == category:
                result = next(l for l in i["entries"] if l["type"] in name)
                return result["type"]
    except:
        pass
    return None


def wiki_lookup(item):
    """Given an item, load its webpage

    :param item: Item object to be used
    """
    base_url = "https://pathofexile.gamepedia.com/"

    base_rarities = {"rare", "gem", "divination card", "normal", "currency"}

    if item:
        if item.rarity == "unique":
            url = base_url + item.name
            logging.info(f"[*] wiki_lookup item : {item.name}")
            url = base_url + item.name.replace(" ", "_")
            logging.info(url)
            webbrowser.open(url)

        elif item.rarity in base_rarities:
            logging.info(f"[*] wiki_lookup item : {item.base}")
            url = base_url + item.base.replace(" ", "_")
            logging.info(url)
            webbrowser.open(url)

        # Only items not supported are magic items.
        else:
            logging.error("[!] Wiki page not found.")


def open_trade_site(rid, league):
    """Open up the web browser to the site we search

    :param rid: Unique ID given from the POST response
    :param league: League to search
    """
    trade_url = f"https://pathofexile.com/trade/search/{league}/{rid}"
    logging.debug("Opening trade site with url: %s" % trade_url)
    webbrowser.open(trade_url)


def open_exchange_site(rid, league):
    """Open up the web browser to the exchange site we search

    :param rid: Unique ID given from the POST response
    :param league: League to search
    """
    url = f"https://www.pathofexile.com/trade/exchange/{league}/{rid}"
    logging.debug("Opening exchange site with url: %s" % url)
    webbrowser.open(url)


def get_poe_prices_info(item):
    """Query the poeprice.info API with the item's text.

    :param item: The item whose info we will query
    """
    try:
        league = bytes(config.LEAGUE, "utf-8")
        try:
            logging.debug(
                b"Visiting "
                + b"https://poeprices.info/api?l="
                + league
                + b"&i="
                + base64.b64encode(bytes(item.text, "utf-8"))
            )
            addr = (
                b"https://poeprices.info/api?l="
                + league
                + b"&i="
                + base64.b64encode(bytes(item.text, "utf-8"))
            )

            results = post_request(addr, 10, 2).json()

            logging.debug(results)
            return results
        except Exception:
            logging.info("poeprices.info took too long to respond.")
            return {}
    except Exception:
        logging.error("Could not retrieve data from poeprices.info")
        logging.error(item.text)
        logging.error(traceback.print_exc())
        return {}
