from tkinter import *
from PIL import Image, ImageTk
import time
from overlay import Window
import win32gui
import win32com.client
import os


def windowEnumerationHandler(hwnd, top_windows):
    top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

def assemble_price_gui(price, currency):
    root = Toplevel()
    root.overrideredirect(True)
    # This is necessary for displaying the GUI window above active window(s)
    # TODO: Figure out how to give focus back to the OG window.

    # This is necessary for displaying the GUI window above active window(s) on the Windows OS
    if os.name == "nt":
        # In order to prvent SetForegroundWindow from erroring, we must satisfy the requirements
        # Listed here: 
        # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow
        # We satisfy this by internally sending the alt character so that Windows believes we are
        # an active window.
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(root.winfo_id())

    x = root.winfo_pointerx()
    y = root.winfo_pointery()

    abs_coord_x = root.winfo_pointerx() - root.winfo_rootx()
    abs_coord_y = root.winfo_pointery() - root.winfo_rooty()
    root.geometry(f"100x75+{abs_coord_x}+{abs_coord_y}")

    Label(root, text=price[0]).grid(column=0, row=1)
    Label(root, text=price[1]).grid(column=1, row=1)
    Label(root, text=price[2]).grid(column=2, row=1)

    curr_types = ["alchemy", "chaos", "exalt", "mirror"]
    if currency in curr_types:
        #Use chaos pic
        img = ImageTk.PhotoImage(Image.open(f'images/{currency}.png'))
        a = Label(root, image = img)
        a.grid(column=1, row=0)

    root.update()
    time.sleep(5)
    root.destroy()

     # Restore focus to a window called "path of exile" which should be the game, if on Windows.
    if os.name == "nt":
        results = []
        top_windows = []
        win32gui.EnumWindows(windowEnumerationHandler, top_windows)
        for i in top_windows:
            if "path of exile" == i[1].lower():
                win32gui.ShowWindow(i[0],5)
                win32gui.SetForegroundWindow(i[0])
                break