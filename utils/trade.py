import logging
import pathlib
import zipfile
from itertools import chain
from typing import List, Tuple, Optional

import requests
from tqdm import tqdm

from factories.item_modifier import build_from_json
from models.item_modifier import ItemModifier
from utils.config import RELEASE_URL, VERSION
from utils.exceptions import InvalidAPIResponseException
from utils.types import (
    add_magic_base,
    add_map_base,
)

ninja_bases = []

item_cache = []
map_cache = set()

mod_list = []
mod_list_dict_id = {}
mod_list_dict_text = {}

def search_url(league: str) -> str:
    return f"https://www.pathofexile.com/api/trade/search/{league}"

def exchange_url(league: str) -> str:
    return f"https://www.pathofexile.com/api/trade/exchange/{league}"

def exchange_currency(query: dict, league: str) -> dict:
    """
    :param query: A JSON query to send to the currency trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = requests.post(exchange_url(league), json=query)
    return results.json()


def query_item(query: dict, league: str) -> dict:
    """
    :param query: A JSON query to send to the trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = requests.post(search_url(league), json=query)
    return results.json()


def fetch(q_res: dict, exchange: bool = False) -> List[dict]:  # JSON
    """
    Fetch is the last step of the API. The item's attributes have already been decided, and this function checks to see if
    there are any similar items like it listed.

    returns JSON of all available similar items.
    """

    # TODO: Bring back debug statement

    results = []
    # Limited to crawling by 10 results at a time due to API restrictions, so check first 50
    # TODO: This doesn't work...
    DEFAULT_CAP = 50
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

            res = requests.get(url)
            if res.status_code != 200:
                logging.error(
                    f"[!] Trade result retrieval failed: HTTP {res.status_code}! "
                    f'Message: {res.json().get("error", "unknown error")}'
                )
                break

            # Return the results from our fetch (this has who to whisper, prices, and more!)
            results += res.json()["result"]

    else:
        raise InvalidAPIResponseException()

    return results


def get_leagues() -> Tuple[str, ...]:
    """
    Get all valid leagues from the PoE API and put them into a tuple
    """
    leagues = requests.get(url="https://www.pathofexile.com/api/trade/data/leagues").json()
    return tuple(x["id"] for x in leagues["result"])


def get_item_modifiers_by_text(element: Tuple) -> ItemModifier:
    global mod_list_dict_text
    if len(mod_list_dict_text) == 0:
        item_modifiers = get_item_modifiers()
        mod_list_dict_text = {(e.text, e.type): e for e in item_modifiers}
    if element in mod_list_dict_text:
        return mod_list_dict_text[element]

def get_item_modifiers_by_id(element: str) -> ItemModifier:
    global mod_list_dict_id
    if len(mod_list_dict_id) == 0:
        item_modifiers = get_item_modifiers()
        mod_list_dict_id = {e.id: e for e in item_modifiers}
    if element in mod_list_dict_id:
        return mod_list_dict_id[element]

def get_item_modifiers() -> Tuple[ItemModifier, ...]:
    """
    Get all valid Item Modifiers (affixes) from the PoE API
    """
    global mod_list
    if mod_list:
        return mod_list
    else:
        json_blob = requests.get(url="https://www.pathofexile.com/api/trade/data/stats").json()
        mod_list = tuple(chain(*[[build_from_json(y) for y in x["entries"]] for x in json_blob["result"]]))
        logging.info(f"[*] Loaded {len(mod_list)} item mods.")
        return mod_list


def find_latest_update():
    """
    Find the latest version of the software both locally and remote. If not the newest version,
    prompt for an upgrade.
    """
    # Get the list of releases from github, choose newest (even pre-release)
    remote = requests.get(url=RELEASE_URL).json()[0]
    # local version
    local = VERSION
    # Check if the same
    if remote["tag_name"] != local:
        logging.info("[!] You are not running the latest version of Path of Accounting. Would you like to update? (y/n)")
        # Keep going till user makes a valid choice
        choice_made = False
        while not choice_made:
            user_choice = input()
            if user_choice.lower() == "y":
                choice_made = True
                # Get the sole zip url
                r = requests.get(url=remote["assets"][0]["browser_download_url"], stream=True)

                # Set up a progress bar
                total_size = int(r.headers.get("content-length", 0))
                block_size = 1024
                timer = tqdm(total=total_size, unit="iB", unit_scale=True)

                # Write the file
                with open("Path-of-Accounting.zip", "wb") as f:
                    for data in r.iter_content(block_size):
                        timer.update(len(data))
                        f.write(data)
                timer.close()
                print()

                # This means data got lost somewhere...
                if total_size != 0 and timer.n != total_size:
                    logging.error("[!] Error, something went wrong while downloading the file.")
                else:
                    # Unzip it and tell the user where we unzipped it to.
                    with zipfile.ZipFile("Path-of-Accounting.zip", "r") as zip_file:
                        zip_file.extractall()
                    logging.info(f"[*] Extracted zip file to: {pathlib.Path().absolute()}\\Path of Accounting")

                # subprocess.Popen(f"{pathlib.Path().absolute()}\\Path\\ of\\Accounting\\parse.exe")
                # sys.exit()

            elif user_choice.lower() == "n":
                choice_made = True
            else:
                logging.error("I did not understand your response. Please user either y or n.")


def get_ninja_bases():
    """
    Retrieve all of the bases and their respective prices listed on poe.ninja

    Returns list[dict]
    """
    global ninja_bases
    if not ninja_bases:
        query = requests.get("https://poe.ninja/api/data/itemoverview?league=Metamorph&type=BaseType&language=en")
        tbases = query.json()

        ninja_bases = [
            {
                "base": b["baseType"],
                "ilvl": b["levelRequired"],
                "influence": b["variant"],
                "corrupted": b["corrupted"],
                "exalt": b["exaltedValue"],
                "chaos": b["chaosValue"],
                "type": b["itemType"]
            }
            for b in tbases["lines"]
        ]

        unique_ninja_bases = [
            e for e in ninja_bases if not e["influence"]
        ]

        # Populate magic item base graph
        for e in unique_ninja_bases:
            add_magic_base(e["base"], e["type"])

    return ninja_bases

def get_items():
    global item_cache
    if not item_cache:
        query = requests.get("https://www.pathofexile.com/api/trade/data/items")
        items = query.json()
        item_cache = items["result"]
    return item_cache

def get_maps():
    global item_cache
    global map_cache
    if not map_cache:
        get_items()
        for item_type in item_cache:
            if item_type["label"] != "Maps":
                continue

            for map_entry in item_type["entries"]:
                map_base = map_entry["type"]
                if map_base not in map_cache:
                    map_cache.add(map_base)

    return map_cache

def build_map_bases():
    global map_cache
    get_maps()
    for e in map_cache:
        add_map_base(e)
