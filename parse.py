import logging
import sys
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
from models.Item import (
    Item,
    Exchangeable,
    Map,
    Prophecy,
    Fragment,
    Organ,
    Flask,
    Currency,
    Card,
    Gem,
)
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
    get_item_modifiers_by_text,
    get_item_modifiers_by_id,
    get_leagues,
    get_ninja_bases,
    query_item,
)
from utils.web import open_trade_site, wiki_lookup

def parse_item_info(text: str) -> Item:
    """
    Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
    """
    # TODO: test if poe item
    # TODO: synthesis items -> Item class
    # TODO: stats
    # TODO: handle veiled items (not veiled mods, these are handled) e.g. Veiled Prefix

    item_list = text.split('--------')
    for i, region in enumerate(item_list):
        item_list[i] = region.strip().splitlines()

    # Remove the Note region; this is always located on the last line.
    if item_list[-1][0].startswith("Note:"):
        del item_list[-1]

    rarity = item_list[0][0][8:].lower()
    name = re.sub(r'<<set:M?S?>>', '', item_list[0][1])

    quality = 0
    for line in item_list[1]:
        if line.startswith('Quality'):
            quality = int(line[line.find('+')+1:-13])
            break

    influence = []
    ilevel = 0
    modifiers = []
    corrupted = False
    base = None
    if len(item_list[0]) == 3:
        base = item_list[0][2]
    #base = name if rarity == 'normal' and len(item_list[0]) == 2 else item_list[0][2]
    raw_sockets = ''
    mirrored = False

    iiq = None
    iir = None
    pack_size = None

    item_class = Item

    # TODO: Maybe use this instead of if/elif massive branches?
    special_types = {
        'Right-click to add this prophecy to your character.': Prophecy,
        'Can be used in a personal Map Device.': Fragment,
        "Combine this with four other different samples in Tane's Laboratory.": Organ,
        'Right click to drink. Can only hold charges while in belt. Refills as you kill monsters.': Flask,
        'Travel to this Map by using it in a personal Map Device. Maps can only be used once.': Map
    }

    # This will only be used to temporarily store organ modifiers in,
    # because we need to sort them and count them to provide the proper
    # values for them.
    organ_modifiers = []

    for region in item_list:
        if region[0] in special_types:
            item_class = special_types[region[0]]
            break

    for region in item_list:
        first_line = region[0]
        if first_line.startswith('Requirements:'):
            continue  # we ignore this for pricing
        elif rarity == 'currency':
            return Currency(rarity=rarity, name=name)
        elif rarity == 'divination card':
            return Card(rarity=rarity, name=name)
        elif rarity == 'gem':
            level = [
                int(line.replace(' (Max)', '')[7:]) for line in item_list[1]
                if line.startswith('Level')
            ][0]
            corrupted = item_list[-1] == ['Corrupted']
            return Gem(rarity=rarity, name=name, quality=quality,
                       ilevel=level, corrupted=corrupted)
        elif first_line.startswith('Sockets'):
            raw_sockets = first_line.lstrip('Sockets: ')
        elif first_line == 'Corrupted':
            corrupted = True
        elif first_line == 'Mirrored':
            mirrored = True
        elif first_line.startswith('Item Level'):
            ilevel = first_line.lstrip('Item Level: ')
        elif first_line.count(' ') == 1 and first_line.endswith('Item'):
            for line in item_list[-1]:
                influence.append(line.strip(' Item').lower())
        elif first_line.startswith('Allocates'):
            for line in region:
                mod_value = line.lstrip('Allocates ')
                element = ('Allocates #', ItemModifierType.ENCHANT)
                mod = get_item_modifiers_by_text(element)
                modifiers.append((mod, mod_value))
        elif first_line == "Travel to this Map by using it in a personal Map Device. Maps can only be used once.":
            tier = int(item_list[1][0][10:])
            corrupted = item_list[-1][0] == 'Corrupted'

            augmented = [
                e.replace(" (augmented)", "").replace('+', '').replace('%', '')
                for e in item_list[1]
            ]

            # Parse out map-specific augmented fields.
            for aug in augmented:
                if aug.startswith("Item Quantity: "):
                    iiq = int(aug.lstrip("Item Quantity: "))
                elif aug.startswith("Item Rarity: "):
                    iir = int(aug.lstrip("Item Rarity: "))
                elif aug.startswith("Monster Pack Size: "):
                    pack_size = int(aug.lstrip("Monster Pack Size: "))

            item_class = Map

        elif first_line == 'Right-click to add this prophecy to your character.':
            return Prophecy(rarity=rarity, name=name)
        elif first_line.startswith('Can be used in a personal Map Device.'):
            return Fragment(rarity=rarity, name=name)
        elif first_line.startswith("Combine this with four other different samples in Tane's Laboratory."):
            item_class = Organ
        elif first_line.endswith('Right click to drink. Can only hold charges while in belt. Refills as you kill monsters.'):
            item_class = Flask
        else:
            for line in region:
                # Match all mods containing (+|-)<number> or The Shaper,
                # The Elder, etc. These should all be implicits.
                matches = re.findall(r'([+-]|The )?(\d+|Shaper|Elder|Constrictor|Enslaver|Eradicator|Purifier)', line)

                # First, glue together mods we find in case we encounter + or -
                # Then, join them into a string separated by ','
                mod_value = ','.join([''.join(m) for m in matches])
                mod_text = re.sub(r'([+-]|The )?(\d+|Shaper|Elder|Constrictor|Enslaver|Eradicator|Purifier)', '#', line)

                # If we were unable to substitute above, we have a mod without
                # these qualities. Attempt to match the mod straight up.
                if not mod_text:
                    mod_text = line

                logging.debug("Parsing %s" % line)
                if " (implicit)" in mod_text:
                    item_type = ItemModifierType.IMPLICIT
                    mod_text = mod_text[:-11]
                    logging.debug("Figuring out if '%s' is an implicit mod" % mod_text)
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Implicit matched")
                        modifiers.append((mod, mod_value))
                    else:
                        logging.debug("No implicit match")
                elif " (crafted)" in mod_text:
                    item_type = ItemModifierType.CRAFTED
                    logging.debug("Figuring out if '%s' is a crafted mod" % mod_text)
                    mod_text = mod_text[:-10]
                    logging.debug("Figuring out if '%s' is a crafted mod" % mod_text)
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Crafted matched")
                        modifiers.append((mod, mod_value))
                    else:
                        logging.debug("No crafted match")
                else:
                    logging.debug("Figuring out if '%s' is an enchant" % str(mod_text))
                    # First, try to match an enchant mod
                    item_type = ItemModifierType.ENCHANT
                    if not mod_value: # trigger X on kill\hit mods
                        mod_text = '#% chance to ' + mod_text
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Enchant matched")
                        modifiers.append((mod, mod_value))
                    # Else, if we're not on a map, try to match an explicit mod
                    else:
                        if not mod:
                            raw_text = line
                        logging.debug("Figuring out if '%s' is an explicit" % str(mod_text))
                        item_type = ItemModifierType.EXPLICIT
                        mod = get_item_modifiers_by_text((raw_text, item_type))

                        if not mod:
                            mod = get_item_modifiers_by_text((mod_text, item_type))

                        # Try again with (Local) if the previous mod didn't match
                        if mod is None:
                            altered = mod_text + " (Local)"
                            mod = get_item_modifiers_by_text((altered, item_type))

                        if mod is not None:
                            logging.debug("Explicit matched")
                            modifiers.append((mod, mod_value))
                        elif 'reduced' in mod_text or 'increased' in mod_text:
                            [orig] = [x for x in ('reduced', 'increased') if x in line]
                            target = 'reduced' if orig == 'increased' else 'increased'

                            # In the case where we have "reduced" inside of the
                            # modifier, it could be a negative value of an
                            # "increased" modifier. Therefore, since we found no
                            # matches originally, we try again by replacing text.
                            # If the "increased" version matches, we add a negative
                            # sign in front of the mod_value.
                            # Example: 18% reduced Required Attributes is really
                            # #% increased Required Attributes with a mod_value
                            # of -18.
                            # This implementation addition fixes mods we could
                            # not earlier find in these cases.
                            altered = mod_text.replace(orig, target)
                            mod = get_item_modifiers_by_text((altered, item_type))
                            if mod:
                                mod_value = '-' + mod_value
                                modifiers.append((mod, mod_value))
                            else:
                                logging.debug("No explicit matched")
                        else:
                            logging.debug("No explicit matched")

                        # Metamorph Organ modifiers
                        logging.debug("Modifier class: %s" % str(item_class))
                        if item_class == Organ:
                            logging.debug("Attempting to determine if '%s' is an organ modifier" % line)
                            item_type = ItemModifierType.MONSTER
                            text = line.lstrip(' ').rstrip(' ') + " (\u00d7#)"
                            mod = get_item_modifiers_by_text((text, item_type))
                            if mod:
                                logging.debug("Adding %s to organ_modifiers" % str(mod))
                                organ_modifiers.append(mod)

    organ_mod_counts = dict()
    if len(organ_modifiers) > 0:
        for mod in organ_modifiers:
            if mod in organ_mod_counts:
                organ_mod_counts[mod] += 1
            else:
                organ_mod_counts[mod] = 1

    for mod, mod_value in organ_mod_counts.items():
        modifiers.append((mod, str(mod_value)))

    def produce_map():
        return Map(rarity=rarity, name=name, base=base, quality=quality,
                   ilevel=tier, corrupted=corrupted, modifiers=modifiers,
                   iiq=iiq, iir=iir, pack_size=pack_size)

    other_types = {
        Map: produce_map
    }

    if item_class in other_types:
        f = other_types[item_class]
        return f()

    return item_class(rarity=rarity, name=name, base=base, quality=quality,
                      stats=[], raw_sockets=raw_sockets, ilevel=ilevel,
                      modifiers=modifiers, corrupted=corrupted,
                      mirrored=mirrored, influence=influence)

