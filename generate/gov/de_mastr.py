from audioop import avg
from collections import defaultdict
import csv
import os
from typing import Iterable
import xmltodict
import io
import time
import json
import pprint
import datetime as dt

import requests

from generate.battery_project import BatteryProject
from generate.utils import (
    GovShortData,
    check_di_difference,
    create_summary_for_gov_projects,
)


# EinheitenStromSpeicher_1.xml ca 100k entries


# EinheitenStromSpeicher_{number}.xml
EINHEITEN_PREFIX = "EinheitenStromSpeicher_"
# AnlagenStromSpeicher_{number}.xml
ANLAGEN_PREFIX = "AnlagenStromSpeicher_"
# Marktakteure_{number}.xml
MARKTAKTEURE_PREFIX = "Marktakteure_"

BASE_DETAIL_URL = (
    "https://www.marktstammdatenregister.de/MaStR/Einheit/Detail/IndexOeffentlich/"
)

technology_dict = {
    "524": "battery",
    "525": "compressed air",  # druckluft
    "526": "flywheel",  # schwungrad
    "784": "other",
    "1537": "pumped hydro",
}

battery_tech_dict = {
    "727": "li ion",
    "728": "lead",
    "729": "redox flow",
    "730": "high temperature battery",  # Hochtemperaturbatterie
    "731": "nickel metal hydride",
    "732": "other",
}

MANUFACTURER_DICT = {
    "sonnen": "sonnen",
    "byd": "byd",
    "e3": "e3dc",
    # "e3dc": "e3dc",
    "senec": "senec",
    "tesla": "tesla",
    "powerwall": "tesla",
    "lg": "lg",
    "varta": "varta",
    "jes-": "jes.ag",  # they are an installer and put their reference numbers as the name
}

MANUFACTURER_KEYWORDS = MANUFACTURER_DICT.keys()

# EinheitBetriebsstatus
STATUS_DI = {
    "31": "planning",
    "35": "operation",
}

BUNDESLAND_DI = {
    "1400": "brandenburg",
    # '1401': "",
    "1402": "baden-wuerttemberg",
    "1403": "bavaria",
    "1404": "bremen",
    # '1405': "",
    # '1406': "",
    "1407": "mecklenburg-vorpommern",
    "1408": "lower saxony",
    "1409": "nrw",
    # '1410': "",
    "1411": "schleswig-holstein",
    "1412": "saarland",
    "1413": "saxony",
    "1414": "saxony-anhalt",
    "1415": "thuringia",
}

# mapping to go to the details url (to prevent calling the website that often which slows things down)
# move to file if it becomes too big
MASTR_DETAIL_IDS_DI = {
    "SEE927528071629": 3179493,
    "SEE953605889740": 2568940,
    "SEE900291433160": 2377745,
    "SEE905490507995": 2607685,
    "SEE905843309764": 4667064,
    "SEE905930139120": 2725831,
    "SEE908096553144": 3430593,
    "SEE910324388312": 4139056,
    "SEE913862454280": 2023224,
    "SEE919443669678": 3429839,
    "SEE931375347240": 3059314,
    "SEE933095868289": 4273037,
    "SEE935506652999": 2940061,
    "SEE937857006797": 3371345,
    "SEE940316838242": 3638550,
    "SEE941708872783": 3395953,
    "SEE946919525862": 4680516,
    "SEE963081865633": 2562804,
    "SEE964940893804": 3430514,
    "SEE966091400436": 2607339,
    "SEE971138728251": 3430427,
    "SEE971932533266": 4667306,
    "SEE976362409624": 2562905,
    "SEE976927444749": 2667151,
    "SEE984446277410": 3370616,
    "SEE990521990150": 3430313,
    "SEE999790559914": 3984077,
    "SEE977720016904": 4750172,
    "SEE982806373970": 5001456,
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
    "SEE931343723014",
    "SEE932138261353",
    "SEE901022823045",
    "SEE914588158179",
    "SEE930426596439",
    "SEE945645791312",
    "SEE949104628768",  # gasthof lang
]


####
# code for website
####


def cast_to_mega(ip):
    return int(float(ip) / 1000)


