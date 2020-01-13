from enum import Enum


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
