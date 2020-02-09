import logging
import copy
import re
from attr import attrs
from typing import Dict, List

from .item_modifier import ItemModifier
from enums.item_modifier_type import ItemModifierType
from utils.trade import (
    get_ninja_bases,
    get_item_modifiers_by_text,
    build_map_bases,
    search_url,
    exchange_url,
)
from utils.mods import create_pseudo_mods
from utils.types import (
    get_magic_type,
    get_map_base,
)

# Synthesis uniques
synthesis_uniques = dict()

# A global type cache for Base -> Item derivative conversions
types = dict()

def get_synthesis_uniques() -> Dict:
    '''
    :return: Conversion dictionary of synthesis unique -> Item subclass
    '''
    global synthesis_uniques
    if len(synthesis_uniques) == 0:
        synthesis_uniques = {
            ("Bottled Faith", "Sulphur Flask"): Flask,
            ("Maloney's Mechanism", "Ornate Quiver"): Quiver,
            ("Circle of Anguish", "Ruby Ring"): Ring,
            ("Circle of Fear", "Sapphire Ring"): Ring,
            ("Circle of Guilt", "Iron Ring"): Ring,
            ("Circle of Nostalgia", "Amethyst Ring"): Ring,
            ("Circle of Regret", "Topaz Ring"): Ring,
            ("Garb of the Ephemeral", "Savant's Robe"): BodyArmor,
            ("Offering to the Serpent", "Legion Gloves"): Gloves,
            ("March of the Legion", "Legion Boots"): Boots,
            ("Mask of the Tribunal", "Magistrate Crown"): Helmet,
            ("Storm's Gift", "Assassin's Mitts"): Gloves,
            ("Perepiteia", "Ezomyte Spiked Shield"): Shield,
            ("Hyrri's Truth", "Jade Amulet"): Amulet,
            ("Nebulis", "Void Sceptre"): Weapon
        }
    return synthesis_uniques

def set_modifiers(json_data: Dict, modifiers: List) -> Dict:
    '''
    This function integrates a list of modifiers into a json query.

    :param json_data: Root json dictionary to set modifiers of
    :param modifiers: List of modifiers
    :return: Altered json dictionary
    '''

    # Temporary hack. This is allowing us to search up mods with values
    # that we store separated by commas, like Adds # to # Physical Damage.
    mods = []
    for e in modifiers:
        try:
            if ',' in e[1]:
                value = re.sub(r',.*', '', e[1])
                mods.append({ "id": e[0].id, "value": { "min": float(value) }})
            else:
                mods.append({ "id": e[0].id, "value": { "min": float(e[1]) }})
        except ValueError:
            # If we cannot cast the mod value stored to a float, then
            # we are not concerned with including that mod in the lookup.
            pass

    json_data["query"]["stats"][0]["filters"] = mods
    return json_data

