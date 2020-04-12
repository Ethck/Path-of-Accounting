import logging
import re
from math import floor

from colorama import Fore

from item.itemModifier import ItemModifierType
from utils.currency import currency_global
from utils.web import (
    get_base,
    get_item_modifiers_by_id,
    get_item_modifiers_by_text,
    get_ninja_bases,
    is_duplicate_mod_type,
)


def round_mod(number):
    return round(number, 2)


class ModInfo:
    def __init__(self, mod, m_min, m_max, option, can_reduce=True):
        self.mod = mod
        self.min = m_min
        self.max = m_max
        self.option = option
        self.can_reduce = can_reduce


class BaseItem:
    """Base class that holds default values for all items."""

    def __init__(self, name):
        self.name = name
        self.online = "online"
        self.mods = []
        self.text = ""

    def set_offline(self):
        self.online = "any"

    def print(self):
        print("[!] Found: ", self.name)

    def get_json(self):
        """Base JSON for all items"""
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
        """Add the modifiers found in the given list.

        :param json: JSON of the item to modify
        :param modifiers: Modifier list to transform
        """
        mods = []
        for e in modifiers:
            data = {
                "id": e.mod.id,
                "value": {"option": e.option, "max": e.max, "min": e.min,},
            }
            mods.append(data)
        json["query"]["stats"][0]["filters"] = mods
        return json

    def create_pseudo_mods(self):
        return {}

    def relax_modifiers(self):
        pass

    def remove_duplicate_mods(self):
        return ""

    def remove_bad_mods(self):
        return ""

    def get_item_stats(self):
        return ""

    def remove_all_mods(self):
        self.mods = []

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
    """Representation of gear that can be equipped. Belts, Chests, Helmets, Weapons, etc."""

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
        text,
    ):
        super().__init__(name)
        self.rarity = rarity
        self.quality = quality
        self.base = base
        self.category = category
        self.ilevel = ilevel
        if self.ilevel > 86:
            self.ilevel == 86
        self.mods = mods
        self.sockets = sockets
        self.influence = influence
        self.identified = identified
        self.corrupted = corrupted
        self.mirrored = mirrored
        self.veiled = veiled
        self.synthesised = synthesised
        self.text = text

    def print(self):
        super().print()
        logging.info(f"[Base] {self.base}")
        logging.info(f"[Item Level] {self.ilevel}")
        logging.info(f"[Quality] {self.quality}")
        for mod in self.mods:
            t = f"[Mod] {mod.mod.text}"
            if mod.min:
                t += f": [{Fore.YELLOW}{mod.min}{Fore.RESET}]"
            if mod.max:
                t += f": [{Fore.YELLOW}{mod.max}{Fore.RESET}]"

            logging.info(t)

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.base)
        json = self.set_rarity(json, self.rarity)
        json = self.set_ilevel(json, self.ilevel)
        json = self.set_category(json, self.category)
        # json = self.set_quality(json, self.quality)
        json = self.set_influence(json, self.influence)
        json = self.add_mods(json, self.mods)

        if self.synthesised:
            json["query"]["filters"]["misc_filters"]["filters"][
                "synthesised_item"
            ] = {"option": self.synthesised}
        if self.corrupted:
            json["query"]["filters"]["misc_filters"]["filters"][
                "corrupted"
            ] = {"option": self.corrupted}
        if self.mirrored:
            json["query"]["filters"]["misc_filters"]["filters"]["mirrored"] = {
                "option": self.mirrored
            }
        if self.veiled:
            json["query"]["filters"]["misc_filters"]["filters"]["veiled"] = {
                "option": self.veiled
            }
        if self.identified:
            json["query"]["filters"]["misc_filters"]["filters"][
                "identified"
            ] = {"option": self.identified}

        if self.sockets:
            sockets = self.sockets.lower()
            r_sockets = sockets.count("r")
            b_sockets = sockets.count("b")
            g_sockets = sockets.count("g")
            w_sockets = sockets.count("w")
            a_sockets = sockets.count("a")

            links = 0
            counter = 0
            for c in sockets:
                if c == " ":
                    if counter > links:
                        links = counter
                    counter = 0
                elif c == "-":
                    counter += 1
            if counter > links:
                links = counter
            links = links + 1
            sockets = r_sockets + b_sockets + g_sockets + w_sockets + a_sockets

            if sockets == 6 or links >= 5:
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
            json = self.set_name(json, self.name)

        return json

    def create_pseudo_mods(self):
        """Turn certain modifiers into their pseudo variants to find more matches
        Returns the mods that was turned"""
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

        spell_crit = 0
        global_crit = 0
        global_multi = 0
        increased_ele_attacks = 0

        rMods = []
        nMods = []
        for mod in self.mods:
            if mod.mod.id in solo_resist_ids:
                total_ele_resists += float(mod.min)
                rMods.append(mod)
            elif mod.mod.id in dual_resist_ids:
                total_ele_resists += 2 * float(mod.min)
                rMods.append(mod)
            elif mod.mod.id in triple_resist_ids:
                total_ele_resists += 3 * float(mod.min)
                rMods.append(mod)
            elif mod.mod.id in solo_chaos_resist_ids:
                total_chaos_resist += float(mod.min)
                rMods.append(mod)
            elif mod.mod.id in dual_chaos_resist_ids:
                total_ele_resists += float(mod.min)
                total_chaos_resist += float(mod.min)
                rMods.append(mod)
            elif mod.mod.id in life_ids:
                total_life += float(mod.min)
                rMods.append(mod)
            # Life gained from strength
            elif mod.mod.id == "explicit.stat_4080418644":
                total_life += (float(mod.min) / 10) * 5
                nMods.append(mod)
            elif "increased Critical Strike Chance for Spells" in mod.mod.text:
                spell_crit += float(mod.min)
                rMods.append(mod)
            elif "Global Critical Strike Chance" in mod.mod.text:
                global_crit += float(mod.min)
                nMods.append(mod)
            elif "Global Critical Strike Multiplier" in mod.mod.text:
                global_multi += float(mod.min)
                rMods.append(mod)
            elif (
                "increased Elemental Damage with Attack Skills" in mod.mod.text
            ):
                increased_ele_attacks += float(mod.min)
                rMods.append(mod)
            else:
                nMods.append(mod)

        self.mods = nMods

        if spell_crit != 0:
            spell_crit += global_crit
            modType = get_item_modifiers_by_id(
                "pseudo.pseudo_critical_strike_chance_for_spells"
            )
            mod = ModInfo(modType, spell_crit, None, None)
            self.mods.append(mod)

        if global_multi != 0:
            modType = get_item_modifiers_by_id(
                "pseudo.pseudo_global_critical_strike_multiplier"
            )
            mod = ModInfo(modType, global_multi, None, None)
            self.mods.append(mod)

        if increased_ele_attacks != 0:
            modType = get_item_modifiers_by_id(
                "pseudo.pseudo_increased_elemental_damage_with_attack_skills"
            )
            mod = ModInfo(modType, increased_ele_attacks, None, None)
            self.mods.append(mod)

        if total_ele_resists > 0:
            modType = get_item_modifiers_by_id(
                "pseudo.pseudo_total_elemental_resistance"
            )
            mod = ModInfo(modType, total_ele_resists, None, None)
            self.mods.append(mod)

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
            modType = get_item_modifiers_by_id(
                "pseudo.pseudo_total_chaos_resistance"
            )
            mod = ModInfo(modType, total_chaos_resist, None, None)
            self.mods.append(mod)

            logging.info(
                "[o] Combining the "
                + Fore.CYAN
                + f"chaos resistance"
                + Fore.RESET
                + " mods from the list into a pseudo-parameter"
            )
            logging.info(
                "[+] Pseudo-mod "
                + Fore.GREEN
                + f"+{total_chaos_resist}% total Chaos Resistance (pseudo)"
            )

        if total_life > 0:
            modType = get_item_modifiers_by_id("pseudo.pseudo_total_life")
            mod = ModInfo(modType, total_life, None, None)
            self.mods.append(mod)
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

        return rMods

    def relax_modifiers(self):
        if self.rarity == "unique":  # dont do this on uniques
            return

        for mod in self.mods:
            if mod.can_reduce:
                if mod.max:
                    if mod.max > 0:
                        mod.max = round_mod(mod.max * 1.1)
                    else:
                        mod.max = round_mod(mod.max * 0.9)
                if mod.min:
                    if mod.min > 0:
                        mod.min = round_mod(mod.min * 0.9)
                    else:
                        mod.min = round_mod(mod.min * 1.1)

    def remove_duplicate_mods(self):
        nMods = []
        restr = ""
        for mod in self.mods:
            if is_duplicate_mod_type(mod.mod):
                restr += f"    {mod.mod.text}\n"
            else:
                nMods.append(mod)
        self.mods = nMods
        if restr != "":
            restr = f"[!] Removing duplicate mods on trade site:\n" + restr
        return restr

    def remove_bad_mods(self):
        """Mods to remove first if found on any individual item if no matches are found before relaxing"""

        if self.rarity == "unique":  # dont do this on uniques
            return ""

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
        restr = ""
        for mod in self.mods:
            for bad in bad_mod_list:
                if bad in mod.mod.text:
                    found = True
                    restr += f"    {mod.mod.text}\n"
            if not found:
                nMods.append(mod)
            found = False
        self.mods = nMods
        if restr != "":
            restr = "[!] Removed some mods From Search:\n" + restr
        restr += f"[!] Removed Quality From Search\n"
        # restr += f"[!] Removed Item Level From Search\n"
        self.quality = 0
        # self.ilevel = 0

        return restr


