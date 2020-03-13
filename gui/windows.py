from datetime import datetime, timezone

import timeago

from gui.gui import DisplayWindow
from utils.config import MIN_RESULTS


class BaseResults(DisplayWindow):
    """Basic results window"""

    def __init__(self):
        super().__init__()
        self.base = None
        self.influence = None
        self.ilvl = None
        self.price = None
        self.currency = None

    def add_base_result(self, base, influence, ilvl, price, currency):
        self.base = base
        self.influence = influence
        self.ilvl = ilvl
        self.price = price
        self.currency = currency

    def add_components(self):
        """
        Assemble a simple poe.ninja result when searching for the
        worth of an item base, including it's influence and item level.
        """

        self.create_label_header("Base: %s" % self.base, 0, 0, "WE")

        row = 0
        if self.influence is not None:
            row += 1
            conversion = {
                "elder": "Elder",
                "shaper": "Shaper",
                "redeemer": "Redeemer",
                "crusader": "Crusader",
                "warlord": "Warlord",
                "hunter": "Hunter",
            }
            self.create_label_header(
                "Influence: %s" % conversion[self.influence], 0, row, "WE"
            )

        self.create_label_header(
            "Item Level: %d" % self.ilvl, 0, row + 1, "WE"
        )
        self.create_label_header(
            "Price: %d %s" % (self.price, self.currency), 0, row + 2, "WE"
        )


class NotEnoughInformation(DisplayWindow):
    """Window to display when we determine there is not enough information to accurately price"""

    def __init__(self):
        super().__init__()

    def add_components(self):
        self.create_label_header("Not Enough Data", 0, 0, "WE")
        self.create_label_header(
            "Relying on data from PoEPrices", 0, 1, "WE",
        )


class Information(DisplayWindow):
    def __init__(self):
        super().__init__()
        self.info = None

    def add_info(self, info):
        self.info = info

    def add_components(self):
        self.create_label_header(self.info, 0, 1, "WE")


class PriceInformation(DisplayWindow):
    """Window to display prices of found items"""

    def __init__(self):
        super().__init__()
        self.data = None
        self.offline = False

    def add_price_information(self, data, offline=False):
        self.data = data
        self.offline = offline

    def add_components(self):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """
        self.create_label_header("", 0, 0, "WE", 4)
        self.create_label_header("Prices  ", 0, 0, "E")
        self.create_label_header("Avg. Time Listed", 1, 0, "E", 2)

        counter = 0
        count = 0
        # dict{price: [count , time]}
        for price, values in self.data.items():
            date = datetime.now().replace(tzinfo=timezone.utc)
            now = values[1]
            time = timeago.format(now, date)
            count += values[0]
            if counter % 2:
                self.create_label_BG1("", 0, counter + 2, "WE", 3)
                self.create_label_BG1(price + "  ", 0, counter + 2, "E")
                self.create_label_BG1(
                    time + " (" + str(values[0]) + ")", 1, counter + 2, "E", 2
                )
            else:
                self.create_label_BG2("", 0, counter + 2, "WE", 3)
                self.create_label_BG2(price + "  ", 0, counter + 2, "E")
                self.create_label_BG2(
                    time + " (" + str(values[0]) + ")", 1, counter + 2, "E", 2
                )
            counter += 1

        # self.create_label_header("", 0, counter + 3, "WE", 3)
        # self.create_label_header("Low:" + str(self.price[0]), 0, counter + 3, "W")
        # self.create_label_header("Avg:" + str(self.price[1]), 1, counter + 3, "WE")
        # self.create_label_header("High:" + str(self.price[2]), 2, counter + 3, "E")

        counter = counter + 4
        if self.offline:
            self.create_label_header(
                "[!] Offline Results", 0, counter, "WE", 3
            )
            counter += 1

        if count < MIN_RESULTS:
            self.create_label_header(
                "Found limited search results", 0, counter, "WE", 3
            )
            self.create_label_header(
                "Use alt+t to search manually", 0, counter + 1, "WE", 3
            )


priceInformation = PriceInformation()
notEnoughInformation = NotEnoughInformation()
baseResults = BaseResults()
information = Information()