@attrs(auto_attribs=True)
class Item:
    rarity: str = 'rare'
    name: str = None
    base: str = None
    ilevel: int = 0
    quality: int = 0

    # TODO: handle base stats
    stats: [str] = []

    raw_sockets: str = ''

    modifiers: [(ItemModifier, str)] = []
    corrupted: bool = False
    mirrored: bool = False
    veiled: bool = False

    # A list of influences that affect the item.
    influence: [str] = []

    links: int = 0

    synthesised: bool = False

    def __attrs_post_init__(self):
        if not self.base:
            self.base = self.name
            self.name = None
        sockets = self.raw_sockets.lower()
        self.r_sockets = sockets.count('r')
        self.b_sockets = sockets.count('b')
        self.g_sockets = sockets.count('g')
        self.w_sockets = sockets.count('w')
        self.a_sockets = sockets.count('a') # Abyssal sockets
        # R-R-R-R R-R is not incorrectly registered as 5 link
        self.links = sockets.count('-') - sockets.count(' ') + 1

        if self.base.startswith("Veiled"):
            self.veiled = True

        # Some debug logging of the attributes of our class. If we are
        # not running with DEBUG logging enabled, this becomes a no-op
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            logging.debug("====== %s ======" % self.__class__.__name__)
            for k, v in self.__dict__.items():
                logging.debug("%s: %s" % (k, v))
            logging.debug("====== End of %s ======" % self.__class__.__name__)

    def sanitize_modifiers(self):
        '''
        This method normally allows subclasses of Item to specifically
        sanitize modifiers. It is also needed within the base class, so
        that we can call it on any derivative without checking.

        :return: None
        '''
        pass

    def deduce_specific_object(self):
        '''
        This method's responsibility is to convert any unconverted Item
        into it's specific subclass.

        :return: Either the object itself or a subclassed object
        '''
        # If we're already a different object, turn this into a no-op method
        if self.__class__.__name__ != "Item":
            return self

        weapon_types = {
            "One Handed Sword",
            "Two Handed Sword",
            "One Handed Axe",
            "Two Handed Axe",
            "One Handed Mace",
            "Two Handed Mace",
            "Staff",
            "Wand",
            "Claw",
            "Bow",
            "Dagger",
        }

        other_types = {
            "Helmet": Helmet,
            "Body Armour": BodyArmor,
            "Boots": Boots,
            "Gloves": Gloves,
            "Ring": Ring,
            "Amulet": Amulet,
            "Belt": Belt,
            "Shield": Shield,
            "Quiver": Quiver,
            "Jewel": Jewel
        }

        global types
        if len(types) == 0:
            ninja_bases = get_ninja_bases()
            for e in ninja_bases:
                item_type = e["type"]
                item_base = e["base"]
                if item_base in types:
                    continue
                if item_type in weapon_types:
                    types[item_base] = Weapon
                elif item_type in other_types:
                    types[item_base] = other_types[item_type]
            # Synthesis league-specific base; the only non-unique one.
            types["Ornate Quiver"] = Quiver

        cls = None
        if self.base in types:
            cls = types[self.base]
            logging.debug(
                "Found base's type and converted the Item to %s" % str(cls.__class__.__name__)
            )

        if self.rarity == "magic":
            # If this item is a magic item, we can determine it's type
            # through our magic type graph algorithm
            logging.debug("Searching '%s' via get_magic_type" % self.base)
            base = re.sub(r' of .*$', '', self.base)
            result = get_magic_type(base)
            if result is not None:
                logging.debug("Magic base: %s" % str(result))
                item_base = result[0]
                item_type = result[1]
                self.base = item_base
                if item_type in weapon_types:
                    cls = Weapon
                elif item_type in other_types:
                    cls = other_types[item_type]

        elif self.rarity == "unique":
            name_and_base = (self.name, self.base.replace("Synthesised ", ''))
            synthesis_uniques = get_synthesis_uniques()
            if name_and_base in synthesis_uniques:
                self.synthesised = True
                self.base = self.base.replace("Synthesised ", '')
                cls = synthesis_uniques[name_and_base]
                logging.debug(
                    "Found item to be a synthesis unique and "
                    + "converted the Item to %s" % str(cls.__class__.__name__)
                )

        if not cls:
            # Oil, Catalyst, Fossil, Resonator, and Incubator is taken
            # care of by the Currency class, as they are of 'Currency' rarity
            end = ' ' + self.base.split(' ')[-1]
            possible_ends = {
                " Scarab": Scarab,
            }
            if end in possible_ends:
                cls = possible_ends[end]
            elif "Essence of " in self.base:
                cls = Essence
            elif "Vial of " in self.base:
                cls = Vial

        if cls:
            kwargs = copy.copy(self.__dict__)
            to_exclude = (
                "r_sockets",
                "b_sockets",
                "g_sockets",
                "w_sockets",
                "a_sockets"
            )
            for attr in to_exclude:
                del kwargs[attr]
            return cls(**kwargs)

        logging.error(
            "deduce_specific_object was called via Item, "
            + "but no base could be found to be converted"
        )
        return self

    def get_pseudo_mods(self):
        raise NotImplementedError

    def get_json(self) -> Dict:
        '''
        This method is the root of all json production for items. It only
        concerns itself with fields that the majority of subclasses use.

        :return: json data for the Item base class
        '''
        data = {
            "query": {
                "status": {
                    "option": "online"
                },

                "stats": [
                    {
                        "type": "and",
                        "filters": []
                    }
                ],
            },
            "sort": {
                "price": "asc"
            }
        }

        if self.rarity == "unique" and self.name is not None:
            data["query"]["name"] = self.name

        if self.base:
            data["query"]["type"] = self.base

        if len(self.modifiers) > 0:
            set_modifiers(data, self.modifiers)

        # If we have 6 sockets, we'll include that in the query
        data["query"]["filters"] = {}

        # Get a total count of sockets on this item
        sockets = self.r_sockets + self.g_sockets + self.b_sockets
        sockets += self.w_sockets + self.a_sockets

        # In most items, the only time a price really differs is
        # when an item is 6 socketed vs not 6 socketed. For this
        # reason, we'll only set the socket filter when we realize
        # that an item has 6 sockets
        if sockets == 6:
            data["query"]["filters"]["socket_filters"] = {
                "filters": {
                    "sockets": {
                        "min": 6,
                        "max": 6
                    }
                }
            }

        # If we have 5 or more links, we'll include that in the query
        if self.links >= 5:
            data["query"]["filters"]["socket_filters"]["filters"]["links"] = {
                "min": self.links,
                "max": self.links
            }

        # Set this key up; if it's not further modified, that's okay
        # from the API's perspective
        data["query"]["filters"]["misc_filters"] = {
            "filters": {}
        }

        for influence in self.influence:
            text = "%s_item" % influence
            data["query"]["filters"]["misc_filters"]["filters"][text] = {
                "option": "true"
            }

        if self.corrupted:
            data["query"]["filters"]["misc_filters"]["filters"]["corrupted"] = {
                "option": "true"
            }

        if self.mirrored:
            data["query"]["filters"]["misc_filters"]["filters"]["mirrored"] = {
                "option": "true"
            }

        # TODO: Parse this out correctly in parse_item_info; this is an
        # incomplete conditional at the moment.
        if self.veiled:
            data["query"]["filters"]["misc_filters"]["filters"]["veiled"] = {
                "option": "true"
            }

        # Figure out if we should set identified to false for our query json
        explicit_mods = [
            mod for mod in self.modifiers
            if mod[0].type == ItemModifierType.EXPLICIT
        ]
        unidentifiable = ('magic', 'rare', 'unique')
        if len(explicit_mods) == 0 and self.rarity in unidentifiable:
            data["query"]["filters"]["misc_filters"]["filters"]["identified"] = {
                "option": "false"
            }

        return data

