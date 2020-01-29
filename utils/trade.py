import pathlib
import zipfile
from itertools import chain
from typing import List, Tuple

import requests
from tqdm import tqdm

from factories.item_modifier import build_from_json
from models.item_modifier import ItemModifier
from utils.config import RELEASE_URL, VERSION
from utils.exceptions import InvalidAPIResponseException


def exchange_currency(query: dict, league: str) -> dict:
    """
    :param query: A JSON query to send to the currency trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = requests.post(f"https://www.pathofexile.com/api/trade/exchange/{league}", json=query)
    return results.json()


def query_item(query: dict, league: str) -> dict:
    """
    :param query: A JSON query to send to the trade api
    :param league: the league to search in
    :return results: return a JSON object with the amount of items found and a key to get
     item details
    """
    results = requests.post(f"https://www.pathofexile.com/api/trade/search/{league}", json=query)
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
                print(
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


def get_item_modifiers() -> Tuple[ItemModifier, ...]:
    """
    Get all valid Item Modifiers (affixes) from the PoE API
    """
    json_blob = requests.get(url="https://www.pathofexile.com/api/trade/data/stats").json()
    items = tuple(chain(*[[build_from_json(y) for y in x["entries"]] for x in json_blob["result"]]))
    return items


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
        print("[!] You are not running the latest version of Path of Accounting. Would you like to update? (y/n)")
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
                    print("[!] Error, something went wrong while downloading the file.")
                else:
                    # Unzip it and tell the user where we unzipped it to.
                    with zipfile.ZipFile("Path-of-Accounting.zip", "r") as zip_file:
                        zip_file.extractall()
                    print(f"[*] Extracted zip file to: {pathlib.Path().absolute()}\\Path of Accounting")

                # subprocess.Popen(f"{pathlib.Path().absolute()}\\Path\\ of\\Accounting\\parse.exe")
                # sys.exit()

            elif user_choice.lower() == "n":
                choice_made = True
            else:
                print("I did not understand your response. Please user either y or n.")


def get_ninja_bases():
    """
    Retrieve all of the bases and their respective prices listed on poe.ninja

    Returns list[dict]
    """
    query = requests.get("https://poe.ninja/api/data/itemoverview?league=Metamorph&type=BaseType&language=en")
    tbases = query.json()

    bases = [
        {
            "base": b["baseType"],
            "ilvl": b["levelRequired"],
            "influence": b["variant"],
            "corrupted": b["corrupted"],
            "exalt": b["exaltedValue"],
            "chaos": b["chaosValue"],
        }
        for b in tbases["lines"]
    ]

    return bases
