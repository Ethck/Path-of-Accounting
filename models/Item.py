import logging
from attr import attrs
from .item_modifier import ItemModifier

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
