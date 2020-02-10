
from gui.gui import DisplayWindow, ActiveWindow, close_all_windows
from utils.config import USE_GUI, MIN_RESULTS

import tkinter
import timeago
from datetime import datetime, timezone

class BaseResults(DisplayWindow):
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
                "hunter": "Hunter"
            }
            self.create_label_header("Influence: %s" % conversion[self.influence], 0, row, "WE")

        self.create_label_header("Item Level: %d" % self.ilvl, 0, row+1, "WE")
        self.create_label_header("Price: %d %s" % (self.price, self.currency), 0, row+2, "WE")

class NotEnoughInformation(DisplayWindow):
    def __init__(self):
        super().__init__()

    def add_components(self):
        self.create_label_header("Not Enough Data", 0, 0, "WE")
        self.create_label_header("Could not find enough data to confidently price this item.", 0, 1, "WE")


class PriceInformation(DisplayWindow):
    def __init__(self):
        super().__init__()
        self.data = None

    def add_price_information(self, data):
        self.data = data

    def add_components(self):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """
        self.create_label_header("", 0, 0, "WE", 4)
        self.create_label_header("Prices  ", 0, 0, "E")
        self.create_label_header("Avg. Time Listed", 1, 0, "E", 2)
        

        counter = 0
        # dict{price: [count , time]}
        for price, values in self.data.items():
            date = datetime.now().replace(tzinfo=timezone.utc)
            now = values[1]
            time = timeago.format(now, date)

            if counter % 2:
                self.create_label_BG1("", 0, counter + 2, "WE", 3)
                self.create_label_BG1(price + "  ", 0, counter + 2, "E")
                self.create_label_BG1(time + " (" + str(values[0]) + ")", 1, counter + 2, "E", 2)
            else:
                self.create_label_BG2("", 0, counter + 2, "WE", 3)
                self.create_label_BG2(price + "  ", 0, counter + 2, "E")
                self.create_label_BG2(time + " (" + str(values[0]) + ")", 1, counter + 2, "E", 2)
            counter += 1

        #self.create_label_header("", 0, counter + 3, "WE", 3)
        #self.create_label_header("Low:" + str(self.price[0]), 0, counter + 3, "W")
        #self.create_label_header("Avg:" + str(self.price[1]), 1, counter + 3, "WE")
        #self.create_label_header("High:" + str(self.price[2]), 2, counter + 3, "E")

        if len(self.data) < MIN_RESULTS:
            self.create_label_header("", 0, counter + 4, "WE", 3)
            self.create_label_header("Found limited search results", 0, counter+4, "WE", 3)
            self.create_label_header("", 0, counter + 5, "WE", 3)
            self.create_label_header("Use alt+t to search manually", 0, counter+5, "WE", 3)


priceInformation = PriceInformation()
notEnoughInformation = NotEnoughInformation()
baseResults = BaseResults()


        
