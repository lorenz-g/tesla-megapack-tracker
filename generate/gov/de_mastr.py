


from collections import defaultdict
import os
from typing import Iterable
import xmltodict
import io
import time
import json
import pprint
import datetime as dt
from generate.battery_project import BatteryProject

from generate.utils import GovShortData, check_di_difference


# EinheitenStromSpeicher_1.xml ca 100k entries
# EinheitenStromSpeicher_4.xml is good for testing as it is only 3.5MB



BASE_PATH = "path/to/Gesamtdatenexport_20211104__faea4c0e41fb4ec2b57f7f908b3b569e"
EINHEITEN_PATH = BASE_PATH + "/EinheitenStromSpeicher_{number}.xml"
ANLAGEN_PATH = BASE_PATH + "/AnlagenStromSpeicher_{number}.xml"

technology_dict = {
    "524": "battery",
    "525": "compressed air", # druckluft
    "526": "flywheel", # schwungrad
    "784": "other",
    "1537": "pumped hydro",

}

battery_tech_dict = {
    "727": "li ion",
    "728": "lead",
    "730": "high temperature battery",  # Hochtemperaturbatterie
    "731": "nickel metal hydride",
    "732": "other",

}

# EinheitBetriebsstatus
STATUS_DI = {
    "31": "planning",
    "35": "operation",

}

BUNDESLAND_DI = {
    '1400': "brandenburg",
    # '1401': "",
    '1402': "baden-wuerttemberg",
    '1403': "bavaria",
    '1404': "bremen",
    # '1405': "",
    # '1406': "",
    '1407': "mecklenburg-vorpommern",
    '1408': "lower saxony",
    '1409': "nrw",
    # '1410': "",
    '1411': "schleswig-holstein",
    '1412': "saarland",
    '1413': "saxony",
    # '1414': "",
    '1415': "thuringia",
}


"""
https://www.marktstammdatenregister.de/MaStR/Einheit/Detail/IndexOeffentlich/4234727#speicher

Es gibt 2 nummern, einmal der einheit, und dann noch des speichers
MaStR-Nummer der Einheit:	SEE999869964380

im xml is das die 
('SpeMastrNummer', 'SSE975130777286')
MaStR-Nummer des Stromspeichers:	SSE975130777286

Nutzbare Speicherkapazität:	21.041 kWh	

diese infos sind dann in:
AnlagenStromSpeicher_4.xml

es macht wahrscheinlich mehr sinn durch die stromspeicher zu gehen weil es dort deutlich weniger felder gibt...


# TODO: the coordinates are missing, why is that?
they might be in a different xml file... 
TODO: check that...


# todo: they also have a leistungshistorie
https://www.marktstammdatenregister.de/MaStR/Einheit/Leistungsaenderung/LeistungsaenderungsHistorie/2568940

# TODO: need to get anlagenbetreiber also via the anlagenbetreibernummer


# TODO: lookup the urls
this is the url to rall to resolve the markstammdatennummer to the id of the detail page
https://www.marktstammdatenregister.de/MaStR/Schnellsuche/Schnellsuche?praefix=SEE&mastrNummer=927528071629
{"url":"/MaStR/Einheit/Detail/IndexOeffentlich/3179493"}
https://www.marktstammdatenregister.de/MaStR/Einheit/Detail/IndexOeffentlich/3179493



"""

# those units are mostly too large by a factor of 1000, i.e. a 10kw system is treated as 10mw
units_bad_kw_data = [
    'SEE931343723014', 
    'SEE932138261353', 
    'SEE901022823045',
    'SEE914588158179',
    'SEE930426596439',
    "SEE945645791312"
]


####
# code for website
####

def cast_to_mega(ip):
    return int(float(ip) / 1000)

def format_date(d):
    " 2021-02-15T12:47:02.2298795  to 2016-10-18"
    if not d:
        return ""
    return dt.date.fromisoformat(d.split("T")[0]).isoformat()


