![Logo](/images/logo.png)

Path of Accounting is a (hopeful) poe Trade Macro replacement that utilizes Path of Exile's Official API.

Path of Accounting supports the following features right now:
* Currency Evaluation
* Unique Item Evaluation
* non-Unique item support (including mod evaluations)

Support is currently being developed for:
* Other leagues (Not just Metamorph SC)
* Better logic on pricing items with many mods.
* In game GUI (a la Trade Macro)
* Global hotkeys (like going to your hideout)

If there is something that you want to see included in Path of Accounting, leave an issue here in GitHub.

In order to use Path of Accounting right now follow these steps:

* Download the `dist` folder to your computer, and simply execute the `parse.exe` file.
* Copy an item you want to price into your clipboard (control c) and watch the output from the script.

The program reads what is entered into your clipboard in real time and determines whether or not it is Path of Exile related, if it is not the info is immediately discarded. If it is a PoE item, it then queries the official API to determine pricing based on what everyone else has listed that item for.

![Sample display](/images/display.png)