@attrs(auto_attribs=True)
class Searchable(Item):
    def query_url(self, league: str) -> str:
        '''
        :param league: Path of Exile league to format the query URL with
        :return: A formatted string of the PoE search trade API endpoint
        '''
        return search_url(league)

@attrs(auto_attribs=True)
class Exchangeable(Item):
    # A conversion table for different types of bases
    convert = {
        "Chaos Orb": "chaos",
        "Exalted Orb": "exa",
        "Mirror of Kalandra": "mir",
    }

    def get_json(self) -> Dict:
        '''
        :return: An exchange API JSON dictionary for this item
        '''
        base = self.base
        if base in self.convert:
            base = self.convert[self.base]

        data = {
            "exchange": {
                "status": {
                    "option": "online"
                },
                "have": ["chaos"],
                "want": [base.lower().replace(' ', '-')]
            }
        }
        return data

    def query_url(self, league: str) -> str:
        '''
        :param league: Path of Exile league to format the query URL with
        :return: A formatted string of the PoE exchange trade API endpoint
        '''
        return exchange_url(league)

@attrs(auto_attribs=True)
class Wearable(Searchable):
    def get_json(self) -> Dict:
        '''
        :return: A JSON dictionary for this item, including it's item level
        '''
        data = super().get_json()
        # For unique items, we don't really care about the item level spec.
        if self.rarity != "unique":
            data["query"]["filters"]["misc_filters"]["filters"]["ilvl"] = {
                "min": self.ilevel
            }

        return data

@attrs(auto_attribs=True)
class Currency(Exchangeable): pass

@attrs(auto_attribs=True)
class Card(Searchable): pass

@attrs(auto_attribs=True)
class Gem(Searchable):
    def get_json(self) -> Dict:
        data = super().get_json()
        data["query"]["filters"]["misc_filters"]["filters"]["gem_level"] = {
            "min": self.ilevel
        }
        data["query"]["filters"]["misc_filters"]["filters"]["quality"] = {
            "min": self.quality
        }
        return data

# TODO: Make this work.
@attrs(auto_attribs=True)
class Beast(Searchable): pass

