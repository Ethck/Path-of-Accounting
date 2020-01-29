from gui.guiComponent import *
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
        self.create_at_cursor()
    
    def add_components(self):
        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        spacerLabel = Label(self.frame, text="   ", bg="#0d0d0d")
        spacerLabel.grid(column=0, row=0, columnspan=3, sticky="w" + "e")

        # Setting up header row of labels.
        bglabel = Label(self.frame, bg="#0d0d0d").grid(column=0, row=1, columnspan=3, sticky="w" + "e")
        headerLabel = Label(self.frame, text="Listed Price:", bg="#0d0d0d", fg="#e6b800").grid(column=0, row=1, padx=5)
        headerLabel2 = Label(self.frame, text="Avg. Time Listed:", bg="#0d0d0d", fg="#e6b800").grid(
            column=2, row=1, padx=5
        )
        headerLabel3 = Label(self.frame, text="   ", bg="#0d0d0d", fg="#e6b800").grid(column=1, row=1, sticky="w" + "e")

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
                bgAltLabel = Label(self.frame, bg="#1a1a1a").grid(column=0, row=2 + row, columnspan=3, sticky="w" + "e")
                priceLabel = Label(self.frame, text=self.price_vals[row], bg="#1a1a1a", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = Label(self.frame, text=avg_time_text, bg="#1a1a1a", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )
            else:
                priceLabel = Label(self.frame, text=self.price_vals[row], bg="#1f1f1f", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = Label(self.frame, text=avg_time_text, bg="#1f1f1f", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )

        footerbgLabel = Label(self.frame, bg="#0d0d0d").grid(column=0, row=rows_used + 3, columnspan=3, sticky="w" + "e")

        minPriceLabel = Label(self.frame, text="Low: " + str(self.price[0]), bg="#0d0d0d", fg="#e6b800")
        minPriceLabel.grid(column=0, row=rows_used + 3, padx=10)

        avgPriceLabel = Label(self.frame, text="Avg: " + str(self.price[1]), bg="#0d0d0d", fg="#e6b800")
        avgPriceLabel.grid(column=1, row=rows_used + 3, padx=10)

        maxPriceLabel = Label(self.frame, text="High: " + str(self.price[2]), bg="#0d0d0d", fg="#e6b800")
        maxPriceLabel.grid(column=2, row=rows_used + 3, padx=10)

        extrabgLabel = None
        extrabgLabel2 = None
        notEnoughLabel = None
        manualSearchLabel = None

        if self.not_enough:
            extrabgLabel = Label(self.frame, bg="#0d0d0d")
            extrabgLabel.grid(column=0, row=rows_used + 4, columnspan=3, sticky="w" + "e")
            notEnoughText = "Found limited search results"
            notEnoughLabel = Label(self.frame, text=notEnoughText, bg="#0d0d0d", fg="#e6b800")
            notEnoughLabel.grid(column=0, row=rows_used + 4, columnspan=3)
            extrabgLabel2 = Label(self.frame, bg="#0d0d0d")
            extrabgLabel2.grid(column=0, row=rows_used + 5, columnspan=3, sticky="w" + "e")
            manualSearchText = "Use alt+t to search manually"
            manualSearchLabel = Label(self.frame, text=manualSearchText, bg="#0d0d0d", fg="#e6b800")
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
        masterFrame = Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = Label(self.frame, text="Not Enough Data", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)

        displayText = "Could not find enough data to confidently price this item."
        annotation = Label(self.frame, text=displayText, bg="#0d0d0d", fg="#e6b800")
        annotation.grid(column=0, row=2)


class SelectSearchingMods(GuiRunningComponent):
    def __init__(self):
        super().__init__()
        self.info = {}
        self.selected = []
        self.searched = False
    def add_info(self, info):
        self.info = info
        self.selected = {}
        #print(info)
    def search(self):
        print("You have selected:")
        values = []
        for key, value in self.selected.items():
            if value.get():
                values.append(key)
                print(key)
        print("                                            ")
        self.info["stats"] = values
        self.stop()
    def add_components(self):

        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = Frame(self.frame, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = Label(self.frame, text="Select Mods to include in search", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)

        j = 2
        for key, value in self.info.items():
            #print(key,value)
            if key == "stats":
                for v in value:
                    if v == "--------":
                        continue
                    self.selected[v] = IntVar()
                    Checkbutton(self.frame, text=v, variable=self.selected[v], bg="#1f1f1f", fg="#e6b800").grid(row=j, sticky=W)
                    j = j+1
        
        Button(self.frame, text='Search', command=self.search).grid(row=j, sticky=S)
    