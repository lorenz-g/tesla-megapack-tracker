import csv
import datetime as dt
import io
import os
import pprint
import zipfile
from collections import defaultdict
from pathlib import Path

import pylightxl as xl
import requests

from generate.constants import US_STATES_SHORT_TO_LONG
from generate.utils import (
    GovShortData,
    check_di_difference,
    create_summary_for_gov_projects,
)


def stats_eia_data():
    """
    for the eia data, whenever a new year happens the projects that went into operation in the previous
    year are dropped from the table.

    """
    folder = "misc/eia-data/merged/"
    filenames = sorted(os.listdir(folder))
    months = [f.split(".")[0] for f in filenames]

    monthly_diffs = []
    last_report = {}

    # projects with their history
    projects_di = defaultdict(dict)

    for fn in filenames:
        month = fn.split(".")[0]
        with open(folder + fn) as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]

        report_di = {}
        monthly_changes = {"month": month, "new": [], "updated": [], "disappeared": []}

        for r in rows:
            # every gov project should have a ext_id and status
            r["mw"] = int(float(r["net summer capacity (mw)"]))
            p_id = r["plant id"]
            g_id = r["generator id"]
            if p_id not in report_di:
                report_di[p_id] = {}
            report_di[p_id][g_id] = r

            if p_id in last_report and g_id in last_report[p_id]:
                # need to check for changes here
                dif = check_di_difference(
                    last_report[p_id][g_id],
                    r,
                    ignore=["month", "year", "net summer capacity (mw)"],
                )

                if dif:
                    monthly_changes["updated"].append([r, dif])
                    projects_di[p_id][g_id]["changes"].append(
                        {"month": month, "li": dif}
                    )

                    in_construction = any([ch["to"] == "construction" for ch in dif])
                    if in_construction:
                        projects_di[p_id][g_id]["dates"]["start_construction"] = month
            else:
                # new project
                monthly_changes["new"].append(r)
                projects_di[p_id][g_id] = {
                    "first": r,
                    "first_month": month,
                    "changes": [],
                    "current": r,
                    "current_month": month,
                    "dates": {
                        "first_heard": month,
                        "start_construction": None,
                    },
                }

            projects_di[p_id][g_id]["current"] = r
            projects_di[p_id][g_id]["current_month"] = month

        # find projects that disappeared
        # note that the table 6_03 with the operational projects is emptied every year (i.e. in the March report)
        # but we want to exclude those projects
        for p_id, v in last_report.items():
            for g_id, r in v.items():
                if not (p_id in report_di and g_id in report_di[p_id]):
                    if r["status"] != "operation":
                        # TODO: should change the status of projects of the projects that disappeared and should not show them in the list anymore...
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


def min_date(li):
    "return min date but ignore empty dates"
    dates = [i for i in li if i not in (None, "")]
    if dates:
        return min(dates)
    else:
        return ""


def max_date(li):
    "return max date but ignore empty dates"
    dates = [i for i in li if i not in (None, "")]
    if dates:
        return max(dates)
    else:
        return ""


def gen_short_project(generator_di):
    """as the plant ids can hav multiple generator ids we need to summarise them and try to"""

    sub_p = generator_di.values()
    sub_p_cu = [p["current"] for p in sub_p]
    p0 = sub_p_cu[0]

    # pprint.pprint(sub_p)
    plant_names = set(p["plant name"] for p in sub_p_cu)
    if len(plant_names) != 1:
        # have one exception here
        if "Camino Solar" not in plant_names:
            print("Plant names differ", plant_names)

    assert len(set(p["entity name"] for p in sub_p_cu)) == 1
    assert len(set(p["entity id"] for p in sub_p_cu)) == 1
    assert len(set(p["plant state"] for p in sub_p_cu)) == 1

    mw_total = sum([p["mw"] for p in sub_p_cu])
    status_li = [p["status"] for p in sub_p_cu]

    # chose earliest status in case there are multiple projects
    if "planning" in status_li:
        status = "planning"
    elif "construction" in status_li:
        status = "construction"
    else:
        status = "operation"

    date_first_heard = min_date([p["dates"]["first_heard"] for p in sub_p])

    if status == "planning":
        start_construction = ""
    else:
        start_construction = min_date([p["dates"]["start_construction"] for p in sub_p])

    if status == "operation":
        start_operation = max_date([p["date"] for p in sub_p_cu])
        start_estimated = ""
    else:
        start_operation = ""
        start_estimated = max_date([p["date"] for p in sub_p_cu])

    return GovShortData(
        data_source="us_eia",
        name=p0["plant name"],
        external_id=p0["plant id"],
        state=US_STATES_SHORT_TO_LONG[p0["plant state"]],
        country="usa",
        mwh=0,
        # estimate 2 hour system
        estimate_mwh=2 * mw_total,
        power_mw=mw_total,
        owner=p0["entity name"],
        status=status,
        # TODO: probably good to add last heard of here
        date_first_heard=date_first_heard,
        start_construction=start_construction,
        start_operation=start_operation,
        start_estimated=start_estimated,
        has_multiple_projects=len(sub_p_cu) > 1,
        coords_hint=-1,
    )


def read_eia_data_all_months():
    print("\n\n------- function: read_eia_data_all_months")
    folders = [str(f) for f in Path("misc/eia-data/original/").iterdir()]
    for folder in folders:
        if ".DS_Store" in folder:
            continue
        print(folder)
        read_eia_data_single_month(folder)


