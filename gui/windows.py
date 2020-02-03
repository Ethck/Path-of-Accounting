
from gui.gui import DisplayWindow, ActiveWindow, close_all_windows
from utils.config import USE_GUI, TIMEOUT_GUI

import tkinter
import re
import time
from functools import partial

class PriceInformation(DisplayWindow):

    def show_base_result(self, base, influence, ilvl, price, currency):
        """
        Assemble a simple poe.ninja result when searching for the
        worth of an item base, including it's influence and item level.
        """
        close_all_windows()
        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        baseLabel = tkinter.Label(self.frame,
            text="Base: %s" % base,
            bg="#1f1f1f",
            fg="#e6b800"
        )
        baseLabel.grid(column=0, row=0)

        row = 1
        if influence is not None:
            row += 1

            conversion = {
                "elder": "Elder",
                "shaper": "Shaper",
                "redeemer": "Redeemer",
                "crusader": "Crusader",
                "warlord": "Warlord",
                "hunter": "Hunter"
            }

            influenceLabel = tkinter.Label(self.frame,
                text="Influence: %s" % conversion[influence],
                bg="#1f1f1f",
                fg="#e6b800"
            )
            influenceLabel.grid(column=0, row=row)

        row += 1
        itemLevelLabel = tkinter.Label(self.frame,
            text="Item Level: %d" % ilvl,
            bg="#1f1f1f",
            fg="#e6b800"
        )
        itemLevelLabel.grid(column=0, row=row)

        row += 1
        priceLabel = tkinter.Label(self.frame,
            text="Price: %d %s" % (price, currency),
            bg="#1f1f1f",
            fg="#e6b800"
        )
        priceLabel.grid(column=0, row=row)

    def show_not_enough_data(self):
        """
        Assemble a simple informative window which tells the user
        that we were unable to confidently price the current clipboard
        item.
        """
        close_all_windows()
        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = tkinter.Label(self.frame, text="Not Enough Data", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)

        displayText = "Could not find enough data to confidently price this item."
        annotation = tkinter.Label(self.frame, text=displayText, bg="#0d0d0d", fg="#e6b800")
        annotation.grid(column=0, row=2)


    def show_price(self, price, price_vals, avg_times, not_enough=False):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """
        close_all_windows()
        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        spacerLabel = tkinter.Label(self.frame, text="   ", bg="#0d0d0d")
        spacerLabel.grid(column=0, row=0, columnspan=3, sticky="w" + "e")

        # Setting up header row of labels.
        bglabel = tkinter.Label(self.frame, bg="#0d0d0d").grid(column=0, row=1, columnspan=3, sticky="w" + "e")
        headerLabel = tkinter.Label(self.frame, text="Listed Price:", bg="#0d0d0d", fg="#e6b800").grid(column=0, row=1, padx=5)
        headerLabel2 = tkinter.Label(self.frame, text="Avg. Time Listed:", bg="#0d0d0d", fg="#e6b800").grid(
            column=2, row=1, padx=5
        )
        headerLabel3 = tkinter.Label(self.frame, text="   ", bg="#0d0d0d", fg="#e6b800").grid(column=1, row=1, sticky="w" + "e")

        rows_used = len(price_vals)

        for row in range(rows_used):
            days = avg_times[row][0]
            if days > 0:
                days = str(days) + " days, "
            else:
                days = None

            hours = None
            if avg_times[row][1] > 3600:
                hours = str(round(avg_times[row][1] / 3600, 2)) + " hours"
            else:
                hours = "< 1 hour"

            if days is not None:
                avg_time_text = days + hours
            else:
                avg_time_text = hours

            # Alternates row color.
            if row % 2 == 0:
                # Needed here because other color is consistent with canvas color.
                bgAltLabel = tkinter.Label(self.frame, bg="#1a1a1a").grid(column=0, row=2 + row, columnspan=3, sticky="w" + "e")
                priceLabel = tkinter.Label(self.frame, text=price_vals[row], bg="#1a1a1a", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = tkinter.Label(self.frame, text=avg_time_text, bg="#1a1a1a", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )
            else:
                priceLabel = tkinter.Label(self.frame, text=price_vals[row], bg="#1f1f1f", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = tkinter.Label(self.frame, text=avg_time_text, bg="#1f1f1f", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )

        footerbgLabel = tkinter.Label(self.frame, bg="#0d0d0d").grid(column=0, row=rows_used + 3, columnspan=3, sticky="w" + "e")

        minPriceLabel = tkinter.Label(self.frame, text="Low: " + str(price[0]), bg="#0d0d0d", fg="#e6b800")
        minPriceLabel.grid(column=0, row=rows_used + 3, padx=10)

        avgPriceLabel = tkinter.Label(self.frame, text="Avg: " + str(price[1]), bg="#0d0d0d", fg="#e6b800")
        avgPriceLabel.grid(column=1, row=rows_used + 3, padx=10)

        maxPriceLabel = tkinter.Label(self.frame, text="High: " + str(price[2]), bg="#0d0d0d", fg="#e6b800")
        maxPriceLabel.grid(column=2, row=rows_used + 3, padx=10)

        extrabgLabel = None
        extrabgLabel2 = None
        notEnoughLabel = None
        manualSearchLabel = None

        if not_enough:
            extrabgLabel = tkinter.Label(self.frame, bg="#0d0d0d")
            extrabgLabel.grid(column=0, row=rows_used + 4, columnspan=3, sticky="w" + "e")
            notEnoughText = "Found limited search results"
            notEnoughLabel = tkinter.Label(self.frame, text=notEnoughText, bg="#0d0d0d", fg="#e6b800")
            notEnoughLabel.grid(column=0, row=rows_used + 4, columnspan=3)
            extrabgLabel2 = tkinter.Label(self.frame, bg="#0d0d0d")
            extrabgLabel2.grid(column=0, row=rows_used + 5, columnspan=3, sticky="w" + "e")
            manualSearchText = "Use alt+t to search manually"
            manualSearchLabel = tkinter.Label(self.frame, text=manualSearchText, bg="#0d0d0d", fg="#e6b800")
            manualSearchLabel.grid(column=0, row=rows_used + 5, columnspan=3)


priceInformation = PriceInformation()

def init_gui():
    if USE_GUI:
        tk = tkinter.Tk().withdraw()
        priceInformation.prepare_window()
        