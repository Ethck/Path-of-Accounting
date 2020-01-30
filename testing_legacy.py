import io
import sys
import unittest

import parse
from utils import config
from tests.sampleItems import items


class TestItemLookup(unittest.TestCase):
    def test_lookups(self):
        config.USE_GUI = False
        for i in range(len(items)):
            with self.subTest(i=i):
                out = io.StringIO()
                sys.stdout = out
                parse.price_item(items[i])
                sys.stdout = sys.__stdout__
                alternate = "[!] Not enough data to confidently price this item."
                self.assertTrue("[$]" in out.getvalue() or alternate in out.getvalue())

if __name__ == "__main__":
    unittest.main()
