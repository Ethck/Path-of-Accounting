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
def makeFetchURL(result, exchange=False):
    url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(result["result"][0:10])}?query={result["id"]}'
    if exchange:
        url += "exchange=true"
    return url

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

class TkMockObject:
    def __init__(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def place(self, *args, **kwargs):
        pass

    def withdraw(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def wm_attributes(self, *args, **kwargs):
        pass

    def show(self, *args, **kwargs):
        pass

    def hide(self, *args, **kwargs):
        pass

    def winfo_children(self):
        return []

    def winfo_pointerx(self):
        return 0

    def winfo_pointery(self):
        return 0

    def winfo_x(self):
        return 0

    def winfo_y(self):
        return 0

    def winfo_width(self):
        return 200

    def winfo_height(self):
        return 200

    def geometry(self, geo):
        pass

    def deiconify(self):
        pass

    def overrideredirect(self, *args, **kwargs):
        pass

    def option_add(self, *args, **kwargs):
        pass

    def after(self, *args, **kwargs):
        pass

    def quit(self, *args, **kwargs):
        pass

    def mainloop(self, *args, **kwargs):
        pass

# Mock up Tkinter classes
class TkMock(TkMockObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class LabelMock(TkMockObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ButtonMock(TkMockObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ToplevelMock(TkMockObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class FrameMock(TkMockObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class MonitorMock:
    height = 200
    width = 200
    x = 0
    y = 0

def mock_get_monitors():
    return [MonitorMock()]

