import requests
import json
from tkinter import Tk, TclError
import re
import time
from colorama import init, deinit, Fore, Back, Style
import yaml

#Local imports
from currency import (CURRENCY, OILS, CATALYSTS, FRAGMENTS_AND_SETS, INCUBATORS, SCARABS, RESONATORS,
						FOSSILS, VIALS, ESSENCES, DIV_CARDS)

DEBUG = False

# If using hotkeys, we also import the hotkeys local module in the main loop.
# If using GUI, import GUI
with open("settings.yaml", "r") as settings_file:
	settings = yaml.safe_load(settings_file)

if settings['use_gui'] == True:
	import testGui


# Current Leagues. Not used.
leagues = requests.get(url="https://www.pathofexile.com/api/trade/data/leagues").json()
# All available stats on items.
stats = requests.get(url="https://www.pathofexile.com/api/trade/data/stats").json()

def parse_item_info(text):
	"""
	Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
	"""
	# Find out if this is a path of exile item
	m = re.findall(r'^Rarity: (\w+)\r?\n(.+?)\r?\n(.+?)\r?\n', text)

	if not m: # Different check
		m = re.findall(r"^Rarity: (.*)\n(.*)", text)
		if not m:
			return {}
		else:
			info = {'name': m[0][1], 'rarity': m[0][0], 'itype': m[0][0]}
	else:

		# get some basic info
		info = {'name': m[0][1], 'rarity': m[0][0], 'itype': m[0][2]}


	unident = bool(re.search('Unidentified', text, re.M))
	metamorph = bool(re.search("Tane", text, re.M))
	prophecy = bool(re.search("Right-click to add this prophecy to your character.", text, re.M))

	# Get Qual
	m = re.findall(r'Quality: \+(\d+)%', text)

	info['quality'] = int(m[0]) if m else 0

	if 'Map' in info['name'] and 'Map' not in info['itype']: #Seems to be all Superior maps...
		if info['itype'] == "--------":
			info['itype'] = info['name']

	if '<<set:MS>><<set:M>><<set:S>>' in info['name']: # For checking in chat items... For some reason this is added.
		info['name'] = info['name'].replace('<<set:MS>><<set:M>><<set:S>>', "").strip()

	# Oh, it's currency!
	if info['rarity'] == 'Currency':
		info['itype'] = info.pop('rarity')
	elif info['rarity'] == 'Divination Card':
		info['itype'] = info.pop('rarity')
	elif info['rarity'] == 'Normal' and 'Scarab' in info['name']:
		info['itype'] = 'Currency'
	elif 'Map' in info['itype']:
		if info['quality'] != 0:
			info['itype'] = info['itype'].replace("Superior", "").strip()
		map_mods = {}
		map_mods['tier'] = re.findall(r"Map Tier: (\d+)", text)[0]

		iiq_re = re.findall(r"Item Quantity: \+(\d+)%", text)
		if len(iiq_re) > 0:
			map_mods['iiq'] = iiq_re[0]

		pack_re = re.findall(r"Pack Size: \+(\d+)%", text)
		if len(pack_re) > 0:
			map_mods['pack'] = pack_re[0]

		iir_re = re.findall(r"Item Rarity: \+(\d+)%", text)
		if len(iir_re) > 0:
			map_mods['iir'] = iir_re[0]

		map_mods['blight'] = bool(re.search(r"Blighted", text, re.M))
		map_mods['shaper'] = bool(re.search('Area is influenced by The Shaper', text, re.M))
		map_mods['elder'] = bool(re.search('Area is influenced by The Elder', text, re.M))
		map_mods['enslaver'] = bool(re.search('Map is occupied by The Enslaver', text, re.M))
		map_mods['eradicator'] = bool(re.search('Map is occupied by The Eradicator', text, re.M))
		map_mods['constrictor'] = bool(re.search('Map is occupied by The Constrictor', text, re.M))
		map_mods['purifier'] = bool(re.search('Map is occupied by The Purifier', text, re.M))

		info['maps'] = map_mods

	elif info['itype'] == "--------" and unident: #Unided
		info['itype'] = info['name']
		if info['rarity'] == 'Unique':
			print("[!] " + Fore.RED + "Can't price " + Fore.WHITE + "this item because it is " + Fore.YELLOW + "unidentified" + Fore.WHITE + ". Please identify and try again.")
			return 0
		# Item Level
		m = re.findall(r'Item Level: (\d+)', text)

		if m:
			info['ilvl'] = int(m[0])
	elif metamorph:
		info['itype'] = "Metamorph"
		m = re.findall(r'Item Level: (\d+)', text)

		if m:
			info['ilvl'] = int(m[0])

	elif info['rarity'] == 'Normal' and prophecy: #Prophecies
		info['itype'] = 'Prophecy'

	else:
		if info['rarity'] == 'Magic' or info['rarity'] == 'Normal':
			info['itype'] = None

		if info['rarity'] == 'Gem':
			m = bool(re.search('Vaal', text, re.M))
			a = bool(re.search('Awakened', text, re.M))
			c = bool(re.search('^Corrupted', text, re.M))

			lvl = re.findall(r'Level: (\d+)', text)[0]
			if lvl is not None:
				info['gem_level'] = lvl

			if c:
				info['corrupted'] = True
			if m and not a:
				info['itype'] = "Vaal " + info['name']
			else:
				info['itype'] = info['name']

		# Sockets and Links
		m = re.findall(r'Sockets:(.*)', text)

		if m:
			info['links'] = m[0].count("-") + 1

		# Corruption status and influenced status
		info['corrupted'] = bool(re.search('^Corrupted$', text, re.M))

		info['influenced'] = {}
		info['influenced']['shaper'] = bool(re.search('Shaper Item', text, re.M))
		info['influenced']['elder'] = bool(re.search('Elder Item', text, re.M))
		info['influenced']['crusader'] = bool(re.search('Crusader Item', text, re.M))
		info['influenced']['hunter'] = bool(re.search('Hunter Item', text, re.M))
		info['influenced']['redeemer'] = bool(re.search('Redeemer Item', text, re.M))
		info['influenced']['warlord'] = bool(re.search('Warlord Item', text, re.M))

		# Item Level
		m = re.findall(r'Item Level: (\d+)', text)

		if m:
			info['ilvl'] = int(m[0])

		# Find all the affixes
		m = re.findall(r'Item Level: \d+\n--------\n(.+)((?:\n.+)+)', text)
		if DEBUG:
			print("STATS:", m)

		if m:
			info['stats'] = []
			info['stats'].append(m[0][0])
			info['stats'].extend(m[0][1].split('\n'))

			# Clean up the leftover stuff / Make it useable data
			if info['stats'][1] == "" and info['stats'][2] == "--------": #Implicits and enchantments.
				del info['stats'][1:3]
			elif "--------" in info['stats']:
				index = info['stats'].index('--------')
				print(info)
				info['stats'] = info['stats'][:index]
			else:
				info['stats'] = info['stats'][:-1]
			
			if "" in info['stats']:
				info['stats'].remove("")

	if DEBUG:#DEBUG
		print("COMPLETE INFO: ", info)

	return info