class Armour(Item):
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
        text,
    ):
        super().__init__(
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
            text,
        )
        self.armour = None
        self.es = None
        self.evasion = None

    def merge_mods(self, regions):
        for line in regions[1]:
            line = line.replace(" (augmented)", "")
            if "Energy Shield: " in line:
                try:
                    self.es = float(line.replace("Energy Shield: ", ""))
                except Exception:
                    pass
            if "Evasion Rating: " in line:
                try:
                    self.evasion = float(line.replace("Evasion Rating: ", ""))
                except Exception:
                    pass
            if "Armour: " in line:
                try:
                    self.armour = float(line.replace("Armour: ", ""))
                except Exception:
                    pass

        statList = [
            "maximum Energy Shield",
            "increased maximum Energy Shield",
            "increased Energy Shield",
            "increased Armour",
            "to Armour",
            "to Evasion Rating",
            "increased Evasion Rating",
        ]

        nMods = []
        for mod in self.mods:
            mod_text = mod.mod.text
            found = False
            for s in statList:
                if s in mod_text:
                    found = True
                    break
            if not found:
                nMods.append(mod)

        self.mods = nMods

    def relax_modifiers(self):
        super().relax_modifiers()
        if self.armour:
            self.armour = round_mod(self.armour * 0.9)
        if self.evasion:
            self.evasion = round_mod(self.evasion * 0.9)
        if self.es:
            self.es = round_mod(self.es * 0.9)

    def get_json(self):
        json = super().get_json()
        json["query"]["filters"]["armour_filters"] = {
            "filters": {
                "ar": {"min": self.armour},
                "es": {"min": self.es},
                "ev": {"min": self.evasion},
            }
        }
        return json

    def get_item_stats(self):
        s = f"Armour: {self.armour} \nEvasion: {self.evasion} \nEnergy Shield: {self.es}"
        return s