# We should not have to worry about influences for map mods, as
# we now know they are provided as implicits and can be searched
# via stats like an item is normally.

#        iiq_re = re.findall(r"Item Quantity: \+(\d+)%", text)
#        if len(iiq_re) > 0:
#            map_mods["iiq"] = iiq_re[0]

#        pack_re = re.findall(r"Pack Size: \+(\d+)%", text)
#        if len(pack_re) > 0:
#            map_mods["pack"] = pack_re[0]

#        iir_re = re.findall(r"Item Rarity: \+(\d+)%", text)
#        if len(iir_re) > 0:
#            map_mods["iir"] = iir_re[0]

#        map_mods["blight"] = bool(re.search(r"Blighted", text, re.M))
#        map_mods["shaper"] = bool(re.search("Area is influenced by The Shaper", text, re.M))
#        map_mods["elder"] = bool(re.search("Area is influenced by The Elder", text, re.M))
#        map_mods["enslaver"] = bool(re.search("Map is occupied by The Enslaver", text, re.M))
#        map_mods["eradicator"] = bool(re.search("Map is occupied by The Eradicator", text, re.M))
#        map_mods["constrictor"] = bool(re.search("Map is occupied by The Constrictor", text, re.M))
#        map_mods["purifier"] = bool(re.search("Map is occupied by The Purifier", text, re.M))

