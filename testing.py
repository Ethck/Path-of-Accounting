import io
import sys
import unittest

import parse
from tests.sampleItems import items


class TestItemLookup(unittest.TestCase):
    def test_lookups(self):
        for i in range(len(items)):
            with self.subTest(i=i):
                out = io.StringIO()
                sys.stdout = out
                parse.price_item(items[i])
                sys.stdout = sys.__stdout__
                self.assertTrue("[$]" in out.getvalue())


if __name__ == "__main__":
    unittest.main()