class Weapon(Item):
    """Representation of weapons."""

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
        text,
    ):
        super().__init__(
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
            text,
        )
        self.pdps = 0
        self.edps = 0
        self.speed = 0
        self.crit = 0

    def merge_mods(self, regions):
        pValues = None
        eValues = None
        for line in regions[1]:
            line = line.replace(" (augmented)", "")
            if "Physical Damage" in line:
                line = line.replace("Physical Damage: ", "")
                pValues = line.split("-")
            elif "Elemental Damage: " in line:
                line = line.replace("Elemental Damage: ", "")
                values = line.split(", ")
                minValues = 0
                maxValues = 0
                for v in values:
                    v2 = v.split("-")
                    minValues += float(v2[0])
                    maxValues += float(v2[1])
                eValues = []
                eValues.append(minValues)
                eValues.append(maxValues)
            elif "Critical Strike Chance: " in line:
                line = line.replace("Critical Strike Chance: ", "")
                line = line.replace("%", "")
                self.crit = float(line)
            elif "Attacks per Second: " in line:
                self.speed = float(line.replace("Attacks per Second: ", ""))

        if pValues and self.speed:
            self.pdps = floor(
                (
                    (float(pValues[0]) * self.speed)
                    + (float(pValues[1]) * self.speed)
                )
                / 2
            )
        if eValues and self.speed:
            self.edps = floor(
                (
                    (float(eValues[0]) * self.speed)
                    + (float(eValues[1]) * self.speed)
                )
                / 2
            )

        # Remove mods that affect weapon stats, and search for weapon stats instead
        is_caster_weapon = 0
        nMods = []
        for mod in self.mods:
            mod_text = mod.mod.text
            if (
                ("Adds # to #" in mod_text and "to Spells" not in mod_text)
                or (mod_text == "#% increased Critical Strike Chance")
                or ("increased Attack Speed" in mod_text)
                or ("increased Physical Damage" in mod_text)
                or ("total Attack Speed" in mod_text)
            ):
                continue
            else:
                nMods.append(mod)

            if "Spell" in mod_text:
                is_caster_weapon += 1
            elif "Spells" in mod_text:
                is_caster_weapon += 1
        self.mods = nMods

        if self.pdps < 150 and self.edps < 150 and is_caster_weapon >= 2:
            self.pdps = None
            self.edps = None
            self.crit = None

    # Relax weapon stats
    def relax_modifiers(self):
        super().relax_modifiers()
        if self.pdps:
            self.pdps = round_mod(self.pdps * 0.9)
        if self.edps:
            self.edps = round_mod(self.edps * 0.9)
        if self.speed:
            self.speed = round_mod(self.speed * 0.9)
        if self.crit:
            self.crit = round_mod(self.crit * 0.9)

    def get_json(self):
        json = super().get_json()
        json["query"]["filters"]["weapon_filters"] = {
            "filters": {
                "aps": {"min": self.speed},
                "crit": {"min": self.crit},
                "edps": {"min": self.edps},
                "pdps": {"min": self.pdps},
            }
        }
        return json

    def get_item_stats(self):
        s = f"Physical DPS: {self.pdps} \nElemental DPS: {self.edps} \nSpeed: {self.speed}\nCrit: {self.crit}"
        return s


