import logging
import copy
import timeit
from attr import attrs
from .item_modifier import ItemModifier
from utils.trade import get_ninja_bases

NINJA_BASES = []
TYPES = {}

@attrs(auto_attribs=True)
class Item:
    rarity: str = 'Rare'
    name: str = None
    base: str = None

    quality: int = 0
    # TODO: handle base stats
    stats: [str] = []

    raw_sockets: str = ''
    # Item level/ Map tier
    ilevel: int = 0

    modifiers: [(ItemModifier, str)] = []
    corrupted: bool = False
    mirrored: bool = False

    # A list of influences that affect the item.
    influence: [str] = []

    links: [int] = 0

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value

    def print_attributes(self, label = "Item"):
        logging.debug("====== %s ======" % label)
        for k, v in self:
            logging.debug("%s: %s" % (k, v))
        logging.debug("====== End of %s ======" % label)

    def print_class(self):
        self.print_attributes("Item")

    def __attrs_post_init__(self):
        if not self.base:
            self.base = self.name
            self.name = None
        sockets = self.raw_sockets.lower()
        self.r_sockets = sockets.count('r')
        self.b_sockets = sockets.count('b')
        self.g_sockets = sockets.count('g')
        self.w_sockets = sockets.count('w')
        self.a_sockets = sockets.count('a')  # abyssal
        # R-R-R-R R-R is not incorrectly registered as 5 link
        self.links = sockets.count('-') - sockets.count(' ') + 1

        if str(self.__class__.__name__) == "Item":
            self.print_attributes()

    def deduce_specific_object(self):
        # If we're already a different object, we will not perform this
        # conversion.
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

        global TYPES
        if len(TYPES) == 0:
            ninja_bases = get_ninja_bases()
            for e in ninja_bases:
                item_type = e["type"]
                item_base = e["base"]
                if item_base in TYPES:
                    continue
                if item_type in weapon_types:
                    TYPES[item_base] = Weapon
                elif item_type in other_types:
                    TYPES[item_base] = other_types[item_type]

        if self.base in TYPES:
            cls = TYPES[self.base]
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
        raise NotImplementedError

@attrs(auto_attribs=True)
class Map(Item):
    iiq: int = 0
    iir: int = 0
    pack_size: int = 0

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Map")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

@attrs(auto_attribs=True)
class Prophecy(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Prophecy")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

@attrs(auto_attribs=True)
class Fragment(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Fragment")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

@attrs(auto_attribs=True)
class Organ(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Organ")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

@attrs(auto_attribs=True)
class Flask(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Flask")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

''' Specific Items '''
@attrs(auto_attribs=True)
class Accessory(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()

        if str(self.__class__.__name__) == "Accessory":
            super().print_attributes("Accessory")

    def get_json(self):
        data = super().get_json()
        # Fill data with more json fields as needed.
        raise NotImplementedError

@attrs(auto_attribs=True)
class Ring(Accessory):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Ring")


@attrs(auto_attribs=True)
class Amulet(Accessory):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Ring")

@attrs(auto_attribs=True)
class Belt(Accessory):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Ring")

@attrs(auto_attribs=True)
class Helmet(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Helmet")

@attrs(auto_attribs=True)
class BodyArmor(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("BodyArmor")

@attrs(auto_attribs=True)
class Boots(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Boots")

@attrs(auto_attribs=True)
class Gloves(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Gloves")

@attrs(auto_attribs=True)
class Shield(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Shield")

@attrs(auto_attribs=True)
class Quiver(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Quiver")

@attrs(auto_attribs=True)
class Weapon(Item):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        super().print_attributes("Weapon")

