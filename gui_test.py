
from gui.windows import PriceInformation
from gui.gui import init_ui, DisplayWindow

import time
import tkinter

if __name__ == "__main__":

    init_ui()
    test = DisplayWindow()

    tkinter.Frame(test.frame, bg="#1f1f1f").place(relwidth=1, relheight=1)

    tkinter.Label(test.frame, text="   ", bg="#0d0d0d").grid(column=0, row=0, columnspan=3, sticky="w" + "e")

    test.create_at_cursor()
    time.sleep(2)
