from typing import Dict

from enums.item_modifier_type import ItemModifierType
from models.item_modifier import ItemModifier


def build_from_json(blob: Dict) -> ItemModifier:
    return ItemModifier(id=blob["id"], text=blob["text"], type=ItemModifierType(blob["type"].lower()))
