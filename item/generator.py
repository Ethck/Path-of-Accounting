import re
from models.itemModifier import ItemModifierType
from models.item import get_item_modifiers_by_text
from utils.web import get_ninja_bases
from utils.config import LEAGUE
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
        pass

class Prophecy(BaseItem):
    def __init__(self,name):
        self.name = name
        pass

class Organ(BaseItem):
    def __init__(self, name, ilvl, mods):
        self.name = name
        self.ilvl = ilvl
        self.mods = mods

class Flask(BaseItem):
    pass

class Gem(BaseItem):
    def __init__(self, rarity, name, quality, level, corrupted):
        pass

class Map(BaseItem):
    def __init__(self, name, rarity, ilvl, iiq, iir, pack_size):
        pass




def get_explicit_mod(mod_text: str, mod_values):
    mod_type = ItemModifierType.EXPLICIT
    mod = get_item_modifiers_by_text((mod_text, mod_type))
    if not mod:
        mod = get_item_modifiers_by_text((mod_text, mod_type))
    if not mod:
        if 'reduced' in mod_text:
            mod_text = mod_text.replace('reduced','increased')
            mod_values = str(float(mod_values) *(-1))
        elif 'increased' in mod_text:
            mod_text = mod_text.replace('increased', 'reduced')
            mod_values = str(float(mod_values) *(-1))
        mod = get_item_modifiers_by_text((mod_text, mod_type))
    if not mod:
        mod = get_item_modifiers_by_text((mod_text + ' (Local)'))
    print(mod_values)
    return mod, mod_values



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
    if rarity == 'currency' or rarity == 'divination card':
        return Currency(name, rarity)
    for n in names:
        if name in n:
            return Currency(name, rarity)

    mapText = 'Travel to this Map by using it in a personal Map Device. Maps can only be used once.'
    for i in range(len(regions) -3, len(regions)):
        if 'Map Device' in regions[i][0]  and not mapText in regions[i][0]:
            return Currency(name, rarity)
    return None


def parse_map(regions : list, rarity, name):
    map_mods = []
    for i in range(2,len(regions)):
        for line in regions[i]:
            if line.startswith('Area is influenced by') or line.startswith('Map is occupied by'):
                mod_text = line[:-11]
                mod = get_item_modifiers_by_text((mod_text), ItemModifierType.IMPLICIT)
                if not mod:
                    print(f'Could not find map mod: {line}')
                else:
                    map_mods.append(((mod, None)))

    ilvl = int(regions[1][0][10:])
    iiq = 0
    iir = 0
    pack_size = 0
    for line in regions[1]:
        if line.startswith('Item Quantity: +'):
            iiq = int(line[16:-13])
        elif line.startswith('Item Rarity: +'):
            iir = int(line[14:-13])
        elif line.startswith('Monster Pack Size: +'):
            pack_size = int(line[19:-13])

    print(name, rarity, ilvl, iiq, iir, pack_size)
    return Map(name, rarity, ilvl, iiq, iir, pack_size)

def parse_organ(regions : list, name):
    mods = {}
    for line in regions[3]:
        line = line.lstrip(' ').rstrip(' ') + " (×#)"
        mod = get_item_modifiers_by_text((line, ItemModifierType.MONSTER))
        if mod:
            if not mod in mods:
                mods[mod] = 1
            else:
                mods[mod] += 1
        else:
            print(f'Could not find organ mod: {line}')

    ilevel = int(regions[2][0][11:])
    print(name, ilevel,mods)
    return Organ(name, ilevel, mods)

def parse_flask(regions: list, rarity: str, quality: int, name: str):
    mods = []
    for line in regions[4]:
        mod_values = re.findall(r'[+-]?\d+\.?\d?\d?', line)
        for v in mod_values:
            print(v)
        mod_values = ','.join([''.join(v) for v in mod_values])
        mod_text = re.sub(r'[+-]?\d+\.?\d?\d?', '#', line)
        mod, mod_values = get_explicit_mod(mod_text, mod_values)
        if mod:
            mods.append((mod, mod_values))
        else:
            print(f"Unable to find mod: {line}")

    base = name
    category = None

    name_prefixes = '|'.join([
        "Small",
        "Medium",
        "Large",
        "Greater",
        "Grand",
        "Giant",
        "Colossal",
        "Sacred",
        "Hallowed",
        "Sanctified",
        "Divine",
        "Eternal",
    ])

    match = re.findall(r"([a-zA-Z']+ )?((?!%s)?[ ]?.+ Flask)( .*)?" % name_prefixes, base)
    base = match[0][1]

    print(base, rarity, quality, mods, category)
    return None

