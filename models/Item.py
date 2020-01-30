from attr import attrs

from models.item_modifier import ItemModifier


@attrs(auto_attribs=True)
class Item:
    rarity: str = 'Rare'
    name: str = 'Pseudo'
    base: str = 'Pseudo'

    quality: int = 0
    # TODO: handle base stats
    stats: [str] = []

    # can we use a named tuple here?
    level: str = 0  # also use for tier?
    str: int = 0
    dex: int = 0
    int: int = 0

    raw_sockets: str = ''
    r_sockets: int = 0
    b_sockets: int = 0
    g_sockets: int = 0
    w_sockets: int = 0
    links: int = 0

    modifiers: [ItemModifier] = []
    corrupted: bool = False

    # TODO: handle influence types, as an enum?
    influence: str = ''

    # optionals
    # Some items have their class included (e.g. Rune Dagger for base Boot Blade)
    item_class: str = ''

    # do we need type to differentiate between item/gem/jewls/cards/currency?
    type: str = 'Pseudo'

    flavour_text: str = ''
    instruction_text: str = ''
    stack_size: int = 0