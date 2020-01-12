from typing import List, Tuple
import requests


def get_leagues() -> Tuple[str, ...]:
    leagues = requests.get(url="https://www.pathofexile.com/api/trade/data/leagues").json()
    return tuple(x['id'] for x in leagues['result'])
