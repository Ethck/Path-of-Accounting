
import os
import tkinter
import screeninfo
import time
import traceback
if os.name == "nt":
    import pythoncom
    import win32com.client
    import win32gui

from utils.config import USE_GUI, TIMEOUT_GUI

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
        try:
            win32gui.SetForegroundWindow(root.winfo_id())
        except Exception as e:
            pass


def set_foreground_window(wid):
    if os.name == "nt":
        win32gui.ShowWindow(wid, 5)
        win32gui.SetForegroundWindow(wid)
def get_foreground_window():
    if os.name == "nt":
        return win32gui.GetForegroundWindow()
    return 0

components = []



class DisplayWindow:
    def __init__(self):
        self.frame = None
        self.opened = time.time() # When the window was created
        self.elapsed = 0 # Used to see how long the window was open
        self.created = False
        self.prev = None # The Active foreground window before this one
        self.window_id = 0
        components.append(self)
    
    def prepare_window(self):
        frame = tkinter.Toplevel()
        frame.wm_attributes("-topmost", 1)
        frame.overrideredirect(True)
        frame.option_add("*Font", "courier 12")
        frame.withdraw()
        self.frame = frame

    def destory(self, event = None):
        self.frame.withdraw()
        self.frame.destroy()
        self.frame.update()

    def close(self, event = None):
        self.frame.update()
        if self.window_id == get_foreground_window():
            set_foreground_window(self.prev)
        self.frame.withdraw()
        if self.created:
            for child in self.frame.winfo_children():
                child.destroy()
            self.frame.withdraw()
            self.frame.destory()
            self.created = False

    def should_close(self):
        self.elapsed = time.time() - self.opened
        if self.elapsed >= int(TIMEOUT_GUI):
            elapsed = 0
            self.close()

    def add_callbacks(self):
        pass

    def create(self, x_cord, y_cord):
        if self.created:
            return
        close_all_windows()
        self.prev = get_foreground_window()
        self.created = True
        self.finalize(x_cord, y_cord)

    def create_at_cursor(self):
        if self.created:
            return
        close_all_windows()
        self.prev = get_foreground_window()
        self.created = True
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
        width = 0
        height = 0
        try:
            current_screen = get_monitor_from_coord(self.frame.winfo_x(), self.frame.winfo_y())
            width = current_screen.width
            height = current_screen.height
        except screeninfo.common.ScreenInfoError as e:
            exception = traceback.format_exc()
            print("====== TRACEBACK =====")
            print(exception)
            self.close()
            return
        # Get the monitor's size
        root_w = self.frame.winfo_width()
        root_h = self.frame.winfo_height()

        if m_x + root_w >= width:
            m_x = width - root_w - 5

        if m_y + root_h >= height:
            m_y = height - root_h - 5

        self.finalize(m_x,m_y)

    def finalize(self, x_cord, y_cord):
        windowToFront(self.frame)
        self.frame.deiconify()
        self.frame.geometry(f"+{x_cord}+{y_cord}")
        self.frame.resizable(False, False)
        self.has_focus = True
        self.frame.update()
        self.add_callbacks()
        self.opened = time.time()
        self.window_id = get_foreground_window()

class ActiveWindow(DisplayWindow):
    def close(self, event = None):
        if self.created:
            for child in self.frame.winfo_children():
                child.destroy()
            self.frame.unbind('<Escape>')
            self.frame.unbind('<FocusOut>')
            self.frame.quit()
            self.frame.update()
            self.frame.withdraw()
            self.created = False
            set_foreground_window(self.prev)

    def run(self):
        self.frame.mainloop()
    
    def add_callbacks(self):
        self.frame.bind('<Escape>', self.close)
        self.frame.bind("<FocusOut>", self.close)



def close_all_windows():
    for x in components:
        x.close()

def check_timeout_gui():
    for x in components:
        x.should_close()

def destroy_gui():
    for x in components:
        x.destory()
        