class Currency(BaseItem):
    """Representation of currency items"""

    def __init__(self, name, text):
        super().__init__(name)
        self.text = text

    def get_json(self):
        unsupportedCurrency = [
            "Warlord's Exalted Orb",
            "Crusader's Exalted Orb",
            "Redeemer's Exalted Orb",
            "Hunter's Exalted Orb",
            "Awakener's Orb",
        ]
        if self.name not in unsupportedCurrency:
            json = {
                "exchange": {
                    "status": {"option": "online"},
                    "have": ["chaos"],
                    "want": [currency_global[self.name]],
                },
            }
        else:
            json = {
                "query": {"type": self.name},
                "status": {"option": "online"},
                "sort": {"price": "asc"},
            }
        return json


class Prophecy(BaseItem):
    """Representation of Prophecy items"""

    def __init__(self, name, text):
        super().__init__(name)
        self.text = text

    def get_json(self):
        json = super().get_json()
        json = self.set_name(json, self.name)
        json = self.set_type(json, "Prophecy")
        json = self.set_category(json, "prophecy")
        return json


class Organ(BaseItem):
    """Representation of Metamorph Organs"""

    def __init__(self, name, ilevel, mods, text):
        super().__init__(name)
        self.ilevel = ilevel
        self.mods = mods
        self.text = text

    def print(self):
        super().print()
        print(f"[Item Level] {self.ilevel}")
        for mod in self.mods:
            print(f"[Mod] {mod.mod.text}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, "Metamorph " + self.name.split(" ")[-1])
        json = self.set_ilevel(json, self.ilevel)
        json = self.add_mods(json, self.mods)
        return json


class Flask(BaseItem):
    """Representation of Flasks"""

    def __init__(self, name, base, rarity, quality, mods, text):
        super().__init__(name)
        self.base = base
        self.rarity = rarity
        self.quality = quality
        self.mods = mods
        self.text = text

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Quality] {self.quality}")
        for mod in self.mods:
            print(f"[Mod] {mod.mod.text}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.base)
        json = self.set_rarity(json, self.rarity)
        json = self.set_quality(json, self.quality)
        json = self.add_mods(json, self.mods)
        return json


class Gem(BaseItem):
    """Representation of Skill Gems"""

    def __init__(self, name, quality, level, corrupted, text):
        super().__init__(name)
        self.quality = quality
        self.level = level
        self.corrupted = corrupted
        self.text = text

    def print(self):
        super().print()
        print(f"[Item Level] {self.level}")
        print(f"[Quality] {self.quality}")

    def get_json(self):
        json = super().get_json()
        json = self.set_type(json, self.name)
        json = self.set_category(json, "gem")
        json["query"]["filters"]["misc_filters"]["filters"]["gem_level"] = {
            "min": int(self.level)
        }
        json = self.set_quality(json, self.quality)
        json["query"]["filters"]["misc_filters"]["filters"]["corrupted"] = {
            "option": self.corrupted
        }
        return json


class Map(BaseItem):
    """Representation for Maps"""

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
        text,
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
        self.text = text

    def print(self):
        super().print()
        print(f"[Base] {self.base}")
        print(f"[Item Level] {self.ilevel}")
        for mod in self.map_mods:
            print(f"[Mod] {mod.mod.text}")

    def get_json(self):
        json = super().get_json()
        json["query"]["filters"]["map_filters"] = {
            "filters": {
                "map_tier": {"min": self.ilevel},
                "map_iiq": {"min": self.iiq},
                "map_iir": {"min": self.iir},
                "map_packsize": {"min": self.pack_size},
                "map_blighted": {"option": self.name.startswith("Blighted")},
            }
        }
        if self.rarity == "unique" and self.identified:
            json = self.set_name(json, self.name.replace(" " + self.base, ""))

        json = self.set_type(json, self.base)
        json = self.add_mods(json, self.map_mods)
        json = self.set_rarity(json, self.rarity)
        return json


class Beast(BaseItem):
    """Representation for itemized Beasts"""

    def __init__(self, name, base, ilevel, text):
        super().__init__(name)
        self.base = base
        self.ilevel = ilevel
        self.text = text

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
    """Given the text of the mod, find the appropriate ItemModifier object

    :param mod_text: Text of the mod
    :param mod_values: Value of the referenced mod
    :param category: Specific category of mods to check
    """
    global prev_mod

    can_reduce = True
    m_min = None
    m_max = None
    option = None

    mod = None
    mod_type = ItemModifierType.EXPLICIT

    mod_text = mod_text.rstrip()

    if mod_values == []:
        mod_values = ""

    if mod_text.startswith("Allocates"):
        mod_text = mod_text.replace("Allocates ", "")
        mod_text = mod_text.replace(" (enchant)", "")
        element = ("Allocates #", ItemModifierType.ENCHANT)
        mod = get_item_modifiers_by_text(element)
        mod_values = mod.options[mod_text]
        option = mod_values
        can_reduce = False

    if mod_text.endswith("(implicit)"):
        mod_text = mod_text[:-11]
        mod_type = ItemModifierType.IMPLICIT
    elif mod_text.endswith("(crafted)"):
        mod_text = mod_text[:-10]
        mod_type = ItemModifierType.CRAFTED

    # Added Small Passive Skills grant: #% increased Damage while affected by a Herald (enchant) 10

    # Added Small Passive Skills grant:
    # 10% increased Damage while affected by a Herald (enchant)
    # {"id":"enchant.stat_3948993189","value":{"option":26}

    elif mod_text.endswith("(enchant)"):
        mod_text = mod_text.replace(" (enchant)", "")
        mod_type = ItemModifierType.ENCHANT
        can_reduce = False

    if (
        "Passive Skill" in mod_text
        or "Socketed Gems are Supported by Level" in mod_text
    ):
        can_reduce = False

    if "Added Small Passive Skills grant:" in mod_text:
        element = (
            "Added Small Passive Skills grant: #",
            ItemModifierType.ENCHANT,
        )
        mod = get_item_modifiers_by_text(element)
        mod_text = mod_text.replace("Added Small Passive Skills grant: ", "")
        mod_text = mod_text.replace("#", mod_values)
        mod_values = mod.options[mod_text]
        option = mod_values

    # {"id":"explicit.stat_4079888060","value":{"min":1}
    # # Added Passive Skill is a Jewel Socket -> # Added Passive Skills are Jewel Sockets
    if "# Added Passive Skill is a Jewel Socket" in mod_text:
        element = (
            "# Added Passive Skills are Jewel Sockets",
            ItemModifierType.EXPLICIT,
        )
        mod = get_item_modifiers_by_text(element)

    if category == "weapon":
        if (
            "Adds # to #" in mod_text
            and "to Spells" not in mod_text
            or "to Accuracy Rating" in mod_text
            or "increased Attack Speed" in mod_text
        ):
            mod = get_item_modifiers_by_text((mod_text + " (Local)", mod_type))
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
            mod = get_item_modifiers_by_text(
                ("#% chance to " + mod_text, ItemModifierType.ENCHANT)
            )
        else:
            mod = get_item_modifiers_by_text(
                (mod_text, ItemModifierType.ENCHANT)
            )

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
        pass

    if not mod:
        # print("["+mod_text+"]")
        return None

    if not option:
        try:
            if float(mod_values) < 0:
                m_max = float(mod_values)
            else:
                m_min = float(mod_values)
        except ValueError:
            if mod_values:
                option = mod_values

    if "Adds # Passive Skills" in mod.text:
        m_max = float(mod_values)
        m_min = None

    prev_mod = mod_text
    m = ModInfo(mod, m_min, m_max, option, can_reduce)
    return m


def isCurrency(name: str, rarity: str, regions: list):
    """Determine if given item is a currency"""
    if rarity == "currency" or rarity == "divination card":
        return Currency(name, regions)
    if name in currency_global:
        return Currency(name, regions)

    mapText = "Travel to this Map by using it in a personal Map Device. Maps can only be used once."
    for i in range(len(regions) - 3, len(regions)):
        if "Map Device" in regions[i][0] and mapText not in regions[i][0]:
            return Currency(name, regions)
    return None


def parse_map(regions: list, rarity, name):
    """Parse map text and construct the Map object"""
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
                mod = ModInfo(mod, mod_value, None, None)
                map_mods.append(mod)

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
        name,
        base,
        rarity,
        ilevel,
        iiq,
        iir,
        pack_size,
        map_mods,
        identified,
        regions,
    )


