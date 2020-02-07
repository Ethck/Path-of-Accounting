import logging
import copy
import re
from attr import attrs
from .item_modifier import ItemModifier
from enums.item_modifier_type import ItemModifierType
from utils.trade import (
    get_ninja_bases,
    get_item_modifiers_by_text,
    search_url,
    exchange_url
)

# A global type cache for Base -> Item derivative conversions
types = dict()

def set_modifiers(json_data, modifiers):
    '''
    :param json_data: Root json dictionary to set modifiers of
    :param modifiers: List of modifiers
    :return: Altered json dictionary
    '''

    # Temporary hack. This is allowing us to search up mods with values
    # that we store separated by commas, like Adds # to # Physical Damage.
    mods = []
    for e in modifiers:
        if ',' in e[1]:
            value = re.sub(r',.*', '', e[1])
            mods.append({ "id": e[0].id, "value": { "min": int(value) }})
        else:
            mods.append({ "id": e[0].id, "value": { "min": int(e[1]) }})

    '''
    mods = [
        {
            "id": e[0].id,
            "value": {
                "min": int(e[1]) if ',' not in e[1] else e[1]
            }
        } for e in modifiers
    ]
    '''
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
        # If we're already a different object, turn this into a no-op method
        if str(self.__class__.__name__) != "Item":
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

        if self.base in types:
            cls = types[self.base]
            logging.debug(
                "Found base's type and converted the Item to %s" % cls.__class__.__name__
            )
            kwargs = copy.copy(self.__dict__)
            for k in ("r_sockets", "b_sockets", "g_sockets", "w_sockets", "a_sockets"):
                del kwargs[k]
            return cls(**kwargs)

        logging.error(
            "deduce_specific_object was called via Item, "
            + "but no base could be found to be converted"
        )
        return self

    def get_pseudo_mods(self):
        raise NotImplementedError

    def get_json(self):
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
    def query_url(self, league):
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

    def get_json(self):
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

    def query_url(self, league):
        '''
        :param league: Path of Exile league to format the query URL with
        :return: A formatted string of the PoE exchange trade API endpoint
        '''
        return exchange_url(league)

@attrs(auto_attribs=True)
class Wearable(Searchable):
    def get_json(self):
        data = super().get_json()
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
    def get_json(self):
        data = super().get_json()
        data["query"]["filters"]["misc_filters"]["filters"]["gem_level"] = {
            "min": self.ilevel
        }
        data["query"]["filters"]["misc_filters"]["filters"]["quality"] = {
            "min": self.quality
        }
        return data

# TODO: Implement this.
@attrs(auto_attribs=True)
class Beast(Searchable): pass

@attrs(auto_attribs=True)
class Map(Searchable):
    iiq: int = 0
    iir: int = 0
    pack_size: int = 0

    def get_json(self):
        data = super().get_json()

        data["query"]["filters"]["map_filters"] = {
            "filters": {
                "map_iiq": {
                    "min": self.iiq
                },
                "map_iir": {
                    "min": self.iir
                },
                "map_packsize": {
                    "min": self.pack_size
                },
                "map_tier": {
                    "min": self.ilevel,
                    "max": self.ilevel
                }
            }
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
    def get_json(self):
        data = super().get_json()
        data["query"]["name"] = self.base
        data["query"]["type"] = "Prophecy"
        return data

@attrs(auto_attribs=True)
class Fragment(Searchable): pass

@attrs(auto_attribs=True)
class Organ(Searchable):
    def get_json(self):
        '''
        In this subclass override, we carry over the stats produced by
        it's base, and produce a new JSON dictionary more specific to
        a Metamorph Organ.

        :return: POST query json data for a Metamorph Organ
        '''
        data = super().get_json()
        data = {
            "query": {
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
class Ring(Accessory): pass

@attrs(auto_attribs=True)
class Amulet(Accessory): pass

@attrs(auto_attribs=True)
class Belt(Accessory): pass

# Base class for any Armor-type Items located below this class
@attrs(auto_attribs=True)
class Armor(Wearable):
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
                print("Sanitizing %s" % str(mod))
                if re.search(possible, mod_text):
                    altered = mod_text + " (Local)"
                    sanitized_mod = get_item_modifiers_by_text((altered, mod_type))
                    self.modifiers[i] = (sanitized_mod, mod[1])
                    print("Altered mod to be local: %s" % str(self.modifiers[i]))
                else:
                    print("No sanitization needed")

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
class Weapon(Wearable):
    def sanitize_modifiers(self):
        '''
        Sanitize modifiers for an Weapon base or subclass. With these items,
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
                print("Sanitizing %s" % str(mod))
                if re.search(possible, mod_text):
                    altered = mod_text + " (Local)"
                    sanitized_mod = get_item_modifiers_by_text((altered, mod_type))
                    self.modifiers[i] = (sanitized_mod, mod[1])
                    print("Altered mod to be local: %s" % str(self.modifiers[i]))
                else:
                    print("No sanitization needed")

