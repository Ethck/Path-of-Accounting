import os
from tkinter import *
import screeninfo
import time
from utils.config import USE_GUI, TIMEOUT_GUI

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


def init_ui():
    tk = Tk().withdraw()

components = []

class GuiComponent:
    def __init__(self):
        self.frame = None
        self.closed = True
        self.opened = time.time()
        self.elapsed = 0
        self.have_timeout = False
        self.hidden = True
        components.append(self)

    def stop(self):
        self.frame.quit()
        self.close()

    def run(self):
        self.frame.mainloop()

    def should_close(self):
        if self.is_closed():
            return
        if not self.have_timeout:
            return
        self.elapsed = time.time() - self.opened
        if self.elapsed >= int(TIMEOUT_GUI):
            elapsed = 0
            self.close()
            windowRefocus("path of exile")

    
    def prepare_window(self):
        frame = Toplevel()
        frame.overrideredirect(True)
        frame.option_add("*Font", "courier 12")
        frame.withdraw()
        self.frame = frame
        self.hidden = True

    def is_closed(self):
        if self.closed:
            return True
        return False

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.frame.destroy()
        self.frame.update()
        self.frame = None


    def add_components(self):
        pass

    def create(self, x_cord, y_cord):
        close_all_windows()
        if not self.closed:
            return
        self.closed = False
        self.prepare_window()
        self.add_components()
        windowToFront(self.frame)
        self.frame.deiconify()
        self.frame.geometry(f"+{x_cord}+{y_cord}")
        self.frame.update()
        self.opened = time.time()


    def hide(self, refocus=True):
        if self.hidden:
            return
        self.hidden = True
        self.frame.withdraw()
        self.frame.update()
        if refocus:
            windowRefocus("path of exile")

    def create_at_cursor(self):
        close_all_windows()
        if not self.closed:
            return
        self.closed = False
        self.prepare_window()
        self.add_components()
        self.hidden = False
        windowToFront(self.frame)
        self.frame.update()
        m_x = self.frame.winfo_pointerx()
        m_y = self.frame.winfo_pointery()
        def get_monitor_from_coord(x, y):
            monitors = screeninfo.get_monitors()
            for m in reversed(monitors):
                if m.x <= x <= m.width + m.x and m.y <= y <= m.height + m.y:
                    return m
            return monitors[0]

        # Get the screen which contains top
        current_screen = get_monitor_from_coord(self.frame.winfo_x(), self.frame.winfo_y())
        # Get the monitor's size
        root_w = self.frame.winfo_width()
        root_h = self.frame.winfo_height()

        if m_x + root_w >= current_screen.width:
            m_x = current_screen.width - root_w - 5

        if m_y + root_h >= current_screen.height:
            m_y = current_screen.height - root_h - 5

        self.frame.deiconify()
        self.frame.geometry(f"+{m_x}+{m_y}")
        self.frame.update()
        self.opened = time.time()

class GuiRunningComponent(GuiComponent):
    def stop(self):
        self.frame.quit()
        self.close()

    def run(self):
        self.frame.mainloop()
    
    def prepare_window(self):
        frame = Toplevel()
        frame.option_add("*Font", "courier 12")
        frame.title(" ")
        self.frame = frame


    def add_components(self):
        pass
    
    def create(self, x_cord, y_cord):
        if not self.closed:
            return
        self.closed = False
        self.prepare_window()
        self.add_components()
        windowToFront(self.frame)
        self.frame.geometry(f"+{x_cord}+{y_cord}")
        self.frame.update()
        self.opened = time.time()



def close_all_windows():
    for x in components:
        x.close()

def check_timeout_gui():
    for x in components:
        x.should_close()

def destroy_gui():
    for x in components:
        x.close()