def format_date(d):
    "2021-02-15T12:47:02.2298795  to 2016-10-18"
    if not d:
        return ""
    return dt.date.fromisoformat(d.split("T")[0]).isoformat()


def stats_de_mastr_data():
    folder = "misc/de-mastr/filtered/"
    filenames = sorted(os.listdir(folder))
    months = [f.split(".")[0] for f in filenames]

    monthly_diffs = []
    last_report = {}

    # projects with their history
    projects_di = defaultdict(dict)

    for fn in filenames:
        month = fn.split(".")[0]
        with open(folder + fn) as f:
            # using json files for german
            rows = json.load(f)

        report_di = {}
        monthly_changes = {"month": month, "new": [], "updated": [], "disappeared": []}

        for r in rows:
            # every gov project should have a ext_id and status
            r["ext_id"] = r["EinheitMastrNummer"]
            # status is already present.

            # TODO: use netto or bruttoleisung here, not sure?
            # nettoleistung = min(bruttoleistung, wechselrichterleistung), so I guess nettoleistung is better
            r["mw"] = cast_to_mega(r["Nettonennleistung"])
            r["status"] = STATUS_DI[r["EinheitBetriebsstatus"]]

            ref = r["EinheitMastrNummer"]
            report_di[ref] = r

            if ref in last_report:
                # need to check for changes here
                dif = check_di_difference(last_report[ref], r, ignore=[])

                if dif:
                    monthly_changes["updated"].append([r, dif])
                    projects_di[ref]["changes"].append({"month": month, "li": dif})

                    # in case the start construction column is not filled, can try to guess it that way
                    in_construction = any([ch["to"] == "construction" for ch in dif])
                    if in_construction:
                        projects_di[ref]["dates"]["start_construction"] = format_date(
                            r["DatumLetzteAktualisierung"]
                        )
                    in_operation = any([ch["to"] == "operation" for ch in dif])
                    if in_operation:
                        projects_di[ref]["dates"]["start_operation"] = r[
                            "Inbetriebnahmedatum"
                        ]

            else:
                # the mastr was only launched end of 2019, so there are some registration dates where the project
                # is already in operation and we don't want to set the date first heard there
                if (
                    r["status"] == "operation"
                    and r["Registrierungsdatum"] > r["Inbetriebnahmedatum"]
                ):
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
                        "start_estimated": r.get("GeplantesInbetriebnahmedatum", ""),
                    },
                }

            projects_di[ref]["current"] = r
            projects_di[ref]["current_month"] = month

        # find projects that disappeared
        for ref, r in last_report.items():
            if not (ref in report_di):
                monthly_changes["disappeared"].append(r)

        monthly_changes["new"] = sorted(
            monthly_changes["new"], key=lambda x: x["mw"], reverse=True
        )
        monthly_changes["updated"] = sorted(
            monthly_changes["updated"], key=lambda x: x[0]["mw"], reverse=True
        )
        monthly_changes["disappeared"] = sorted(
            monthly_changes["disappeared"], key=lambda x: x["mw"], reverse=True
        )

        monthly_diffs.append(monthly_changes)
        last_report = report_di

    # todo, maybe for the future it might be good to have a projects short history at then would be the
    # same across all government sources...
    projects_short = {}
    for k, v in projects_di.items():
        projects_short[k] = gen_short_project(v)

    summary = {
        "current": create_summary_for_gov_projects(projects_short.values()),
        "current_month": months[-1],
        # want the in descending order
        "monthly_diffs": monthly_diffs[::-1],
        "projects": projects_di,
        # in case there are multiple generator ids, that
        "projects_short": projects_short,
    }

    return summary


def gen_short_project(history_di):
    """input is the row dict from the csv"""
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
        owner=r["owner"],
        status=r["status"],
        date_first_heard=date_first_heard,
        start_construction=start_construction,
        start_operation=start_operation,
        start_estimated=start_estimated,
        lat=r["Breitengrad"],
        long=r["Laengengrad"],
        # TODO: check if projects are really exact and we can maybe put a 1 here
        coords_hint=1,
        pr_url=BASE_DETAIL_URL + str(r["pr_url_id"]),
    )


