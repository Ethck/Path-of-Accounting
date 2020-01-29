import sys
import os

# Append the root directory to sys.path so we can import like normal.
BASE_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, ".."))

import parse

# A helper used to generate a mock dictionary response
# from a PoE/trade POST request.
#
# n: Number of trade results to generate.
# Returns mock dictionary response.
def mockResponse(n):
    return {
        # result0, result1, result2, ...
        "result": [
            "result%d" % i for i in range(n)
        ],
        # Don't change this during mock for simplification
        "id": "mockID",
        "total": n
    }

# A helper that takes a JSON result from PoE/trade search and generates
# a URL used to fetch the items after the POST request.
#
# result: A MockResponse dict-converted value
# Returns a formatted fetch URL.
def makeFetchURL(result):
    return f'https://www.pathofexile.com/api/trade/fetch/{",".join(result["result"][0:10])}?query={result["id"]}'

# A simple helper function that generates the (info, json) of
# an item before using them to search the item on PoE/trade.
#
# Returns a tuple (item info, json data)
def makeItemInfo(item):
    info = parse.parse_item_info(items[i])
    data = parse.build_json_official(
        **{
            k: v
            for k, v in info.items()
            if k
            in (
                "name",
                "itype",
                "ilvl",
                "links",
                "corrupted",
                "influenced",
                "stats",
                "rarity",
                "gem_level",
                "quality",
                "maps",
            )
        },
    )
    return (info, data)