@attrs(auto_attribs=True)
class Map(Searchable):
    iiq: int = 0
    iir: int = 0
    pack_size: int = 0

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        build_map_bases()

        if self.rarity == "magic":
            logging.debug("Extracting base for magic map out of: %s" % self.base)
            base = get_map_base(self.base)
            if base:
                self.base = base
                logging.debug("Map base found and extracted: %s" % self.base)

    def get_json(self) -> Dict:
        '''
        

        :return: Map-specific JSON dictionary
        '''
        data = super().get_json()

        data["query"]["filters"]["map_filters"] = {
            "filters": {
                "map_tier": {
                    "min": self.ilevel,
                    "max": self.ilevel
                }
            }
        }

        if self.iiq:
            data["query"]["filters"]["map_filters"]["filters"]["map_iiq"] = {
                "min": self.iiq
            }

        if self.iir:
            data["query"]["filters"]["map_filters"]["filters"]["map_iir"] = {
                "min": self.iir
            }

        if self.pack_size:
            data["query"]["filters"]["map_filters"]["filters"]["map_packsize"] = {
                "min": self.pack_size
            }

        # If it's a blighted map, we'll include the blighted filter
        if self.base.startswith("Blighted"):
            data["query"]["filters"]["map_filters"]["filters"]["map_blighted"] = {
                "option": "true"
            }
            data["query"]["type"] = {
                "option": self.base.replace("Blighted ", '')
            }
        else:
            data["query"]["type"] = {
                "option": self.base
            }

        # Override the mods in json with just implicits; we do this
        # to carry over guardian/conqueror influences of a map
        mods = [
            mod for mod in self.modifiers
            if mod[0].type == ItemModifierType.IMPLICIT
        ]
        set_modifiers(data, mods)

        return data

@attrs(auto_attribs=True)
class Prophecy(Searchable):
    def get_json(self) -> Dict:
        data = super().get_json()
        data["query"]["name"] = self.base
        data["query"]["type"] = "Prophecy"
        return data

# Oils, Catalysts, Fossils, Incubators, and Resonators are all
# of currency rarity, and so they are taken care of by Currency.
@attrs(auto_attribs=True)
class Fragment(Searchable): pass

@attrs(auto_attribs=True)
class Essence(Searchable): pass

@attrs(auto_attribs=True)
class Scarab(Searchable): pass

@attrs(auto_attribs=True)
class Vial(Searchable): pass

@attrs(auto_attribs=True)
class Organ(Searchable):
    def get_json(self) -> Dict:
        '''
        In this subclass override, we carry over the stats produced by
        it's base, and produce a new JSON dictionary more specific to
        a Metamorph Organ.

        :return: POST query json data for a Metamorph Organ
        '''
        data = super().get_json()
        data = {
            "query": {
                "status": {
                    "option": "online"
                },
                # For the base, we only truly care about the last word
                # in the item's base: Organ, Heart, Lung, Eye, or Liver.
                "type": "Metamorph " + self.base.split(' ')[-1],
                "stats": data["query"]["stats"],
                "filters": {
                    "misc_filters": {
                        "filters": {
                            "ilvl": {
                                "min": self.ilevel
                            }
                        }
                    }
                }
            },
            "sort": {
                "price": "asc"
            }
        }
        return data

@attrs(auto_attribs=True)
class Flask(Searchable):
    name_prefixes = '|'.join([
        "Small",
        "Medium",
        "Large",
        "Greater",
        "Grand",
        "Giant",
        "Colossal",
        "Sacred",
        "Hallowed",
        "Sanctified",
        "Divine",
        "Eternal",
    ])

    def __attrs_post_init__(self):
        '''
        An extension of __attrs_post_init__ for the Flask subclass.
        Flasks have different layouts when copied, as the name is also
        included in the item's base field. In this extended override,
        we call the base class original method, then fix up self.base
        as needed for non-unique flasks.

        :return: None
        '''
        super().__attrs_post_init__()
        if self.rarity != "unique":
            # Extract the actual flask base out, and use it as the base
            # we search for. Since we also provide explicit modifiers
            # when performing the lookup, we will not miss prefixes
            # or suffixes.
            match = re.findall(
                r"([a-zA-Z']+ )?((?!%s)?[ ]?.+ Flask)( .*)?" % self.name_prefixes,
                self.base
            )
            self.base = match[0][1]

            logging.debug("Flask regex matches: %s" % str(match))
            logging.debug("Deduced flask base: %s" % str(self.base))

''' Specific Items '''
@attrs(auto_attribs=True)
class Accessory(Wearable): pass

