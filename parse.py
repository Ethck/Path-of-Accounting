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
from utils.input import Keyboard, get_clipboard
from utils.trade import (
    exchange_currency,
    fetch,
    find_latest_update,
    get_item_modifiers,
    get_leagues,
    get_ninja_bases,
    query_item,
)
from utils.web import open_trade_site, wiki_lookup

DEBUG = False


def parse_item_info(text: str) -> Dict:
    """
    Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
    """
    # Find out if this is a path of exile item
    m = re.findall(r"^Rarity: (\w+)\r?\n(.+?)\r?\n(.+?)\r?\n", text)

    if not m:  # Different check
        m = re.findall(r"^Rarity: (.*)\n(.*)", text)
        if not m:
            return {}
        else:
            info = {"name": m[0][1], "rarity": m[0][0], "itype": m[0][0]}
    else:

        # get some basic info
        info = {"name": m[0][1], "rarity": m[0][0], "itype": m[0][2]}

    unident = bool(re.search("Unidentified", text, re.M))
    metamorph = bool(re.search("Tane", text, re.M))
    prophecy = bool(re.search("Right-click to add this prophecy to your character.", text, re.M))

    # Corruption status and influenced status

    info["influenced"] = {}
    info["influenced"]["shaper"] = bool(re.search(r"^Shaper Item", text, re.M))
    info["influenced"]["elder"] = bool(re.search(r"^Elder Item", text, re.M))
    info["influenced"]["crusader"] = bool(re.search("Crusader Item", text, re.M))
    info["influenced"]["hunter"] = bool(re.search("Hunter Item", text, re.M))
    info["influenced"]["redeemer"] = bool(re.search("Redeemer Item", text, re.M))
    info["influenced"]["warlord"] = bool(re.search("Warlord Item", text, re.M))
    info["corrupted"] = bool(re.search("^Corrupted$", text, re.M))

    # Get Qual
    m = re.findall(r"Quality: \+(\d+)%", text)

    info["quality"] = int(m[0]) if m else 0

    if "Map" in info["name"] and "Map" not in info["itype"]:  # Seems to be all Superior maps...
        if info["itype"] == "--------":
            info["itype"] = info["name"]

    if "Synthesised" in info["itype"]:
        info["itype"] = info["itype"].replace("Synthesised ", "")

    if "<<set:MS>><<set:M>><<set:S>>" in info["name"]:  # For checking in chat items... For some reason this is added.
        info["name"] = info["name"].replace("<<set:MS>><<set:M>><<set:S>>", "").strip()

    # Oh, it's currency!
    if info["rarity"] == "Currency":
        info["itype"] = info.pop("rarity").rstrip()
    elif info["rarity"] == "Divination Card":
        info["rarity"] = info["rarity"].strip()
        info["itype"] = info.pop("rarity")
    elif info["rarity"] == "Normal" and "Scarab" in info["name"]:
        info["itype"] = "Currency"
    elif "Map" in info["itype"]:
        if info["quality"] != 0:
            info["itype"] = info["itype"].replace("Superior", "").strip()
        map_mods = {}
        map_mods["tier"] = re.findall(r"Map Tier: (\d+)", text)[0]

        iiq_re = re.findall(r"Item Quantity: \+(\d+)%", text)
        if len(iiq_re) > 0:
            map_mods["iiq"] = iiq_re[0]

        pack_re = re.findall(r"Pack Size: \+(\d+)%", text)
        if len(pack_re) > 0:
            map_mods["pack"] = pack_re[0]

        iir_re = re.findall(r"Item Rarity: \+(\d+)%", text)
        if len(iir_re) > 0:
            map_mods["iir"] = iir_re[0]

        map_mods["blight"] = bool(re.search(r"Blighted", text, re.M))
        map_mods["shaper"] = bool(re.search("Area is influenced by The Shaper", text, re.M))
        map_mods["elder"] = bool(re.search("Area is influenced by The Elder", text, re.M))
        map_mods["enslaver"] = bool(re.search("Map is occupied by The Enslaver", text, re.M))
        map_mods["eradicator"] = bool(re.search("Map is occupied by The Eradicator", text, re.M))
        map_mods["constrictor"] = bool(re.search("Map is occupied by The Constrictor", text, re.M))
        map_mods["purifier"] = bool(re.search("Map is occupied by The Purifier", text, re.M))

        info["maps"] = map_mods

    elif info["itype"] == "--------" and unident:  # Unided
        info["itype"] = info["name"]
        if info["rarity"] == "Unique":
            print(
                "[!] "
                + Fore.RED
                + "Can't price "
                + Fore.WHITE
                + "this item because it is "
                + Fore.YELLOW
                + "unidentified"
                + Fore.WHITE
                + ". Please identify and try again."
            )
            return 0
        # Item Level
        m = re.findall(r"Item Level: (\d+)", text)

        if m:
            info["ilvl"] = int(m[0])

    elif metamorph:
        info["itype"] = "Metamorph"
        m = re.findall(r"Item Level: (\d+)", text)

        if m:
            info["ilvl"] = int(m[0])

    elif info["rarity"] == "Normal" and prophecy:  # Prophecies
        info["itype"] = "Prophecy"

    else:
        if info["rarity"] == "Magic" or info["rarity"] == "Normal" or info["rarity"] == "Rare":
            info["base"] = info["itype"]
            info["itype"] = None

        if info["rarity"] == "Gem":
            m = bool(re.search("Vaal", text, re.M))
            no_vaal = bool(re.search("Cannot support Vaal skills", text, re.M))
            a = bool(re.search("Awakened", text, re.M))
            c = bool(re.search("^Corrupted", text, re.M))

            lvl = re.findall(r"Level: (\d+)", text)[0]
            if lvl is not None:
                info["gem_level"] = lvl

            if c:
                info["corrupted"] = True
            if m and not a and not no_vaal:
                impurity = bool(re.search(r"Purity of \w+", text, re.M))
                if impurity:
                    info["itype"] = "Vaal Im" + info["name"][0].lower() + info["name"][1:]
                else:
                    info["itype"] = "Vaal " + info["name"]
            else:
                info["itype"] = info["name"]

        # Sockets and Links
        m = re.findall(r"Sockets:(.*)", text)

        if m:
            info["links"] = m[0].count("-") + 1

        # Item Level
        m = re.findall(r"Item Level: (\d+)", text)

        if m:
            info["ilvl"] = int(m[0])

        # Find all the affixes
        m = re.findall(r"Item Level: \d+[\r\n]+--------[\r\n]+(.+)((?:[\r\n]+.+)+)", text)

        if DEBUG:
            print("STATS:", m)

        if m:
            info["stats"] = []
            info["stats"].append(m[0][0])
            info["stats"].extend(m[0][1].split("\n"))

            # Clean up the leftover stuff / Make it useable data
            if info["stats"][1] == "" and info["stats"][2] == "--------":  # Implicits and enchantments.
                del info["stats"][1:3]
            elif "--------" in info["stats"]:
                pass  # It might have implicits, annointments, and/or enchantments.
            else:
                info["stats"] = info["stats"][:-1]

            if "" in info["stats"]:
                info["stats"].remove("")

            info["stats"] = [stat.strip() for stat in info["stats"]]

    if DEBUG:  # DEBUG
        print("COMPLETE INFO: ", info)

    return info


