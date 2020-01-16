import pathlib
import zipfile
from itertools import chain
from typing import List, Tuple

import requests
from tqdm import tqdm

from factories.item_modifier import build_from_json
from models.item_modifier import ItemModifier
from utils.config import VERSION


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
    remote = requests.get(url="https://api.github.com/repos/Ethck/Path-of-Accounting/releases").json()[0]
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
                    print(f"[*] Extracted zip file to: {pathlib.Path().absolute()}\\Path-of-Accounting")

            elif user_choice.lower() == "n":
                choice_made = True
            else:
                print("I did not understand your response. Please user either y or n.")
