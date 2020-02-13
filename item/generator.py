import re

from colorama import Fore

from item.itemModifier import ItemModifierType
from utils.config import LEAGUE
from utils.currency import currency_global
from utils.web import (
    get_base,
    get_item_modifiers_by_id,
    get_item_modifiers_by_text,
    get_ninja_bases,
)


class BaseItem:
    def __init__(self, name):
        self.name = name
        self.online = "online"

    def set_offline(self):
        self.online = "any"

    def print(self):
        print("[!] Found: ", self.name)

    def get_json(self):
        json = {
            "query": {
                "status": {"option": self.online},
                "filters": {
                    "misc_filters": {"filters": {}},
                    "type_filters": {"filters": {}},
                    "socket_filters": {
                        "filters": {"sockets": {}, "links": {}},
                    },
                },
                "stats": [{"type": "and", "filters": []}],
            },
            "sort": {"price": "asc"},
        }
        return json

    def add_mods(self, json, modifiers):
        mods = []
        for e in modifiers:
            if e[1]:
                if e[0].id == 'enchant.stat_2954116742':
	                mods.append({ "id": e[0].id, "value": { "option": e[1] }})
                else:
                    try:
                        if float(e[1]) < 0:
                            mods.append(
                                {"id": e[0].id, "value": {"max": float(e[1])}}
                            )
                        else:
                            mods.append(
                                {"id": e[0].id, "value": {"min": float(e[1])}}
                            )
                    except ValueError:
                        if e[1]:
                            mods.append({"id": e[0].id, "value": {"option": e[1]}})
            else:
                mods.append({"id": e[0].id})
        json["query"]["stats"][0]["filters"] = mods
        return json

    def create_pseudo_mods(self):
        pass

    def relax_modifiers(self):
        pass

    def remove_bad_mods(self):
        pass

    def set_name(self, json, name):
        json["query"]["name"] = name
        return json

    def set_type(self, json, item_type):
        json["query"]["type"] = item_type
        return json

    def set_ilevel(self, json, ilevel):
        json["query"]["filters"]["misc_filters"]["filters"]["ilvl"] = {
            "min": ilevel
        }
        return json

    def set_quality(self, json, quality):
        json["query"]["filters"]["misc_filters"]["filters"]["quality"] = {
            "min": quality
        }
        return json

    def set_rarity(self, json, rarity):
        json["query"]["filters"]["type_filters"]["filters"]["rarity"] = {
            "option": rarity
        }
        return json

    def set_category(self, json, category):
        json["query"]["filters"]["type_filters"]["filters"]["category"] = {
            "option": category
        }
        return json

    def set_influence(self, json, influences):
        for influence in influences:
            text = "%s_item" % influence
            json["query"]["filters"]["misc_filters"]["filters"][text] = {
                "option": "true"
            }
        return json


