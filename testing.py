import io
import sys
import unittest

import parse
from tests.sampleItems import items


class TestItemLookup(unittest.TestCase):
    def test_lookups(self):
        # Don't use gui during tests
        config.USE_GUI = False
        
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
                out = io.StringIO()
                sys.stdout = out
                parse.price_item(items[i])
                sys.stdout = sys.__stdout__
                self.assertTrue("[$]" in out.getvalue())


if __name__ == "__main__":
    unittest.main()
