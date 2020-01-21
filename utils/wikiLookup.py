import webbrowser


def wikiLookup(text, info):

    baseURL = "https://pathofexile.gamepedia.com/"

    x = info.get("itype")

    if info:
        if info["itype"] == "Currency":
            print(f'[*] wikiLookup item : {info["name"]}')
            print(baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        elif any(i in info["rarity"] for i in ["Unique", "Gem", "Divination Card", "Normal"]):
            print(f'[*] wikiLookup item : {info["name"]}')
            print(baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        # Non-Unique flasks will have a NoneType, that is why we store them in x so other non uniques may be checked.
        elif any(j in info["rarity"] for j in ["Magic", "Rare"]) and x != "None":
            print(f'[*] wikiLookup item : {info["itype"]}')
            print(baseURL + info["itype"])
            webbrowser.open(baseURL + info["itype"])

        # Only items currently not supported are non-unique flasks to my knowledge.
        else:
            print("[!] Wiki page not found.")
