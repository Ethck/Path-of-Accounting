import tkinter
from gui.gui import ActiveWindow
from utils.config import (
     MIN_RESULTS, 
     GUI_BG1, 
     GUI_BG2, 
     GUI_FONT_COLOR, 
     GUI_FONT, 
     GUI_FONT_SIZE, 
     LEAGUE
)

from item.generator import Item, Currency
from utils.common import price_item, get_response
from utils.web import open_exchange_site, open_trade_site

class AdvancedSearch(ActiveWindow):
    """Advanced Search Window"""

    def __init__(self):
        super().__init__()
        self.item = None
        self.selected = []

    def add_item(self, item):
        self.item = item
        self.selected = []


    def edit_item(self):
        nMods = []
        for mod in self.item.mods:
            if self.selected[mod[0].id].get():
                nMods.append(mod)
        self.item.mods = nMods
        self.item.print()

    def search(self):
        self.edit_item()
        price_item(self.item)
        self.close()

    def open_trade(self):
        self.edit_item()
        response = get_response(self.item)
        if response:
            if isinstance(self.item, Currency):
                open_exchange_site(response["id"], LEAGUE)
            else:
                open_trade_site(response["id"], LEAGUE)
        self.close()


    def add_components(self):
        """
        
        """
        
        if not isinstance(self.item, Item):
            return
        
        masterFrame = tkinter.Frame(self.frame, bg=GUI_BG1)
        masterFrame.place(relwidth=1, relheight=1)

        self.create_label_header("Advanced Search", 0, 0, "WE", 3)
        

        j = 0
        self.selected = {}
        if isinstance(self.item, Item):
            for mod in self.item.mods:
                self.selected[mod[0].id] = tkinter.IntVar()
                if j % 2:
                    s = tkinter.Checkbutton(self.frame, text=mod[0].text, variable=self.selected[mod[0].id], bg=GUI_BG2, fg=GUI_FONT_COLOR)
                else:
                    s = tkinter.Checkbutton(self.frame, text=mod[0].text, variable=self.selected[mod[0].id], bg=GUI_BG1, fg=GUI_FONT_COLOR)
                s.select()
                s.grid(row=j+1, sticky="WE", columnspan=3)
                s.config(font=(GUI_FONT, GUI_FONT_SIZE))
                j += 1
        

        s = tkinter.Button(self.frame, text='Search', command=self.search, bg=GUI_BG1, fg=GUI_FONT_COLOR)
        s.grid(column=0, row=j+1, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(self.frame, text='Open on Trade', command=self.open_trade, bg=GUI_BG1, fg=GUI_FONT_COLOR)
        s.grid(column=1, row=j+1, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))
        s = tkinter.Button(self.frame, text='Close', command=self.close, bg=GUI_BG1, fg=GUI_FONT_COLOR)
        s.grid(column=2, row=j+1, sticky="WE")
        s.config(font=(GUI_FONT, GUI_FONT_SIZE))


advancedSearch = AdvancedSearch()