def fetch(q_res, exchange = False):
	"""
	Fetch is the last step of the API. The item's attributes are decided, and this function checks to see if
	there are any similar items like it listed.

	returns JSON of all available similar items.
	"""

	if DEBUG:
		print(q_res)

	results = []
	# Limited to crawling by 10 results at a time due to API restrictions, so check first 50
	DEFAULT_CAP = 50
	DEFAULT_INTERVAL = 10
	cap = DEFAULT_CAP
	interval = DEFAULT_INTERVAL

	# If there's less than 10 results, change to the number there is.
	if len(q_res) < DEFAULT_CAP:
		cap = int((len(q_res) / 10) * 10)

	# Find all the results
	if 'result' in q_res:
		for i in range(0, cap, interval):
			url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(q_res["result"][i:i+10])}?query={q_res["id"]}'

			if exchange:
				url += "exchange=true"

			res = requests.get(url)
			if res.status_code != 200:
				print(f'[!] Trade result retrieval failed: HTTP {res.status_code}! '
						f'Message: {res.json().get("error", "unknown error")}')
				break

			# Return the results from our fetch (this has who to whisper, prices, and more!)
			results += res.json()['result']
	else:
				print("[!] Something went horribly wrong. Please make an issue on the github page and include the item that caused this error. https://github.com/ethck/path-of-accounting/issues")

	if DEBUG:
		print(results)

	return results


