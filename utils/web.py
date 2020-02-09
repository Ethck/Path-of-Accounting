import webbrowser
import logging
from models.item import (
    Currency
)

def wiki_lookup(item):
    base_url = "https://pathofexile.gamepedia.com/"

    base_rarities = {
        "rare",
        "gem",
        "divination card",
        "normal",
        "currency"
    }

    if item:
        if item.rarity == "unique":
            url = base_url + item.name
            logging.info(f'[*] wiki_lookup item : {item.name}')
            url = base_url + item.name.replace(' ', '_')
            logging.info(url)
            webbrowser.open(url)

        elif item.rarity in base_rarities:
            logging.info(f'[*] wiki_lookup item : {item.base}')
            url = base_url + item.base.replace(' ', '_')
            logging.info(url)
            webbrowser.open(url)

        # Only items not supported are magic items.
        else:
            logging.error("[!] Wiki page not found.")

def open_trade_site(rid, league):
    trade_url = f"https://pathofexile.com/trade/search/{league}/{rid}"
    logging.debug("Opening trade site with url: %s" % trade_url)
    webbrowser.open(trade_url)
