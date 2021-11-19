
- data is public and can be downloaded from here
  - https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract#history
  - there is a csv and an excel version with for easy filtering
  - it has coordinates called x and y - need to check how to integrate that. 

- conversion of x and y coordinates given:
  - https://gridreferencefinder.com/#gr=TL0324326320|503243_s__c__s_226320|1


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