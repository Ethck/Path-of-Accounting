import tkinter
import time
from gui.gui import ActiveWindow, close_all_windows
from item.generator import Currency, Item, ModInfo
from utils.common import get_response, price_item
from utils import config
from utils.config import (
    GUI_BG1,
    GUI_BG2,
    GUI_FONT,
    GUI_FONT_COLOR,
    GUI_FONT_SIZE,
    MIN_RESULTS,
)
from utils.web import open_exchange_site, open_trade_site


class AdvancedSearch(ActiveWindow):
    """Advanced Search Window"""

    def __init__(self):
        super().__init__()
        self.item = None
        self.selected = []
        self.searchable_mods = []

    def add_item(self, item):
        self.item = item
        self.selected = []
        self.searchable_mods = []

    def edit_item(self):
        nMods = []
        for mod in self.searchable_mods:
            if self.selected[mod.mod.id].get():
                min_val = mod.min
                max_val = mod.max
                if mod.mod.id in self.entries:
                    try:
                        min_val = float(self.entries[mod.mod.id][0].get())
                        max_val = float(self.entries[mod.mod.id][1].get())
                    except ValueError as e:
                        pass
                nMod = ModInfo(mod.mod, min_val, max_val, mod.option)
                nMods.append(nMod)
        self.item.mods = nMods
        self.item.print()

    def search(self):
        try:
            self.edit_item()
            results = price_item(self.item)
            if results > 0:
                self.close()
            else:
                time.sleep(1.2)
                close_all_windows()
        except Exception:
            self.close()
            traceback.print_exc()

    def open_trade(self):
        try:
            self.edit_item()
            response = get_response(self.item)
            if response:
                if isinstance(self.item, Currency):
                    open_exchange_site(response["id"], config.LEAGUE)
                else:
                    open_trade_site(response["id"], config.LEAGUE)
            self.close()
        except Exception:
            self.close()
            traceback.print_exc()

    def add_components(self):
        """
        Add all of the components necessary for the GUI to display information.
        """

        masterFrame = tkinter.Frame(self.frame, bg=GUI_BG1)
        masterFrame.place(relwidth=1, relheight=1)

        self.create_label_header("Advanced Search", 0, 0, "WE", 6)
        self.create_label_header(self.item.name, 0, 1, "WE", 6)
        j = 0
        self.selected = {}
        self.entries = {}

        for mod in self.item.create_pseudo_mods():

            self.searchable_mods.append(mod)
            self.selected[mod.mod.id] = tkinter.IntVar()
            # CheckButton
            bgColor = GUI_BG2 if j % 2 else GUI_BG1
            cb = tkinter.Checkbutton(
                self.frame,
                text=mod.mod.text,
                variable=self.selected[mod.mod.id],
                bg=bgColor,
                fg=GUI_FONT_COLOR,
                activebackground=bgColor,
                activeforeground=GUI_FONT_COLOR,
            )
            #cb.select()
            cb.grid(row=j + 2, sticky="W", columnspan=3)
            cb.config(font=(GUI_FONT, GUI_FONT_SIZE))

            # Entry
            if mod.min or mod.max:  # If mod has values
                val = tkinter.StringVar()
                if mod.min:
                    val.set(mod.min)
                else:
                    val.set("Min")
                e = tkinter.Entry(
                    self.frame,
                    bg=bgColor,
                    fg=GUI_FONT_COLOR,
                    width=5,
                    textvariable=val,
                    exportselection=0,
                )
                e.grid(row=j + 2, column=4, sticky="E", columnspan=1)
                val2 = tkinter.StringVar()
                if mod.max:
                    val2.set(mod.max)
                else:
                    val2.set("Max")
                e2 = tkinter.Entry(
                    self.frame,
                    bg=bgColor,
                    fg=GUI_FONT_COLOR,
                    width=5,
                    textvariable=val2,
                    exportselection=0,
                )
                e2.grid(row=j + 2, column=5, sticky="E", columnspan=1)
                self.entries[mod.mod.id] = [e,e2]

                j += 1

        for mod in self.item.mods:
            self.searchable_mods.append(mod)
            self.selected[mod.mod.id] = tkinter.IntVar()

            # CheckButton
            bgColor = GUI_BG2 if j % 2 else GUI_BG1
            cb = tkinter.Checkbutton(
                self.frame,
                text=mod.mod.text,
                variable=self.selected[mod.mod.id],
                bg=bgColor,
                fg=GUI_FONT_COLOR,
                activebackground=bgColor,
                activeforeground=GUI_FONT_COLOR,
            )
            cb.select()
            cb.grid(row=j + 2, sticky="W", columnspan=3)
            cb.config(font=(GUI_FONT, GUI_FONT_SIZE))

            # Entry
            if mod.min or mod.max:  # If mod has values
                val = tkinter.StringVar()
                if mod.min:
                    val.set(mod.min)
                else:
                    val.set("Min")
                e = tkinter.Entry(
                    self.frame,
                    bg=bgColor,
                    fg=GUI_FONT_COLOR,
                    width=5,
                    textvariable=val,
                    exportselection=0,
                )
                e.grid(row=j + 2, column=4, sticky="E", columnspan=1)
                val2 = tkinter.StringVar()
                if mod.max:
                    val2.set(mod.max)
                else:
                    val2.set("Max")
                e2 = tkinter.Entry(
                    self.frame,
                    bg=bgColor,
                    fg=GUI_FONT_COLOR,
                    width=5,
                    textvariable=val2,
                    exportselection=0,
                )
                e2.grid(row=j + 2, column=5, sticky="E", columnspan=1)
                self.entries[mod.mod.id] = [e,e2]

                j += 1

        s = tkinter.Button(
            self.frame,
            text="Search",
            command=self.search,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=0, row=j + 2, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(
            self.frame,
            text="Open on Trade",
            command=self.open_trade,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=2, row=j + 2, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(
            self.frame,
            text="Close",
            command=self.close,
            bg=GUI_BG1,
            fg=GUI_FONT_COLOR,
        )
        s.grid(column=4, row=j + 2, columnspan=2, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))


advancedSearch = AdvancedSearch()
