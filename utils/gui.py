import os
import time
from tkinter import *

from PIL import Image, ImageTk

# We do not need this on Linux.
if os.name == "nt":
    import win32com.client
    import win32gui


def windowEnumerationHandler(hwnd, top_windows):
    """
    Handler for Windows OS enumeration of all open windows.
    Used to return to the Path of Exile window after displaying the overlay.
    """
    top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

def windowToFront(root):
    # This is necessary for displaying the GUI window above active window(s) on the Windows OS
    if os.name == "nt":
        # In order to prevent SetForegroundWindow from erroring, we must satisfy the requirements
        # listed here:
        # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow
        # We satisfy this by internally sending the alt character so that Windows believes we are
        # an active window.
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("%")
        win32gui.SetForegroundWindow(root.winfo_id())

def windowRefocus(name):
    """
    Restore focus to a window, if on Windows.
    TODO: If originating window was NOT "name", return to previous window.
    """

    if os.name == "nt":
        results = []
        top_windows = []
        win32gui.EnumWindows(windowEnumerationHandler, top_windows)
        for i in top_windows:
            if name == i[1].lower():
                win32gui.ShowWindow(i[0], 5)
                win32gui.SetForegroundWindow(i[0])
                break

class Gui():
    def __init__(self):
        self.root = self.prepare_window()

    def prepare_window(self):
        root = Toplevel()
        root.overrideredirect(True)
        root.option_add("*Font", "courier 12")
        return root

    def relayout_grid(self):
        col_count, row_count = self.root.grid_size()

        for col in range(col_count):
            self.root.grid_columnconfigure(col, minsize=20)

        for row in range(row_count):
            self.root.grid_rowconfigure(row, minsize=20)

    def mouse_pos(self):
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        return x, y

    def reset(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show(self):
        windowToFront(self.root)
        self.relayout_grid()

        abs_coord_x, abs_coord_y = self.mouse_pos()
        self.root.geometry(f"+{abs_coord_x}+{abs_coord_y}")
        self.root.deiconify()
        self.root.update()

    def hide(self):
        abs_coord_x, abs_coord_y = self.mouse_pos()
        self.root.withdraw()
        self.root.geometry(f"-{abs_coord_x}-{abs_coord_y}")
        windowRefocus("path of exile")

    def show_price(self, price, currency):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """

        self.reset()

        # Currently only support for these items with pictures, will get the rest in a later update.
        curr_types = ["alchemy", "chaos", "exalt", "mirror"]
        if currency in curr_types:
            img = ImageTk.PhotoImage(Image.open(f"images/{currency}.png"))
            currencyLabel = Label(self.root, image=img)
            currencyLabel.grid(column=1, row=0)

        minPriceLabel = Label(self.root, text=price[0])
        minPriceLabel.grid(column=0, row=1, padx=10)

        avgPriceLabel = Label(self.root, text=price[1])
        avgPriceLabel.grid(column=1, row=1, padx=10)

        maxPriceLabel = Label(self.root, text=price[2])
        maxPriceLabel.grid(column=2, row=1, padx=10)

        # Show the new GUI, then get rid of it after 5 seconds. Might lower delay in the future.
        self.show()
        time.sleep(5)
        self.hide()
