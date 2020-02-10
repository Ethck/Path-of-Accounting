import re


class BaseItem():
    def __init__(self, name, rarity, baseType = None):
        self.name = name
        self.rarity = rarity
        self.baseType = baseType
    def get_json(self):
        pass

class Currency(BaseItem):
    def __init__(self, name, rarity):
        super().__init__(name,rarity)
    def get_json(self):

class Prophecy(BaseItem):
    pass

class Organ(BaseItem):
    pass

class Flask(BaseItem):
    passs

class Map(BaseItem):
    pass


def isCurrency(name : str, rarity: str, regions: list):
    names = ["Offering to the Goddess",
             "Divine Vessel",
             "Scarab",
             "Fossil",
             "Resonator",
             "Incubator",
             "Oil",
             "Catalyst",
             "Vial",
             "Essence"]
    if rarity == 'currency':
        return Currency(name, rarity)
    for n in names:
        if name in n:
            return Currency(name, rarity)

    mapText = 'Travel to this Map by using it in a personal Map Device. Maps can only be used once.'
    for i in range(len(regions) -3, len(regions)):
        if regions[i][0] in 'Map Device' and not regions[i][0] in mapText:
            return Currency(name, rarity)
    return None


def parse_map():
    return None


def parse_item_info(text: str):
    regions = text.split('--------')
    if len(regions) <= 2:
        return None

    for i, region in enumerate(regions):
        regions[i] = region.strip().splitlines

    if regions[-1][0].startwith("Note"):
        del regions[-1]

    rarity = regions[0][0][8:].lower()

    name = re.sub(r'<<set:M?S?>>', '', regions[0][1])

    mapText = 'Travel to this Map by using it in a personal Map Device. Maps can only be used once.'
    prophecyText = 'Right-click to add this prophecy to your character.'
    organText = "Combine this with four other different samples in Tane's Laboratory."
    flaskText = 'Right click to drink. Can only hold charges while in belt. Refills as you kill monsters.'

    for i in range(len(regions) - 1, 0, -1):
        if regions[i][0] in mapText:
            return parse_map()
        elif regions[i][0] in prophecyText:
            return Prophecy()
        elif regions[i][0] in organText:
            return Organ()
        elif regions[i][0] in flaskText:
            return Flask()


    c = isCurrency(name, rarity)
    if c: return c


    quality = 0

    for line in regions[1]:
        if line.startwith('Quality'):
            quality = int(line[line.find('+')+1:-13])
            break

    if rarity == 'gem':
        level = regions[1][1].replace(' (Max)', '')
        corrupted = regions[-1] == ['Corrupted']
        return Gem(rarity=rarity, name=name, quality=quality,
                   ilevel=level, corrupted=corrupted)

    sockets = 0
    corrupted = False
    mirrored = False
    ilvl = 0
    influences = []
    mods = []

    influenceText = {'Elder', 'Shaper', 'Hunter', 'Redeemer', 'Warlord', 'Crusader'}

    for i in range(len(regions)):
        first_line = regions[i][0]
        if first_line.startswith('Sockets'):
            sockets = first_line[9:]
        elif first_line == 'Corrupted':
            corrupted = True
        elif first_line == 'Mirrored':
            mirrored = True
        elif first_line.startswith('Item Level'):
            ilvl = int(first_line[12:])
        elif first_line.count(' ') == 1, and first_line.endswith('Item'):
            if line[:-5] in influenceText:
                influences.append(line[:-5])
        elif i > 1:
            for line in regions[i]:
                mod_values = re.findall(r'([+-])?(\d+\.?\d?\d?|%s)', line)
                mod_values = ','.join([''.join(v) for v in mod_values])
                mod_text = re.sub(r'([+-])?(\d+\.?\d?\d?|%s)', '#', line)
                mod_type = None
                mod = None
                if not mod_text:
                    mod_text = line
                if line.endswith('(implicit)'):
                    mod_text = mod_text[:-11]
                    mod_type = ItemModifierType.IMPLICIT
                elif line.endswith('(crafted)'):
                    mod_text = mod_text[:-10]
                    mod_type = ItemModifierType.CRAFTED
                if mod_type:
                    mod = get_item_modifiers_by_text((mod_text, mod_type))
                else:
                    mod_type = ItemModiferType.ENCHANT
                    if not mod_values: # trigger x on kill/hit?
                        print("WHEN IS THIS HIT?")
                        mod_text = '#% chance to ' + mod_text
                    mod = get_item_modifiers_by_text((mod_text, mod_type))
                    if not mod:
                        mod_type = ItemModifierType.EXPLICIT
                        mod = get_item_modifiers_by_text((line, mod_type))
                        if not mod:
                            mod = get_item_modifiers_by_text((mod_text, mod_type))
                        if not mod:
                            mod = get_item_modifiers_by_text((mod_text + ' (Local)'))
                        if not mod:
                            if 'reduced' in mod_text:
                                mod_text = mod_text.replace('reduced','increased')
                            elif 'increased' in mod_text:
                                mod_text = mod_text.replace('increased', 'reduced')
                            mod = get_item_modifiers_by_text((mod_text, mod_type))
                if mod:
                    mods.append((mod, mod_values))
                else:
                    print(f"Unable to find mod: {line}")