def query_trade(name = None, ilvl = None, itype = None, links = None, corrupted = None, influenced = None, rarity = None, league = 'Metamorph', stats = [], gem_level = None, quality = None, maps = None):
	"""
	Build JSON for fetch request of an item for trade.
	Take all the parsed item info, and construct JSON based off of it.

	returns results of the fetch function.
	"""
	# Basic JSON structure
	j = {'query':{'filters':{}}, 'sort': {'price': 'asc'}}

	if maps is not None:
		j['query']['filters']['map_filters'] = {}
		j['query']['filters']['map_filters']['filters'] = {}

		if rarity == "Unique": # Unique maps, may be unidentified
			j['query']['filters']['type_filters'] = {}
			j['query']['filters']['type_filters']['filters'] = {'rarity': {'option': 'unique'}}
			j['query']['type'] = {'option': name}
			name = None

		if maps['blight']:
			j['query']['filters']['map_filters']['filters']['map_blighted'] = 'True'
			itype = itype.replace("Blighted", "").strip()

		if 'iiq' in maps:
			if maps['iiq']:
				j['query']['filters']['map_filters']['filters']['map_iiq'] = {'min': maps['iiq'], 'max': 'null'}

		if 'iir' in maps: # False if Unidentified
			if maps['iir']:
				j['query']['filters']['map_filters']['filters']['map_iir'] = {'min': maps['iir'], 'max': 'null'}
		if 'pack' in maps: # False if Unidentified
			if maps['pack']:
				j['query']['filters']['map_filters']['filters']['map_packsize'] = {'min': maps['pack'], 'max': 'null'}

		if maps['tier']:
			j['query']['filters']['map_filters']['filters']['map_tier'] = {'min': maps['tier'], 'max': 'null'}

		if maps['shaper'] or maps['elder']:
			j['query']['stats'] = [{}]
			j['query']['stats'][0]['type'] = 'and'
			j['query']['stats'][0]['filters'] = []

			if maps['shaper']:
				j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_1792283443', 'value': {'option': '1'}})
			elif maps['elder']:
				j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_1792283443', 'value': {'option': '2'}})

			if maps['enslaver'] or maps['eradicator'] or maps['constrictor'] or maps['purifier']:
				if maps['enslaver']:
					j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_3624393862', 'value': {'option': '1'}})
				elif maps['eradicator']:
					j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_3624393862', 'value': {'option': '2'}})
				elif maps['constrictor']:
					j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_3624393862', 'value': {'option': '3'}})
				elif maps['purifier']:
					j['query']['stats'][0]['filters'].append({'id': 'implicit.stat_3624393862', 'value': {'option': '4'}})

	# If unique, Div Card, or Gem search by name
	if rarity == "Unique" or itype == "Divination Card":
		if name != None:
			j['query']['name'] = name

	if itype == "Metamorph":
		mm_parts = ["Brain", "Lung", "Eye", "Heart", "Liver"]

		for part in mm_parts:
			if part in name:
				del j['query']['name']
				j['query']['type'] = "Metamorph " + part

	# Set itemtype. TODO: change to allow similar items of other base types... Unless base matters...
	elif itype:
		j['query']['type'] = itype

	if itype == "Prophecy":
		j['query']['name'] = name

	# Only search for items online
	j['query']['status'] = {}
	j['query']['status']['option'] = 'online'

	# Set required links
	if links:
		j['query']['filters']['socket_filters'] = {'filters': {'links': {'min': links}}}

	j['query']['filters']['misc_filters'] = {}
	j['query']['filters']['misc_filters']['filters'] = {}

	# Set corrupted status
	if corrupted:
		j['query']['filters']['misc_filters']['filters']['corrupted'] = {'option': 'true'}

	if gem_level:
		# Only used for skill gems
		j['query']['filters']['misc_filters']['filters']['gem_level'] = {'min': gem_level, 'max': 'null'}
		j['query']['filters']['misc_filters']['filters']['quality'] = {'min': quality, 'max': 'null'}

	# Set influenced status
	if influenced:
		if True in influenced.values():
			for influence in influenced:
				if influenced[influence]:
					j['query']['filters']['misc_filters']['filters'][influence + "_item"] = "true"


	if (name == itype or rarity == 'Normal' or rarity == 'Magic' or itype == 'Metamorph') and ilvl != None: #Unidentified item
		j['query']['filters']['misc_filters']['filters']['ilvl'] = {'min': ilvl - 3, 'max': ilvl + 3}

	fetch_called = False

	if DEBUG:
		print(j)
	# Find every stat
	if stats:
		j['query']['stats'] = [{}]
		j['query']['stats'][0]['type'] = 'and'
		j['query']['stats'][0]['filters'] = []
		for stat in stats:
			(proper_affix, value) = find_affix_match(stat)
			affix_types = ["implicit", "crafted", "explicit", "enchantments"]
			if any(atype in proper_affix for atype in affix_types): #If proper_affix is an actual mod...
				j['query']['stats'][0]['filters'].append({'id': proper_affix, 'value': {'min': value, 'max': 999}})

		# Turn life + resists into pseudo-mods
		j = create_pseudo_mods(j)

		# Now search for similar items, if none found remove a stat and try again. TODO: Refactor and include more vars.
		num_stats_ignored = 0
		total_num_stats = len(j['query']['stats'][0]['filters'])
		while len(j['query']['stats'][0]['filters']) > 0:

			# If we ignore more than half of the stats, it's not accurate
			if num_stats_ignored > (int(total_num_stats * 0.6)):
				print(f"[!] Take any values after this with a grain of salt. You should probably do a" + Fore.RED + " MANUAL search")

			# Make the actual request.
			query = requests.post(f'https://www.pathofexile.com/api/trade/search/{league}', json=j)

			# No results found. Trim the mod list until we find results.
			if 'result' in query.json():
				if (len(query.json()['result'])) == 0:
					
					# Choose a non-priority mod
					i = choose_bad_mod(j)

					# Tell the user which mod we are deleting
					print("[-] Removing the" + Fore.CYAN + f" {stat_translate(i)} " + Fore.WHITE + "mod from the list due to" + Fore.RED + " no results found.")

					# Remove bad mod.
					j['query']['stats'][0]['filters'].remove(i)
					num_stats_ignored += 1
				else: # Found a result!
					res = query.json()
					fetch_called = True
					results = fetch(res)

					if DEBUG:
						print("Found results!")


					if result_prices_are_none(results):
						if DEBUG:
							print("All resulting prices are none.")
						# Choose a non-priority mod
						i = choose_bad_mod(j)

						# Tell the user which mod we are deleting
						print("[-] Removing the" + Fore.CYAN + f" {stat_translate(i)} " + Fore.WHITE + "mod from the list due to" + Fore.RED + " no results found.")

						# Remove bad mod.
						j['query']['stats'][0]['filters'].remove(i)
						num_stats_ignored += 1
					else:
						return results
			else:
				print("[!] Something went horribly wrong. Please make an issue on the github page and include the item that caused this error. https://github.com/ethck/path-of-accounting/issues")

	if not fetch_called: # Any time we ignore stats.
		query = requests.post(f'https://www.pathofexile.com/api/trade/search/{league}', json=j)
		res = query.json()
		results = fetch(res)
		return results

