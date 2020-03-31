import io
import json
import sys
import unittest
from collections import OrderedDict
from datetime import datetime, timezone
from unittest.mock import patch

import requests_mock
from colorama import Fore, deinit, init

import Accounting
from gui.gui import close_all_windows, init_gui
from tests.mocks import *
from tests.sampleItems import items
from utils import config, web

LOOKUP_URL = "https://www.pathofexile.com/api/trade/search/Standard"
EXCHANGE_URL = "https://www.pathofexile.com/api/trade/exchange/Standard"


class TestItemLookup(unittest.TestCase):
    @patch("tkinter.Tk", TkMock)
    @patch("tkinter.Toplevel", ToplevelMock)
    @patch("tkinter.Frame", FrameMock)
    @patch("tkinter.Label", LabelMock)
    @patch("tkinter.Button", ButtonMock)
    @patch("screeninfo.get_monitors", mock_get_monitors)
    @patch("time.sleep", lambda s: s)
    @patch("utils.config.USE_GUI", True)
    @patch("os.name", "Mock")
    def test_lookups(self):
        # Required to do the gui creation step in tests. We need to
        # create it here, after we patch our python modules.
        init_gui()
        config.LEAGUE = "Standard"

        # Mockups of response data from pathofexile.com/trade
        expected = [
            # (mocked up json response, expected condition, search url)
            (mockResponse(11), lambda v: "[$]" in v, LOOKUP_URL),  # 0
            (mockResponse(12), lambda v: "[$]" in v, LOOKUP_URL),  # 1
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 2
            (mockResponse(10), lambda v: "[$]" in v, LOOKUP_URL,),  # 3
            (
                mockResponse(1),
                lambda v: "INFO:root:[!] Not enough data to confidently price this item"  # 4
                in v,
                LOOKUP_URL,
            ),
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 5
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 6
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 7
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 8
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 9
            (mockResponse(66), lambda v: "[$]" in v, LOOKUP_URL),  # 10
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 11
            (mockResponse(0), lambda v: "INFO:root:" in v, LOOKUP_URL,),  # 12
            # 13 item in sampleItems is a divination card, which is looked
            # up via exchange URL instead of search.
            (
                mockResponse(0),
                lambda v: "INFO:root:" in v,
                EXCHANGE_URL,
            ),  # 13
            (mockResponse(10), lambda v: "[$]" in v, LOOKUP_URL,),  # 14
            (mockResponse(10), lambda v: "[$]" in v, LOOKUP_URL),  # 15
        ]

        # Mocked up prices to return when searching. We only take the first
        # 10 results from any search. We don't have to worry about sorting by
        # price here, as we know that PoE/trade sorts by default.
        prices = [
            [(45, "Alch"),] * 10,  # List 0
            [  # List 1
                # 5 x 1 chaos
                *(((1, "Chaos"),) * 5),
                # 1 x 3 chaos
                (3, "Chaos"),
                # 4 x 2 alch
                *(((2, "Alch"),) * 4),
            ],
            [],  # List 2
            [(1, "Chaos")] * 10,  # List 3
            [(666, "Exa")],  # List 4
            [],  # List 5
            [],  # List 6
            [],  # List 7
            [],  # List 8
            [],  # List 9
            [(2.5, "Mir")] * 10,  # List 10
            [],  # List 11
            [],  # List 12
            [],  # List 13
            [(25, "Chaos")] * 10,  # List 14
            [(1, "Fuse")] * 10,  # List 15
        ]

        for i in range(len(items)):
            with self.subTest(i=i):
                sortedPrices = sorted(prices[i])
                priceCount = OrderedDict()
                for price in sortedPrices:
                    if price in priceCount:
                        priceCount[price] += 1
                    else:
                        priceCount[price] = 1

                # Middleman our stdout, so we can check programmatically
                out = io.StringIO()
                sys.stdout = out

                # Mockup response
                with requests_mock.Mocker() as mock:
                    mock.post(expected[i][2], json=expected[i][0])
                    with open("tests/mockModifiers.txt") as f:
                        mock.get(
                            "https://www.pathofexile.com/api/trade/data/stats",
                            json=json.load(f),
                        )
                    with open("tests/mockItems.txt") as f:
                        mock.get(
                            "https://www.pathofexile.com/api/trade/data/items",
                            json=json.load(f),
                        )

                    poePricesRes = {
                        "min": 57.760000000000005,
                        "max": 86.64,
                        "currency": "chaos",
                        "warning_msg": "",
                        "error": 0,
                        "pred_explanation": [
                            [
                                "(pseudo) (total) +# to maximum Life",
                                0.6233922907451513,
                            ],
                            [
                                "(pseudo) # Elemental Resistances",
                                0.05952270963592211,
                            ],
                            ["+# Life gained on Kill", 0.00895634747376225],
                            [
                                "(pseudo) (total) +#% to Lightning Resistance",
                                0.003846337537816363,
                            ],
                            [
                                "(pseudo) (total) +#% to Fire Resistance",
                                -0.013732066984023333,
                            ],
                            ["ES", -0.018150229290251393],
                            [
                                "(pseudo) (total) +#% to Cold Resistance",
                                -0.025894263910260087,
                            ],
                            [
                                "(pseudo) +#% total Elemental Resistance",
                                -0.24650575442281308,
                            ],
                        ],
                        "pred_confidence_score": 85.2540600516464,
                        "error_msg": "",
                    }

                    mock.get(
                        makePoePricesURL(i), json=poePricesRes,
                    )

                    response = {
                        "result": [
                            {
                                "id": "result%d" % x,
                                "listing": {
                                    # Mocked account name of the lister
                                    "account": {"name": "account%d" % x},
                                    # Price of this item result; we should mock
                                    # and test against this amount.
                                    "price": {
                                        "type": "~",
                                        "amount": sortedPrices[x][0],
                                        "currency": sortedPrices[x][1],
                                    },
                                    # Indexed now.
                                    "indexed": datetime.strftime(
                                        datetime.now(timezone.utc),
                                        "%Y-%m-%dT%H:%M:%SZ",
                                    ),
                                },
                            }
                            for x in range(min(expected[i][0]["total"], 10))
                        ]
                    }
                    # If we have at least MIN_RESULTS items, we should mock
                    # the GET request for fetching the first 10 items.
                    # See search_item's pathing in parse.py
                    if len(expected[i][0]["result"]) >= 0:
                        fetch_url = makeFetchURL(
                            expected[i][0],
                            # True if the expected item's search url is EXCHANGE_URL
                            expected[i][2] == EXCHANGE_URL,
                        )
                        mock.get(fetch_url, json=response)

                    # Callout to API and price the item
                    with self.assertLogs(level="INFO") as logger:
                        Accounting.basic_search(items[i])
                        [output] = logger.output[-1:]

                        # Get the expected condition
                        currentExpected = expected[i][1]

                        # Expect that our truthy condition is true
                        self.assertTrue(currentExpected(output))

                        if len(expected[i][0]["result"]) >= config.MIN_RESULTS:
                            # Expect that the currency is output properly, including
                            # the color(s) expected.
                            priceList = []
                            for k, v in priceCount.items():
                                # Normalize any non-integer decimal number. That is,
                                # if k[0] == int(k[0]), output it as a pure integer.
                                # Otherwise, use the string formatter, so 2.750
                                # becomes 2.75 but retains it's floating pointness.
                                fmt = "%i" if int(k[0]) == k[0] else "%s"
                                priceList.append(
                                    ("%s" + fmt + " %s" + Fore.RESET + " x %d")
                                    % (Fore.YELLOW, k[0], k[1], v)
                                )
                            expectedStr = "INFO:root:[$] Prices: " + (
                                ", "
                            ).join(priceList)
                            self.assertTrue(expectedStr in logger.output[-1:])
        close_all_windows()


