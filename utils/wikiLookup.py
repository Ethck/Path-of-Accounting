import webbrowser

def wikiLookup(text, info):

    baseURL = 'https://pathofexile.gamepedia.com/'

    x = info.get("itype")
    x = str(x)
    print(x)

    if info:
        if info["itype"] == "Currency":
            print(f'wikiLookup item : {info["name"]}')
            print (baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        elif info["rarity"] == "Unique" or info["rarity"] == "Gem" or info["rarity"] == "Divination Card\r" or info["rarity"] == "Normal":
            print(f'wikiLookup item : {info["name"]}')
            print (baseURL + info["name"])
            webbrowser.open(baseURL + info["name"])

        # Non-Unique flasks will have a NoneType, that is why we store them in x so other non uniques may be checked.
        elif x != "None" and info["rarity"] == "Magic" or info["rarity"] == "Rare":
            print(f'wikiLookup item : {info["itype"]}')
            print (baseURL + info["itype"])
            webbrowser.open(baseURL + info["itype"])
        
        # Only items currently not supported are non-unique flasks to my knowledge.
        else:
            print("Wiki page not found.")