def parse_organ(regions: list, name):
    """Parse text and construct the Organ object"""
    mods = {}
    for line in regions[3]:
        line = line.lstrip(" ").rstrip(" ")
        mod = get_item_modifiers_by_text((line, ItemModifierType.MONSTER))
        if mod:
            found = False
            for key, value in mods.items():
                if key == mod.id:
                    found = True
            if not found:
                mods[mod.id] = 1
            else:
                mods[mod.id] += 1
    nMods = []
    for key, value in mods.items():
        mod = get_item_modifiers_by_id(key)
        m = ModInfo(mod, value, None, None)
        nMods.append(m)

    ilevel = int(regions[2][0][11:])
    return Organ(name, ilevel, nMods, regions)


def parse_flask(regions: list, rarity: str, quality: int, name: str):
    """Parse text and construct Flask object"""
    mods = []
    for i in range(4, len(regions)):
        for line in regions[i]:
            mod_values = re.findall(r"[+-]?\d+\.?\d?\d?", line)
            mod_values = ",".join(["".join(v) for v in mod_values])
            mod_text = re.sub(r"[+-]?\d+\.?\d?\d?", "#", line)
            mod = parse_mod(mod_text, mod_values)
            if mod:
                mods.append(mod)

    if rarity != "Unique":
        base = get_base("Flasks", name)
    else:
        base = name
    return Flask(name, base, rarity, quality, mods, regions)


