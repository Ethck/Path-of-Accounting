import requests
import json
from tkinter import Tk, TclError
import re
import time

leagues = requests.get(url="https://www.pathofexile.com/api/trade/data/leagues").json()
#static = requests.get(url="https://www.pathofexile.com/api/trade/data/static").json()
stats = requests.get(url="https://www.pathofexile.com/api/trade/data/stats").json()


def parse_item_info(text):
	"""
	Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
	"""
	m = re.findall(r'^Rarity: (\w+)\r?\n(.+?)\r?\n(.+?)\r?\n', text)

	if not m:
		return {}
	info = {'name': m[0][1], 'rarity': m[0][0], 'itype': m[0][2]}

	if info['rarity'] == 'Currency':
		info['itype'] = info.pop('rarity')

	else:
		m = re.findall(r'^Quality: +(\d+)%', text)

		info['quality'] = int(m[0]) if m else 0

		m = re.findall(r'Sockets:(.*)', text)

		if m:
			info['links'] = len(m[0]) // 2

		# Corruption status and influenced status
		info['corrupted'] = bool(re.search('^Corrupted$', text, re.M))

		info['influenced'] = {}
		info['influenced']['shaper'] = bool(re.search('Shaper Item', text, re.M))
		info['influenced']['elder'] = bool(re.search('Elder Item', text, re.M))
		info['influenced']['crusader'] = bool(re.search('Crusader Item', text, re.M))
		info['influenced']['hunter'] = bool(re.search('Hunter Item', text, re.M))
		info['influenced']['redeemer'] = bool(re.search('Redeemer Item', text, re.M))
		info['influenced']['warlord'] = bool(re.search('Warlord Item', text, re.M))

		m = re.findall(r'Item Level: (\d+)', text)

		if m:
			info['ilvl'] = int(m[0])

		# Find all the affixes
		m = re.findall(r'Item Level: \d+\n--------\n(.+)((?:\n.+)+)', text)

		if m:
			info['stats'] = []
			info['stats'].append(m[0][0])
			info['stats'].extend(m[0][1].split('\n'))

			# Clean up the leftover stuff
			if "(implicit)" in info['stats'][0]:
				del info['stats'][1:2]
			elif "--------" in info['stats']:
				index = info['stats'].index('--------')
				info['stats'] = info['stats'][:index]
			else:
				info['stats'] = info['stats'][:-1]
			
			if "" in info['stats']:
				info['stats'].remove("")

	return info


def fetch(q_res, exchange = False):
	"""
	Fetch results given trade results and exchange status.
	"""
	results = []
	# Limited to crawling by 10 results at a time due to API restrictions, so check first 20
	for i in range(0, 50, 10):
		url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(q_res["result"][i:i+10])}?query={q_res["id"]}'

		if exchange:
			url += "exchange=true"

		res = requests.get(url)
		if res.status_code != 200:
			print(f'[!] Trade result retrieval failed: HTTP {res.status_code}! '
					f'Message: {res.json().get("error", "unknown error")}')
			break
		results += res.json()['result']

	#for i, result in enumerate(results):
	#	results[i] = {k: str(v).encode("utf-8") for k,v in result.items()}

	return results


def query_trade(name=None, itype=None, links=None, corrupted=None, influenced = None, rarity=None, league='Metamorph', stats = []):
	"""
	Build JSON for fetch request of an item for trade.
	"""

	j = {'query':{'filters':{}}, 'sort': {'price': 'asc'}}

	if name and rarity == "Unique":
		j['query']['name'] = name

	if itype:
		j['query']['type'] = itype

	j['query']['status'] = {}
	j['query']['status']['option'] = 'online'

	if links:
		j['query']['filters']['socket_filters'] = {'filters': {'links': {'min': links}}}

	if corrupted is not None:
		j['query']['filters']['misc_filters'] = {'filters': {'corrupted': {'option':
				str(corrupted).lower()}}}

	if influenced:
		if True in influenced.values():
			j['query']['filters']['misc_filters'] = {}
			j['query']['filters']['misc_filters']['disabled'] = 'false'
			j['query']['filters']['misc_filters']['filters'] = {}
			
			for influence in influenced:

				if influenced[influence]:
					j['query']['filters']['misc_filters']['filters'][influence + "_item"] = "true"


	if stats:
		j['query']['stats'] = [{}]
		j['query']['stats'][0]['type'] = 'and'
		j['query']['stats'][0]['filters'] = []
		for stat in stats:
			proper_affix = find_affix_match(stat)
			affix_types = ["implicit", "crafted", "explicit"]
			if any(atype in proper_affix for atype in affix_types):
				j['query']['stats'][0]['filters'].append({'id': proper_affix, 'value': {'min': 50, 'max': 200}, 'disabled': 'false'})

	#print(j)

	
	query = requests.post(f'https://www.pathofexile.com/api/trade/search/{league}', json=j)
	res = query.json()

	if query.status_code != 200:
		print(f'[!] Trade query failed: HTTP {query.status_code}! ')
		print(res)
		return []

	results = fetch(res)
	return results


