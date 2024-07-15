
# blog

- the link table of contents don't work
- non formatted links don't show up

- breadcrumbs for the page
- second indentation with only two indents does not work

- https://github.com/trentm/python-markdown2
  - maybe using the markdown2 over the markdown package fixes a lot
  - https://github.com/Python-Markdown/markdown


# general

- [ ] add a check for generated single html pages that were deleted from the csv (so that they can be deleted from the filesystem)
- [ ] add a proper footer in the base template



# integration of government data

Priority:
- handle projects that disappear
  - e.g. http://localhost:2222/tesla-megapack-tracker/projects/780.html
- make a summary for every government import that can easily be share on twitter



Rest:
- column to overwrite government data
- log when stuff is overwritten (ideally as json and human readable)
- can be shown on the website. (separate between user overwrites and governmnet data overwrites)
- based on the id, have distance to the coordinate for all projects that I cannot located
- for the second integration maybe have a class with some helper methods

- make a project class
  - ui rendering functions
  - history
  - government data etc
  - maybe can p


- think about how to be able to add a comment to certain changes
  - i guess having a yaml, automatically creating it and then being able to add a comment
  - however the triggering of the history script should only run whenever sth is committed, no?


- maybe add some accordions on the detail page to quickly show some info...
- if the overwrite is turned on, need to define the overwrite fields

- should automatically add a field since when the project is tracked. 

- maybe could treat the manual research just as another data sourece
  
- better table on mobile...

- how to deal with projects like the edwards sanborn? (could also just leave them as is...)
  - many small projects in the eia data
  - but the media refers to it as one big one
  - could add a `group with` column in the CSV and then those projects will be shown as one?
  - could still generate the detail page for all (but then say thats not the main page)
  - in terms of overall status and dates always use the last ones
  - figure out how many are affected
  - use the gps coords of the main project
  - either put `self` or the id in the main project `group with` column to see

- run a check to see if some coords are too close to each other or not


- for eia hybrid projects, they solar system has the same plant id ad the battery
  - e.g. sof the townsite solar project in the 2022-02 table 6_03 it says the PV has 160 MW

- when adding projects from governments
  - could just add a government name column and only add that, the external id and the id. 
  - then have to think about how to label where the data comes from...
  - could just use the emojis again






# DONE

- add changelog blog and refer to it from the readme
- fix bug for eia data that where old projects in operation disappear from the summary