class TestBaseLookup(unittest.TestCase):
    @patch("tkinter.Tk", TkMock)
    @patch("tkinter.Toplevel", ToplevelMock)
    @patch("tkinter.Frame", FrameMock)
    @patch("tkinter.Label", LabelMock)
    @patch("tkinter.Button", ButtonMock)
    @patch("screeninfo.get_monitors", mock_get_monitors)
    @patch("time.sleep", lambda s: s)
    @patch("utils.config.USE_GUI", True)
    @patch("os.name", "Mock")
    def test_base_lookups(self):
        # Required to do the gui creation step in tests. We need to
        # create it here, after we patch our python modules.
        init_gui()
        config.LEAGUE = "Standard"

        # Mock json data for poe.ninja bases
        data = {
            "lines": [
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": None,
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Elder",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Shaper",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Warlord",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Redeemer",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Crusader",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Hunter",
                    "corrupted": False,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0,
                    "itemType": "Dagger",
                },
            ]
        }

        expected = [lambda v: "[$]" in v, lambda v: "[!]" in v]

        with requests_mock.Mocker(real_http=True) as mock:
            web.ninja_bases = []
            mock.get(
                "https://poe.ninja/api/data/itemoverview?league=Standard&type=BaseType&language=en",
                json=data,
            )
            with open("tests/mockModifiers.txt") as f:
                mock.get(
                    "https://www.pathofexile.com/api/trade/data/stats",
                    json=json.load(f),
                )
            with open("tests/mockItems.txt") as f:
                mock.get(
                    "https://www.pathofexile.com/api/trade/data/items",
                    json=json.load(f),
                )

            for i in range(len(items[:2])):
                item = items[i]
                with self.assertLogs(level="INFO") as logger:
                    Accounting.search_ninja_base(item)
                    [output] = logger.output[-1:]
                    self.assertTrue(expected[i](output))

            # We'll take the first sample item and modify it so that we
            # can match against all types of influences we support.
            item = items[0]

            supportedInfluence = [
                "Elder",
                "Shaper",
                "Warlord",
                "Redeemer",
                "Crusader",
                "Hunter",
            ]

            for inf in supportedInfluence:
                current = item + ("\n--------\n%s Item\n" % inf)
                with self.assertLogs(level="INFO") as logger:
                    Accounting.search_ninja_base(current)
                    [output] = logger.output[-1:]
                    self.assertTrue(expected[0](output))
        close_all_windows()


if __name__ == "__main__":
    init(autoreset=True)  # Colorama
    unittest.main(failfast=True)
    deinit()
