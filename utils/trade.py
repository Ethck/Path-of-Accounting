from itertools import chain
from typing import List, Tuple

import requests

from models.item_modifier import ItemModifier
from factories.item_modifier import build_from_json


def get_leagues() -> Tuple[str, ...]:
    leagues = requests.get(
        url="https://www.pathofexile.com/api/trade/data/leagues"
    ).json()
    return tuple(x["id"] for x in leagues["result"])


def get_item_modifiers() -> Tuple[ItemModifier, ...]:
    json_blob = requests.get(url="https://www.pathofexile.com/api/trade/data/stats").json()
    items = tuple(chain(*[[build_from_json(y) for y in x['entries']] for x in json_blob['result']]))
    return items