def create_pseudo_mods(j):
	"""
	Combines life and resists into pseudo-mods

	Returns item
	"""
	# Combine life and resists for pseudo-stats
	total_ele_resists = 0
	total_chaos_resist = 0
	total_life = 0

	# TODO: Find a way to not hard-code
	# TODO: Support for attributes (including str->life), added phys to attacks, life regen
	solo_resist_ids = [
		'explicit.stat_3372524247', # Explicit fire resist
		'explicit.stat_1671376347', # Explicit lightning resist
		'explicit.stat_4220027924', # Explicit cold resist
		'implicit.stat_3372524247', # Implicit fire resist
		'implicit.stat_1671376347', # Implicit lightning resist
		'implicit.stat_4220027924', # Implicit cold resist
		'crafted.stat_3372524247',  # Crafted fire resist
		'crafted.stat_1671376347',  # Crafted lightning resist
		'crafted.stat_4220027924',  # Crafted cold resist
	]

	dual_resist_ids = [
		'explicit.stat_2915988346', # Explicit fire and cold resists
		'explicit.stat_3441501978', # Explicit fire and lightning resists
		'explicit.stat_4277795662', # Explicit cold and lightning resists
		'implicit.stat_2915988346', # Implicit fire and cold resists
		'implicit.stat_3441501978', # Implicit fire and lightning resists
		'implicit.stat_4277795662', # Implicit cold and lightning resists
		'crafted.stat_2915988346',  # Crafted fire and cold resists
		'crafted.stat_3441501978',  # Crafted fire and lightning resists
		'crafted.stat_4277795662',  # Crafted cold and lightning resists
	]

	triple_resist_ids = [
		'explicit.stat_2901986750', # Explicit all-res
		'implicit.stat_2901986750', # Implicit all-res
		'crafted.stat_2901986750',  # Crafted all-res
	]

	solo_chaos_resist_ids = [
		'explicit.stat_2923486259', # Explicit chaos resist
		'implicit.stat_2923486259', # Implicit chaos resist
	]

	dual_chaos_resist_ids = [
		'crafted.stat_378817135',   # Crafted fire and chaos resists
		'crafted.stat_3393628375',  # Crafted cold and chaos resists
		'crafted.stat_3465022881',  # Crafted lightning and chaos resists
	]

	life_ids = [
		'explicit.stat_3299347043', # Explicit maximum life
		'implicit.stat_3299347043', # Implicit maximum life
	]

	combined_filters = []

	# Solo elemental resists
	for i in j['query']['stats'][0]['filters']:
		if i['id'] in solo_resist_ids:
			total_ele_resists += int(i['value']['min'])
			combined_filters.append(i)

	# Dual elemental resists
		elif i['id'] in dual_resist_ids:
			total_ele_resists += 2*int(i['value']['min'])
			combined_filters.append(i)

	# Triple elemental resists
		elif i['id'] in triple_resist_ids:
			total_ele_resists += 3*int(i['value']['min'])
			combined_filters.append(i)

	# Solo chaos resists
		elif i['id'] in solo_chaos_resist_ids:
			total_chaos_resist += int(i['value']['min'])
			combined_filters.append(i)

	# Dual chaos resists
		elif i['id'] in dual_chaos_resist_ids:
			total_chaos_resist += int(i['value']['min'])
			total_ele_resists += int(i['value']['min'])
			combined_filters.append(i)

	# Maximum life
		elif i['id'] in life_ids:
			total_life += int(i['value']['min'])
			combined_filters.append(i)

	# Round down to nearest 10 for combined stats (off by default)
	do_round = False
	if do_round:
		total_ele_resists = total_ele_resists - (total_ele_resists % 10)
		total_chaos_resist = total_chaos_resist - (total_chaos_resist % 10)
		total_life = total_life - (total_life % 10)

	# Remove stats that have been combined into psudo-stats
	j['query']['stats'][0]['filters'] = [e for e in j['query']['stats'][0]['filters'] if e not in combined_filters]
	
	if total_ele_resists > 0:
		j['query']['stats'][0]['filters'].append({'id': 'pseudo.pseudo_total_elemental_resistance', 'value': {'min': total_ele_resists, 'max': 999}})
		print("[o] Combining the" + Fore.CYAN + f" elemental resistance " + Fore.WHITE + "mods from the list into a pseudo-parameter")
		print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_ele_resists}% total Elemental Resistance (pseudo)")

	if total_chaos_resist > 0:
		j['query']['stats'][0]['filters'].append({'id': 'pseudo.pseudo_total_chaos_resistance', 'value': {'min': total_chaos_resist, 'max': 999}})
		print("[o] Combining the" + Fore.CYAN + f" chaos resistance " + Fore.WHITE + "mods from the list into a pseudo-parameter")
		print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_chaos_resist}% total Chaos Resistance (pseudo)")

	if total_life > 0:
		j['query']['stats'][0]['filters'].append({'id': 'pseudo.pseudo_total_life', 'value': {'min': total_life, 'max': 999}})
		print("[o] Combining the" + Fore.CYAN + f" maximum life " + Fore.WHITE + "mods from the list into a pseudo-parameter")
		print("[+] Pseudo-mod " + Fore.GREEN + f"+{total_life} to maximum Life (pseudo)")

	return j