@attrs(auto_attribs=True)
class Ring(Accessory):
    def sanitize_modifiers(self):
        '''
        Sanitize modifiers for a Ring specifically.

        :return: None
        '''
        # Some of the synthesised explicit mods are also standard enchanted
        # mods. Fix them up if this ring is synthesised.
        if self.synthesised:
            convert = [
                r'Herald of (Ash|Thunder) has #% reduced Mana Reservation',
                r'#% to Cold Resistance while affected by Herald of Ice',
            ]

            for i in range(len(self.modifiers)):
                for possible in convert:
                    mod = self.modifiers[i]
                    mod_text = mod[0].text
                    mod_type = ItemModifierType.EXPLICIT
                    logging.debug("Sanitizing %s" % str(mod))
                    if re.search(possible, mod_text):
                        sanitized_mod = get_item_modifiers_by_text(
                            (mod_text, mod_type)
                        )
                        if sanitized_mod:
                            self.modifiers[i] = (sanitized_mod, mod[1])
                            logging.debug(
                                "Altered mod to be explicit: %s" % str(self.modifiers[i])
                            )
                    else:
                        logging.debug("No sanitization needed")

@attrs(auto_attribs=True)
class Amulet(Accessory): pass

@attrs(auto_attribs=True)
class Belt(Accessory): pass

# Base class for any Armor-type Items located below this class
@attrs(auto_attribs=True)
class Armor(Wearable):
    '''
    Armor base class for any Armor-type items: Helmet, BodyArmor, Boots,
    Gloves, Shield.
    '''

    def sanitize_modifiers(self):
        '''
        Sanitize modifiers for an Armor base or subclass. With these items,
        we should convert certain global modifiers to local modifiers if we
        find them. This method modifies our modifiers attribute in-place.

        :return: None
        '''
        convert = [
            r'# to maximum (Energy Shield|Armou?r|Evasion Rating)',
            r'#% increased (Armour|Evasion( Rating)?|Energy Shield)(, .*)?( and )?(.*)?',
            r'# to (Armou?r|Energy Shield|Evasion Rating)',
        ]

        for i in range(len(self.modifiers)):
            for possible in convert:
                mod = self.modifiers[i]
                mod_text = mod[0].text
                mod_type = mod[0].type
                logging.debug("Sanitizing %s" % str(mod))
                if re.search(possible, mod_text):
                    altered = mod_text + " (Local)"
                    sanitized_mod = get_item_modifiers_by_text(
                        (altered, mod_type)
                    )
                    if sanitized_mod:
                        self.modifiers[i] = (sanitized_mod, mod[1])
                        logging.debug(
                            "Altered mod to be local: %s" % str(self.modifiers[i])
                        )
                else:
                    logging.debug("No sanitization needed")

@attrs(auto_attribs=True)
class Helmet(Armor): pass

@attrs(auto_attribs=True)
class BodyArmor(Armor): pass

@attrs(auto_attribs=True)
class Boots(Armor): pass

@attrs(auto_attribs=True)
class Gloves(Armor): pass

@attrs(auto_attribs=True)
class Shield(Armor): pass

@attrs(auto_attribs=True)
class Quiver(Wearable): pass

@attrs(auto_attribs=True)
class Jewel(Searchable): pass

@attrs(auto_attribs=True)
class Weapon(Wearable):
    def sanitize_modifiers(self):
        '''
        Sanitize modifiers for a Weapon or subclass of it. With these items,
        we should convert certain global modifiers to local modifiers if we
        find them. This method modifies our modifiers attribute in-place.

        :return: None
        '''
        convert = [
            r'increased Attack Speed',
            r'Adds # to # (.*) Damage',
            r'# to Accuracy Rating',
            r'#% chance to Poison on Hit',
        ]

        for i in range(len(self.modifiers)):
            for possible in convert:
                mod = self.modifiers[i]
                mod_text = mod[0].text
                mod_type = mod[0].type
                logging.debug("Sanitizing %s" % str(mod))
                if re.search(possible, mod_text):
                    altered = mod_text + " (Local)"
                    sanitized_mod = get_item_modifiers_by_text(
                        (altered, mod_type)
                    )
                    self.modifiers[i] = (sanitized_mod, mod[1])
                    logging.debug(
                        "Altered mod to be local: %s" % str(self.modifiers[i])
                    )
                else:
                    logging.debug("No sanitization needed")

