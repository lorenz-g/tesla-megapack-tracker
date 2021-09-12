Table of Contents:
- [tesla-megapack-tracker](#tesla-megapack-tracker)
- [project structure](#project-structure)
- [good information sources](#good-information-sources)
- [inspiration](#inspiration)


# tesla-megapack-tracker

- project tries to track all tesla megapack and powerpack (>5MWh) installations and other big batteries larger than 10MWh
- the site is hosted via github pages and this is the link https://lorenz-g.github.io/tesla-megapack-tracker/

# project structure

for now:
- tesla data is in the [projects-tesla.csv](./projects-tesla.csv) file
- data for all other manufacturers is in [projects-other-man.csv](./projects-other-man.csv)
- the generated website is in the [docs](./docs) folder (it is called docs because of github pages)
- To generate the website, install the dependencies and run `python generate_website.py`
- To develop it is handy to use a tool like [watchexec](https://watchexec.github.io/downloads/) to listen to file changes and then rebuild the site. 
- to edit the CSV files, it is best to use Libre Office

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

- wikipedia (but need to double check their sources also)
  - https://en.wikipedia.org/wiki/Battery_storage_power_station
  - https://en.wikipedia.org/wiki/List_of_energy_storage_power_plants
- tesla news sites
  - https://www.tesmanian.com/
  - https://www.teslarati.com/
- battery / ev news sites:
  - https://www.energy-storage.news/
  - https://cleantechnica.com/
  - https://electrek.co/
- owners websites (they often list their portfolios)
  - https://www.lspower.com/map/
  - https://www.harmonyenergy.co.uk/projects/ 
  - https://recurrentenergy.com/project-portfolio/# 
- authorities websites (often the applications are public)
  - e.g. [goleta planning doc](https://www.cityofgoleta.org/city-hall/planning-and-environmental-review/ceqa-review/cortona-battery-storage-project)
- google 
  - search for the project name and add `approval` and e.g. the county name and often you will find the approval docs which are great to determine the exact location. 
- google maps
  - for old installations you will often be able to spot the installations on the satellite view and can then add precise GPS coordinates. 
- youtube
  - some installations will have drone flyover videos. From there it is also easy to determine exact location. 

# inspiration

There are many other great trackers about various tesla stats, such as:
  - Tesla Carriers tracker https://fmossott.github.io/TeslaCarriersMap/
  - Norway car registration tracker https://elbilstatistikk.no/
  - Model 3 VIN tracker (not active anymore) https://www.model3vins.com/ 
  - Power tracker of big batteries in Australia: http://nemlog.com.au/show/unit/yesterday/?k1=VBBG1,VBBL1 
  