class Item(BaseItem):
    def __init__(
        self,
        name,
        base,
        category,
        rarity,
        quality,
        ilevel,
        mods,
        sockets,
        influence,
        identified,
        corrupted,
        mirrored,
        veiled,
        synthesised,
    ):
        super().__init__(name)
        self.rarity = rarity
        self.quality = quality
        self.base = base
        self.category = category
        self.ilevel = ilevel
        self.mods = mods
        self.sockets = sockets
        self.influence = influence
        self.identified = identified
        self.corrupted = corrupted
        self.mirrored = mirrored
        self.veiled = veiled
        self.synthesised = synthesised

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Item Level] {self.ilevel}")
        print(f"[Quality] {self.quality}")
        for mod in self.mods:
            if mod[1]:
                print(
                    f"[Mod] {mod[0].text}: [{Fore.YELLOW}{mod[1]}{Fore.RESET}]"
                )
            else:
                print(f"[Mod] {mod[0].text}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.base)
        json = self.set_rarity(json, self.rarity)
        json = self.set_ilevel(json, self.ilevel)
        json = self.set_category(json, self.category)
        json = self.set_quality(json, self.quality)
        json = self.set_influence(json, self.influence)
        json = self.add_mods(json, self.mods)

        json["query"]["filters"]["misc_filters"]["filters"][
            "synthesised_item"
        ] = {"option": self.synthesised}
        json["query"]["filters"]["misc_filters"]["filters"]["corrupted"] = {
            "option": self.corrupted
        }
        json["query"]["filters"]["misc_filters"]["filters"]["mirrored"] = {
            "option": self.mirrored
        }
        json["query"]["filters"]["misc_filters"]["filters"]["veiled"] = {
            "option": self.veiled
        }
        json["query"]["filters"]["misc_filters"]["filters"]["identified"] = {
            "option": self.identified
        }

        if self.sockets:
            sockets = self.sockets.lower()
            r_sockets = sockets.count("r")
            b_sockets = sockets.count("b")
            g_sockets = sockets.count("g")
            w_sockets = sockets.count("w")
            a_sockets = sockets.count("a")
            links = sockets.count("-") - sockets.count(" ") + 1
            sockets = r_sockets + b_sockets + g_sockets + w_sockets + a_sockets

            json["query"]["filters"]["socket_filters"]["filters"]
            if sockets == 6:
                json["query"]["filters"]["socket_filters"]["filters"][
                    "sockets"
                ] = {"min": 6}

            # If we have 5 or more links, we'll include that in the query
            if links >= 5:
                json["query"]["filters"]["socket_filters"]["filters"][
                    "links"
                ] = {"min": links}

        if self.rarity == "unique" and self.identified:
            json = self.set_name(json, self.name.replace(" " + self.base, ""))

        return json

    def create_pseudo_mods(self):
        if self.rarity == "unique":
            return

        # Combine life and resists for pseudo-stats
        total_ele_resists = 0
        total_chaos_resist = 0
        total_life = 0

        solo_resist_ids = {
            "explicit.stat_3372524247",  # Explicit fire resist
            "explicit.stat_1671376347",  # Explicit lightning resist
            "explicit.stat_4220027924",  # Explicit cold resist
            "implicit.stat_3372524247",  # Implicit fire resist
            "implicit.stat_1671376347",  # Implicit lightning resist
            "implicit.stat_4220027924",  # Implicit cold resist
            "crafted.stat_3372524247",  # Crafted fire resist
            "crafted.stat_1671376347",  # Crafted lightning resist
            "crafted.stat_4220027924",  # Crafted cold resist
        }

        dual_resist_ids = {
            "explicit.stat_2915988346",  # Explicit fire and cold resists
            "explicit.stat_3441501978",  # Explicit fire and lightning resists
            "explicit.stat_4277795662",  # Explicit cold and lightning resists
            "implicit.stat_2915988346",  # Implicit fire and cold resists
            "implicit.stat_3441501978",  # Implicit fire and lightning resists
            "implicit.stat_4277795662",  # Implicit cold and lightning resists
            "crafted.stat_2915988346",  # Crafted fire and cold resists
            "crafted.stat_3441501978",  # Crafted fire and lightning resists
            "crafted.stat_4277795662",  # Crafted cold and lightning resists
        }

        triple_resist_ids = {
            "explicit.stat_2901986750",  # Explicit all-res
            "implicit.stat_2901986750",  # Implicit all-res
            "crafted.stat_2901986750",  # Crafted all-res
        }

        solo_chaos_resist_ids = {
            "explicit.stat_2923486259",  # Explicit chaos resist
            "implicit.stat_2923486259",  # Implicit chaos resist
        }

        dual_chaos_resist_ids = {
            "crafted.stat_378817135",  # Crafted fire and chaos resists
            "crafted.stat_3393628375",  # Crafted cold and chaos resists
            "crafted.stat_3465022881",  # Crafted lightning and chaos resists
        }

        life_ids = {
            "explicit.stat_3299347043",  # Explicit maximum life
            "implicit.stat_3299347043",  # Implicit maximum life
            "crafted.stat_3299347043",  # Crafted maximum life
        }

        nMods = []
        for mod in self.mods:

            if mod[0].id in solo_resist_ids:
                total_ele_resists += float(mod[1])
            elif mod[0].id in dual_resist_ids:
                total_ele_resists += 2 * float(mod[1])
            elif mod[0].id in triple_resist_ids:
                total_ele_resists += 3 * float(mod[1])
            elif mod[0].id in solo_chaos_resist_ids:
                total_chaos_resist += float(mod[1])
            elif mod[0].id in dual_chaos_resist_ids:
                total_ele_resists += float(mod[1])
                total_chaos_resist += float(mod[1])
            elif mod[0].id in life_ids:
                total_life += float(mod[1])
            else:
                nMods.append(mod)
        self.mods = nMods

        if total_ele_resists > 0:
            mod = (
                get_item_modifiers_by_id(
                    "pseudo.pseudo_total_elemental_resistance"
                ),
                total_ele_resists,
            )
            self.mods.append(mod)
            print(
                "[o] Combining the "
                + Fore.CYAN
                + f"elemental resistance"
                + Fore.RESET
                + " mods from the list into a pseudo-parameter"
            )
            print(
                "[+] Pseudo-mod "
                + Fore.GREEN
                + f"+{total_ele_resists}% total Elemental Resistance (pseudo)"
                + Fore.RESET
            )

        if total_chaos_resist > 0:
            mod = (
                get_item_modifiers_by_id(
                    "pseudo.pseudo_total_chaos_resistance"
                ),
                total_chaos_resist,
            )
            self.mods.append(mod)
            print(
                "[o] Combining the "
                + Fore.CYAN
                + f"chaos resistance"
                + Fore.RESET
                + " mods from the list into a pseudo-parameter"
            )
            print(
                "[+] Pseudo-mod "
                + Fore.GREEN
                + f"+{total_chaos_resist}% total Chaos Resistance (pseudo)"
            )

        if total_life > 0:
            mod = (
                get_item_modifiers_by_id("pseudo.pseudo_total_life"),
                total_life,
            )
            self.mods.append(mod)
            print(
                "[o] Combining the "
                + Fore.CYAN
                + f"maximum life"
                + Fore.RESET
                + " mods from the list into a pseudo-parameter"
            )
            print(
                "[+] Pseudo-mod "
                + Fore.GREEN
                + f"+{total_life} to maximum Life (pseudo)"
                + Fore.RESET
            )

    def relax_modifiers(self):
        if self.rarity == "unique":  # dont do this on uniques
            return
        nMods = []
        for mod in self.mods:
            if mod[0].type == ItemModifierType.ENCHANT:
                nMods.append(mod)
                continue
            try:
                n = (mod[0], float(mod[1]) - (float(mod[1]) * 0.1))
                nMods.append(n)
            except ValueError:
                nMods.append(mod)
        self.mods = nMods

    def remove_bad_mods(self):

        # TODO Add more, move to config ( config parse does not support multiple lines atm, prob need to write a custom one)
        bad_mod_list = [
            "Physical Attack Damage Leeched as Life",
            "to maximum Mana",
            "Life gained for each Enemy hit by Attacks",
            "of Physical Attack Damage Leeched as Mana",
            "increased Mana Regeneration Rate",
            "Life gained on Kill",
            "Mana gained on Kill",
            "Reflects # Physical Damage to Melee Attackers",
            "Life gained for each Enemy hit by Attacks",
            "to Armour",
            "increased Rarity of Items found",
            "increased Stun Duration",
            "Regenerate",
            "Regeneration",
            "increased Stun and Block Recovery",
            "Minions have",
            "additional Physical Damage Reduction against Abyssal Monsters",
            "reduced Enemy Stun Threshold",
            "increased Damage against Abyssal Monsters",
            "increased Movement Speed if you haven't taken Damage Recently",
            "increased Projectile Speed",
        ]

        nMods = []
        found = False
        for mod in self.mods:
            for bad in bad_mod_list:
                if bad in mod[0].text:
                    found = True
                    print(f"[!] Removed {mod[0].text} From Search")
            if not found:
                nMods.append(mod)
            found = False
        self.mods = nMods
        print(f"[!] Removed Quality From Search")
        print(f"[!] Removed Item Level From Search")
        self.quality = 0
        self.ilevel = 0


class Currency(BaseItem):
    def __init__(self, name):
        super().__init__(name)

    def get_json(self):
        json = {
            "exchange": {
                "status": {"option": "online"},
                "have": ["chaos"],
                "want": [currency_global[self.name]],
            },
        }
        return json


class Prophecy(BaseItem):
    def __init__(self, name):
        super().__init__(name)

    def get_json(self):
        json = super().get_json()
        json = self.set_name(json, self.name)
        json = self.set_type(json, "Prophecy")
        json = self.set_category(json, "prophecy")
        return json


class Organ(BaseItem):
    def __init__(self, name, ilevel, mods):
        super().__init__(name)
        self.ilevel = ilevel
        self.mods = mods

    def print(self):
        super().print()
        print(f"[Item Level] {self.ilevel}")
        for mod in self.mods:
            print(f"[Mod] {mod[0].text}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, "Metamorph " + self.name.split(" ")[-1])
        json = self.set_ilevel(json, self.ilevel)
        json = self.add_mods(json, self.mods)
        return json


class Flask(BaseItem):
    def __init__(self, name, base, rarity, quality, mods):
        super().__init__(name)
        self.base = base
        self.rarity = rarity
        self.quality = quality
        self.mods = mods

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Quality] {self.quality}")
        for mod in self.mods:
            print(f"[Mod] {mod[0].text}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.base)
        json = self.set_rarity(json, self.rarity)
        json = self.set_quality(json, self.quality)
        json = self.add_mods(json, self.mods)
        return json


class Gem(BaseItem):
    def __init__(self, name, quality, level, corrupted):
        super().__init__(name)
        self.quality = quality
        self.level = level
        self.corrupted = corrupted

    def print(self):
        super().print()
        print(f"[Item Level] {self.level}")
        print(f"[Quality] {self.quality}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.name)
        json = self.set_category(json, "gem")
        json["query"]["filters"]["misc_filters"]["filters"]["gem_level"] = {
            "min": self.level
        }
        json = self.set_quality(json, self.quality)
        json["query"]["filters"]["misc_filters"]["filters"]["corrupted"] = {
            "option": self.corrupted
        }
        return json


class Map(BaseItem):
    def __init__(
        self,
        name,
        base,
        rarity,
        ilevel,
        iiq,
        iir,
        pack_size,
        map_mods,
        identified,
    ):
        super().__init__(name)
        self.base = base
        self.rarity = rarity
        self.ilevel = ilevel
        self.iiq = iiq
        self.iir = iir
        self.pack_size = pack_size
        self.map_mods = map_mods
        self.identified = identified

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Item Level] {self.ilevel}")
        for mod in self.map_mods:
            print(f"[Mod] {mod[0].text}")

    def get_json(self):
        json = super().get_json()

        json["query"]["filters"]["map_filters"] = {
            "filters": {
                "map_tier": {"min": self.ilevel},
                "map_iiq": {"min": self.iiq},
                "map_iir": {"min": self.iir},
                "map_packsize": {"min": self.pack_size},
                "map_blighted": {"option": self.base.startswith("Blighted")},
            }
        }
        if self.rarity == "unique" and self.identified:
            json = self.set_name(json, self.name.replace(" " + self.base, ""))

        json = self.set_type(json, self.base)
        json = self.add_mods(json, self.map_mods)
        json = self.set_rarity(json, self.rarity)
        return json


class Beast(BaseItem):
    def __init__(self, name, base, ilevel):
        super().__init__(name)
        self.base = base
        self.ilevel = ilevel

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Item Level] {self.ilevel}")

    def get_json(self):
        json = super().get_json()
        json = self.set_ilevel(json, self.ilevel)
        json = self.set_type(json, self.base)
        return json


prev_mod = ""


def parse_mod(mod_text: str, mod_values, category=""):
    global prev_mod

    mod = None
    mod_type = ItemModifierType.EXPLICIT

    if mod_text.startswith("Allocates"):
        mod_values = mod_text[10:]
        element = ("Allocates #", ItemModifierType.ENCHANT)
        mod = get_item_modifiers_by_text(element)
        mod_values = mod.options[mod_values]

    if mod_text.endswith("(implicit)"):
        mod_text = mod_text[:-11]
        mod_type = ItemModifierType.IMPLICIT
    elif mod_text.endswith("(crafted)"):
        mod_text = mod_text[:-10]
        mod_type = ItemModifierType.CRAFTED

    if category == "weapon":
        if (
            "Adds # to #" in mod_text
            and "to Spells" not in mod_text
            or "to Accuracy Rating" in mod_text
        ):
            mod = get_item_modifiers_by_text((mod_text + " (Local)", mod_type))
        elif "increased Attack Speed" in mod_text:
            mod = get_item_modifiers_by_text(
                ("+#% total Attack Speed", ItemModifierType.PSEUDO)
            )
        elif "increased Physical Damage" in mod_text:
            mod = get_item_modifiers_by_text(
                ("#% total increased Physical Damage", ItemModifierType.PSEUDO)
            )
        elif (
            "increased Damage with Poison" in mod_text
            and "chance to Poison on Hit" not in prev_mod
        ):
            mod = get_item_modifiers_by_text((mod_text + " (Local)", mod_type))

    if category == "armour":
        if (
            "Armour" in mod_text
            or "Evasion" in mod_text
            or "Energy Shield" in mod_text
        ):
            mod = get_item_modifiers_by_text((mod_text + " (Local)", mod_type))

    if not mod and mod_type == ItemModifierType.CRAFTED:
        mod = get_item_modifiers_by_text((mod_text, ItemModifierType.PSEUDO))

    if not mod:
        mod = get_item_modifiers_by_text((mod_text, mod_type))

    if not mod:
        mod = get_item_modifiers_by_text((mod_text + " (Local)", mod_type))

    if not mod:
        if not mod_values:
            mod_text = "#% chance to " + mod_text
        mod = get_item_modifiers_by_text((mod_text, ItemModifierType.ENCHANT))

    if (
        not mod
    ):  # example: Skills which throw Mines throw up to 1 additional Mine if you have at least 800 Dexterity
        mod_text2 = mod_text.replace("#", "1")
        mod = get_item_modifiers_by_text((mod_text2, mod_type))
    try:
        if not mod:
            if "reduced" in mod_text:
                mod_text = mod_text.replace("reduced", "increased")
                mod_values = str(float(mod_values) * (-1))
            elif "increased" in mod_text:
                mod_text = mod_text.replace("increased", "reduced")
                mod_values = str(float(mod_values) * (-1))
            mod = get_item_modifiers_by_text((mod_text, mod_type))
    except ValueError:
        return None, ""

    prev_mod = mod_text
    return mod, mod_values


def isCurrency(name: str, rarity: str, regions: list):
    if rarity == "currency" or rarity == "divination card":
        return Currency(name)
    if name in currency_global:
        return Currency(name)

    mapText = "Travel to this Map by using it in a personal Map Device. Maps can only be used once."
    for i in range(len(regions) - 3, len(regions)):
        if "Map Device" in regions[i][0] and mapText not in regions[i][0]:
            return Currency(name)
    return None


def parse_map(regions: list, rarity, name):
    map_mods = []
    identified = True
    for i in range(2, len(regions)):
        for line in regions[i]:
            if line == "Unidentified":
                identified = False
            mod_text = line[:-11]
            mod = None
            mod_value = None
            if line.startswith("Area is influenced by"):
                mod_value = mod_text.replace("Area is influenced by ", "")
                mod = get_item_modifiers_by_text(
                    ("Area is influenced by #", ItemModifierType.IMPLICIT)
                )
            elif line.startswith("Map is occupied by"):
                mod_value = mod_text.replace("Map is occupied by ", "")
                mod = get_item_modifiers_by_text(
                    ("Map is occupied by #", ItemModifierType.IMPLICIT)
                )
            if mod and mod_value:
                map_mods.append(((mod, mod_value)))

    ilevel = int(regions[1][0][10:])
    iiq = 0
    iir = 0
    pack_size = 0
    for line in regions[1]:
        if line.startswith("Item Quantity: +"):
            iiq = int(line[16:-13])
        elif line.startswith("Item Rarity: +"):
            iir = int(line[14:-13])
        elif line.startswith("Monster Pack Size: +"):
            pack_size = int(line[19:-13])

    base = get_base("Maps", name)

    return Map(
        name, base, rarity, ilevel, iiq, iir, pack_size, map_mods, identified
    )


def parse_organ(regions: list, name):
    mods = {}
    for line in regions[3]:
        line = line.lstrip(" ").rstrip(" ") + " (×#)"
        mod = get_item_modifiers_by_text((line, ItemModifierType.MONSTER))
        if mod:
            if mod not in mods:
                mods[mod] = 1
            else:
                mods[mod] += 1
    nMods = []
    for key, value in mods.items():
        nMods.append((key, value))

    ilevel = int(regions[2][0][11:])
    return Organ(name, ilevel, nMods)


def parse_flask(regions: list, rarity: str, quality: int, name: str):
    mods = []
    for i in range(4, len(regions)):
        for line in regions[i]:
            mod_values = re.findall(r"[+-]?\d+\.?\d?\d?", line)
            mod_values = ",".join(["".join(v) for v in mod_values])
            mod_text = re.sub(r"[+-]?\d+\.?\d?\d?", "#", line)
            mod, mod_values = parse_mod(mod_text, mod_values)
            if mod:
                mods.append((mod, mod_values))

    if rarity != "Unique":
        base = get_base("Flasks", name)
    else:
        base = name
    return Flask(name, base, rarity, quality, mods)


def parse_beast(name: str, regions: str):
    base = get_base("Itemised Monsters", name + " " + regions[0][2])
    ilevel = int(regions[2][0][12:])
    return Beast(name, base, ilevel)


def parse_item_info(text: str):

    regions = text.split('--------')
    
    if len(regions) < 2:
        print("Not a PoE Item")
        return None

    for i, region in enumerate(regions):
        regions[i] = region.strip().splitlines()

    if regions[-1][0]:
        if "Note" in regions[-1][0]:
            del regions[-1]

    rarity = regions[0][0][8:].lower()

    validRarity = [
        "currency",
        "divination card",
        "gem",
        "normal",
        "magic",
        "rare",
        "unique",
    ]

    if rarity not in validRarity:
        print("Not a PoE Item")
        return None

    name = re.sub(r"<<set:M?S?>>", "", regions[0][1])

    if len(regions[0]) > 2:
        name += " " + regions[0][2]

    if len(name) > 60:
        print("Not a PoE Item")
        return None

    quality = 0

    for line in regions[1]:
        if line.startswith("Quality"):
            quality = int(line[line.find("+") + 1 : -13])
            break

    mapText = "Travel to this Map by using it in a personal Map Device. Maps can only be used once."
    prophecyText = "Right-click to add this prophecy to your character."
    organText = (
        "Combine this with four other different samples in Tane's Laboratory."
    )
    flaskText = "Right click to drink. Can only hold charges while in belt. Refills as you kill monsters."
    beastText = "Right-click to add this to your bestiary."

    for i in range(len(regions) - 1, 0, -1):
        if mapText in regions[i][0]:
            return parse_map(regions, rarity, name)
        elif prophecyText in regions[i][0]:
            return Prophecy(name)
        elif organText in regions[i][0]:
            return parse_organ(regions, name)
        elif flaskText in regions[i][0]:
            return parse_flask(regions, rarity, quality, name)
        elif beastText in regions[i][0]:
            return parse_beast(name, regions)

    c = isCurrency(name, rarity, regions)
    if c:
        return c

    if rarity == "gem":
        level = regions[1][1].replace(" (Max)", "")
        corrupted = regions[-1] == ["Corrupted"]
        if "Vaal" in regions[1][0]:
            name = "Vaal " + name
        return Gem(name, quality, level, corrupted)

    sockets = []
    corrupted = False
    mirrored = False
    identified = True
    veiled = False
    ilevel = 0
    influences = []
    mods = []

    synthesised = False

    if "Synthesised " in name:
        synthesised = True
        name = name.replace("Synthesised ", "")

    base = get_base("Accessories", name)
    category = "accessory"
    if not base:
        base = get_base("Weapons", name)
        category = "weapon"
    if not base:
        base = get_base("Armour", name)
        category = "armour"
    if not base:
        base = get_base("Jewels", name)
        category = "jewel"
    if not base:
        print("Item not found")
        return None

    influenceText = {
        "Elder",
        "Shaper",
        "Hunter",
        "Redeemer",
        "Warlord",
        "Crusader",
    }

    foundExplicit = False

    for i in range(len(regions)):
        first_line = regions[i][0]
        if first_line.startswith("Requirements"):
            pass
        elif first_line.startswith("Sockets"):
            sockets = first_line[9:]
        elif first_line == "Corrupted":
            corrupted = True
        elif first_line == "Mirrored":
            mirrored = True
        elif first_line == "Unidentified":
            identified = False
        elif first_line.startswith("Item Level"):
            ilevel = int(first_line[12:])
        elif first_line.startswith(
            "Place into an allocated Jewel Socket on the Passive Skill Tree. Right click to remove from the Socket."
        ):
            continue
        elif first_line.count(" ") == 1 and first_line.endswith("Item"):
            if line[:-5] in influenceText:
                influences.append(line[:-5])
        elif i > 1 and not foundExplicit:
            for line in regions[i]:
                if "Veiled Prefix" in line or "Veiled Suffix" in line:
                    veiled = True
                else:
                    if (
                        "if you have at least" in line
                        or "inflicted with this Weapon to deal" in line
                    ):
                        mod_values = re.search(
                            r"[+-]?\d+\.?\d?\d?", line
                        ).group(0)
                        numberIndex = re.search(
                            r"[+-]?\d+\.?\d?\d?", line
                        ).start()
                        textIndex = line.find("if you have at least")
                        if textIndex == -1:
                            textIndex = line.find(
                                "inflicted with this Weapon to deal"
                            )
                        if numberIndex < textIndex:
                            mod_text = re.sub(
                                r"[+-]?\d+\.?\d?\d?", "#", line, 1
                            )
                        else:
                            mod_text = line
                    else:
                        mod_values = re.findall(r"[+-]?\d+\.?\d?\d?", line)
                        if len(mod_values) > 1:
                            try:
                                mod_values = (
                                    (float(mod_values[0]))
                                    + float(mod_values[1])
                                ) / 2
                            except ValueError:
                                mod_values = None
                        else:
                            if mod_values:
                                mod_values = mod_values[0]
                        mod_text = re.sub(r"[+-]?\d+\.?\d?\d?", "#", line)

                    mod = None
                    if not mod_text:
                        mod_text = line
                    mod, mod_values = parse_mod(mod_text, mod_values, category)
                    if mod:
                        mods.append((mod, mod_values))
                        if mod.type == ItemModifierType.EXPLICIT:
                            foundExplicit = True  # Dont parse flavor text
                    else:
                        print(f"Unable to find mod: {line}")

    if rarity == "unique" and identified:
        name = name.replace(" " + base, "")

    return Item(
        name,
        base,
        category,
        rarity,
        quality,
        ilevel,
        mods,
        sockets,
        influences,
        identified,
        corrupted,
        mirrored,
        veiled,
        synthesised,
    )
