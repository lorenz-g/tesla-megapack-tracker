# tesla-megapack-tracker
Project tries to track all tesla megapack and powerpack (>5MWh) installations




# project structure

for now:
- all data is in the project.csv file

eventually:
- every battery installation has a toml file located in the [battery-projects](./battery-projects)
- in case there are multiple stages to a project, the will be in that file
- the naming of the toml file is `date_id_project-name`, e.g. `2020-01-01_4_first-megapack-project`
- the generated website is in the [docs](./docs) folder


# inspiration

- there are many other great trackers about various tesla stats, such as:
- 