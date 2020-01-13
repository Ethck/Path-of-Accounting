from attr import attrs, attrib

from enums.item_modifier_type import ItemModifierType


@attrs(auto_attribs=True)
class ItemModifier:
    type: ItemModifierType
    id: str
    text: str
