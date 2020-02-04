
from gui.gui import DisplayWindow, ActiveWindow, close_all_windows
from utils.config import USE_GUI

import tkinter
import timeago
import datetime

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

        self.create_label_dark("Base: %s" % self.base, 0, 0, "WE")

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
            self.create_label_dark("Influence: %s" % conversion[self.influence], 0, row, "WE")

        self.create_label_dark("Item Level: %d" % self.ilvl, 0, row+1, "WE")
        self.create_label_dark("Price: %d %s" % (self.price, self.currency), 0, row+2, "WE")

class NotEnoughInformation(DisplayWindow):
    def __init__(self):
        super().__init__()

    def add_components(self):
        self.create_label_dark("Not Enough Data", 0, 0, "WE")
        self.create_label_dark("Could not find enough data to confidently price this item.", 0, 1, "WE")


class PriceInformation(DisplayWindow):
    def __init__(self):
        super().__init__()
        self.price = None
        self.price_vals = {}
        self.avg_times = {}
        self.not_enough = False

    def add_price_information(self, price, price_vals, avg_times, not_enough=False):
        self.price = price
        self.price_vals = price_vals
        self.avg_times = avg_times
        self.not_enough = not_enough

    def add_components(self):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """
        self.create_label_dark("", 0, 0, "WE", 4)
        self.create_label_dark("Prices", 0, 0, "E")
        self.create_label_dark(" ", 1, 0, "WE")
        self.create_label_dark("Time Listed", 2, 0, "E")
        self.create_label_dark("   Count", 3, 0, "E")

        counter = 0
        for price, count in self.price_vals.items():
            date = datetime.datetime.now()
            now = datetime.datetime.now() + datetime.timedelta(days=self.avg_times[counter][0], seconds=self.avg_times[counter][1])
            time = timeago.format(date, now)

            if counter % 2:
                self.create_label_dark("", 0, counter + 2, "WE", 4)
                self.create_label_dark(price, 0, counter + 2, "E")
                self.create_label_dark(time, 2, counter + 2, "E")
                self.create_label_dark(count, 3, counter + 2, "E")
            else:
                self.create_label("", 0, counter + 2, "WE", 4)
                self.create_label(price, 0, counter + 2, "E")
                self.create_label(time, 2, counter + 2, "E")
                self.create_label(count, 3, counter + 2, "E")
            counter += 1

        self.create_label_dark("", 0, counter + 3, "WE", 4)
        self.create_label_dark("Low:" + str(self.price[0]), 0, counter + 3, "W")
        self.create_label_dark("Avg:" + str(self.price[1]), 2, counter + 3, "E")
        self.create_label_dark("High:" + str(self.price[2]), 3, counter + 3, "E")

        if self.not_enough:
            self.create_label_dark("", 0, counter + 4, "WE", 4)
            self.create_label_dark("Found limited search results", 0, counter+4, "WE", 4)
            self.create_label_dark("", 0, counter + 5, "WE", 4)
            self.create_label_dark("Use alt+t to search manually", 0, counter+5, "WE", 4)


priceInformation = PriceInformation()
notEnoughInformation = NotEnoughInformation()
baseResults = BaseResults()

def init_gui():
    if USE_GUI:
        tk = tkinter.Tk().withdraw()
        
