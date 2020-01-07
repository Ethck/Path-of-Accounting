import re

with open("divCards.txt", "r") as f:
	text = f.readlines()
	with open("divCards.json", "w") as j:
		for card in text:
			print_string = ""
			if len(card.split(" ")) == 1:
				print_string = re.sub('^(.*)', r'"\1": "\1"', card)
				ps1 = print_string.split(':')[0]
				ps2 = print_string.split('"')[3:-1][0].lower()
				print_string = ps1 + ":" + f'"{ps2}",'

			elif len(card.split(" ")) == 2:
				print_string = re.sub('^(.*)', r'"\1": "\1"', card)
				ps1 = print_string.split(':')[0]
				ps2 = print_string.split('"')[3:-1][0].lower()
				ps2 = ps2.replace(" ", "-")
				print_string = ps1 + ":" + f'"{ps2}",'

			elif len(card.split(" ")) == 3:
				print_string = re.sub('^(.*)', r'"\1": "\1"', card)
				ps1 = print_string.split(':')[0]
				ps2 = print_string.split('"')[3:-1][0].lower()
				ps2 = ps2.replace(" ", "-")
				print_string = ps1 + ":" + f'"{ps2}",'

			elif len(card.split(" ")) == 4:
				print_string = re.sub('^(.*)', r'"\1": "\1"', card)
				ps1 = print_string.split(':')[0]
				ps2 = print_string.split('"')[3:-1][0].lower()
				ps2 = ps2.replace(" ", "-")
				print_string = ps1 + ":" + f'"{ps2}",'

			elif len(card.split(" ")) == 5:
				print_string = re.sub('^(.*)', r'"\1": "\1"', card)
				ps1 = print_string.split(':')[0]
				ps2 = print_string.split('"')[3:-1][0].lower()
				ps2 = ps2.replace(" ", "-")
				print_string = ps1 + ":" + f'"{ps2}",'

			j.write(print_string + "\n")