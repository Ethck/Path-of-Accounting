import logging
import re

# Local imports
from enums.item_modifier_type import ItemModifierType
from models.item_modifier import ItemModifier
from models.item import (
    Item,
    Exchangeable,
    Map,
    Prophecy,
    Fragment,
    Organ,
    Flask,
    Currency,
    Card,
    Gem,
)
from utils.trade import get_item_modifiers_by_text

class InvalidItemError(Exception): pass

def parse_item_info(text: str) -> Item:
    """
    Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).

    :param text: A Path of Exile's item clipboard content
    :return: An Item or Item subclass
    """
    # TODO: Determine as many ways as possible to raise InvalidItemError
    # at the proper time.
    # TODO: synthesis items -> Item class: Mostly done, but have to deal with
    # synthesis-item specific modifiers. See Ring.sanitize_modifiers for an
    # attempt that works on most Synthesis unique rings.
    # TODO: stats
    # TODO: handle veiled items (not veiled mods, these are handled) e.g. Veiled Prefix

    item_list = text.split('--------')
    if len(item_list) <= 2:
        raise InvalidItemError

    for i, region in enumerate(item_list):
        item_list[i] = region.strip().splitlines()

    # Remove the Note region; this is always located on the last line.
    if item_list[-1][0].startswith("Note:"):
        del item_list[-1]

    rarity = item_list[0][0][8:].lower()
    # Remove <<set:S>>, <<set:M>>, and/or <<set:MS>> from the name.
    name = re.sub(r'<<set:M?S?>>', '', item_list[0][1])

    quality = 0
    for line in item_list[1]:
        if line.startswith('Quality'):
            quality = int(line[line.find('+')+1:-13])
            break

    influence = []
    ilevel = 0
    modifiers = []
    corrupted = False
    mirrored = False
    base = None
    if len(item_list[0]) == 3:
        base = item_list[0][2]
    raw_sockets = ''

    # Map-only attributes
    iiq = None
    iir = None
    pack_size = None

    # This will only be used to temporarily store organ modifiers in,
    # because we need to sort them and count them to provide the proper
    # values for them.
    organ_modifiers = []

    special_types = {
        'Right-click to add this prophecy to your character.': Prophecy,
        'Can be used in a personal Map Device.': Fragment,
        "Combine this with four other different samples in Tane's Laboratory.": Organ,
        'Right click to drink. Can only hold charges while in belt. Refills as you kill monsters.': Flask,
        'Travel to this Map by using it in a personal Map Device. Maps can only be used once.': Map
    }

    # Default item_class is always just an Item. If we are dealing with a
    # wearable item, this will be used to construct the first class,
    # which Item.deduce_specific_object can then be used on to convert
    # to specific types of items, or edge cases like Scarabs, etc.
    item_class = Item

    # Iterate from the last region to the first. Figure out if a region
    # contains text for a special type of item. If we find that, we'll
    # delete that region from item_list after setting item_class properly.
    for i in range(len(item_list) - 1, 0, -1):
        region = item_list[i]
        if region[0] in special_types:
            item_class = special_types[region[0]]
            del item_list[i]
            break

    for i in range(len(item_list)):
        region = item_list[i]
        first_line = region[0]
        if first_line.startswith('Requirements:'):
            continue  # we ignore this for pricing
        elif rarity == 'currency':
            return Currency(rarity=rarity, name=name)
        elif rarity == 'divination card':
            return Card(rarity=rarity, name=name)
        elif rarity == 'gem':
            level = [
                int(line.replace(' (Max)', '')[7:]) for line in item_list[1]
                if line.startswith('Level')
            ][0]
            corrupted = item_list[-1] == ['Corrupted']
            return Gem(rarity=rarity, name=name, quality=quality,
                       ilevel=level, corrupted=corrupted)
        elif first_line.startswith('Sockets'):
            # Slice 'Sockets: ' off of the beginning
            raw_sockets = first_line[9:]
        elif first_line == 'Corrupted':
            corrupted = True
        elif first_line == 'Mirrored':
            mirrored = True
        elif first_line.startswith('Item Level'):
            # Slice 'Item Level: ' off of the beginning
            ilevel = int(first_line[12:])
        elif first_line.count(' ') == 1 and first_line.endswith('Item'):
            for line in region:
                influence_text = line[:-5]
                influences = {
                    'Elder',
                    'Shaper',
                    'Hunter',
                    'Redeemer',
                    'Warlord',
                    'Crusader'
                }
                if influence_text in influences:
                    influence.append(influence_text.lower())
        elif first_line.startswith('Allocates'):
            for line in region:
                if line.startswith('Allocates'):
                    # Slice 'Allocates ' off of the beginning
                    mod_value = line[10:]
                    element = ('Allocates #', ItemModifierType.ENCHANT)
                    mod = get_item_modifiers_by_text(element)
                    modifiers.append((mod, mod_value))
        elif i > 1: # If the region we're on is past the second region
            for line in region:
                influences = '|'.join([
                    "Shaper",
                    "Elder",
                    "Constrictor",
                    "Enslaver",
                    "Eradicator",
                    "Purifier"
                ])

                # Match all mods containing (+|-)<number> or The Shaper,
                # The Elder, etc. These should all be implicits.
                matches = re.findall(
                    r'([+-]|The )?(\d+\.?\d?\d?|%s)' % influences,
                    line
                )

                # First, glue together mods we find in case we encounter + or -
                # Then, join them into a string separated by ','
                mod_value = ','.join([''.join(m) for m in matches])
                mod_text = re.sub(
                    r'([+-]|The )?(\d+\.?\d?\d?|%s)' % influences,
                    '#', line
                )

                # If we were unable to substitute above, we have a mod without
                # these qualities. Attempt to match the mod straight up.
                if not mod_text:
                    mod_text = line

                logging.debug("Parsing %s" % line)
                if mod_text.endswith("(implicit)"):
                    item_type = ItemModifierType.IMPLICIT
                    # Slice off " (implicit)" from mod_text
                    mod_text = mod_text[:-11]
                    logging.debug("Figuring out if '%s' is an implicit mod" % mod_text)
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Implicit matched")
                        modifiers.append((mod, mod_value))
                    else:
                        logging.debug("No implicit match")
                elif mod_text.endswith("(crafted)"):
                    item_type = ItemModifierType.CRAFTED
                    # Slice off " (crafted)" from mod_text
                    mod_text = mod_text[:-10]
                    logging.debug("Figuring out if '%s' is a crafted mod" % mod_text)
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Crafted matched")
                        modifiers.append((mod, mod_value))
                    else:
                        logging.debug("No crafted match")
                else:
                    logging.debug("Figuring out if '%s' is an enchant" % str(mod_text))
                    # First, try to match an enchant mod
                    item_type = ItemModifierType.ENCHANT
                    if not mod_value: # trigger X on kill\hit mods
                        mod_text = '#% chance to ' + mod_text
                    mod = get_item_modifiers_by_text((mod_text, item_type))
                    if mod is not None:
                        logging.debug("Enchant matched")
                        modifiers.append((mod, mod_value))
                    # Else, if we're not on a map, try to match an explicit mod
                    else:
                        if not mod:
                            raw_text = line
                        logging.debug("Figuring out if '%s' is an explicit" % str(mod_text))
                        item_type = ItemModifierType.EXPLICIT
                        mod = get_item_modifiers_by_text((raw_text, item_type))

                        if not mod:
                            mod = get_item_modifiers_by_text((mod_text, item_type))

                        # Try again with (Local) if the previous mod didn't match
                        if mod is None:
                            altered = mod_text + " (Local)"
                            mod = get_item_modifiers_by_text((altered, item_type))

                        if mod is not None:
                            logging.debug("Explicit matched")
                            modifiers.append((mod, mod_value))
                        elif 'reduced' in mod_text or 'increased' in mod_text:
                            [orig] = [x for x in ('reduced', 'increased') if x in line]
                            target = 'reduced' if orig == 'increased' else 'increased'

                            # In the case where we have "reduced" inside of the
                            # modifier, it could be a negative value of an
                            # "increased" modifier. Therefore, since we found no
                            # matches originally, we try again by replacing text.
                            # If the "increased" version matches, we add a negative
                            # sign in front of the mod_value.
                            # Example: 18% reduced Required Attributes is really
                            # #% increased Required Attributes with a mod_value
                            # of -18.
                            # This implementation addition fixes mods we could
                            # not earlier find in these cases.
                            altered = mod_text.replace(orig, target)
                            mod = get_item_modifiers_by_text((altered, item_type))
                            if mod:
                                mod_value = '-' + mod_value
                                modifiers.append((mod, mod_value))
                            else:
                                logging.debug("No explicit matched")
                        else:
                            logging.debug("No explicit matched")

                        # Metamorph Organ modifiers
                        if item_class == Organ:
                            logging.debug("Attempting to determine if '%s' is an organ modifier" % line)
                            item_type = ItemModifierType.MONSTER
                            text = line.lstrip(' ').rstrip(' ') + " (\u00d7#)"
                            mod = get_item_modifiers_by_text((text, item_type))
                            if mod:
                                logging.debug("Adding %s to organ_modifiers" % str(mod))
                                organ_modifiers.append(mod)

    if item_class == Map:
        # Slice "Item Level: " off of the beginning of the item level line
        ilevel = int(item_list[1][0][10:])

        augmented = [
            re.sub(r'[+%]', '', e.replace(" (augmented)", ""))
            for e in item_list[1]
        ]

        # Parse out map-specific augmented fields.
        for aug in augmented:
            if aug.startswith("Item Quantity: "):
                # Slice 'Item Quantity: ' off of the beginning
                iiq = int(aug[15:])
            elif aug.startswith("Item Rarity: "):
                # Slice 'Item Rarity: ' off of the beginning
                iir = int(aug[13:])
            elif aug.startswith("Monster Pack Size: "):
                # Slice 'Monster Pack Size: ' off of the beginning
                pack_size = int(aug[19:])

        return Map(rarity=rarity, name=name, base=base, quality=quality,
                   ilevel=ilevel, corrupted=corrupted, modifiers=modifiers,
                   iiq=iiq, iir=iir, pack_size=pack_size)

    # For Metamorph Organs, we need to count each modifier we find to
    # provide a correct value for the twisted modifiers that exist
    # for them in our lookup. We do this by counting their occurences
    # in a dictionary.
    organ_mod_counts = dict()
    if len(organ_modifiers) > 0:
        for mod in organ_modifiers:
            if mod in organ_mod_counts:
                organ_mod_counts[mod] += 1
            else:
                organ_mod_counts[mod] = 1

    for mod, mod_value in organ_mod_counts.items():
        modifiers.append((mod, str(mod_value)))

    return item_class(rarity=rarity, name=name, base=base, quality=quality,
                      stats=[], raw_sockets=raw_sockets, ilevel=ilevel,
                      modifiers=modifiers, corrupted=corrupted,
                      mirrored=mirrored, influence=influence)

