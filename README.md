![Logo](/images/logo.png)

Path of Accounting is a replacement of POE TradeMacro that utilizes Path of Exile's Official API. Built from the ground up, Path of Accounting is lightning fast and has support for just about every item in the game.

Path of Accounting supports the following features right now:
* Currency Evaluation
* Unique Item Evaluation
* non-Unique item support (including mod evaluations)
* In game GUI (still developing, taking suggestions)
* Global Hotkeys! (hideout, other copy, still working on more!)

Support is currently being developed for:
* Other leagues (Not just Metamorph SC)
* Better logic on pricing items with many mods.
* More global hotkeys!
* Settings module
* Better GUI
* More mod support
* and More!


If there is something that you want to see included in Path of Accounting, leave an issue here in GitHub.

In order to use Path of Accounting right now follow these steps:

For WINDOWS:
* Head over to the [releases](https://github.com/Ethck/Path-of-Accounting/releases) page, download the newest release, unzip, and execute the `parse.exe` file found inside the parse folder..

For *NIX:
* Clone the repo, use the poetry.lock file (`poetry install`) to install dependencies, then run parse.py

For Everyone!
* Copy an item you want to price into your clipboard (control+c or alt+d) and watch the output from the script and the GUI popup!

The program reads what is entered into your clipboard in real time and determines whether or not it is Path of Exile related, if it is not the info is immediately discarded. If it is a PoE item, it then queries the official API to determine pricing based on what everyone else has listed that item for.

![Sample display](/images/display.png)
![Sample GUI](/images/sampleGui.png)

For anyone interested in helping, Path of Accounting is built with Python 3.6+ and is super easy to understand. Feel free to message me if you have any questions.
For those of you who want to help but don't know how to program, feel free to offer suggestions on the issues page! I can't make this tool better without knowing what everyone want.