def stats_de_mastr_data():
    folder = "misc/de-mastr/filtered/"
    filenames = sorted(os.listdir(folder))
    months = [f.split(".")[0] for f in filenames]
    
    monthly_diffs = []
    last_report = {}
    s_monthly = defaultdict(dict)

    # projects with their history
    projects_di = defaultdict(dict)

    for fn in filenames:
        month = fn.split(".")[0]
        with open(folder + fn) as f:
            # using json files for german 
            rows = json.load(f)
        
        report_di = {}
        monthly_changes = {
            "month": month,
            "new": [],
            "updated": [],
            "disappeared": []
        }

        for r in rows:
            # TODO: use netto or bruttoleisung here, not sure?
            # nettoleistung = min(bruttoleistung, wechselrichterleistung), so I guess nettoleistung is better
            r["mw"] = cast_to_mega(r["Nettonennleistung"])
            r["status"] = STATUS_DI[r["EinheitBetriebsstatus"]]

            if r["status"] not in s_monthly[month]:
                s_monthly[month][r["status"]] = {"count": 0, "gw": 0}
            s_monthly[month][r["status"]]["count"] += 1
            s_monthly[month][r["status"]]["gw"] += int(r["mw"]) / 1000

            ref = r["EinheitMastrNummer"]
            report_di[ref] = r

            if ref in last_report:
                # need to check for changes here
                dif = check_di_difference(
                    last_report[ref], r, 
                    ignore=[]
                )

                if dif:
                    monthly_changes["updated"].append([r, dif])
                    projects_di[ref]["changes"].append({"month": month, "li": dif})

                    # in case the start construction column is not filled, can try to guess it that way
                    in_construction = any([ch["to"] == "construction" for ch in dif])
                    if in_construction:
                        projects_di[ref]["dates"]["start_construction"] = format_date(r["DatumLetzteAktualisierung"])
                    in_operation = any([ch["to"] == "operation" for ch in dif])
                    if in_operation:
                        projects_di[ref]["dates"]["start_operation"] = r["Inbetriebnahmedatum"]

            else:
                # the mastr was only launched end of 2019, so there are some registration dates where the project
                # is already in operation and we don't want to set the date first heard there
                if r["status"]  == "operation" and r["Registrierungsdatum"] > r["Inbetriebnahmedatum"]:
                    first_heard = ""
                else: 
                    first_heard = r["Registrierungsdatum"]

                # new project
                monthly_changes["new"].append(r)
                projects_di[ref] = {
                    "first": r, 
                    "first_month": month,
                    "changes": [],
                    "current": r,
                    "current_month": month,
                    # TODO: the dates don't fully work yet as they are not overwritten by newer entries in case sth changes
                    "dates": {
                        "first_heard": first_heard,
                        "start_construction": "",
                        "start_operation": r.get("Inbetriebnahmedatum", ""),
                        "start_estimated": r.get("GeplantesInbetriebnahmedatum", "")
                    }
                }
            
            projects_di[ref]["current"] = r
            projects_di[ref]["current_month"] = month

        
        # find projects that disappeared
        for ref, r in last_report.items():
            if not (ref in report_di):
                monthly_changes["disappeared"].append(r)

        monthly_changes["new"] = sorted(monthly_changes["new"], key=lambda x:x["mw"], reverse=True)
        monthly_changes["updated"] = sorted(monthly_changes["updated"], key=lambda x:x[0]["mw"], reverse=True)
        monthly_changes["disappeared"] = sorted(monthly_changes["disappeared"], key=lambda x:x["mw"], reverse=True)


        monthly_diffs.append(monthly_changes)
        last_report = report_di

    # todo, maybe for the future it might be good to have a projects short history at then would be the 
    # same across all government sources...
    projects_short = {}
    for k,v in projects_di.items():
        projects_short[k] = gen_short_project(v)
    
    # for k,v in s_monthly.items():
    #     print(k,v)

    summary = {
        "current": s_monthly[months[-1]],
        "current_month": months[-1],
        # want the in descending order
        "monthly_diffs": monthly_diffs[::-1],
        "projects": projects_di,
        # in case there are multiple generator ids, that 
        "projects_short": projects_short
    }

    return summary



def gen_short_project(history_di):
    """ input is the row dict from the csv
    """
    r = history_di["current"]
    dates = history_di["dates"]


    # todo: might not always be correct (adapted from US where not that many dates are given)
    date_first_heard = dates["first_heard"]
    start_construction = dates["start_construction"]
    start_operation = dates["start_operation"]
    start_estimated = dates["start_estimated"]

    
    return GovShortData(
        data_source="de_mastr",
        name=r["NameStromerzeugungseinheit"],
        external_id=r["EinheitMastrNummer"],
        state=BUNDESLAND_DI.get(r["Bundesland"], r["Bundesland"]),
        # Wales, Northern Ireland, England, Scotland (treat it as UK)
        country="germany",
        mwh=r["mwh"],
        estimate_mwh="",
        power_mw=r["mw"],
        owner=r["AnlagenbetreiberMastrNummer"],
        status=r["status"],
        date_first_heard=date_first_heard,
        start_construction=start_construction,
        start_operation=start_operation,
        start_estimated=start_estimated,
        lat=r["Breitengrad"],
        long=r["Laengengrad"],
        # TODO: check if projects are really exact and we can maybe put a 1 here
        coords_hint=1
    )



def match_de_mastr_projects_with_mpt_projects(gov_data, projects: Iterable[BatteryProject]):
    """ print a list of projects that can be copied into the projects.csv file """

    # TODO: can we get rid of the csv here?
    existing_ids = [p.csv.external_id for p in projects if p.country == "germany" and p.csv.external_id != ""]
    max_internal_id = int([p.csv.id for p in projects][-1])

    # list that can be inserted into projects.csv
    start_id = max_internal_id + 1
    print("start id", start_id)
    
    p: GovShortData # thats a great way to give type hints in the code
    for e_id, p in gov_data["projects_short"].items():
        if e_id in existing_ids:
            continue
        li = [
            p.name, "", str(start_id), p.external_id, "1",
            p.state, p.country, str(p.mwh), "",
            str(p.power_mw), "", 
            "", #p.owner (for now that's the number only)
            "", "", "", "", "",
            p.status, 
            p.date_first_heard, p.start_construction,
            p.start_operation, p.start_estimated, 
        ]
        print(";".join(li))
        start_id += 1



