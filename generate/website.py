import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from jinja2 import Environment, FileSystemLoader

from generate.battery_project import (
    USE_CASE_EMOJI_LI,
    BatteryProject,
    setup_battery_project,
)
from generate.blog import gen_blog
from generate.constants import (
    GOV_DATA_INFO_DICT,
    US_STATES_LONG_TO_SHORT,
    US_STATES_SHORT_TO_LONG,
)
from generate.gov.de_mastr import (
    match_de_mastr_projects_with_mpt_projects,
    stats_de_mastr_data,
)
from generate.gov.uk_repd import (
    match_uk_repd_projects_with_mpt_projects,
    stats_uk_repd_data,
)
from generate.gov.us_eia import (
    download_and_extract_eia_data,
    read_eia_data_all_months,
    stats_eia_data,
)
from generate.utils import date_to_quarter, generate_link

# cannot load this for every template rendered, takes too long.
FILE_LOADER = FileSystemLoader("templates")
JINJA_ENV = Environment(loader=FILE_LOADER)


def write_template(template_name, template_arguments, out_filename=None):
    if not out_filename:
        out_filename = template_name.replace(".jinja", "")

    output_dir = "docs"
    template = JINJA_ENV.get_template(template_name)

    template_arguments.update(
        {
            "g_l": generate_link,
        }
    )
    with open(os.path.join(output_dir, out_filename), "w") as f:
        f.write(template.render(**template_arguments))


def load_file(filename="projects.csv", type_="json"):
    "For now from the csv, later from the toml fils"
    with open(filename) as f:
        if type_ == "json":
            reader = csv.DictReader(f)
        elif type_ == "csv":
            reader = csv.reader(f)
        else:
            raise ValueError("type not know")
        rows = [row for row in reader]
    # pprint.pprint(rows[0])
    return rows


def gen_gov_pages(gov_data, projects: Iterable[BatteryProject]):
    gen_ids_from_projects = {p.csv.external_id: p.csv.id for p in projects}
    for country, gov_di in gov_data.items():
        extra = {
            "now": dt.datetime.utcnow(),
            "summary": gov_di,
            "gen_ids_from_projects": gen_ids_from_projects,
        }
        extra.update(GOV_DATA_INFO_DICT[country])
        write_template(
            "gov-page.jinja.html",
            {"extra": extra},
            "gov-%s.html" % extra["output_filename"],
        )


