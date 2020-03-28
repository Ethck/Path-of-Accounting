from enum import Enum

from attr import attrs


class ItemModifierType(Enum):
    PSEUDO = "pseudo"
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    FRACTURED = "fractured"
    ENCHANT = "enchant"
    CRAFTED = "crafted"
    VEILED = "veiled"
    MONSTER = "monster"
    DELVE = "delve"


@attrs(auto_attribs=True)
class ItemModifier:
    type: ItemModifierType
    id: str
    text: str
    options: dict
