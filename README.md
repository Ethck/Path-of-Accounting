# (Abandoned) Path of Accounting [![Travis](https://img.shields.io/travis/Ethck/Path-of-Accounting.svg)](https://travis-ci.org/Ethck/Path-of-Accounting)
This project has been abandoned in favor of the several other utilities that do the same thing and a shift in Dev priorites.
## Intro

Path of Accounting is a replacement of POE TradeMacro that utilizes Path of Exile's Official API. Built from the ground up, Path of Accounting is lightning fast and has support for just about every item in the game.

Path of Accounting supports the following features:
* poeprices.info Machine-Learning algorithm for pricing Rares!
* poeninja cached info for quick results!
* Global Hotkeys! (hideout, ctrl+scroll, simple search, advanced search, and MORE!)

If there is something that you want to see included in Path of Accounting, leave an issue here in GitHub.

## Download(s)

For WINDOWS:
* Head over to the [releases](https://github.com/Ethck/Path-of-Accounting/releases) page, download the newest release, unzip, and execute the `Accounting.exe` file found inside the unzipped folder..
* If that doesn't work, install python and follow the below instructions:

For \*NIX:
* Ensure that your python version is 3.7 or above.
* Download pip with "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py"
* Run "sudo python3 get-pip.py"
* Run "sudo python3 pip install -r requirements.txt"
* Run "sudo Accounting.py"


For Everyone!
* Copy an item you want to price into your clipboard (control+c or alt+d) and watch the output from the script and the GUI popup!

In order to change settings (like `league`and/or `gui`) go to where PoA is downloaded and open up the `settings.cfg` file.

The program reads what is entered into your clipboard in real time and determines whether or not it is Path of Exile related, if it is not the info is immediately discarded. If it is a PoE item, it then queries the official API to determine pricing based on what everyone else has listed that item for.

*NOTICE* Since the beginning of the Delirium League, the official API has slowly become much slower. Please note that this is not because of Path of Accounting when you are searching, but rather because the API is really slow due to lots of use.
## Pictures

Sample searches:

![Basic Search 1](/images/sampleSearch1.png)

![Basic Search 2](/images/sampleSearch2.png)


Base Search

![Base Search](/images/baseSearch.png)


Advanced Search

![Advanced Search](/images/advancedSearch.png)

## Hotkeys

Can be changed in settings.cfg

|Hotkey   | Description  |
|---|---|
| alt+d  | Search for item.  |
|  F5 | Go to hideout  |
| alt+t | Open item in trade site |
| alt+w | Open item in wiki |
| alt+c | Base price check |
| alt+f | Weapon stat check |
| alt+v | Advanced price check |

Windows Only:

|Hotkey   | Description  |
|---|---|
| ctrl+MouseWheel  | Scroll stash tabs without having to hover over it.  |

## Contributing

For anyone interested in helping, Path of Accounting is built with Python 3.6+ and is super easy to understand. Feel free to message me if you have any questions.
For those of you who want to help but don't know how to program, feel free to offer suggestions on the issues page! I can't make this tool better without knowing what everyone want.