def choose_bad_mod(j):
	"""
	Chooses a non-priority mod to delete.

	Returns dictionary
	"""
	# Good mod list
	priority = [
		'pseudo.pseudo_total_elemental_resistance',
		'pseudo.pseudo_total_chaos_resistance',
		'pseudo.pseudo_total_life'
	]

	# Choose a non-priority mod to delete
	for i in j['query']['stats'][0]['filters']:
		if i['id'] not in priority:
			break
	
	return i


def result_prices_are_none(j):
	"""
	Determine if all items in result are unpriced or not.

	Returns BOOLEAN
	"""
	return all(x['listing']['price'] == None for x in j)


def query_exchange(qcur, league='Metamorph'):
	"""
	Build JSON for fetch request of wanted currency exchange.
	"""

	print(f"[*] All values will be reported as their chaos, exalt, or mirror equivalent.")
	IG_CURRENCY = [CURRENCY, OILS, CATALYSTS, FRAGMENTS_AND_SETS, INCUBATORS, SCARABS, RESONATORS,
				FOSSILS, VIALS, ESSENCES, DIV_CARDS]

	selection = "Exalt"
	if any(d.get(qcur, None) for d in IG_CURRENCY):
		for curr_type in IG_CURRENCY:
			if qcur in curr_type:
				selection = curr_type[qcur]


	# Default JSON
	for haveCurrency in ['chaos', 'exa', 'mir']:
		def_json = {'exchange': {'have': [haveCurrency], 'want': [selection], 'status': {'option': 'online'}}}

		query = requests.post(f'https://www.pathofexile.com/api/trade/exchange/{league}', json=def_json)
		res = query.json()
		if DEBUG:
			print(def_json)

		if len(res['result']) == 0:
			continue
		else:
			break


	results = fetch(res, exchange = True)
	return results