def gen_raw_data_files():
    # write the raw data files
    output_dir = os.path.join("docs", "misc")
    json_projects = load_file("projects.csv")
    output_fn = "big-battery-projects"

    with open(os.path.join(output_dir, output_fn + ".json"), "w") as f:
        json.dump(json_projects, f)

    csv_projects = load_file(type_="csv")

    # I think the two csv files are the same, but keep it for now.
    with open(os.path.join(output_dir, output_fn + ".csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerows(csv_projects)


def gen_cars_vs_stationary():
    "prepare data to use it with bootstrap bars, a charting lib might be easier..."

    info_per_quarter = load_file(filename="cars-vs-stationary.csv")
    di = {}

    # those are estimates for the average battery size
    sx_avg_battery_kwh = 90
    y3_avg_battery_kwh = 60

    # aggregate on a yearly basis
    max_mwh = 0
    sum_cars = 0
    sum_ess = 0
    for q in info_per_quarter:
        year = q["year"]
        if year not in di:
            di[year] = {"sx_mwh": 0, "y3_mwh": 0, "stat_mwh": 0, "year": year}

        sx = int(q["sx"]) * sx_avg_battery_kwh / 1000
        y3 = int(q["y3"]) * y3_avg_battery_kwh / 1000
        ess = int(q["stat_mwh"])
        di[year]["sx_mwh"] += sx
        di[year]["y3_mwh"] += y3
        di[year]["stat_mwh"] += ess

        # need to find th max for the percentages
        m = di[year]["sx_mwh"] + di[year]["y3_mwh"] + di[year]["stat_mwh"]
        if m > max_mwh:
            max_mwh = m

        sum_cars += sx + y3
        sum_ess += ess

    li = sorted(di.values(), key=lambda x: x["year"])

    for year in li:
        # compared to max
        year["perc_stat"] = year["stat_mwh"] / max_mwh * 100
        year["perc_sx"] = year["sx_mwh"] / max_mwh * 100
        year["perc_y3"] = year["y3_mwh"] / max_mwh * 100

        # compared this year
        total = year["stat_mwh"] + year["sx_mwh"] + year["y3_mwh"]
        perc_stat_int = int(year["stat_mwh"] / total * 100)
        year["total_gwh"] = total / 1000
        year["perc_cars"] = 100 - perc_stat_int
        year["perc_stat_year"] = perc_stat_int

    total_mwh = sum_cars + sum_ess
    total_gwh = total_mwh / 1000
    total_tesla_twh = total_gwh / 1000
    perc_cars = int(sum_cars / total_mwh * 100)
    li.append(
        {
            "year": "All Time",
            "total_gwh": total_gwh,
            "perc_cars": perc_cars,
            "perc_stat_year": 100 - perc_cars,
        }
    )

    year_in_hours = 365 * 24
    consumption_list = [
        {
            "text": "The entire globe 🌎",
            "twh_per_year": 25343,
            "year_of_consumption": "2021",
            "source": "https://www.statista.com/statistics/280704/world-power-consumption/",
            "display": "minutes",
        },
        {
            "text": "China 🇨🇳",
            "twh_per_year": 8310,
            "year_of_consumption": "2021",
            "source": "https://www.statista.com/statistics/302203/china-electricity-consumption/",
            "display": "minutes",
        },
        {
            "text": "USA 🇺🇸",
            "twh_per_year": 4243,
            "year_of_consumption": "2022",
            "source": "https://www.eia.gov/totalenergy/data/monthly/pdf/sec7_5.pdf",
            "display": "minutes",
        },
        {
            "text": "Germany 🇩🇪",
            "twh_per_year": 511,
            "year_of_consumption": "2021",
            "source": "https://www.statista.com/statistics/383650/consumption-of-electricity-in-germany/",
            "display": "hours",
        },
    ]

    for di in consumption_list:
        if di["display"] == "hours":
            factor = 1
        elif di["display"] == "minutes":
            factor = 60
        else:
            raise ValueError("unknown display type")
        di["value"] = factor * total_tesla_twh / (di["twh_per_year"] / year_in_hours)

    return {
        "list": li,
        "expl": {
            "total_gwh": total_gwh,
            "consumption_list": consumption_list,
        },
    }


def create_project_summaries(projects: Iterable[BatteryProject]):
    # s_ stands for summary_
    s_totals_row = {
        "count": 0,
        "mwh": 0,
        "mw": 0,
    }
    s_by_status = {}
    s_yearly_op = {}
    s_by_country = {}

    emoji_legend = []
    for _, emoji, explanation in USE_CASE_EMOJI_LI:
        emoji_legend.append("%s %s" % (emoji, explanation))
    emoji_legend = ", ".join(emoji_legend)

    # augment raw projects data
    for p in projects:
        if p.status not in s_by_status:
            s_by_status[p.status] = {"count": 0, "gwh": 0, "gw": 0}

        s_by_status[p.status]["count"] += 1
        s_by_status[p.status]["gwh"] += p.mwh / 1000
        s_by_status[p.status]["gw"] += p.mw / 1000

        if p.in_operation:
            year = p.start_operation[:4]
            if year not in s_yearly_op:
                s_yearly_op[year] = {"year": year, "gwh": 0, "perc": None}
            s_yearly_op[year]["gwh"] += p.mwh / 1000

        s_totals_row["count"] += 1
        s_totals_row["mwh"] += p.mwh
        s_totals_row["mw"] += p.mw

        if p.country not in s_by_country:
            s_by_country[p.country] = {"flag": p.flag, "gwh": 0}
        if p.in_operation:
            s_by_country[p.country]["gwh"] += p.mwh / 1000

    for year in s_yearly_op.values():
        year["perc"] = 100 * year["gwh"] / s_by_status["operation"]["gwh"]

    s_yearly_op = sorted(s_yearly_op.values(), key=lambda x: x["year"])
    s_by_country = sorted(s_by_country.values(), key=lambda x: x["gwh"], reverse=True)

    return {
        "totals_row": s_totals_row,
        "by_status": s_by_status,
        "yearly_operation": s_yearly_op,
        "emoji_legend": emoji_legend,
        "by_country": s_by_country,
    }


def gen_projects_template(projects, template_name):
    # generate the index template
    summary = create_project_summaries(projects)
    extra = {
        "now": dt.datetime.utcnow(),
        "cars": gen_cars_vs_stationary(),
        "summary": summary,
        "projects": projects,
        "projects_json": json.dumps([p.to_dict() for p in projects]),
    }
    write_template(template_name, {"extra": extra})


def gen_individual_pages(projects: Iterable[BatteryProject]):
    # generate the individual pages
    for p in projects:
        write_template(
            "single.jinja.html",
            {"p": p, "gov_data_info_dict": GOV_DATA_INFO_DICT},
            os.path.join("projects", p.csv.id + ".html"),
        )


def gen_de_small_batteries():
    """
    Column names:
    quarter	category	count	mwh_sum	kwh_avg	mw_sum	kw_avg
    """
    # TODO: automatically use the latest month
    month = "2022-12"
    in_filename = "misc/de-mastr/small-batteries/%s-hss-summary.csv" % month
    rows = []
    mwh_cum = 0
    mw_cum = 0
    count_cum = 0

    current_quarter = date_to_quarter(month)

    with open(in_filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # don't show future quarters
            if row["quarter"] > current_quarter:
                continue

            mwh_cum += Decimal(row["mwh_sum"])
            mw_cum += Decimal(row["mw_sum"])
            count_cum += int(row["count"])
            row["mwh_cum"] = mwh_cum
            row["mw_cum"] = mw_cum
            row["count_cum"] = count_cum
            rows.append(row)

    extra = {
        "rows": rows,
        "month": month,
    }
    extra.update(GOV_DATA_INFO_DICT["germany"])

    write_template(
        "gov-de-mastr-small-batteries.jinja.html",
        {"extra": extra},
    )


def match_eia_projects_with_mpt_projects(eia_data, projects: Iterable[BatteryProject]):
    """match by state and then print in desceding order of capacity"""

    pr_by_state = defaultdict(lambda: {"eia": [], "mpt": []})

    mpt_plant_ids = set([p.csv.external_id for p in projects])

    for v in eia_data["projects"].values():
        # ignore if there are multiple generator codes
        pr = list(v.values())[0]["current"]
        if pr["plant id"] not in mpt_plant_ids:
            pr_by_state[pr["plant state"]]["eia"].append(pr)

    for pr in projects:
        if pr.country != "usa":
            continue
        if not pr.state:
            continue

        if not pr.csv.external_id:
            state_short = US_STATES_LONG_TO_SHORT.get(pr.state)
            if state_short:
                pr_by_state[state_short]["mpt"].append(pr)
            else:
                print("could not find state", pr.state, pr)

    for state, temp_projects in sorted(pr_by_state.items()):
        print("\n\n")
        print(US_STATES_SHORT_TO_LONG[state].upper())
        print("eia projects:")
        eia = sorted(temp_projects["eia"], key=lambda x: x["mw"], reverse=True)
        for p in eia:
            print(p["mw"], p["plant name"], p["plant id"], p["status"])

        print("\nmpt projects:")
        mpt = sorted(temp_projects["mpt"], key=lambda x: x.mw, reverse=True)
        for p in mpt:
            print(p.mw, p.csv.name)

    # list that can be inserted into projects.csv
    # TODO: probably should try and ignore the ones that I had in the US that are not covered here.
    print("\n\n")
    # max internal id plus 1
    start_id = int([p.csv.id for p in projects][-1]) + 1

    for state, temp_projects in sorted(pr_by_state.items()):
        eia = sorted(temp_projects["eia"], key=lambda x: x["mw"], reverse=True)
        for p in eia:
            # estimate a two hour system
            mwh_estimate = str(p["mw"] * 2)

            # set different dates
            start_operation = ""
            start_estimated = ""

            if p["status"] == "operation":
                start_operation = p["date"] + "-01"
            else:
                start_estimated = p["date"]

            li = [
                p["plant name"],
                "",
                str(start_id),
                p["plant id"],
                "1",
                US_STATES_SHORT_TO_LONG[state],
                "usa",
                "",
                mwh_estimate,
                str(p["mw"]),
                "",
                p["entity name"],
                "",
                "",
                "",
                "",
                "",
                p["status"],
                "",
                "",
                start_operation,
                start_estimated,
            ]
            print(";".join(li))
            start_id += 1


def main(match_country):
    # 1) Load an prepare data
    csv_projects = load_file("projects.csv")

    gov_datasets = {
        "usa": stats_eia_data(),
        "uk": stats_uk_repd_data(),
        "germany": stats_de_mastr_data(),
    }

    projects: list[BatteryProject] = []
    for p in csv_projects:
        # skip for an empty row (sometimes the case at the end)
        if p["name"] == "":
            continue

        gov = None
        gov_history = None

        if p["country"] in gov_datasets and p["external_id"]:
            gov = gov_datasets[p["country"]]["projects_short"][p["external_id"]]
            gov_history = gov_datasets[p["country"]]["projects"][p["external_id"]]

        projects.append(setup_battery_project(p, gov, gov_history))

    # sort by go live as datatables js also sorts like that
    projects = sorted(projects, key=lambda x: x.go_live, reverse=True)

    # projects that are not cancelled
    active_projects = [p for p in projects if p.is_active]
    tesla_projects = [p for p in active_projects if p.is_tesla]

    # 2) Generate the pages
    gen_projects_template(tesla_projects, "index.jinja.html")
    gen_projects_template(active_projects, "all-big-batteries.jinja.html")
    gen_individual_pages(projects)
    gen_gov_pages(gov_datasets, projects)
    gen_de_small_batteries()
    gen_raw_data_files()
    gen_blog()

    ajax_data = {
        "project_length": {
            "tesla_str": "(%d)" % len(tesla_projects),
            "all_str": "(%d)" % len(active_projects),
        },
        # TODO: can move the static site generated at into here also
        # "generated_at":
    }
    # load some data via ajax to keep the commit history of the individual project html files cleaner
    with open("docs/ajax-data.json", "w") as f:
        json.dump(ajax_data, f)

    # 3) Match and print project that are not in projects.csv
    # this does not have to be run every time, just for manual assignment
    match_functions = {
        "usa": match_eia_projects_with_mpt_projects,
        "uk": match_uk_repd_projects_with_mpt_projects,
        "germany": match_de_mastr_projects_with_mpt_projects,
    }
    if match_country:
        match_functions[match_country](gov_datasets[match_country], projects)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("usa", "uk", "germany"):
        match_country = sys.argv[1]
    else:
        match_country = None

    if match_country == "usa":
        # to download a new report, need to enable those two lines and make sure the month is correct
        download_and_extract_eia_data()
        # only need this to reprocess the downloaded files
        # read_eia_data_all_months()

    main(match_country)
