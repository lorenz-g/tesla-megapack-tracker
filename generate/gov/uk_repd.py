import csv
import datetime as dt
import os
import pprint
from collections import defaultdict
from typing import Iterable

from generate.battery_project import BatteryProject
from generate.bng_to_latlong import OSGB36toWGS84
from generate.utils import (
    GovMonthlyChanges,
    GovShortData,
    check_di_difference,
    create_summary_for_gov_projects,
)

# for simplicity introducing cancelled state here but filtering it out.
STATUS_DI = {
    "Under Construction": "construction",
    "Abandoned": "cancelled",
    "Application Submitted": "planning",
    "Application Withdrawn": "cancelled",
    "Awaiting Construction": "planning",
    "Planning Permission Expired": "cancelled",
    "Application Refused": "cancelled",
    "Appeal Refused": "cancelled",
    "Operational": "operation",
    "Finished": "operation",
    # TODO: not sure about that one...
    "Revised": "planning",
    "Pre-Planning": "planning",
    "Scoping": "planning",
    "Appeal Lodged": "planning",
}


def generate_filtered_csv(in_filename, out_filename):
    projects_li = []
    mw_total = 0
    i = 0

    pr_by_status = defaultdict(lambda: {"cnt": 0, "mw": 0})

    # in case getting a unicode decode error, might be useful to read as binary with rb
    # and printing the location and then deleting the character.
    # happened with the q4 21 and q1 22 report with one char.
    with open(in_filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            i += 1
            if row["Technology Type"].lower() != "battery":
                continue

            try:
                mw = int(float(row["Installed Capacity (MWelec)"]))
            except:
                mw = 0

            if mw < 10:
                continue

            status = STATUS_DI[row["Development Status (short)"]]
            pr_by_status[status]["cnt"] += 1
            pr_by_status[status]["mw"] += mw

            # TODO: now that the cancelled status is handled, no longer need to filter
            # them out, but would have to regenerate all the filtered files.
            if status == "cancelled":
                continue

            # only one affected: 6830 10162 Ochiltree - Battery Sorage
            # to laze to implement behavior if no coords are given.
            if row["X-coordinate"] == "":
                print(
                    i,
                    row["Ref ID"],
                    row["Site Name"],
                    "does not have coords, skipping this one",
                )
                continue

            lat_long = OSGB36toWGS84(int(row["X-coordinate"]), int(row["Y-coordinate"]))
            row["lat"] = lat_long[0]
            row["long"] = lat_long[1]
            row["status"] = status
            row["mw"] = mw
            projects_li.append(row)

            mw_total += mw

            # if i > 10:
            #     break

    pprint.pprint(pr_by_status)
    print("# projects >10MW: ", len(projects_li))
    print("mw projects >10MW: ", mw_total)

    with open(out_filename, "w") as f:
        writer = csv.DictWriter(f, fieldnames=projects_li[0].keys())
        writer.writeheader()
        for p in projects_li:
            writer.writerow(p)


def stats_uk_repd_data():
    folder = "misc/uk-repd/filtered/"
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
        monthly_changes = GovMonthlyChanges(month=month)

        for r in rows:
            # every gov project should have a ext_id and status
            r["ext_id"] = r["Ref ID"]
            r["mw"] = int(r["mw"])
            ref = r["Ref ID"]
            report_di[ref] = r

            if ref in last_report:
                # need to check for changes here
                dif = check_di_difference(last_report[ref], r, ignore=[])

                if dif:
                    monthly_changes.add_updated_project(r, dif)
                    projects_di[ref]["changes"].append({"month": month, "li": dif})

                    # in case the start construction column is not filled, can try to guess it that way
                    in_construction = any([ch["to"] == "construction" for ch in dif])
                    if in_construction:
                        projects_di[ref]["dates"]["start_construction"] = format_date(
                            r["Record Last Updated (dd/mm/yyyy)"]
                        )
                    in_operation = any([ch["to"] == "operation" for ch in dif])
                    if in_operation:
                        projects_di[ref]["dates"]["start_operation"] = format_date(
                            r["Record Last Updated (dd/mm/yyyy)"]
                        )

            else:
                # new project
                monthly_changes.new.append(r)
                projects_di[ref] = {
                    "first": r,
                    "first_month": month,
                    "changes": [],
                    "current": r,
                    "current_month": month,
                    "dates": {
                        "first_heard": format_date(
                            r["Record Last Updated (dd/mm/yyyy)"]
                        ),
                        "start_construction": "",
                        "start_operation": "",
                    },
                    "month_disappeared": "",
                }

            projects_di[ref]["current"] = r
            projects_di[ref]["current_month"] = month

        # find projects that disappeared
        for ref, r in last_report.items():
            if not (ref in report_di):
                monthly_changes.disappeared.append(r)
                if projects_di[ref]["current"]["status"] == "operation":
                    raise ValueError(
                        f"project {ref} disappeared but was in operation before"
                    )
                projects_di[ref]["month_disappeared"] = month

        monthly_changes.sort_lists_by_descending_mw()
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


def format_date(d):
    "18/10/2016  to 2016-10-18"
    if not d or d == " ":
        return ""
    return dt.datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")


def pick_first(first, second):
    "pickt the first acceptable value"
    if first not in (None, ""):
        return first
    else:
        return second


def gen_short_project(history_di):
    """input is the row dict from the csv"""
    r = history_di["current"]
    dates = history_di["dates"]

    date_first_heard = pick_first(
        format_date(r["Planning Permission Granted"]), dates["first_heard"]
    )
    # Some projects have "Implemented" in this column, which is not a date. So ignoring that
    if r["Under Construction"] == "Implemented":
        r["Under Construction"] = ""
    start_construction = pick_first(
        format_date(r["Under Construction"]), dates["start_construction"]
    )
    start_operation = pick_first(
        format_date(r["Operational"]), dates["start_operation"]
    )

    if history_di.get("month_disappeared", "") != "":
        month_disappeared = history_di["month_disappeared"]
        status = "cancelled"
    else:
        month_disappeared = ""
        status = r["status"]

    return GovShortData(
        data_source="uk_repd",
        name=r["Site Name"],
        external_id=r["Ref ID"],
        state=r["Region"].lower(),
        # Wales, Northern Ireland, England, Scotland (treat it as UK)
        country="uk",
        mwh=0,
        # estimate 1 hour system (in the uk generally a bit less, especially if they were build before 2020)
        estimate_mwh=int(r["mw"]),
        power_mw=int(r["mw"]),
        owner=r["Operator (or Applicant)"],
        status=status,
        date_first_heard=date_first_heard,
        start_construction=start_construction,
        start_operation=start_operation,
        month_disappeared=month_disappeared,
        # does not exist in the data source
        start_estimated="",
        lat=r["lat"],
        long=r["long"],
        coords_hint=2,
    )


def match_uk_repd_projects_with_mpt_projects(
    uk_repd_data, projects: Iterable[BatteryProject]
):
    """print a list of projects that can be copied into the projects.csv file"""
    existing_ids = [
        p.csv.external_id
        for p in projects
        if p.country == "uk" and p.csv.external_id != ""
    ]
    # list that can be inserted into projects.csv
    # max internal id plus 1
    start_id = int([p.csv.id for p in projects][-1]) + 1

    p: GovShortData  # thats a great way to give type hints in the code
    for e_id, p in uk_repd_data["projects_short"].items():
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
            "",
            str(p.estimate_mwh),
            str(p.power_mw),
            "",
            p.owner,
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


if __name__ == "__main__":
    # only runt it with new gov data
    in_filename = "misc/uk-repd/original/repd-july-2023.csv"
    out_filename = "misc/uk-repd/filtered/2023-07.csv"
    generate_filtered_csv(in_filename, out_filename)

    # stats_uk_repd_data()