def affix_equals(text, affix):
	"""
	Clean up the affix to match the given text so we can find the correct id to search with.

	returns tuple (BOOLEAN, value)
	"""
	value = 0
	match = re.findall(r"\d+", affix)
	if len(match) > 0:
		value = match[0]
	query = re.sub(r"\d+", "#", affix)
	query = re.sub(r"\+", "", query)


	if query.endswith(r" (implicit)"):
		text = text + r" (implicit)"

	if query.endswith(r" (crafted)"):
		text = text + r" (crafted)"

	if query.endswith(r" (pseudo)"):
		text = text + r" (pseudo)"
		query = r"+" + query

	if text.endswith("(Local)"):
		query = query + r" (Local)"

	if text == query:
		print("[+] Found mod " + Fore.GREEN + f"{text[0:]}: {value}") #TODO: support "# to # damage to attacks" type mods and other similar
		return (True, value)

	return (False, 0)


def find_affix_match(affix):
	"""
	Search for the proper id to return the correct results.

	returns tuple (id of the affix requested, value)
	"""
	pseudos = stats['result'][0]['entries']
	explicits = stats['result'][1]['entries']
	implicits = stats['result'][2]['entries']
	crafted = stats['result'][5]['entries']
	enchantments = stats['result'][4]['entries']
	proper_affix = ("", 0)

	if DEBUG:
		print("AFFIX:", affix)

	if "(pseudo)" in affix:
		for pseudo in pseudos:
			(match, value) = affix_equals(pseudo['text'], affix)
			if match:
				proper_affix = (pseudo['id'], value)

	elif "(implicit)" in affix:
		for implicit in implicits:
			(match, value) = affix_equals(implicit['text'], affix)
			if match:
				proper_affix = (implicit['id'], value)

	elif "(crafted)" in affix:
		for craft in crafted:
			(match, value) = affix_equals(craft['text'], affix)
			if match:
				proper_affix = (craft['id'], value)

	else:
		Found = False
		for explicit in explicits:
			(match, value) = affix_equals(explicit['text'], affix)
			if match:
				proper_affix = (explicit['id'], value)
				Found = True

		if not Found:
			# Maybe it's an enchantment
			for enchant in enchantments:
				(match, value) = affix_equals(enchant['text'], affix)
				if match:
					proper_affix = (enchant['id'], value)

	return proper_affix


