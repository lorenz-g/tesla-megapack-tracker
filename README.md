Table of Contents:
- [tesla-megapack-tracker](#tesla-megapack-tracker)
- [project structure](#project-structure)
- [good information sources](#good-information-sources)
- [for profit usage](#for-profit-usage)
- [want to contribute?](#want-to-contribute)
- [inspiration](#inspiration)

# tesla-megapack-tracker

- project tries to track all tesla megapack and powerpack (>5MWh) installations and other big batteries larger than 10MWh or 10MW
- the site is hosted via github pages and this is the link:
  - 🟢 👉 https://lorenz-g.github.io/tesla-megapack-tracker/ 👈 🟢

![map of image](./docs/pics/og-image.jpg)

# project structure

for now:
- raw data (tesla and other manufacturers) are in [projects.csv](./projects.csv) file
- the generated website is in the [docs](./docs) folder (it is called docs because of github pages)
- To generate the website, install the dependencies with `pip install -r requirements.txt` and run `python generate/website.py`. It is recommended to setup a python virtualenv for the project beforehand. 
  - all python code lives in the `generate` folder
- To develop it is handy to use a tool like [watchexec](https://watchexec.github.io/downloads/) to listen to file changes and then rebuild the site. 
- to edit the CSV files, it is best to use Libre Office
- the external government data is the `misc` folder
- the blog entries are written in Markdown and in the `misc`

eventually:
- every battery installation has a toml file located in the `battery-projects`
- in case there are multiple stages to a project, they will be in that file
- the naming of the toml file is `date_id_project-name`, e.g. `2020-01-01_4_first-megapack-project`

for the cars vs stationary:
- raw data is in the [cars-vs-stationary.csv](./cars-vs-stationary.csv) file
- using the vehicle production numbers (from the tesla quarterly press releases)
- estimating the avg model 3/y battery with 60kWh and the model s/x with 90kwh
  - in the future could also add a new column use a more precise estimate per quarter, but fine for now.

# good information sources

This has grown, so you can find it here now: [Big Battery Info Sources](./misc/2021-11-19-big-battery-info-sources.md)

# for profit usage

- if you are a corporate and can use some the data here please do. You can also sell it on (but please respect the MIT license to give credit where it's due)
- and if you have used it, please consider contributing some info/insights back to the project via pull requests. Thanks 👏

# want to contribute?

- battery projects
  - just add them to the `projects.csv` file and submit a PR (Pull Request)
- feature / website improvements
  - there is a [TODO](./misc/TODO.md) file. You can just grab sth there. 
- new government integration
  - they are the best to keep data up to date. Feel free to add one. 
- blog post
  - just write / amend one and submit a PR. 

# inspiration

There are many other great trackers about various tesla stats, such as:
  - Tesla Carriers tracker https://fmossott.github.io/TeslaCarriersMap/
  - Norway car registration tracker https://elbilstatistikk.no/
  - Model 3 VIN tracker (not active anymore) https://www.model3vins.com/ 
  - Power tracker of big batteries in Australia: http://nemlog.com.au/show/unit/yesterday/?k1=VBBG1,VBBL1 
  - EU EVs tracker https://eu-evs.com/ 
  - https://map.evuniverse.io/#mapstart map of EV the ev industry 
