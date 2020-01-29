import configparser

config = configparser.ConfigParser()
config.read("settings.cfg")

USE_HOTKEYS = True if config["GENERAL"]["useHotKeys"] == "yes" else False

LEAGUE = config["GENERAL"]["league"]

USE_GUI = True if config["GENERAL"]["useGUI"] == "yes" else False

PROJECT_URL = config["GENERAL"]["projectURL"]

VERSION = config["GENERAL"]["version"]

RELEASE_URL = config["GENERAL"]["releaseURL"]

TIMEOUT_GUI = config["GENERAL"]["timeoutGUI"]

MIN_RESULTS = 10
