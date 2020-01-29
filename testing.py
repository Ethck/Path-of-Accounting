import io
import sys
import unittest
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

class TestItemLookup(unittest.TestCase):
    def test_lookups(self):
        # Mockups of response data from pathofexile.com/trade
        expected = [
            # (mocked up json response, expected condition)
            (mockResponse(11), lambda v: "[$]" in v),
            (mockResponse(12), lambda v: "[$]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(1), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(66), lambda v: "[$]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(0), lambda v: "[!]" in v),
            (mockResponse(10), lambda v: "[$]" in v),
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
                        LOOKUP_URL,
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
                    if len(expected[i][0]["result"]) >= config.MIN_RESULTS:
                        fetch_url = makeFetchURL(expected[i][0])
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

if __name__ == "__main__":
    init(autoreset=True) # Colorama
    unittest.main(failfast=True)
    deinit()