def build_json_official(
    name: str = None,
    ilvl: int = None,
    itype: str = None,
    links: int = None,
    corrupted: bool = None,
    influenced: bool = None,
    rarity: str = None,
    stats: List[str] = None,
    gem_level: int = None,
    quality: int = None,
    maps=None,
) -> List[Dict]:  # JSON
    """
    Build JSON for fetch request of an item for trade.
    Take all the parsed item info, and construct JSON based off of it.

    returns JSON of format for pathofexile.com/trade.
    """
    if stats is None:
        stats = []
    # Basic JSON structure
    j = {"query": {"filters": {}}, "sort": {"price": "asc"}}

    if maps is not None:
        j["query"]["filters"]["map_filters"] = {}
        j["query"]["filters"]["map_filters"]["filters"] = {}

        if rarity == "Unique":  # Unique maps, may be unidentified
            j["query"]["filters"]["type_filters"] = {}
            j["query"]["filters"]["type_filters"]["filters"] = {"rarity": {"option": "unique"}}
            j["query"]["type"] = {"option": name}
            name = None

        if maps["blight"]:
            j["query"]["filters"]["map_filters"]["filters"]["map_blighted"] = "True"
            itype = itype.replace("Blighted", "").strip()

        if "iiq" in maps:
            if maps["iiq"]:
                j["query"]["filters"]["map_filters"]["filters"]["map_iiq"] = {
                    "min": maps["iiq"],
                    "max": "null",
                }

        if "iir" in maps:  # False if Unidentified
            if maps["iir"]:
                j["query"]["filters"]["map_filters"]["filters"]["map_iir"] = {
                    "min": maps["iir"],
                    "max": "null",
                }
        if "pack" in maps:  # False if Unidentified
            if maps["pack"]:
                j["query"]["filters"]["map_filters"]["filters"]["map_packsize"] = {
                    "min": maps["pack"],
                    "max": "null",
                }

        if maps["tier"]:
            j["query"]["filters"]["map_filters"]["filters"]["map_tier"] = {
                "min": maps["tier"],
                "max": "null",
            }

        if maps["shaper"] or maps["elder"]:
            j["query"]["stats"] = [{}]
            j["query"]["stats"][0]["type"] = "and"
            j["query"]["stats"][0]["filters"] = []

            if maps["shaper"]:  # Area is influenced by the Shaper
                j["query"]["stats"][0]["filters"].append({"id": "implicit.stat_1792283443", "value": {"option": "1"}})
            elif maps["elder"]:  # Area is influenced by the Elder
                j["query"]["stats"][0]["filters"].append({"id": "implicit.stat_1792283443", "value": {"option": "2"}})

            if maps["enslaver"] or maps["eradicator"] or maps["constrictor"] or maps["purifier"]:
                if maps["enslaver"]:
                    j["query"]["stats"][0]["filters"].append(
                        {"id": "implicit.stat_3624393862", "value": {"option": "1"}}
                    )
                elif maps["eradicator"]:
                    j["query"]["stats"][0]["filters"].append(
                        {"id": "implicit.stat_3624393862", "value": {"option": "2"}}
                    )
                elif maps["constrictor"]:
                    j["query"]["stats"][0]["filters"].append(
                        {"id": "implicit.stat_3624393862", "value": {"option": "3"}}
                    )
                elif maps["purifier"]:
                    j["query"]["stats"][0]["filters"].append(
                        {"id": "implicit.stat_3624393862", "value": {"option": "4"}}
                    )

    # If unique, Div Card, or Gem search by name
    if rarity == "Unique" or itype == "Divination Card":
        if name != None:
            j["query"]["name"] = name

    if itype == "Metamorph":
        mm_parts = ["Brain", "Lung", "Eye", "Heart", "Liver"]

        for part in mm_parts:
            if part in name:
                del j["query"]["name"]
                j["query"]["type"] = "Metamorph " + part

    # Set itemtype. TODO: change to allow similar items of other base types... Unless base matters...
    elif itype:
        j["query"]["type"] = itype

    if itype == "Prophecy":
        j["query"]["name"] = name

    # Only search for items online
    j["query"]["status"] = {}
    j["query"]["status"]["option"] = "online"

    # Set required links
    if links:
        if links >= 5:
            j["query"]["filters"]["socket_filters"] = {"filters": {"links": {"min": links}}}

    j["query"]["filters"]["misc_filters"] = {}
    j["query"]["filters"]["misc_filters"]["filters"] = {}

    # Set corrupted status
    if corrupted:
        j["query"]["filters"]["misc_filters"]["filters"]["corrupted"] = {"option": "true"}

    if gem_level:
        # Only used for skill gems
        j["query"]["filters"]["misc_filters"]["filters"]["gem_level"] = {
            "min": gem_level,
            "max": "null",
        }
        j["query"]["filters"]["misc_filters"]["filters"]["quality"] = {
            "min": quality,
            "max": "null",
        }

    # Set influenced status
    if influenced:
        if True in influenced.values():
            for influence in influenced:
                if influenced[influence]:
                    j["query"]["filters"]["misc_filters"]["filters"][influence + "_item"] = "true"

    if (
        name == itype or rarity == "Normal" or rarity == "Magic" or itype == "Metamorph"
    ) and ilvl != None:  # Unidentified item
        j["query"]["filters"]["misc_filters"]["filters"]["ilvl"] = {
            "min": ilvl - 3,
            "max": ilvl + 3,
        }

    fetch_called = False

    if DEBUG:
        print(j)
    # Find every stat
    if stats:
        j["query"]["stats"] = [{}]
        j["query"]["stats"][0]["type"] = "and"
        j["query"]["stats"][0]["filters"] = []
        for stat in stats:
            try:
                (proper_affix, value) = find_affix_match(stat)
                value = int(float(value) * 0.95)
            except NotImplementedError:
                # Can't find mod, move on
                continue
            affix_types = ["implicit", "crafted", "explicit", "enchantments"]
            if any(atype in proper_affix for atype in affix_types):  # If proper_affix is an actual mod...
                j["query"]["stats"][0]["filters"].append({"id": proper_affix, "value": {"min": value, "max": 999}})

        # Turn life + resists into pseudo-mods
        j = create_pseudo_mods(j)

    if DEBUG:
        print("FULL Query:", j)

    return j


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
                print(
                    f"[!] Take any values after this with a grain of salt. You should probably do a"
                    + Fore.RED
                    + " MANUAL search"
                )

            # Make the actual request.
            res = query_item(j, league)

            # No results found. Trim the mod list until we find results.
            if "result" in res:
                if (len(res["result"])) == 0:

                    # Choose a non-priority mod
                    i = choose_bad_mod(j)

                    # Tell the user which mod we are deleting
                    print(
                        "[-] Removing the"
                        + Fore.CYAN
                        + f" {stat_translate(i['id']).text} "
                        + Fore.WHITE
                        + "mod from the list due to"
                        + Fore.RED
                        + " no results found."
                    )

                    # Remove bad mod.
                    j["query"]["stats"][0]["filters"].remove(i)
                    num_stats_ignored += 1
                else:  # Found a result!
                    results = fetch(res)

                    if DEBUG:
                        print("Found results!")

                    if result_prices_are_none(results):
                        if DEBUG:
                            print("All resulting prices are none.")
                        # Choose a non-priority mod
                        i = choose_bad_mod(j)

                        # Tell the user which mod we are deleting
                        print(
                            "[-] Removing the"
                            + Fore.CYAN
                            + f" {stat_translate(i['id']).text} "
                            + Fore.WHITE
                            + "mod from the list due to"
                            + Fore.RED
                            + " no results found."
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


def create_pseudo_mods(j: Dict) -> Dict:
    """
    Combines life and resists into pseudo-mods

    Returns modified JSON #TODO change this to only modify the stats section of the JSON
    """
    # Combine life and resists for pseudo-stats
    total_ele_resists = 0
    total_chaos_resist = 0
    total_life = 0

    # TODO: Find a way to not hard-code
    # TODO: Support for attributes (including str->life), added phys to attacks, life regen
    solo_resist_ids = [
        "explicit.stat_3372524247",  # Explicit fire resist
        "explicit.stat_1671376347",  # Explicit lightning resist
        "explicit.stat_4220027924",  # Explicit cold resist
        "implicit.stat_3372524247",  # Implicit fire resist
        "implicit.stat_1671376347",  # Implicit lightning resist
        "implicit.stat_4220027924",  # Implicit cold resist
        "crafted.stat_3372524247",  # Crafted fire resist
        "crafted.stat_1671376347",  # Crafted lightning resist
        "crafted.stat_4220027924",  # Crafted cold resist
    ]

    dual_resist_ids = [
        "explicit.stat_2915988346",  # Explicit fire and cold resists
        "explicit.stat_3441501978",  # Explicit fire and lightning resists
        "explicit.stat_4277795662",  # Explicit cold and lightning resists
        "implicit.stat_2915988346",  # Implicit fire and cold resists
        "implicit.stat_3441501978",  # Implicit fire and lightning resists
        "implicit.stat_4277795662",  # Implicit cold and lightning resists
        "crafted.stat_2915988346",  # Crafted fire and cold resists
        "crafted.stat_3441501978",  # Crafted fire and lightning resists
        "crafted.stat_4277795662",  # Crafted cold and lightning resists
    ]

    triple_resist_ids = [
        "explicit.stat_2901986750",  # Explicit all-res
        "implicit.stat_2901986750",  # Implicit all-res
        "crafted.stat_2901986750",  # Crafted all-res
    ]

    solo_chaos_resist_ids = [
        "explicit.stat_2923486259",  # Explicit chaos resist
        "implicit.stat_2923486259",  # Implicit chaos resist
    ]

    dual_chaos_resist_ids = [
        "crafted.stat_378817135",  # Crafted fire and chaos resists
        "crafted.stat_3393628375",  # Crafted cold and chaos resists
        "crafted.stat_3465022881",  # Crafted lightning and chaos resists
    ]

    life_ids = [
        "explicit.stat_3299347043",  # Explicit maximum life
        "implicit.stat_3299347043",  # Implicit maximum life
    ]

    combined_filters = []

    # Solo elemental resists
    for i in j["query"]["stats"][0]["filters"]:
        if i["id"] in solo_resist_ids:
            total_ele_resists += int(i["value"]["min"])
            combined_filters.append(i)

        # Dual elemental resists
        elif i["id"] in dual_resist_ids:
            total_ele_resists += 2 * int(i["value"]["min"])
            combined_filters.append(i)

        # Triple elemental resists
        elif i["id"] in triple_resist_ids:
            total_ele_resists += 3 * int(i["value"]["min"])
            combined_filters.append(i)

        # Solo chaos resists
        elif i["id"] in solo_chaos_resist_ids:
            total_chaos_resist += int(i["value"]["min"])
            combined_filters.append(i)

        # Dual chaos resists
        elif i["id"] in dual_chaos_resist_ids:
            total_chaos_resist += int(i["value"]["min"])
            total_ele_resists += int(i["value"]["min"])
            combined_filters.append(i)

        # Maximum life
        elif i["id"] in life_ids:
            total_life += int(i["value"]["min"])
            combined_filters.append(i)

    # Round down to nearest 10 for combined stats (off by default)
    do_round = False
    if do_round:
        total_ele_resists = total_ele_resists - (total_ele_resists % 10)
        total_chaos_resist = total_chaos_resist - (total_chaos_resist % 10)
        total_life = total_life - (total_life % 10)

    # Remove stats that have been combined into psudo-stats
    j["query"]["stats"][0]["filters"] = [e for e in j["query"]["stats"][0]["filters"] if e not in combined_filters]

    if total_ele_resists > 0:
        j["query"]["stats"][0]["filters"].append(
            {"id": "pseudo.pseudo_total_elemental_resistance", "value": {"min": total_ele_resists, "max": 999},}
        )
        print(
            "[o] Combining the"
            + Fore.CYAN
            + f" elemental resistance "
            + Fore.WHITE
            + "mods from the list into a pseudo-parameter"
        )
        print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_ele_resists}% total Elemental Resistance (pseudo)")

    if total_chaos_resist > 0:
        j["query"]["stats"][0]["filters"].append(
            {"id": "pseudo.pseudo_total_chaos_resistance", "value": {"min": total_chaos_resist, "max": 999},}
        )
        print(
            "[o] Combining the"
            + Fore.CYAN
            + f" chaos resistance "
            + Fore.WHITE
            + "mods from the list into a pseudo-parameter"
        )
        print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_chaos_resist}% total Chaos Resistance (pseudo)")

    if total_life > 0:
        j["query"]["stats"][0]["filters"].append(
            {"id": "pseudo.pseudo_total_life", "value": {"min": total_life, "max": 999}}
        )
        print(
            "[o] Combining the"
            + Fore.CYAN
            + f" maximum life "
            + Fore.WHITE
            + "mods from the list into a pseudo-parameter"
        )
        print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_life} to maximum Life (pseudo)")

    return j


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

    print(f"[*] All values will be reported as their chaos, exalt, or mirror equivalent.")
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
        if DEBUG:
            print(def_json)

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
        print(
            "[+] Found mod " + Fore.GREEN + f"{text[0:]}: {value}"
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

    if DEBUG:
        print("AFFIX:", affix)

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
    return next(x for x in ITEM_MODIFIERS if x.id == jaffix)


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
        info = parse_item_info(text)
        trade_info = None
        json = None

        if info:
            # Uniques, only search by corrupted status, links, and name.

            if info["itype"] == "Currency":
                print(f'[-] Found currency {info["name"]} in clipboard')
                trade_info = query_exchange(info["name"])

            elif info["itype"] == "Divination Card":
                print(f'[-] Found Divination Card {info["name"]}')
                trade_info = query_exchange(info["name"])

            else:
                # Do intensive search.
                if info["itype"] != info["name"] and info["itype"] != None:
                    print(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {info['itype']}", flush=True)
                else:
                    extra_strings = ""
                    if info["rarity"] == "Gem":
                        extra_strings += f"Level: {info['gem_level']}+, "

                    if "corrupted" in info:
                        if info["corrupted"]:
                            extra_strings += "Corrupted: True, "

                    if info["quality"] != 0:
                        extra_strings += f"Quality: {info['quality']}+"

                    print(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {extra_strings}")

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
                        print_string += f"{prices[price_dict]} x " + Fore.YELLOW + f"{pretty_price}" + Fore.WHITE + ", "
                        total_count += prices[price_dict]

                    # Print the pretty string, ignoring trailing comma
                    print(f"[$] Price: {print_string[:-2]}\n\n")
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
                        print(f"[$] Price: {Fore.YELLOW}{price} \n\n")
                        time = datetime.now(timezone.utc) - datetime.replace(
                            datetime.strptime(trade_info[0]["listing"]["indexed"], "%Y-%m-%dT%H:%M:%SZ"),
                            tzinfo=timezone.utc,
                        )
                        time = [[time.days, time.seconds]]
                        price_vals = [[str(price_val) + price_curr]]

                        print("[!] Not enough data to confidently price this item.")
                        if config.USE_GUI:
                            gui.show_price(price, price_vals, time, True)
                    else:
                        print(f"[$] Price: {Fore.YELLOW}None \n\n")
                        print("[!] Not enough data to confidently price this item.")
                        if config.USE_GUI:
                            gui.show_not_enough_data()

            elif trade_info is not None:
                print("[!] No results!")
                if config.USE_GUI:
                    gui.show_not_enough_data()

    except NotFoundException as e:
        print("[!] No results!")
        if config.USE_GUI:
            gui.show_not_enough_data()

    except InvalidAPIResponseException as e:
        print(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW ==================")
        print(
            f"[!] Failed to parse response from POE API. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        print(f"{Fore.GREEN}================== START ISSUE DATA ==================")
        print(f"{Fore.GREEN}Title:")
        print("Failed to query item from trade API.")
        print(f"{Fore.GREEN}Body:")
        print("Macro failed to lookup item from POE trade API. Here is the item in question.")
        print("====== ITEM DATA=====")
        print(f"{text}")
        print(f"{Fore.GREEN}================== END ISSUE DATA ==================")
        print(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE ==================")

    except Exception as e:
        exception = traceback.format_exc()
        print(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS BELOW ==================")
        print(
            f"[!] Something went horribly wrong. If this error occurs again please open an issue at {PROJECT_URL}issues with the info below"
        )
        print(f"{Fore.GREEN}================== START ISSUE DATA ==================")
        print(f"{Fore.GREEN}Title:")
        print("Failed to query item from trade API.")
        print(f"{Fore.GREEN}Body:")
        print("Here is the item in question.")
        print("====== ITEM DATA=====")
        print(f"{text}")
        print("====== TRACEBACK =====")
        print(exception)
        print(f"{Fore.GREEN}================== END ISSUE DATA ==================")
        print(f"{Fore.RED}================== LOOKUP FAILED, PLEASE READ INSTRUCTIONS ABOVE ==================")
        print(exception)


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
    print("[*] Watching clipboard (Ctrl+C to stop)...")
    keyboard.clipboard_callback = lambda _: hotkey_handler(keyboard, "clipboard")
    keyboard.start()


def search_ninja_base(text):
    info = parse_item_info(text)
    influence = None
    if any(i == True for i in info["influenced"].values()):
        if info["influenced"]["shaper"]:
            influence = "shaper"
        elif info["influenced"]["elder"]:
            influence = "elder"
        elif info["influenced"]["crusader"]:
            influence = "crusader"
        elif info["influenced"]["warlord"]:
            influence = "warlord"
        elif info["influenced"]["redeemer"]:
            influence = "redeemer"
        elif info["influenced"]["hunter"]:
            influence = "hunter"

    ilvl = info["ilvl"] if info["ilvl"] >= 84 else 84

    base = info["itype"] if info["itype"] != None else info["base"]

    print(f"[*] Searching for base {base}. Item Level: {ilvl}, Influence: {influence}")
    result = None
    try:
        result = next(
            item
            for item in NINJA_BASES
            if (
                item["base"] == base
                and (
                    (influence == None and item["influence"] == None)
                    or (influence != None and item["influence"] != None and influence == item["influence"].lower())
                )
                and ilvl == item["ilvl"]
            )
        )
    except StopIteration:
        print("[!] Could not find the requested item.")
        if config.USE_GUI:
            gui.show_not_enough_data()

    if result != None:
        price = result["exalt"] if result["exalt"] >= 1 else result["chaos"]
        currency = "ex" if result["exalt"] >= 1 else "chaos"
        print(f"[$] Price: {price} {currency}")
        if config.USE_GUI:
            gui.show_base_result(base, influence, ilvl, price, currency)

def hotkey_handler(keyboard, hotkey):
    # Without this block, the clipboard's contents seem to always be from 1 before the current
    if hotkey != "clipboard":
        keyboard.press_and_release("ctrl+c")
        time.sleep(0.1)

    text = get_clipboard()
    if hotkey == "alt+t":
        info = parse_item_info(text)
        j = build_json_official(
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
        res = query_item(j, LEAGUE)
        open_trade_site(res["id"], LEAGUE)

    elif hotkey == "alt+w":
        info = parse_item_info(text)
        wiki_lookup(text, info)

    elif hotkey == "alt+c":
        search_ninja_base(text)

    else:  # alt+d, ctrl+c
        price_item(text)


# This is necessary to do Unit Testing, needs to be GLOBAL
ITEM_MODIFIERS: Optional[Tuple[ItemModifier, ...]] = get_item_modifiers()

def create_gui():
    global gui
    from utils.gui import Gui
    gui = Gui()
    gui.wait()

if __name__ == "__main__":
    find_latest_update()

    init(autoreset=True)  # Colorama
    # Get some basic setup stuff
    print(f"[*] Loaded {len(ITEM_MODIFIERS)} item mods.")
    valid_leagues = get_leagues()

    NINJA_BASES = get_ninja_bases()
    print(f"[*] Loaded {len(NINJA_BASES)} bases and their prices.")

    # Inform user of choices
    print(f"If you wish to change the selected league you may do so in settings.cfg.")
    print(f"Valid league values are {Fore.MAGENTA}{', '.join(valid_leagues)}.")

    if LEAGUE not in valid_leagues:
        print(f"Unable to locate {LEAGUE}, please check settings.cfg.")
    else:
        print(f"All values will be from the {Fore.MAGENTA}{LEAGUE} league")
        keyboard = Keyboard()
        watch_keyboard(keyboard, USE_HOTKEYS)

        try:
            if config.USE_GUI:
                create_gui()
            else:
                keyboard.wait()
        except KeyboardInterrupt:
            pass

        print(f"[!] Exiting, user requested termination.")

        # Apparently things go bad if we don't call this, so here it is!
        deinit()  # Colorama

