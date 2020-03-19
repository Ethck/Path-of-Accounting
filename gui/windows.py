from datetime import datetime, timezone
from math import floor

import timeago
from timeago import locales
from timeago.locales import en

from gui.gui import DisplayWindow
from item.generator import Weapon
from utils import config
from utils.config import MIN_RESULTS


class BaseResults(DisplayWindow):
    """DisplayWindow for the poe.ninja base check results."""

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
            self.create_label_header(
                "Influence: %s" % self.influence.title(), 0, row, "WE"
            )

        self.create_label_header(
            "Item Level: %d" % self.ilvl, 0, row + 1, "WE"
        )
        self.create_label_header(
            "Price: %d %s" % (self.price, self.currency), 0, row + 2, "WE"
        )

        self.base = None
        self.influence = None
        self.ilvl = None
        self.price = None
        self.currency = None


class NotEnoughInformation(DisplayWindow):
    """Window to display when we determine there is not enough information to accurately price"""

    def __init__(self):
        super().__init__()
        self.price = None

    def add_poe_info_price(self, price):
        self.price = price

    def add_components(self):
        self.create_label_header("No matching results found!", 0, 0, "WE")

        if self.price:
            self.create_label_header(
                "PoEPrices machine learning result:", 0, 1, "WE",
            )
            txt = ""
            if "min" in self.price:
                txt = txt + "Min: [" + str(round(self.price["min"], 2)) + "] "
            if "max" in self.price:
                txt = txt + "Max: [" + str(round(self.price["max"], 2)) + "] "
            if "currency" in self.price:
                txt = txt + "[" + self.price["currency"] + "] "
            if "pred_confidence_score" in self.price:
                txt = (
                    txt
                    + "Confidence: "
                    + str(floor(self.price["pred_confidence_score"]))
                    + "% "
                )

            self.create_label_header(txt, 0, 2)
        self.price = None


class Information(DisplayWindow):
    def __init__(self):
        super().__init__()
        self.info = None

    def add_info(self, info):
        self.info = info

    def add_components(self):
        if self.info:
            self.create_label_header(self.info, 0, 1, "WE")

        self.info = None


class GearInformation(DisplayWindow):
    """DisplayWindow for the stat check feature for weapons."""

    def __init__(self):
        super().__init__()
        self.item = None

    def add_info(self, item):
        self.item = item

    def add_components(self):

        if self.item:
            self.create_label_header(self.item.name, 0, 0, "W")
        if isinstance(self.item, Weapon):
            self.create_label_BG2(
                "Phys DPS: " + str(self.item.pdps), 0, 1, "W"
            )
            self.create_label_BG1("Ele DPS: " + str(self.item.edps), 0, 2, "W")
            self.create_label_BG2(
                "Total DPS: " + str(self.item.pdps + self.item.edps), 0, 3, "W"
            )
            self.create_label_BG1("Speed: " + str(self.item.speed), 0, 4, "W")
            self.create_label_BG2("Crit: " + str(self.item.crit), 0, 5, "W")
        else:
            self.create_label_header("No extra info yet!", 0, 1, "W")

        self.item = None


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
                "Use " + config.ADV_SEARCH + " to search manually",
                0,
                counter + 1,
                "WE",
                3,
            )
        self.data = None
        self.offline = False


priceInformation = PriceInformation()
notEnoughInformation = NotEnoughInformation()
baseResults = BaseResults()
information = Information()
gearInformation = GearInformation()
