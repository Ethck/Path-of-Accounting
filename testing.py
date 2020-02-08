import io
import sys
import unittest
from unittest.mock import patch
import requests_mock
import json
from collections import OrderedDict
from datetime import datetime, timezone
from colorama import Fore, deinit, init

import parse
from utils import config
from tests.mocks import *
from tests.sampleItems import items

LOOKUP_URL = "https://www.pathofexile.com/api/trade/search/Metamorph"
EXCHANGE_URL = "https://www.pathofexile.com/api/trade/exchange/Metamorph"


class TestItemLookup(unittest.TestCase):

    @patch('tkinter.Tk', TkMock)
    @patch('tkinter.Toplevel', ToplevelMock)
    @patch('tkinter.Frame', FrameMock)
    @patch('tkinter.Label', LabelMock)
    @patch('tkinter.Button', ButtonMock)
    @patch('screeninfo.get_monitors', mock_get_monitors)
    @patch('time.sleep', lambda s: s)
    @patch('utils.config.USE_GUI', True)
    def test_lookups(self):
        # Required to do the gui creation step in tests. We need to
        # create it here, after we patch our python modules.
        parse.create_gui()

        # Mockups of response data from pathofexile.com/trade
        expected = [
            # (mocked up json response, expected condition, search url)
            (mockResponse(11), lambda v: "[$]" in v, LOOKUP_URL),
            (mockResponse(12), lambda v: "[$]" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(1), lambda v: "[!] Not enough data to confidently price this item" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(66), lambda v: "[$]" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            # 14th item in sampleItems is a divination card, which is looked
            # up via exchange URL instead of search.
            (mockResponse(0), lambda v: "[!] No results!" in v, EXCHANGE_URL),
            (mockResponse(0), lambda v: "[!] No results!" in v, LOOKUP_URL),
            (mockResponse(10), lambda v: "[$]" in v, LOOKUP_URL),
        ]

        # Mocked up prices to return when searching. We only take the first
        # 10 results from any search. We don't have to worry about sorting by
        # price here, as we know that PoE/trade sorts by default.
        prices = [
            [ # List 1
                (45, "alch"),
            ] * 10,
            [ # List 2
                # 5 x 1 chaos
                *(((1, "chaos"),) * 5),
                # 1 x 3 chaos
                (3, "chaos"),
                # 4 x 2 alch
                *(((2, "alch"),) * 4)
            ],
            [], # List 3
            [], # List 4
            [ # List 5
                (666, "exa")
            ],
            [], # List 6
            [], # List 7
            [], # List 8
            [], # List 9
            [], # List 10
            [ # List 11
                (2.5, "mir")
            ] * 10,
            [], # List 12
            [], # List 13
            [], # List 14
            [], # List 15
            [ # List 16
                (1, "fuse")
            ] * 10,
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
                    mock.post(
                        expected[i][2],
                        json=expected[i][0]
                    )

                    response = {
                        "result": [
                            {
                                "id": "result%d" % x,
                                "listing": {
                                    # Mocked account name of the lister
                                    "account": { "name": "account%d" % x },

                                    # Price of this item result; we should mock
                                    # and test against this amount.
                                    "price": {
                                        "type": "~",
                                        "amount": sortedPrices[x][0],
                                        "currency": sortedPrices[x][1]
                                    },

                                    # Indexed now.
                                    "indexed": datetime.strftime(
                                        datetime.now(timezone.utc),
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    ),
                                }
                            } for x in range(min(expected[i][0]["total"], 10))
                        ]
                    }
                    # If we have at least MIN_RESULTS items, we should mock
                    # the GET request for fetching the first 10 items.
                    # See search_item's pathing in parse.py
                    if len(expected[i][0]["result"]) >= 0:
                        fetch_url = makeFetchURL(
                            expected[i][0],
                            # True if the expected item's search url is EXCHANGE_URL
                            expected[i][2] == EXCHANGE_URL
                        )
                        mock.get(fetch_url, json=response)

                    # Callout to API and price the item
                    parse.price_item(items[i])

                # Get the expected condition
                currentExpected = expected[i][1]

                # Restore stdout and assert that the expected condition is true
                sys.stdout = sys.__stdout__

                # Expect that our truthy condition is true
                self.assertTrue(currentExpected(out.getvalue()))

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
                            ("%d x %s" + fmt + " %s") % (
                                v, Fore.YELLOW, k[0], k[1]
                            )
                        )
                    expectedStr = ("%s, " % Fore.WHITE).join(priceList)
                    self.assertTrue(expectedStr in out.getvalue())

    @patch('tkinter.Tk', TkMock)
    @patch('tkinter.Toplevel', ToplevelMock)
    @patch('tkinter.Frame', FrameMock)
    @patch('tkinter.Label', LabelMock)
    @patch('tkinter.Button', ButtonMock)
    @patch('screeninfo.get_monitors', mock_get_monitors)
    @patch('time.sleep', lambda s: s)
    @patch('utils.config.USE_GUI', True)
    def test_base_lookups(self):
        # Required to do the gui creation step in tests. We need to
        # create it here, after we patch our python modules.
        parse.create_gui()

        # Mock json data for poe.ninja bases
        data = {
            "lines": [
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": None,
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Elder",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Shaper",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Warlord",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Redeemer",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Crusader",
                    "corrupted": True,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                },
                {
                    "baseType": "Boot Blade",
                    "levelRequired": 84,
                    "variant": "Hunter",
                    "corrupted": False,
                    "exaltedValue": 0.5,
                    "chaosValue": 80.0
                }
            ]
        }

        expected = [
            lambda v: "[$]" in v,
            lambda v: "[!]" in v
        ]

        # Needs mocking to prepare NINJA_BASES properly in parse.py
        with requests_mock.Mocker() as mock:
            mock.get("https://poe.ninja/api/data/itemoverview?league=Metamorph&type=BaseType&language=en", json=data)
            #parse.NINJA_BASES = parse.get_ninja_bases()

        for i in range(len(items[:2])):
            item = items[i]

            out = io.StringIO()
            sys.stdout = out

            #parse.search_ninja_base(item)

            sys.stdout = sys.__stdout__

            self.assertTrue(expected[i](out.getvalue()))

        # We'll take the first sample item and modify it so that we
        # can match against all types of influences we support.
        item = items[0]

        supportedInfluence = [
            "Elder",
            "Shaper",
            "Warlord",
            "Redeemer",
            "Crusader",
            "Hunter"
        ]

        for inf in supportedInfluence:
            current = item + ("%s Item\n" % inf)

            out = io.StringIO()
            sys.stdout = out

            parse.search_ninja_base(current)

            sys.stdout = sys.__stdout__

            self.assertTrue(expected[0](out.getvalue()))

if __name__ == "__main__":
    init(autoreset=True) # Colorama
    unittest.main(failfast=True)
    deinit()
