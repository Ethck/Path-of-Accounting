import webbrowser


def wiki_lookup(text, info):

    baseURL = "https://pathofexile.gamepedia.com/"

    x = info.get("itype")
    x = str(x)

    if info:
        if info["itype"] == "Currency":
            print(f'[*] wiki_lookup item : {info["name"]}')
            print(baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        elif (
            info["rarity"] == "Unique"
            or info["rarity"] == "Gem"
            or info["rarity"] == "Divination Card\r"
            or info["rarity"] == "Normal"
        ):
            print(f'[*] wiki_lookup item : {info["name"]}')
            print(baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        # Magic items will have a NoneType, that is why we store them in x so other non uniques may be checked.
        elif x != "None" and info["rarity"] == "Magic" or info["rarity"] == "Rare":
            print(f'[*] wiki_lookup item : {info["itype"]}')
            print(baseURL + info["itype"])
            webbrowser.open(baseURL + info["itype"])

        # Only items not supported are magic items.
        else:
            print("[!] Wiki page not found.")


def open_trade_site(rid, league):
    tradeURL = f"https://pathofexile.com/trade/search/{league}/{rid}"
    webbrowser.open(tradeURL)
