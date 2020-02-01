from gui.guiComponent import *
import re
import time
class PriceInfo(GuiComponent):
    def __init__(self):
        super().__init__()
        self.have_timeout = True
        self.price = []
        self.price_vals = []
        self.avg_times = []
        self.not_enough = False
    def add_price_info(self, price, price_vals, avg_times, not_enough):
        if not self.is_closed():
            self.close()
        self.price = price
        self.price_vals = price_vals
        self.avg_times = avg_times
        self.not_enough = not_enough
    
    def add_components(self):
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

        rows_used = len(self.price_vals)

        for row in range(rows_used):
            days = self.avg_times[row][0]
            if days > 0:
                days = str(days) + " days, "
            else:
                days = None

            hours = None
            if self.avg_times[row][1] > 3600:
                hours = str(round(self.avg_times[row][1] / 3600, 2)) + " hours"
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
                priceLabel = tkinter.Label(self.frame, text=self.price_vals[row], bg="#1a1a1a", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = tkinter.Label(self.frame, text=avg_time_text, bg="#1a1a1a", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )
            else:
                priceLabel = tkinter.Label(self.frame, text=self.price_vals[row], bg="#1f1f1f", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = tkinter.Label(self.frame, text=avg_time_text, bg="#1f1f1f", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )

        footerbgLabel = tkinter.Label(self.frame, bg="#0d0d0d").grid(column=0, row=rows_used + 3, columnspan=3, sticky="w" + "e")

        minPriceLabel = tkinter.Label(self.frame, text="Low: " + str(self.price[0]), bg="#0d0d0d", fg="#e6b800")
        minPriceLabel.grid(column=0, row=rows_used + 3, padx=10)

        avgPriceLabel = tkinter.Label(self.frame, text="Avg: " + str(self.price[1]), bg="#0d0d0d", fg="#e6b800")
        avgPriceLabel.grid(column=1, row=rows_used + 3, padx=10)

        maxPriceLabel = tkinter.Label(self.frame, text="High: " + str(self.price[2]), bg="#0d0d0d", fg="#e6b800")
        maxPriceLabel.grid(column=2, row=rows_used + 3, padx=10)

        extrabgLabel = None
        extrabgLabel2 = None
        notEnoughLabel = None
        manualSearchLabel = None

        if self.not_enough:
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

class NoResult(GuiComponent):
    def __init__(self):
        super().__init__()
        self.have_timeout = True
    def add_components(self):
        """
        Assemble a simple informative window which tells the user
        that we were unable to confidently price the current clipboard
        item.
        """

        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = tkinter.Label(self.frame, text="Not Enough Data", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)

        displayText = "Could not find enough data to confidently price this item."
        annotation = tkinter.Label(self.frame, text=displayText, bg="#0d0d0d", fg="#e6b800")
        annotation.grid(column=0, row=2)

class ShowBaseResult(GuiComponent):
    def __init__(self):
        super().__init__()
        self.have_timeout = True
        self.base = None
        self.influence = None
        self.ilvl = None
        self.price = None
        self.currency = None
    def add_base_info(self, base, influence, ilvl, price, currency):
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

        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        baseLabel = tkinter.Label(self.frame,
            text="Base: %s" % self.base,
            bg="#1f1f1f",
            fg="#e6b800"
        )
        baseLabel.grid(column=0, row=0)

        row = 1
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

            influenceLabel = tkinter.Label(self.frame,
                text="Influence: %s" % conversion[self.influence],
                bg="#1f1f1f",
                fg="#e6b800"
            )
            influenceLabel.grid(column=0, row=row)

        row += 1
        itemLevelLabel = tkinter.Label(self.frame,
            text="Item Level: %d" % self.ilvl,
            bg="#1f1f1f",
            fg="#e6b800"
        )
        itemLevelLabel.grid(column=0, row=row)

        row += 1
        priceLabel = tkinter.Label(self.frame,
            text="Price: %d %s" % (self.price, self.currency),
            bg="#1f1f1f",
            fg="#e6b800"
        )
        priceLabel.grid(column=0, row=row)

class SelectSearchingMods(GuiRunningComponent):
    def __init__(self):
        super().__init__()
        self.info = {}
        self.selected = []
        self.searched = False
        self.openTrade = False
    def add_info(self, info):
        self.info = info
        self.selected = {}
    def search(self):
        self.searched = True
        print("You have selected:")
        values = []
        for key, value in self.selected.items():
            if value.get():
                values.append(key)
                print(key)
        print("                                            ")
        self.info["stats"] = values
        self.stop()
    def open_trade(self):
        print("You have selected:")
        values = []
        for key, value in self.selected.items():
            if value.get():
                values.append(key)
                print(key)
        print("                                            ")
        self.info["stats"] = values
        self.searched = True
        self.openTrade = True
        self.stop()
    def add_components(self):

        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = tkinter.Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = tkinter.Label(self.frame, text="Select Mods to include in search", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)
        bglabel = tkinter.Label(self.frame, bg="#0d0d0d").grid(column=0, row=1, columnspan=3, sticky="w" + "e")

        def hasNumber(string):
            return re.search('\d', string)
        j = 2
        for key, value in self.info.items():
            #print(key,value)
            if key == "stats":
                for v in value:
                    if v == "--------":
                        continue
                    if not hasNumber(v):
                        continue
                    self.selected[v] = IntVar()
                    if j % 2:
                        s = Checkbutton(self.frame, text=v, variable=self.selected[v], bg="#1f1f1f", fg="#e6b800")
                        s.select()
                        s.grid(row=j, sticky=W)
                    else:
                        s = Checkbutton(self.frame, text=v, variable=self.selected[v], bg="#1a1a1a", fg="#e6b800")
                        s.select()
                        s.grid(row=j, sticky=W)
                    j = j+1
        tkinter.Button(self.frame, text='Search', command=self.search, bg="#1f1f1f", fg="#e6b800").grid(row=j, sticky=SW)
        tkinter.Button(self.frame, text='Open on Trade', command=self.open_trade, bg="#1f1f1f", fg="#e6b800").grid(row=j, sticky=SE)
        tkinter.Button(self.frame, text='Close', command=self.stop, bg="#1f1f1f", fg="#e6b800").grid(row=j, sticky=SE)

priceInfo = PriceInfo()
noResult = NoResult()
selectSearch = SelectSearchingMods()
showBaseResults = ShowBaseResult()