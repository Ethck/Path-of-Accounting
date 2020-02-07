from attr import attrib, attrs

from enums.item_modifier_type import ItemModifierType

@attrs(auto_attribs=True, frozen=True)
class ItemModifier:
    type: ItemModifierType
    id: str
    text: str