def parse_beast(name: str, rarity: str, regions: str):
    genus = None
    group = None
    family = None
    for line in regions[1]:
        if line.startswith('Genus: '):
            genus = line[7:]
        elif line.startswith('Group: '):
            group = line[7:]
        elif line.startswith('Family: '):
            family = line[8:]
    base = None
    if rarity == 'rare':
        base = regions[0][2]
    
    print(name, genus, group, family, base)


def parse_item_info(text: str):
    regions = text.split('--------')
    if len(regions) <= 2:
        return None

    for i, region in enumerate(regions):
        regions[i] = region.strip().splitlines()

    if regions[-1][0].startswith("Note"):
        del regions[-1]

    rarity = regions[0][0][8:].lower()

    name = re.sub(r'<<set:M?S?>>', '', regions[0][1])

    quality = 0

    for line in regions[1]:
        if line.startswith('Quality'):
            quality = int(line[line.find('+')+1:-13])
            break

    mapText = 'Travel to this Map by using it in a personal Map Device. Maps can only be used once.'
    prophecyText = 'Right-click to add this prophecy to your character.'
    organText = "Combine this with four other different samples in Tane's Laboratory."
    flaskText = 'Right click to drink. Can only hold charges while in belt. Refills as you kill monsters.'
    beastText = 'Right-click to add this to your bestiary.'

    for i in range(len(regions) - 1, 0, -1):
        if regions[i][0] in mapText:
            return parse_map(regions, rarity, name)
        elif regions[i][0] in prophecyText:
            return Prophecy(name)
        elif regions[i][0] in organText:
            return parse_organ(regions, name)
        elif regions[i][0] in flaskText:
            parse_flask(regions, rarity, quality, name)
            return
        elif regions[i][0] in beastText:
            parse_beast(name,rarity, regions)
            return


    c = isCurrency(name, rarity, regions)
    if c:
        print(name)
        return c

    if rarity == 'gem':
        level = regions[1][1].replace(' (Max)', '')
        corrupted = regions[-1] == ['Corrupted']
        print(rarity, name, quality, level, corrupted)
        return Gem(rarity, name, quality,
                   level, corrupted)

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
        elif first_line.count(' ') == 1 and first_line.endswith('Item'):
            if line[:-5] in influenceText:
                influences.append(line[:-5])
        elif i > 2:
            for line in regions[i]:
                mod_values = re.findall(r'[+-]?\d+\.?\d?\d?', line)
                mod_values = ','.join([''.join(v) for v in mod_values])
                mod_text = re.sub(r'[+-]?\d+\.?\d?\d?', '#', line)
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
                    mod_type = ItemModifierType.ENCHANT
                    if not mod_values:
                        mod_text = '#% chance to ' + mod_text
                    mod = get_item_modifiers_by_text((mod_text, mod_type))
                    if not mod:
                        mod, mod_values = get_explicit_mod(mod_text, mod_values)
                if mod:
                    mods.append((mod, mod_values))
                else:
                    print(f"Unable to find mod: {line}")

    base = name
    if rarity == 'rare':
        base = regions[0][2]
    category = None

    if "Synthesised " in base:
        synthesised = True
        base = base.replace("Synthesised ", "")
    
    ninja_bases = get_ninja_bases(LEAGUE)
    for e in ninja_bases:
        if e["base"] in base:
            base = e["base"]
            category = e["type"]
            break
    if not category:
        print("Something went wrong with finding item category")


    print(base, category)
    
    print("name: ",name," Q: ", quality," R: ", rarity," ilvl: ",  ilvl," mods: ", mods, " corrupted: ",corrupted, " mirr: ", mirrored)
