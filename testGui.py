from tkinter import *
from PIL import Image, ImageTk
import time

def assemble_price_gui(price, currency):
    root = Toplevel()
    root.overrideredirect(True)

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

    elif currency == "exalt":
        #Use exalt pic
        Label(root, PhotoImage(file='images/exalt.png')).grid(column=0, row=0)

    root.update()
    time.sleep(5)
    root.destroy()