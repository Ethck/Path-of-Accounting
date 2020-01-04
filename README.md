# poeTradeLookup

poeTradeLookup is a (hopeful) poe Trade Macro replacement that utilizes Path of Exile's Official API.

poeTradeLookup supports the following features right now:
* Currency Evaluation
* Unique Item Evaluation

Support is currently being developed for:
* non-Unique item support (including mod evaluations)
* Other leagues (Not just Metamorph SC)

If there is something that you want to see included in poeTradeLookup, leave an issue here in GitHub.

In order to use poeTradeLookup right now follow these steps:

* Install Python 3.7+
* Install the Python requests library (python -m pip install requests)
* Run the parse.py file from the source code (python parse.py)

The program reads what is entered into your clipboard in real time and determines whether or not it is Path of Exile related, if it is not the info is immediately discarded. If it is a PoE item, it then queries the official API to determine pricing based on what everyone else has listed that item for.
