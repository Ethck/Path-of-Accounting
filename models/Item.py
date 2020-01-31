from attr import attrs

from .item_modifier import ItemModifier


@attrs(auto_attribs=True)
class Item:
    rarity: str = 'Rare'
    name: str = 'Pseudo'
    base: str = 'Pseudo'

    quality: int = 0
    # TODO: handle base stats
    stats: [str] = []

    raw_sockets: str = ''

    modifiers: [ItemModifier] = []
    corrupted: bool = False

    # TODO: handle influence types, as an enum?
    influence: str = ''

    def __attrs_post_init__(self):
        sockets = self.raw_sockets.lower()
        self.r_sockets = sockets.count('r')
        self.b_sockets = sockets.count('b')
        self.g_sockets = sockets.count('g')
        self.w_sockets = sockets.count('w')
        # R-R-R-R R-R is not incorrectly registered as 5 link
        self.links = sockets.split(' ')[0].count('-') + 1

    def get_pseudo_mods(self):
        raise NotImplementedError

    def get_json(self):
        raise NotImplementedError