#        info["maps"] = map_mods

'''
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

    # Log out query json, without stats
    logging.debug(j)

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

    logging.debug("FULL Query:", j)
    return j
'''

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
                logging.info(
                    f"[!] Take any values after this with a grain of salt. You should probably do a"
                    + Fore.RED
                    + " MANUAL search"
                    + Fore.RESET
                )

            # Make the actual request.
            res = query_item(j, league)

            # No results found. Trim the mod list until we find results.
            if "result" in res:
                if (len(res["result"])) == 0:

                    # Choose a non-priority mod
                    i = choose_bad_mod(j)

                    # Tell the user which mod we are deleting
                    logging.info(
                        "[-] Removing the"
                        + Fore.CYAN
                        + f" {stat_translate(i['id']).text}"
                        + Fore.RESET
                        + " mod from the list due to "
                        + Fore.RED
                        + "no results found."
                        + Fore.RESET
                    )

                    # Remove bad mod.
                    j["query"]["stats"][0]["filters"].remove(i)
                    num_stats_ignored += 1
                else:  # Found a result!
                    results = fetch(res)
                    logging.debug("Found results!")

                    if result_prices_are_none(results):
                        logging.debug("All resulting prices are none.")
                        # Choose a non-priority mod
                        i = choose_bad_mod(j)

                        # Tell the user which mod we are deleting
                        logging.info(
                            "[-] Removing the "
                            + Fore.CYAN
                            + f"{stat_translate(i['id']).text}"
                            + Fore.RESET
                            + " mod from the list due to "
                            + Fore.RED
                            + "no results found."
                            + Fore.RESET
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
        logging.info(
            "[o] Combining the "
            + Fore.CYAN
            + f"elemental resistance"
            + Fore.RESET
            + " mods from the list into a pseudo-parameter"
        )
        logging.info(
            "[+] Pseudo-mod "
            + Fore.GREEN
            + f"+{total_ele_resists}% total Elemental Resistance (pseudo)"
            + Fore.RESET
        )

    if total_chaos_resist > 0:
        j["query"]["stats"][0]["filters"].append(
            {"id": "pseudo.pseudo_total_chaos_resistance", "value": {"min": total_chaos_resist, "max": 999},}
        )
        logging.info(
            "[o] Combining the "
            + Fore.CYAN
            + f"chaos resistance"
            + Fore.RESET
            + " mods from the list into a pseudo-parameter"
        )
        logging.info("[+] Pseudo-mod " + Fore.GREEN + f"+{total_chaos_resist}% total Chaos Resistance (pseudo)")

    if total_life > 0:
        j["query"]["stats"][0]["filters"].append(
            {"id": "pseudo.pseudo_total_life", "value": {"min": total_life, "max": 999}}
        )
        logging.info(
            "[o] Combining the "
            + Fore.CYAN
            + f"maximum life"
            + Fore.RESET
            + " mods from the list into a pseudo-parameter"
        )
        logging.info(
            "[+] Pseudo-mod "
            + Fore.GREEN
            + f"+{total_life} to maximum Life (pseudo)"
            + Fore.RESET
        )

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

    logging.info(f"[*] All values will be reported as their chaos, exalt, or mirror equivalent.")
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
        logging.debug(def_json)

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
        logging.info(
            "[+] Found mod " + Fore.GREEN + f"{text[0:]}: {value}" + Fore.RESET
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

    logging.debug("AFFIX:", affix)

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
    return get_item_modifiers_by_id(jaffix)


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
        item = parse_item_info(text)
        item = item.deduce_specific_object()
        item.sanitize_modifiers()

        json = item.get_json()
        logging.debug("json query: %s" % str(json))

        query_url = item.query_url("Metamorph")
        response = requests.post(query_url, json=json)
        logging.debug("json response: %s" % str(response.json()))

        response_json = response.json()
        fetched = fetch(response_json, isinstance(item, Exchangeable))
        logging.debug("Fetched: %s" % str(fetched))

        trade_info = fetched
        logging.debug("Found %d items" % len(trade_info))
        '''
        if info:
            # Uniques, only search by corrupted status, links, and name.

            if info["itype"] == "Currency":
                logging.info(f'[-] Found currency {info["name"]} in clipboard')
                trade_info = query_exchange(info["name"])

            elif info["itype"] == "Divination Card":
                logging.info(f'[-] Found Divination Card {info["name"]}')
                trade_info = query_exchange(info["name"])

            else:
                # Do intensive search.
                if info["itype"] != info["name"] and info["itype"] != None:
                    logging.info(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {info['itype']}", flush=True)
                else:
                    extra_strings = ""
                    if info["rarity"] == "Gem":
                        extra_strings += f"Level: {info['gem_level']}+, "

                    if "corrupted" in info:
                        if info["corrupted"]:
                            extra_strings += "Corrupted: True, "

                    if info["quality"] != 0:
                        extra_strings += f"Quality: {info['quality']}+"

                    logging.info(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {extra_strings}")

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
        '''
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
                    print_string += f"{prices[price_dict]} x " + Fore.YELLOW + f"{pretty_price}" + Fore.RESET + ", "
                    total_count += prices[price_dict]

                # Print the pretty string, ignoring trailing comma
                logging.info(f"[$] Price: {print_string[:-2]}\n\n")
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
                    logging.info(f"[$] Price: {Fore.YELLOW}{price}{Fore.RESET} \n\n")
                    time = datetime.now(timezone.utc) - datetime.replace(
                        datetime.strptime(trade_info[0]["listing"]["indexed"], "%Y-%m-%dT%H:%M:%SZ"),
                        tzinfo=timezone.utc,
                    )
                    time = [[time.days, time.seconds]]
                    price_vals = [[str(price_val) + price_curr]]

                    logging.info("[!] Not enough data to confidently price this item.")
                    if config.USE_GUI:
                        gui.show_price(price, price_vals, time, True)
                else:
                    logging.info(f"[$] Price: {Fore.YELLOW}None{Fore.RESET} \n\n")
                    logging.info("[!] Not enough data to confidently price this item.")
                    if config.USE_GUI:
                        gui.show_not_enough_data()

        elif trade_info is not None:
            logging.info("[!] No results!")
            if config.USE_GUI:
                gui.show_not_enough_data()

    except NotFoundException as e:
        logging.info("[!] No results!")
        if config.USE_GUI:
            gui.show_not_enough_data()

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
    logging.info("[*] Watching clipboard (Ctrl+C to stop)...")
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

    logging.info(f"[*] Searching for base {base}. Item Level: {ilvl}, Influence: {influence}")
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
        logging.error("[!] Could not find the requested item.")
        if config.USE_GUI:
            gui.show_not_enough_data()

    if result != None:
        price = result["exalt"] if result["exalt"] >= 1 else result["chaos"]
        currency = "ex" if result["exalt"] >= 1 else "chaos"
        logging.info(f"[$] Price: {price} {currency}")
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

def create_gui():
    global gui
    from utils.gui import Gui
    gui = Gui()
    gui.wait()

if __name__ == "__main__":
    loglevel = logging.INFO
    if len(sys.argv) > 1 and sys.argv[1] in ("-d", "--debug"):
        loglevel = logging.DEBUG
    logging.basicConfig(format="%(message)s", level=loglevel)

    find_latest_update()

    init(autoreset=True)  # Colorama
    # Get some basic setup stuff
    valid_leagues = get_leagues()

    NINJA_BASES = get_ninja_bases()
    logging.info(f"[*] Loaded {len(NINJA_BASES)} bases and their prices.")

    # Inform user of choices
    logging.info(f"If you wish to change the selected league you may do so in settings.cfg.")
    logging.info(f"Valid league values are {Fore.MAGENTA}{', '.join(valid_leagues)}{Fore.RESET}.")

    if LEAGUE not in valid_leagues:
        logging.error(f"Unable to locate {LEAGUE}, please check settings.cfg.")
    else:
        logging.info(f"All values will be from the {Fore.MAGENTA}{LEAGUE}{Fore.RESET} league")
        keyboard = Keyboard()
        watch_keyboard(keyboard, USE_HOTKEYS)

        try:
            if config.USE_GUI:
                create_gui()
            else:
                keyboard.wait()
        except KeyboardInterrupt:
            pass

        logging.info(f"[!] Exiting, user requested termination.")

        # Apparently things go bad if we don't call this, so here it is!
        deinit()  # Colorama