def read_eia_data_single_month(folder):
    """
    eia = U.S. Energy Information Administration

    Data is downloaded from here:
    https://www.eia.gov/electricity/monthly/ -> overview page
    https://www.eia.gov/electricity/monthly/xls/table_6_03.xlsx -> new operating units
    https://www.eia.gov/electricity/monthly/xls/table_6_05.xlsx -> planned operating

    TODO: download data every month and then create a changelog and publish it on the website

    """

    # so far only planning, construction, operation used, but the eia data is more detailed
    status_verbose_to_status = {
        "(OT) Other": "planning",
        "(L) Regulatory approvals pending. Not under construction": "planning",
        "(T) Regulatory approvals received. Not under construction": "planning",
        "(P) Planned for installation, but regulatory approvals not initiated": "planning",
        "(U) Under construction, less than or equal to 50 percent complete": "construction",
        "(V) Under construction, more than 50 percent complete": "construction",
        "(TS) Construction complete, but not yet in commercial operation": "construction",
        "operation": "operation",
    }

    # use a list here as some projects can have the same plant id
    # plant_id + generator code is always unique
    # e.g. Ravenswood project has 3 entries with the same plant id
    projects = defaultdict(list)

    # this one is to write it to a csv
    projects_li = []

    counts = defaultdict(int)
    files = [
        os.path.join(folder, "Table_6_03.xlsx"),
        os.path.join(folder, "Table_6_05.xlsx"),
    ]

    for file in files:
        if "6_03" in file:
            type_ = "operation"
        elif "6_05" in file:
            type_ = "planned"
        else:
            raise ValueError("unknown table")

        print(file)
        db = xl.readxl(file)
        ws = db.ws(db.ws_names[0])

        # ignore first row and use second row as column names
        rows = list(ws.rows)[1:]
        # only use lower case col names
        column_names = [r.lower() for r in rows[0]]
        rows = rows[1:]
        col_len = len(column_names)

        # print(type_, "\n", "\n".join(column_names))

        for row in rows:
            # similar to a csv dict reader
            pr = {column_names[i]: row[i] for i in range(col_len)}

            # only battery projects
            if not pr["technology"] == "Batteries":
                continue

            if isinstance(pr["net summer capacity (mw)"], str):
                continue

            # only projects with more than 10 MW
            # the library auto converts to float or int if it detects sth
            if pr["net summer capacity (mw)"] < 10:
                continue

            # need to add this manually
            if type_ == "operation":
                pr["status"] = "operation"
            else:
                # don't need it, can rely on the net summer capacity
                pr.pop("nameplate capacity (mw)")

            # set the status and ext_id which need to be set in every project
            pr["status_verbose"] = pr["status"]
            pr["status"] = status_verbose_to_status[pr["status_verbose"]]
            pr["ext_id"] = pr["plant id"]

            pr["date"] = "%d-%02d" % (pr["year"], pr["month"])

            # print(pr)
            projects[pr["plant id"]].append(pr)
            projects_li.append(pr)
            counts[pr["status"]] += 1

    print(counts)

    # e.g. "misc/eia-data/original/2021-01/table.xlsx"
    date = files[0].split("/")[3]
    with open("misc/eia-data/merged/%s.csv" % date, "w") as f:
        writer = csv.DictWriter(f, fieldnames=projects_li[0].keys())
        writer.writeheader()
        for p in projects_li:
            writer.writerow(p)

    # print(len(projects))
    # print(sum(len(i) for i in projects.values()))

    return projects


def download_single_eia_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        print("got %s code, ignoring it" % (r.status_code))
        return False

    try:
        file = zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile:
        # can return here as this will be the first month where data is not available
        print("bad zip file, month not available yet")
        return False

    return file


def download_and_extract_eia_data():
    """
    don't always have to run the entire date range, can just run the latest month...

    https://www.eia.gov/electricity/monthly/archive/july2021.zip

    # TODO: need to find out if they are the same for all the month
    Table_6_03.xlsx
    Table_6_05.xlsx

    seems like the table 6_03 did not exist in 2020
    """
    print("\n\n------ function: download_and_extract_eia_data ")

    years = [
        # [2020, [9,12]], # before 9, there is a key error net summer capacity (mw), not digging further here
        # [2021, [8, 13]],
        # [2022, [7, 13]],
        [2023, [1, 13]],
    ]
    base_url = "https://www.eia.gov/electricity/monthly/archive/%s.zip"
    # the latest month is under this url
    base_url_current_month = (
        "https://www.eia.gov/electricity/monthly/current_month/%s.zip"
    )
    tables = ["Table_6_03.xlsx", "Table_6_05.xlsx"]

    for year, r in years:
        for month in range(r[0], r[1]):
            date = dt.date(year, month, 1)
            url = base_url % date.strftime("%B%Y").lower()
            print(date, "-> ", url)
            file = download_single_eia_url(url)
            # for the first month that is not in the archive we try the current month
            if not file:
                url = base_url_current_month % date.strftime("%B%Y").lower()
                print(date, "-> ", url)
                file = download_single_eia_url(url)

            if file:
                for table in tables:
                    zi = file.getinfo(table)
                    folder = "misc/eia-data/original/%s/" % date.strftime("%Y-%m")
                    file.extract(zi, folder)

                read_eia_data_single_month(folder)
            else:
                break


if __name__ == "__main__":
    projects = stats_eia_data()["projects"]
    for k, v in projects.items():
        # TODO: what happens to the
        genetor_ids = list(v.values())
        current = genetor_ids[0]["current"]
        name = current["plant name"]

        # if genetor_ids[0]["current_month"] != "2021-10":
        #     print(name, genetor_ids[0]["current_month"], current["status"], current["mw"])

        if len(v) > 1:
            print(
                name, genetor_ids[0]["current_month"], current["status"], current["mw"]
            )
        #     if "Stanton" in name:
        #         pprint.pprint(list(v.values()))
