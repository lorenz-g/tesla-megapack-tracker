Table of Contents:
- [tesla-megapack-tracker](#tesla-megapack-tracker)
- [want to contribute?](#want-to-contribute)
- [project structure](#project-structure)
- [for profit usage](#for-profit-usage)
- [inspiration](#inspiration)

# tesla-megapack-tracker

- project tries to track all tesla megapack (>10MWh) installations and other big batteries where government data sources are available (>10MWh or 10MW)
- the site is hosted via github pages and this is the link:
  - 🟢 👉 https://lorenz-g.github.io/tesla-megapack-tracker/ 👈 🟢

![map of image](./docs/pics/og-image.jpg)

# want to contribute?

- battery projects
  - just add or update them in the `projects.csv` file and submit a PR (Pull Request) on Github
  - Using LibreOffice to edit the csv file is recommended

# project structure

for now:
- raw data (tesla and other manufacturers) are in [projects.csv](./projects.csv) file
- the generated website is in the [docs](./docs) folder (it is called docs because of github pages)
- To generate the website, install the dependencies with `pip install -r requirements.txt` and run `python generate/website.py`. It is recommended to setup a python virtualenv for the project beforehand (can use `pip install pip-tools` and `pip-compile requirements.in` to create an up to date version of requirements)
  - all python code lives in the `generate` folder
- some handy commands are in the [./Makefile](./Makefile)
- to edit the CSV files, it is best to use Libre Office
- the external government data is the `misc` folder

for the cars vs stationary:
- raw data is in the [cars-vs-stationary.csv](./cars-vs-stationary.csv) file
- using the vehicle production numbers (from the tesla quarterly press releases)
- estimating the avg model 3/y battery with 60kWh and the model s/x with 90kwh
  - in the future could also add a new column use a more precise estimate per quarter, but fine for now.


# for profit usage

- if you are a corporate and can use some the data here please do. You can also sell it on (but please respect the MIT license to give credit where it's due)
- and if you have used it, please consider contributing some info/insights back to the project via pull requests. Thanks 👏


# inspiration

There are many other great trackers about various tesla stats, such as:
  - Tesla Carriers tracker https://fmossott.github.io/TeslaCarriersMap/
  - Norway car registration tracker https://elbilstatistikk.no/
  - Model 3 VIN tracker (not active anymore) https://www.model3vins.com/ 
  - Power tracker of big batteries in Australia: http://nemlog.com.au/show/unit/yesterday/?k1=VBBG1,VBBL1 
  - EU EVs tracker https://eu-evs.com/ 
  - https://map.evuniverse.io/#mapstart map of EV the ev industry

