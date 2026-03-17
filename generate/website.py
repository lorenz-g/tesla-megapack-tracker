import csv
import datetime as dt
import json
import os
import sys
from decimal import Decimal
from typing import Iterable

from jinja2 import Environment, FileSystemLoader

from generate.battery_project import (
    USE_CASE_EMOJI_LI,
    BatteryProject,
    setup_battery_project,
)
from generate.constants import (
    GOV_DATA_INFO_DICT,
)
from generate.gov.uk_repd import (
    match_uk_repd_projects_with_mpt_projects,
    stats_uk_repd_data,
)
from generate.gov.us_eia import (
    download_and_extract_eia_data,
    match_eia_projects_with_mpt_projects,
    stats_eia_data,
)
from generate.utils import date_to_quarter, generate_link, find_duplicates

# cannot load this for every template rendered, takes too long.
FILE_LOADER = FileSystemLoader("templates")
JINJA_ENV = Environment(loader=FILE_LOADER)
GLOBAL_TEMPLATE_ARGS = {}


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
    template_arguments.update(GLOBAL_TEMPLATE_ARGS)
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

    # append info to the gov dict if the project is megapack or not
    # could probably also be done when the dataclass is created... 
    for p in projects:
        if p.country not in GOV_DATA_INFO_DICT.keys():
            continue
        if p.external_id and p.is_megapack:
            gov_data[p.country]["projects_short"][p.external_id].is_megapack = True

    for country, gov_di in gov_data.items():
        extra = {
            "now": dt.datetime.now(dt.UTC),
            "summary": gov_di,
            "gen_ids_from_projects": gen_ids_from_projects,
        }
        extra.update(GOV_DATA_INFO_DICT[country])
        write_template(
            "gov-page.jinja.html",
            {"extra": extra},
            "gov-%s.html" % extra["output_filename"],
        )

def gen_raw_data_files(projects: list[BatteryProject], filename: str):
    # write the raw data files
    output_dir = os.path.join("docs", "misc")
    csv_projects = [p.to_csv_row() for p in projects]
    # sort projects by id
    csv_projects = sorted(csv_projects, key=lambda x: int(x[0]))

    with open(os.path.join(output_dir, filename), "w") as f:
        writer = csv.writer(f)
        writer.writerow(BatteryProject.csv_header_row())
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

    s_totals_row["mw_k"] = "%.0fk" % (s_totals_row["mw"] / 1000)
    s_totals_row["mwh_k"] = "%.0fk" % (s_totals_row["mwh"] / 1000)

    return {
        "totals_row": s_totals_row,
        "by_status": s_by_status,
        "yearly_operation": s_yearly_op,
        "emoji_legend": emoji_legend,
        "by_country": s_by_country,
    }


def gen_projects_template(projects: list[BatteryProject], is_tesla_page: bool):
    # generate the index template
    summary = create_project_summaries(projects)
    if is_tesla_page:
        out_filename = None
        title = "Megapack"
    else:
        out_filename = "all-big-batteries.html"
        title = "Big battery"

    extra = {
        "title": title,
        "is_tesla_page": is_tesla_page,
        "now": dt.datetime.now(dt.UTC),
        "cars": gen_cars_vs_stationary(),
        "summary": summary,
        "projects": projects,
        "projects_json": json.dumps([p.to_dict() for p in projects]),
    }

    write_template("index.jinja.html", {"extra": extra}, out_filename=out_filename)


def gen_project_detail_page():
    write_template(
        "project.jinja.html",
        {"gov_data_info_dict": GOV_DATA_INFO_DICT},
        out_filename="project.html",
    )


def gen_projects_json(projects: Iterable[BatteryProject]):
    output = {p.csv.id: p.to_dict() for p in projects}
    with open(os.path.join("docs", "projects.json"), "w") as f:
        json.dump(output, f)


def delete_old_html_files():
    projects_dir = "docs/projects"
    if not os.path.isdir(projects_dir):
        return

    html_files = [i for i in os.listdir(projects_dir) if i.endswith(".html")]
    if html_files:
        print("Deleting old project detail pages:")
        for filename in html_files:
            path = os.path.join(projects_dir, filename)
            print(path)
            os.remove(path)


def delete_old_blog_files():
    old_blog_files = [
        os.path.join("docs", "blog.html"),
        os.path.join("docs", "blog"),
    ]

    for path in old_blog_files:
        if os.path.isfile(path):
            print(path)
            os.remove(path)
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                child_path = os.path.join(path, filename)
                if os.path.isfile(child_path):
                    print(child_path)
                    os.remove(child_path)
            if not os.listdir(path):
                print(path)
                os.rmdir(path)


def main(match_country):
    # 1) Load an prepare data
    csv_projects = load_file("projects.csv")

    gov_datasets = {
        "usa": stats_eia_data(),
        "uk": stats_uk_repd_data(),
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

    # check for duplicate project ids
    duplicates = find_duplicates([p.csv.id for p in projects])
    if duplicates:
        print("BAD, please fix: Duplicate project ids: %s" % duplicates)

    # if a project is removed from the csv, delete the html file as well
    delete_old_html_files()

    # sort by go live as datatables js also sorts like that
    projects = sorted(projects, key=lambda x: x.go_live, reverse=True)

    # projects that are not cancelled
    active_projects = [p for p in projects if p.is_active]
    tesla_projects = [p for p in active_projects if p.is_tesla]
    GLOBAL_TEMPLATE_ARGS["project_length"] = {
        "tesla_str": "(%d)" % len(tesla_projects),
        "all_str": "(%d)" % len(active_projects),
    }

    # 2) Generate the pages
    gen_projects_template(tesla_projects, is_tesla_page=True)
    gen_projects_template(active_projects, is_tesla_page=False)
    gen_project_detail_page()
    gen_projects_json(projects)
    gen_gov_pages(gov_datasets, projects)
    gen_raw_data_files(tesla_projects, "megapack-projects.csv")
    delete_old_blog_files()

    # 3) Match and print project that are not in projects.csv
    # this does not have to be run every time, just for manual assignment
    match_functions = {
        "usa": match_eia_projects_with_mpt_projects,
        "uk": match_uk_repd_projects_with_mpt_projects,
    }
    if match_country:
        # max internal id plus 1 - cannot assume that the last id is the highest
        start_id = max([int(p.csv.id) for p in projects]) + 1
        match_functions[match_country](gov_datasets[match_country], projects, start_id)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("usa", "uk"):
        match_country = sys.argv[1]
    else:
        match_country = None

    if match_country == "usa":
        # to download a new report, need to enable those two lines and make sure the month is correct
        download_and_extract_eia_data()
        # only need this to reprocess the downloaded files
        # read_eia_data_all_months()

    main(match_country)