def stat_translate(jaffix):
	"""
	Translate id to the equivalent stat.
	"""
	affix = jaffix['id']

	pseudos = stats['result'][0]['entries']
	explicits = stats['result'][1]['entries']
	implicits = stats['result'][2]['entries']
	crafted = stats['result'][5]['entries']

	if "pseudo" in affix:
		return find_stat_by_id(affix, pseudos)
	elif "implicit" in affix:
		return find_stat_by_id(affix, implicits)
	elif "crafted" in affix:
		return find_stat_by_id(affix, crafted)
	else:
		return find_stat_by_id(affix, explicits)


def find_stat_by_id(affix, stat_list):
	"""
	Helper function to find stats by their id.
	"""
	for stat in stat_list:
		if stat['id'] == affix:
			return stat['text']


def watch_clipboard():
	"""
	Watch clipboard for items being copied to check lowest prices on trade.
	"""
	print('[*] Watching clipboard (Ctrl+C to stop)...')
	prev = None
	while True:
		try:
			text = root.clipboard_get()
		except TclError:	 # ignore non-text clipboard contents
			continue
		try:
			if text != prev:
				info = parse_item_info(text)
				trade_info = None

				if info:
					# Uniques, only search by corrupted status, links, and name.
					if (info.get('rarity') == 'Unique') and (info.get('itype') != "Metamorph"):
						if info['name'] == info['itype']:
							print(f'[*] Found Unique item in clipboard: {info["name"]}')
						else:
							print(f'[*] Found Unique item in clipboard: {info["name"]} {info["itype"]}')
						base = f'Only showing results that are: '
						pprint = base

						if 'corrupted' in info:
							if info['corrupted']:
								pprint += f"Corrupted "

						if "links" in info:
							if info['links'] > 1:
								pprint += f"{info['links']} linked "

						if pprint != base:
							print("[-]", pprint)

						trade_info = query_trade(**{k:v for k, v in info.items() if k in ('name', 'links',
								'corrupted', 'rarity', 'maps')})

					elif info['itype'] == 'Currency':
						print(f'[-] Found currency {info["name"]} in clipboard')
						trade_info = query_exchange(info['name'])

					elif info['itype'] == 'Divination Card':
						print(f'[-] Found Divination Card {info["name"]}')
						trade_info = query_exchange(info['name'])

					else:
						# Do intensive search.
						if info['itype'] != info['name'] and info['itype'] != None:
							print(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {info['itype']}")
						else:
							extra_strings = ""
							if info['rarity'] == "Gem":
								extra_strings += f"Level: {info['gem_level']}+, "

							if 'corrupted' in info:
								if info['corrupted']:
									extra_strings += "Corrupted: True, "

							if info['quality'] != 0:
								extra_strings += f"Quality: {info['quality']}+"

							print(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {extra_strings}")

						trade_info = query_trade(**{k:v for k, v in info.items() if k in ('name', 'itype', 'ilvl', 'links',
								'corrupted', 'influenced', 'stats', 'rarity', 'gem_level', 'quality', 'maps')})
					
					# If results found
					if trade_info:
						# If more than 1 result, assemble price list.
						if len(trade_info) > 1:
							#print(trade_info[0]['item']['extended']) #TODO search this for bad mods
							prev_account_name = ""
							# Modify data to usable status.
							prices = []
							for trade in trade_info: # Stop price fixers
								if trade['listing']['account']['name'] != prev_account_name:
									prices.append(trade['listing']['price'])

								prev_account_name = trade['listing']['account']['name']

							prices = ['%(amount)s%(currency)s' % x for x in prices if x != None]

							prices = {x:prices.count(x) for x in prices}
							print_string = ""
							total_count = 0

							# Make pretty strings.
							for price_dict in prices:
								pretty_price = " ".join(re.split(r"([0-9.]+)", price_dict)[1:])
								print_string += f"{prices[price_dict]} x " + Fore.YELLOW + f"{pretty_price}" + Fore.WHITE + ", "
								total_count += prices[price_dict]

							# Print the pretty string, ignoring trailing comma 
							print(f'[$] Price: {print_string[:-2]}\n\n')
							if settings['use_gui'] == True:

								price = [re.findall(r"([0-9.]+)", tprice)[0] for tprice in prices.keys()]

								currency = None #TODO If a single result shows a higher tier, it currently presents only that value in the GUI.
								if 'mir' in print_string:
									currency = "mirror"
								elif 'exa' in print_string:
									currency = "exalt"
								elif 'chaos' in print_string:
									currency = "chaos"
								elif 'alch' in print_string:
									currency = "alchemy"


								price.sort()

								# Fastest method for calculating average as seen here:
								# https://stackoverflow.com/questions/21230023/average-of-a-list-of-numbers-stored-as-strings-in-a-python-list
								# TODO average between multiple currencies...
								L = [float(n) for n in price if n]
								average = str(round(sum(L)/float(len(L)) if L else '-', 2))

								price = [price[0], average, price[-1]]

								testGui.assemble_price_gui(price, currency)

						else:
							price = trade_info[0]['listing']['price']
							if price != None:
								price_val = price['amount']
								price_curr = price['currency']
								price = f"{price_val} x {price_curr}"

								if settings['use_gui'] == True:
									testGui.assemble_price_gui(price, currency)

							print("[$] Price:" + Fore.YELLOW + f" {price} "+ "\n\n")

					elif trade_info is not None:
						print(f'[!] No results!')

				prev = text
			time.sleep(.3)

		except KeyboardInterrupt:
			break


if __name__ == "__main__":
	init(autoreset=True) #Colorama
	root = Tk()
	root.withdraw()

	if settings['use_hotkeys'] == True:
		import hotkeys
		hotkeys.watch_keyboard()

	watch_clipboard()
	deinit() #Colorama