#####
# preprocessing code
####

def check_for_large_units(filename):
    # TODO: check if streaming would also be possible...
    # https://stackoverflow.com/questions/65021660/%C3%9F-can-not-be-read-from-xml-file-with-utf-16-encoding-with-python
    # rb is important here
    
    print(filename)
    t = time.time()
    with open(filename, "rb") as f:
        # raw = f.read().decode('utf-16')
        # raw = io.open(filename,'r', encoding='utf-16')
        js = xmltodict.parse(f)

    new_tech = []
    large_units = []
    counter = 0
    print("t - reading done", time.time() - t)
    for unit in js["EinheitenStromSpeicher"]["EinheitStromSpeicher"]:
        counter += 1
        if counter % 2000 == 0:
            print("t - ", counter,  time.time() - t)
        
        if "Technologie" not in unit:
            print("tech not in", unit)
            continue

        if unit["Technologie"] not in technology_dict:
            print("not in", unit)
            continue

        if technology_dict[unit["Technologie"]] != "battery":
            continue
        
        kw = float(unit["Bruttoleistung"])
        mw_brutto = int(kw/1000)

        kw = float(unit["Nettonennleistung"])
        mw_netto = int(kw/1000)
        
        if mw_brutto < 10 or mw_netto < 10:
            continue
        
        if unit["EinheitMastrNummer"] in units_bad_kw_data:
            continue
        
        if "Laengengrad" not in unit:
            print("no coordinates, unit has most likely wrong mw value")

        try:
            to_print = (
                unit["EinheitMastrNummer"], 
                unit["Technologie"], 
                unit["Batterietechnologie"],
                unit["Bruttoleistung"],
                unit["Nettonennleistung"],
                unit["NameStromerzeugungseinheit"], 
            )
        except KeyError:
            print("keyerror", unit)
            continue
        
        print(to_print)
        large_units.append(unit)

        if unit["Batterietechnologie"] not in battery_tech_dict:
            new_tech.append(to_print)
        
    for l in new_tech:
        print("new technologies:")
        print(l)

    return large_units

def check_all():
    large_units = []
    for i in [1,2,3,4]:
        print("\n\nStarting with file %d" % i)
        units = check_for_large_units(EINHEITEN_PATH.format(number=str(i)))
        large_units.extend(units)
    
    with open("large-units.json", "w") as f:
        json.dump(large_units, f)


def get_mwh_from_anlagen(unit_list):
    mast_ids = [i["EinheitMastrNummer"] for i in unit_list]
    id_mwh_dict = {}
    print(mast_ids)
    for i in [1,2,3,4]:
        print("\n\nStarting with file %d" % i)
        with open(ANLAGEN_PATH.format(number=str(i)), "rb") as f:
            js = xmltodict.parse(f)
        for unit in js["AnlagenStromSpeicher"]["AnlageStromSpeicher"]:
            if unit["VerknuepfteEinheitenMaStRNummern"] in mast_ids:
                print(unit["NutzbareSpeicherkapazitaet"])
                if unit["VerknuepfteEinheitenMaStRNummern"] in id_mwh_dict:
                    print(unit["VerknuepfteEinheitenMaStRNummern"], "already in dict")
                id_mwh_dict[unit["VerknuepfteEinheitenMaStRNummern"]] = int(float(unit["NutzbareSpeicherkapazitaet"]) / 1000)

    print(id_mwh_dict)
     

def pprint_units():
    with open("large-units.json") as f:
        js = json.load(f)
        print("SpeMastrNummer")
        print([i["SpeMastrNummer"] for i in js])
        print("number of projects", len(js))
        # pprint.pprint(js)
    return js



def temp():
    # can delete this again, just a way to merge the anlagen and einheiten
    with open("misc/de-mastr/filtered/2021-11.json") as f:
        js = json.load(f)
        print("SpeMastrNummer")
        print([i["SpeMastrNummer"] for i in js])
        print("number of projects", len(js))
        # pprint.pprint(js)

    with open("misc/de-mastr/filtered/mwh.json") as f:
        mwh = json.load(f)
    
    for i in js:
        i["mwh"] = mwh[i["EinheitMastrNummer"]]


    with open("misc/de-mastr/filtered/2021-11.json", "w") as f:
        # todo: keep the indent for better readability
        json.dump(js, f, indent=2)










if __name__ == "__main__":

    # preprocessing to get the files that can be checked into git:
    # check_all()
    # li = pprint_units()
    # get_mwh_from_anlagen(li)
    temp()
    