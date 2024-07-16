
- data is public and can be downloaded from here
  - https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract#history
  - there is a csv and an excel version with for easy filtering
  - it has coordinates called x and y - need to check how to integrate that. 

TODO: one can also download historic versions from here:
https://data.gov.uk/dataset/a5b0ed13-c960-49ce-b1f6-3a6bbe0db1b7/renewable-energy-planning-database-repd


- conversion of x and y coordinates given:
  - https://gridreferencefinder.com/#gr=TL0324326320|503243_s__c__s_226320|1
  - This is the library used http://www.nearby.org.uk/tests/GeoTools2.html

```javascript
osgb=new GT_OSGB();
Object { northings: 0, eastings: 0, status: "Undefined" }
osgb.setGridCoordinates(157517, 543117);
undefined
osgb.getWGS84()
Object { latitude: 54.72440697094995, longitude: -5.767212016423667 }

```

https://github.com/thruston/grid-banger
In the end, can use this one here:
https://github.com/fmalina/blocl-bnglatlon/blob/main/bng_latlon/bng_to_latlon.py


```

# projects >0MW:  395
mw projects >0MW:  13296

quite a lot of projects over 10MW
# projects >10MW:  282
mw projects >10MW:  12660

but very few over 100MW
# projects >10MW:  7
mw projects >10MW:  1699

vast majority in planning
'cancelled': {'cnt': 47, 'mw': 1599},
'construction': {'cnt': 21, 'mw': 739},
'operation': {'cnt': 25, 'mw': 640},
'planning': {'cnt': 219, 'mw': 9982}


```

- renewable-energy-planning-database-q3-september-2021.xlsx
  - filtering for battery technology
  - 


- got a `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa0 in position 5473: invalid start byte`
  - fixed it by opening and saving the file as csv with libreoffice


- got a `ValueError: time data '44317' does not match format '%d/%m/%Y'`
  - Lister Drive 7740 went into the csv and deleted that value, it is wrong, should check why it ends up there in the first place. But it is the only wrong value. There were two more for the 2024-april version


# column names

```
It has quite a few columns
Site Name
Technology Type
Storage Type
Storage Co-location REPD Ref ID
Installed Capacity (MWelec)
CHP Enabled
RO Banding (ROC/MWh)
FiT Tariff (p/kWh)
CfD Capacity (MW)
Turbine Capacity (MW)
No. of Turbines
Height of Turbines (m)
Mounting Type for Solar
Development Status
Development Status (short)
Address
County
Region
Country
Post Code
X-coordinate
Y-coordinate
Planning Authority
Planning Application Reference
Appeal Reference
Secretary of State Reference
Type of Secretary of State Intervention
Judicial Review
Offshore Wind Round
Planning Application Submitted
Planning Application Withdrawn
Planning Permission Refused
Appeal Lodged
Appeal Withdrawn
Appeal Refused
Appeal Granted
Planning Permission Granted
Secretary of State - Intervened
Secretary of State - Refusal
Secretary of State - Granted
Planning Permission Expired
Under Construction
Operational
Heat Network Ref
```