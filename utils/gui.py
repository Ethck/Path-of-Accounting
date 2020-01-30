import os
import time
from tkinter import *

import screeninfo

# We do not need this on Linux.
if os.name == "nt":
    import pythoncom
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
        # We need this pythoncom call for win32com use in a thread.
        pythoncom.CoInitialize()
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


class Gui:
    def __init__(self):
        tk = Tk()
        tk.wm_attributes("-topmost", 1)
        tk.update()
        tk.withdraw()

        self.root = self.prepare_window()
        self.last_task = None

    def prepare_window(self):
        root = Toplevel()
        root.overrideredirect(True)
        root.option_add("*Font", "courier 12")
        root.withdraw()

        def check():
            try:
                time.sleep(0.5)
                root.after(50, check)
            except KeyboardInterrupt:
                root.quit()

        check()
        return root

    def wait(self):
        self.root.mainloop()

    def mouse_pos(self):
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        return x, y

    def screen_size(self):
        def get_monitor_from_coord(x, y):
            monitors = screeninfo.get_monitors()

            for m in reversed(monitors):
                if m.x <= x <= m.width + m.x and m.y <= y <= m.height + m.y:
                    return m

            return monitors[0]

        # Get the screen which contains top
        current_screen = get_monitor_from_coord(self.root.winfo_x(), self.root.winfo_y())

        # Get the monitor's size
        return current_screen.width, current_screen.height

    def reset(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show(self):
        windowToFront(self.root)
        self.root.update()

        mouse_x, mouse_y = self.mouse_pos()
        screen_w, screen_h = self.screen_size()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()

        # Confine widget to screen

        coord_x = mouse_x
        if mouse_x + root_w >= screen_w:
            coord_x = screen_w - root_w - 5

        coord_y = mouse_y
        if mouse_y + root_h >= screen_h:
            coord_y = screen_h - root_h - 5

        self.root.geometry(f"+{coord_x}+{coord_y}")
        self.root.deiconify()
        self.root.update()

    def hide(self, refocus=True):
        self.root.withdraw()
        self.root.update()

        if refocus:
            windowRefocus("path of exile")

    def schedule_hide(self, delay=5000):
        if self.last_task:
            self.root.after_cancel(self.last_task)

        self.last_task = self.root.after(delay, self.hide)

    def show_not_enough_data(self):
        """
        Assemble a simple informative window which tells the user
        that we were unable to confidently price the current clipboard
        item.
        """

        self.reset()

        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = Frame(self.root, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        headerLabel = Label(self.root, text="Not Enough Data", bg="#0d0d0d", fg="#e6b800")
        headerLabel.grid(column=0, row=1, padx=5)

        displayText = "Could not find enough data to confidently price this item."
        annotation = Label(self.root, text=displayText, bg="#0d0d0d", fg="#e6b800")
        annotation.grid(column=0, row=2)

        self.show()
        time.sleep(5)
        self.hide()

    def show_price(self, price, price_vals, avg_times, not_enough=False):
        """
        Assemble the simple pricing window. Will overhaul this to get a better GUI in a future update.
        """

        self.hide(False)
        self.reset()

        # Setting up Master Frame, only currently used for background color due to grid format.
        masterFrame = Frame(self.root, bg="#1f1f1f")
        masterFrame.place(relwidth=1, relheight=1)

        spacerLabel = Label(self.root, text="   ", bg="#0d0d0d")
        spacerLabel.grid(column=0, row=0, columnspan=3, sticky="w" + "e")

        # Setting up header row of labels.
        bglabel = Label(self.root, bg="#0d0d0d").grid(column=0, row=1, columnspan=3, sticky="w" + "e")
        headerLabel = Label(self.root, text="Listed Price:", bg="#0d0d0d", fg="#e6b800").grid(column=0, row=1, padx=5)
        headerLabel2 = Label(self.root, text="Avg. Time Listed:", bg="#0d0d0d", fg="#e6b800").grid(
            column=2, row=1, padx=5
        )
        headerLabel3 = Label(self.root, text="   ", bg="#0d0d0d", fg="#e6b800").grid(column=1, row=1, sticky="w" + "e")

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
                bgAltLabel = Label(self.root, bg="#1a1a1a").grid(column=0, row=2 + row, columnspan=3, sticky="w" + "e")
                priceLabel = Label(self.root, text=price_vals[row], bg="#1a1a1a", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = Label(self.root, text=avg_time_text, bg="#1a1a1a", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )
            else:
                priceLabel = Label(self.root, text=price_vals[row], bg="#1f1f1f", fg="#e6b800").grid(
                    column=0, row=2 + row, sticky="w", padx=5
                )
                avgTimeLabel = Label(self.root, text=avg_time_text, bg="#1f1f1f", fg="#e6b800").grid(
                    column=2, row=2 + row, sticky="w", padx=5
                )

        footerbgLabel = Label(self.root, bg="#0d0d0d").grid(column=0, row=rows_used + 3, columnspan=3, sticky="w" + "e")

        minPriceLabel = Label(self.root, text="Low: " + str(price[0]), bg="#0d0d0d", fg="#e6b800")
        minPriceLabel.grid(column=0, row=rows_used + 3, padx=10)

        avgPriceLabel = Label(self.root, text="Avg: " + str(price[1]), bg="#0d0d0d", fg="#e6b800")
        avgPriceLabel.grid(column=1, row=rows_used + 3, padx=10)

        maxPriceLabel = Label(self.root, text="High: " + str(price[2]), bg="#0d0d0d", fg="#e6b800")
        maxPriceLabel.grid(column=2, row=rows_used + 3, padx=10)

        extrabgLabel = None
        extrabgLabel2 = None
        notEnoughLabel = None
        manualSearchLabel = None

        if not_enough:
            extrabgLabel = Label(self.root, bg="#0d0d0d")
            extrabgLabel.grid(column=0, row=rows_used + 4, columnspan=3, sticky="w" + "e")
            notEnoughText = "Found limited search results"
            notEnoughLabel = Label(self.root, text=notEnoughText, bg="#0d0d0d", fg="#e6b800")
            notEnoughLabel.grid(column=0, row=rows_used + 4, columnspan=3)
            extrabgLabel2 = Label(self.root, bg="#0d0d0d")
            extrabgLabel2.grid(column=0, row=rows_used + 5, columnspan=3, sticky="w" + "e")
            manualSearchText = "Use alt+t to search manually"
            manualSearchLabel = Label(self.root, text=manualSearchText, bg="#0d0d0d", fg="#e6b800")
            manualSearchLabel.grid(column=0, row=rows_used + 5, columnspan=3)

        self.show()
        self.schedule_hide()