def query_exchange(qcur, league='Metamorph'):
	"""
	Build JSON for fetch request of wanted exchange.
	"""
	def_json = {'exchange': {'have': ['chaos'], 'want': ['exa'], 'status': {'option': 'online'}}}

	query = requests.post(f'https://www.pathofexile.com/api/trade/exchange/{league}', json=def_json)
	res = query.json()

	if query.status_code != 200:
		print(f'[!] Trade query failed: HTTP {query.status_code}! ')
		return "Could not find requested currency exchange value."


	results = fetch(res, exchange = True)
	return results


def affix_equals(text, affix):
	query = re.sub(r"\d+", "#", affix)
	query = re.sub(r"\+", "", query)

	if query.endswith(r" (implicit)"):
		text = text + r" (implicit)"

	if text.endswith("(Local)"):
		query = query + r" (Local)"

	if text == query:
		print(f"Found mod {text}")
		return True

	return False

def find_affix_match(affix):
	explicits = stats['result'][1]['entries']
	implicits = stats['result'][2]['entries']
	crafted = stats['result'][5]['entries']
	proper_affix = ""

	if "(implicit)" in affix:
		for implicit in implicits:
			if affix_equals(implicit['text'], affix):
				proper_affix = implicit['id']

	elif "(crafted)" in affix:
		for craft in crafted:
			if affix_equals(craft['text'], affix):
				proper_affix = craft['id']

	else:
		for explicit in explicits:
			if affix_equals(explicit['text'], affix):
				proper_affix = explicit['id']

	return proper_affix


def watch_clipboard():
	"""
	Watch clipboard for unique items being copied to check lowest prices on trade.
	"""
	print('[*] Watching clipboard (Ctrl+C to stop)...')
	prev = None
	while 1:
		try:
			text = Tk().clipboard_get()
		except TclError:	 # ignore non-text clipboard contents
			continue
		try:
			if text != prev:
				info = parse_item_info(text)
				trade_info = None

				if info:
					if info.get('rarity') == 'Unique':
						print(f'[*] Found unique item in clipboard: {info["name"]} {info["itype"]}')
						base = f'Only showing results that are: '

						if info['corrupted']:
							base += f"Corrupted "

						if info['links'] > 1:
							base += f"{info['links']} linked "

						print("[-]", base)

						print('[-] Getting prices from pathofexile.com/trade...')
						trade_info = query_trade(**{k:v for k, v in info.items() if k in ('name', 'links',
								'corrupted', 'rarity')})

					elif info['itype'] == 'Currency':
						print(f'[-] Found currency {info["name"]} in clipboard; '
								'getting prices from pathofexile.com/trade/exchange...')
						trade_info = query_exchange(info['name'])

					else:
						print(f"[*] Found {info['rarity']} item in clipboard: {info['name']} {info['itype']}")
						print('[-] Price assesment for this item has been disabled due to technical limitations.')
						#trade_info = query_trade(**{k:v for k, v in info.items() if k in ('name', 'itype', 'links',
								#'corrupted', 'influenced', 'stats')})
					
					if trade_info:
						prices = [x['listing']['price'] for x in trade_info]
						prices = ['%(amount)s%(currency)s' % x for x in prices]
						prices = {'%s x %s' % (prices.count(x), x):None for x in prices}
						print(f'[-] Lowest 50 prices: {", ".join(prices.keys())}')

					elif trade_info is not None:
						print(f'[!] No results!')

				prev = text
			time.sleep(.3)

		except KeyboardInterrupt:
			break


if __name__ == "__main__":
	watch_clipboard()