import base64
import os
import sys

import Accounting
from tests.sampleItems import items

# Append the root directory to sys.path so we can import like normal.
BASE_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, ".."))


# A helper used to generate a mock dictionary response
# from a PoE/trade POST request.
#
# n: Number of trade results to generate.
# Returns mock dictionary response.
def mockResponse(n):
    return {
        # result0, result1, result2, ...
        "result": ["result%d" % i for i in range(n)],
        # Don't change this during mock for simplification
        "id": "mockID",
        "total": n,
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


def makePoePricesURL(i):
    return b"https://poeprices.info/api?l=Standard&i=" + base64.b64encode(
        bytes(items[i], "utf-8")
    )


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

    def winfo_id(self):
        return 0

    def resizable(self, x, y):
        pass

    def bind(self, t, f):
        pass

    def destroy(self):
        pass

    def config(self, *args, **kwargs):
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
