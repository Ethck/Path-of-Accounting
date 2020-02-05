import configparser

config = configparser.ConfigParser()
config.read("settings.cfg")

USE_HOTKEYS = True if config["GENERAL"]["useHotKeys"] == "yes" else False

LEAGUE = config["GENERAL"]["league"]

PROJECT_URL = config["GENERAL"]["projectURL"]

VERSION = config["GENERAL"]["version"]

RELEASE_URL = config["GENERAL"]["releaseURL"]


USE_GUI = True if config["GUI"]["useGUI"] == "yes" else False
TIMEOUT_GUI = config["GUI"]["timeout"]
GUI_BG1 = config["GUI"]["backgroundColor"]
GUI_BG2 = config["GUI"]["backgroundColor2"]
GUI_FONT = config["GUI"]["font"]
GUI_FONT_SIZE = config["GUI"]["fontSize"]
GUI_FONT_COLOR = config["GUI"]["fontColor"]
GUI_HEADER_COLOR = config["GUI"]["headerColor"]


MIN_RESULTS = 10