def parse_beast(name: str, regions: str):
    """Parse text and construct Beast object"""
    base = get_base("Itemised Monsters", name + " " + regions[0][2])
    ilevel = int(regions[2][0][12:])
    return Beast(name, base, ilevel, regions)


def parse_item_info(text: str):
    """Parse given text and construct the approriate object."""
    regions = text.split("--------")

    if len(regions) < 2:
        logging.info("Not a PoE Item")
        return None

    for i, region in enumerate(regions):
        regions[i] = region.strip().splitlines()
        if len(regions[i]) <= 0:
            del regions[i]
            i -= 1

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
        logging.info("Not a PoE Item")
        return None

    name = re.sub(r"<<set:M?S?>>", "", regions[0][1])

    if len(regions[0]) > 2:
        if rarity == "rare":
            modname = name + " " + regions[0][2]
            name = regions[0][2]
        else:
            name += " " + regions[0][2]

    if len(name) > 60:
        logging.info("Not a PoE Item")
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
            return Prophecy(name, regions)
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
        level = level.replace("Level: ", "")
        corrupted = regions[-1] == ["Corrupted"]
        if "Vaal" in regions[1][0]:
            name = "Vaal " + name
        return Gem(name, quality, level, corrupted, regions)

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
        logging.info("[!] Item not found")
        logging.info("[!] Pathofexile.com might be down")
        return None

    if "modname" in locals():
        name = modname

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
            if first_line[:-5] in influenceText:
                influences.append(first_line[:-5].lower())
                if len(regions[i]) > 1:
                    if regions[i][1].count(" ") == 1 and regions[i][
                        1
                    ].endswith("Item"):
                        if regions[i][1][:-5] in influenceText:
                            influences.append(regions[i][1][:-5].lower())

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
                    mod = parse_mod(mod_text, mod_values, category)
                    if mod:
                        mods.append(mod)
                        if mod.mod.type == ItemModifierType.EXPLICIT:
                            foundExplicit = True  # Dont parse flavor text
                    else:
                        logging.info(f"Unable to find mod: {line}")


    if rarity == "unique" and identified:
        name = name.replace(" " + base, "", 1)


    if category == "weapon":
        weapon = Weapon(
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
            text,
        )
        weapon.merge_mods(regions)
        return weapon

    if category == "armour":
        armour = Armour(
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
            text,
        )
        armour.merge_mods(regions)
        return armour

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
        text,
    )