def match_de_mastr_projects_with_mpt_projects(
    gov_data, projects: Iterable[BatteryProject]
):
    """print a list of projects that can be copied into the projects.csv file"""

    # TODO: can we get rid of the csv here?
    existing_ids = [
        p.csv.external_id
        for p in projects
        if p.country == "germany" and p.csv.external_id != ""
    ]

    # max internal id plus 1
    start_id = int([p.csv.id for p in projects][-1]) + 1

    p: GovShortData  # thats a great way to give type hints in the code
    for e_id, p in gov_data["projects_short"].items():
        if e_id in existing_ids:
            continue
        li = [
            p.name,
            "",
            str(start_id),
            p.external_id,
            "1",
            p.state,
            p.country,
            str(p.mwh),
            "",
            str(p.power_mw),
            "",
            "",  # p.owner (for now that's the number only)
            "",
            "",
            "",
            "",
            "",
            p.status,
            p.date_first_heard,
            p.start_construction,
            p.start_operation,
            p.start_estimated,
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
            # print("t - ", counter,  time.time() - t)
            pass

        if "Technologie" not in unit:
            print("tech not in", unit)
            continue

        if unit["Technologie"] not in technology_dict:
            print("not in", unit)
            continue

        if technology_dict[unit["Technologie"]] != "battery":
            continue

        kw = float(unit["Bruttoleistung"])
        mw_brutto = int(kw / 1000)

        kw = float(unit["Nettonennleistung"])
        mw_netto = int(kw / 1000)

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

        # prepare the data a bit here already
        unit["pr_url_id"] = convert_to_details_url_id(unit["EinheitMastrNummer"])

        print(to_print)
        large_units.append(unit)

        if unit["Batterietechnologie"] not in battery_tech_dict:
            new_tech.append(to_print)

    for l in new_tech:
        print("new technologies:")
        print(l)

    return large_units


def guess_manufacturer_from_name(name):
    for keyword in MANUFACTURER_KEYWORDS:
        if keyword in name:
            return MANUFACTURER_DICT[keyword]
    return ""


def date_to_quarter(input):
    if input == "":
        return ""
    # e.g. 2022-02-01
    split = input.split("-")
    return "%s-Q%d" % (split[0], int(int(split[1]) / 4) + 1)


def check_for_small_units(filename):
    t = time.time()
    with open(filename, "rb") as f:
        js = xmltodict.parse(f)

    small_units = []
    counter = 0
    print("t - reading done", time.time() - t)
    for unit in js["EinheitenStromSpeicher"]["EinheitStromSpeicher"]:
        counter += 1

        if "Technologie" not in unit:
            print("tech not in", unit)
            continue

        if unit["Technologie"] not in technology_dict:
            print("not in", unit)
            continue

        if technology_dict[unit["Technologie"]] != "battery":
            continue

        kw = float(unit["Bruttoleistung"])
        kw_brutto = int(kw)

        kw = float(unit["Nettonennleistung"])
        kw_netto = int(kw)

        # filter out the large units
        if kw_brutto > 10000 or kw_netto > 10000:
            continue

        try:
            to_print = (
                unit.get("Inbetriebnahmedatum"),
                unit.get("GeplantesInbetriebnahmedatum"),
                unit["Postleitzahl"],
                unit["EinheitMastrNummer"],
                unit["Technologie"],
                unit.get("Batterietechnologie"),
                unit["Bruttoleistung"],
                unit["Nettonennleistung"],
                unit["NameStromerzeugungseinheit"],
            )
        except KeyError as exc:
            print(exc)
            print("keyerror", unit)
            continue

        # prepare the data a bit here already
        # unit["pr_url_id"] = convert_to_details_url_id(unit["EinheitMastrNummer"])

        # print(to_print)

        # creating a shorter unit with the infos needed
        if "Inbetriebnahmedatum" in unit:
            start_date = unit["Inbetriebnahmedatum"]
            planned = "0"
        elif "GeplantesInbetriebnahmedatum" in unit:
            start_date = unit["GeplantesInbetriebnahmedatum"]
            planned = "1"
        else:
            print("no date for unit", unit)
            start_date = ""
            planned = ""

        unit_short = {
            "id": unit["EinheitMastrNummer"],
            "start_date": date_to_quarter(start_date),
            "planned": planned,
            "kw": kw_netto,
            "plz": unit["Postleitzahl"],
            "manufacturer": guess_manufacturer_from_name(
                unit["NameStromerzeugungseinheit"]
            ),
            "name": unit["NameStromerzeugungseinheit"],
        }

        small_units.append(unit_short)

    return small_units


def get_files_with_prefix(folder, prefix):
    res = []
    for f in os.listdir(folder):
        if f.startswith(prefix):
            res.append(os.path.join(folder, f))
    print("found %d for prefix %s" % (len(res), prefix))
    return sorted(res)


def create_csv_for_small_units(base_path, month):
    """
    execute this function to if you have a new dataset download

    month is the output filename, use the month when you downloaded the dataset. e.g. 2021-10
    """
    # this step takes a lot of time
    small_units = []
    for filename in get_files_with_prefix(base_path, EINHEITEN_PREFIX):
        print("Starting with file", filename)
        small_units.extend(check_for_small_units(filename))

    mastr_ids = [i["id"] for i in small_units]

    # owners don't work, but would be good to get DNOs
    # owner_ids = [i["AnlagenbetreiberMastrNummer"] for i in small_units]
    # owner_di = get_owner_from_marktakeure(base_path, owner_ids)
    # can use this as a backup

    # get the kwh values
    kwh_di = get_kwh_from_anlagen(base_path, mastr_ids)
    count = 0
    for unit in small_units:
        if unit["id"] in kwh_di:
            unit["kwh"] = kwh_di[unit["id"]]
        else:
            unit["kwh"] = 0
            count += 1
    print("could not find kwh values for %d units" % count)

    out_file = "misc/de-mastr/small-batteries/%s.csv" % month
    if False and os.path.exists(out_file):
        print("file already exists, not overwritting it", out_file)
    else:
        with open(out_file, "w") as f:
            fieldnames = [
                "id",
                "plz",
                "start_date",
                "planned",
                "kw",
                "kwh",
                "manufacturer",
                "name",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in small_units:
                writer.writerow(row)

    print("Total units: ", len(small_units))


def create_summary_from_small_units_csv(csv_path, month):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append(r)

    print(rows[0])
    # sample row:
    # {'id': 'SEE900000066023', 'plz': '12169', 'start_date': '2019-Q2', 'planned': '0', 'kw': '3', 'kwh': '12', 'manufacturer': '', 'name': 'Sonnen-eco8-12.5'}

    s = defaultdict(
        lambda: {
            "small": {"kw": [], "kwh": []},
            "medium": {"kw": [], "kwh": []},
            "large": {"kw": [], "kwh": []},
        }
    )
    for r in rows:
        kw = int(r["kw"])
        kwh = int(r["kwh"])

        # use definitions from this paper:
        # The development of battery storage systems in Germany – A market review (status 2022)
        # <= 30kwh HSS - home storage system
        # between 30 and 1000 kwh ISS - industrial storage system
        # larger 1000 kwh large storage
        if kwh < 30:
            category = "small"
        elif kwh < 1000:
            category = "medium"
        else:
            category = "large"

        s[r["start_date"]][category]["kwh"].append(kwh)
        s[r["start_date"]][category]["kw"].append(kw)

    print(len(s))
    # print(sorted(s.keys()))

    s_short = defaultdict(
        lambda: {
            "small": {"kw": [], "kwh": []},
            "medium": {"kw": [], "kwh": []},
            "large": {"kw": [], "kwh": []},
        }
    )
    for quarter, v in s.items():
        for category in ["small", "medium", "large"]:
            s_short[quarter][category] = {}
            for metric in ["kw", "kwh"]:
                sum_metric = sum(v[category][metric])
                count_metric = len(v[category][metric])
                if count_metric > 0:
                    avg_metric = sum_metric / count_metric
                else:
                    avg_metric = 0

                s_short[quarter][category].update(
                    {
                        metric + "_sum": sum_metric,
                        "count": count_metric,
                        metric + "_avg": avg_metric,
                    }
                )

    # pprint.pprint(s_short)

    out_filename = csv_path.replace(".csv", "-hss-summary.csv")
    print("writing summary to ", out_filename)
    with open(out_filename, "w") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["quarter", "category", "count", "mwh_sum", "kwh_avg", "mw_sum", "kw_avg"]
        )
        for quarter in sorted(s_short.keys()):
            if quarter > "2017" and quarter < "2024":
                # ["small", "medium", "large"]
                for category in ["small"]:
                    d = s_short[quarter][category]
                    li = [
                        quarter,
                        category,
                        str(d["count"]),
                        "%d" % (d["kwh_sum"] / 1000),
                        "%.1f" % d["kwh_avg"],
                        "%d" % (d["kw_sum"] / 1000),
                        "%.1f" % d["kw_avg"],
                    ]
                    writer.writerow(li)


def get_capacity_from_anlagen(base_path, mastr_ids, rtype="mwh"):
    # needed for faster lookup
    mastr_ids_dict = {m: 1 for m in mastr_ids}

    id_mwh_dict = {}
    for filename in get_files_with_prefix(base_path, ANLAGEN_PREFIX):
        print("Starting with file", filename)
        count = 0
        with open(filename, "rb") as f:
            js = xmltodict.parse(f)
        for unit in js["AnlagenStromSpeicher"]["AnlageStromSpeicher"]:
            if unit["VerknuepfteEinheitenMaStRNummern"] in mastr_ids_dict:
                # print(unit["NutzbareSpeicherkapazitaet"])
                if unit["VerknuepfteEinheitenMaStRNummern"] in id_mwh_dict:
                    print(unit["VerknuepfteEinheitenMaStRNummern"], "already in dict")
                count += 1
                if "NutzbareSpeicherkapazitaet" not in unit:
                    print(
                        "NutzbareSpeicherkapazitaet not in unit for ",
                        unit["VerknuepfteEinheitenMaStRNummern"],
                    )
                else:
                    capacity = int(float(unit["NutzbareSpeicherkapazitaet"]))
                if rtype == "mwh":
                    capacity = int(capacity / 1000)
                id_mwh_dict[unit["VerknuepfteEinheitenMaStRNummern"]] = capacity
        print("found capacity for %d units" % count)
    return id_mwh_dict


def get_mwh_from_anlagen(base_path, mastr_ids):
    return get_capacity_from_anlagen(base_path, mastr_ids, rtype="mwh")


def get_kwh_from_anlagen(base_path, mastr_ids):
    return get_capacity_from_anlagen(base_path, mastr_ids, rtype="kwh")


def get_owner_from_marktakeure(base_path, owner_ids):
    id_owner_dict = {}

    for filename in get_files_with_prefix(base_path, MARKTAKTEURE_PREFIX):
        print("Starting with file", filename)
        with open(filename, "rb") as f:
            js = xmltodict.parse(f)
        for unit in js["Marktakteure"]["Marktakteur"]:
            if unit["MastrNummer"] in owner_ids:
                if "Firmenname" not in unit:
                    print("firmenname gibt es nicht", unit)
                    name = ""
                else:
                    name = unit["Firmenname"]
                    print(unit["Firmenname"])
                id_owner_dict[unit["MastrNummer"]] = name

    return id_owner_dict


def convert_to_details_url_id(mastr_nr):
    """
    https://www.marktstammdatenregister.de/MaStR/Schnellsuche/Schnellsuche?praefix=SEE&mastrNummer=927528071629
    {"url":"/MaStR/Einheit/Detail/IndexOeffentlich/3179493"}
    https://www.marktstammdatenregister.de/MaStR/Einheit/Detail/IndexOeffentlich/3179493
    """
    if mastr_nr in MASTR_DETAIL_IDS_DI:
        id_ = MASTR_DETAIL_IDS_DI[mastr_nr]
    else:
        url = (
            "https://www.marktstammdatenregister.de/MaStR/Schnellsuche/Schnellsuche?praefix=SEE&mastrNummer="
            + mastr_nr[3:]
        )
        r = requests.get(url)
        id_ = r.json()["url"].split("/")[-1]
        print('"%s": %s,' % (mastr_nr, id_))

    return str(id_)


def create_new_filtered_json_file(base_path, month, start_fresh=False):
    """
    execute this function to if you have a new dataset download

    month is the output filename, use the month when you downloaded the dataset. e.g. 2021-10
    """

    if start_fresh:
        # this step takes a lot of time
        large_units = []
        for filename in get_files_with_prefix(base_path, EINHEITEN_PREFIX):
            print("Starting with file", filename)
            large_units.extend(check_for_large_units(filename))
    else:
        out_file = "misc/de-mastr/filtered/%s.json" % month
        with open(out_file) as f:
            large_units = json.load(f)

    mastr_ids = [i["EinheitMastrNummer"] for i in large_units]
    owner_ids = [i["AnlagenbetreiberMastrNummer"] for i in large_units]

    # get the owner names
    owner_di = get_owner_from_marktakeure(base_path, owner_ids)
    # can use this as a backup
    # owner_di = {'ABR901047920507': 'swb Erzeugung AG ＆ Co. KG', 'ABR901203303755': 'enercity AG', 'ABR901241927012': 'KNE Windpark Nr. 12 GmbH ＆ Co. KG', 'ABR907042335667': 'RWE Generation SE', 'ABR911461408246': 'Versorgungsbetriebe Bordesholm GmbH', 'ABR917063786638': 'Allgäuer Überlandwerk GmbH', 'ABR920405658623': 'ENERPARC Solar Invest 184 GmbH', 'ABR921213385473': 'BES Bennewitz GmbH ＆ Co. KG', 'ABR922907721966': 'Coulomb GmbH', 'ABR930916959300': 'SMAREG 1', 'ABR932212103470': 'VERBUND Energy4Business Germany GmbH', 'ABR937155736822': '', 'ABR942217905054': 'ENGIE Deutschland GmbH', 'ABR967895852209': 'Lausitz Energie Kraftwerke AG', 'ABR976700826632': 'BES Groitzsch GmbH＆ Co. KG', 'ABR985310436612': 'EnspireME', 'ABR992411297332': 'Batteriespeicher Chemnitz GmbH ＆ Co. KG', 'ABR996025035908': 'RRKW Feldheim GmbH ＆ Co. KG', 'ABR998735752212': 'STEAG Battery System', 'ABR999566358659': 'be.storaged GmbH'}
    print(owner_di)
    for unit in large_units:
        unit["owner"] = owner_di[unit["AnlagenbetreiberMastrNummer"]]

    # get the mwh values
    mwh_di = get_mwh_from_anlagen(base_path, mastr_ids)
    for unit in large_units:
        unit["mwh"] = mwh_di[unit["EinheitMastrNummer"]]

    # get the detail page ids
    for unit in large_units:
        unit["pr_url_id"] = convert_to_details_url_id(unit["EinheitMastrNummer"])

    out_file = "misc/de-mastr/filtered/%s.json" % month
    if os.path.exists(out_file):
        print("file already exists, not overwritting it", out_file)
    else:
        with open(out_file, "w") as f:
            json.dump(large_units, f, indent=2)

    # just for debugging
    with open("mastr-test.json", "w") as f:
        json.dump(large_units, f, indent=2)


def pprint_units():
    with open("large-units.json") as f:
        js = json.load(f)
        print("SpeMastrNummer")
        print([i["SpeMastrNummer"] for i in js])
        print("number of projects", len(js))
        # pprint.pprint(js)
    return js


if __name__ == "__main__":
    month = "2022-12"
    print("Month:", month)
    # run the below commands to process a new download for large batteries
    create_new_filtered_json_file(
        "/Users/lorenz/Desktop/marktstammdaten/%s/extracted" % month,
        month,
        start_fresh=True,
    )

    # run the below commands to process a new download for small batteries
    create_csv_for_small_units(
        "/Users/lorenz/Desktop/marktstammdaten/%s/extracted" % month, month
    )
    create_summary_from_small_units_csv(
        "misc/de-mastr/small-batteries/%s.csv" % month, month
    )
