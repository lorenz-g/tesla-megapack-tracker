import collections
import csv
import io
import pprint
import os
import json
import zipfile
from jinja2 import Environment, FileSystemLoader
import datetime as dt
import pylightxl as xl
from collections import defaultdict
import requests
from pathlib import Path
from generate.blog import gen_blog
from generate.battery_project import USE_CASE_EMOJI_LI, BatteryProject, VALID_STATUS
from generate.utils import generate_link, COUNTRY_EMOJI_DI, US_STATES_LONG_TO_SHORT, US_STATES_SHORT_TO_LONG

from typing import Iterable



def load_file(filename='projects.csv', type_="json"):
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

def check_di_difference(old, new, ignore=None):
    """ only focus on single level dicts and assume they have the same keys
    """
    assert sorted(old.keys()) == sorted(old.keys())

    if ignore is None:
        ignore = []

    li = []
    for k,v in old.items():
        if k in ignore:
            continue
        extra = ""
        if k == 'date':
            from_date = dt.datetime.strptime(v, "%Y-%m")
            to_date = dt.datetime.strptime(new[k], "%Y-%m")
            month_delta = (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)
            pill_bg = 'danger' if month_delta > 0 else 'success'
            word = 'delayed' if month_delta > 0 else 'accelerated'
            month = "month" if abs(month_delta) == 1 else "months"
            extra = '<span class="badge rounded-pill bg-%s">%s by %d %s</span>' % (pill_bg, word, abs(month_delta), month)
        if k == 'status' and new[k] == "operation":
            # celebrate
            extra = "🍾 🎉 🍸"


        if new[k] != v:
            li.append({
                "name": k,
                "from": v,
                "to": new[k],
                "extra": extra,
            })
    return li

def stats_eia_data():
    folder = "misc/eia-data/merged/"
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
            reader = csv.DictReader(f)
            rows = [row for row in reader]
        
        report_di = {}
        monthly_changes = {
            "month": month,
            "new": [],
            "updated": [],
        }

        for r in rows:

            r["mw"] = float(r["net summer capacity (mw)"])
            
            if r["status_simple"] not in s_monthly[month]:
                s_monthly[month][r["status_simple"]] = {"count": 0, "gw": 0}
            s_monthly[month][r["status_simple"]]["count"] += 1
            s_monthly[month][r["status_simple"]]["gw"] += float(r["net summer capacity (mw)"]) / 1000

            p_id = r["plant id"]
            g_id = r["generator id"]
            if p_id not in report_di:
                report_di[p_id] = {}
            report_di[p_id][g_id] = r

            if p_id in last_report and g_id in last_report[p_id]:
                # need to check for changes here
                dif = check_di_difference(
                    last_report[p_id][g_id], r, 
                    ignore=["month", "year", "status_simple", "net summer capacity (mw)"]
                )
                if dif:
                    monthly_changes["updated"].append([r, dif])
                    projects_di[p_id][g_id]["changes"].append({"month": month, "li": dif})

            else:
                # new project
                monthly_changes["new"].append(r)
                projects_di[p_id][g_id] = {
                    "first": r, 
                    "first_month": month,
                    "changes": [],
                    "current": r,
                    "current_month": month,
                }
            
            projects_di[p_id][g_id]["current"] = r
            projects_di[p_id][g_id]["current_month"] = month


        
        monthly_changes["new"] = sorted(monthly_changes["new"], key=lambda x:x["mw"], reverse=True)
        monthly_changes["updated"] = sorted(monthly_changes["updated"], key=lambda x:x[0]["mw"], reverse=True)

        monthly_diffs.append(monthly_changes)
        last_report = report_di

    
    # for k,v in s_monthly.items():
    #     print(k,v)

    summary = {
        "current": s_monthly[months[-1]],
        "current_month": months[-1],
        # want the in descending order
        "monthly_diffs": monthly_diffs[::-1],
        "projects": projects_di,
    }

    return summary
    

def read_eia_data_all_months():
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
    status_to_status_simple = {
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
    files = [os.path.join(folder, "Table_6_03.xlsx"), os.path.join(folder, "Table_6_05.xlsx")]


    for file in files:
        if "6_03" in file:
            type_ = "operation"
        elif "6_05" in file:
            type_ = "planned"
        else:
            raise ValueError("unknown table")

        print(file)
        db = xl.readxl(file)
        print(db)
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
            
            # only battery projects and projects of more than 10MW
            if not (pr["technology"] == "Batteries" and float(pr["net summer capacity (mw)"]) >= 10):
                continue
            
            # need to add this manually
            if type_ == 'operation':
                pr["status"] = "operation"
            else:
                # don't need it, can rely on the net summer capacity
                pr.pop('nameplate capacity (mw)')

            pr["status_simple"] = status_to_status_simple[pr["status"]]
            pr["date"] = "%d-%02d" % (pr["year"], pr["month"])
            
            # print(pr)
            projects[pr["plant id"]].append(pr)
            projects_li.append(pr)
            counts[pr["status_simple"]] += 1
    
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

def download_and_extract_eia_data():
    """
    don't always have to run the entire date range, can just run the latest month...

    https://www.eia.gov/electricity/monthly/archive/july2021.zip

    # TODO: need to find out if they are the same for all the month
    Table_6_03.xlsx
    Table_6_05.xlsx

    seems like the table 6_03 did not exist in 2020
    """

    years = [
        # [2020, [9,12]], # before 9, there is a key error net summer capacity (mw), not digging further here
        [2021, [8, 13]],
    ]
    base_url = "https://www.eia.gov/electricity/monthly/archive/%s.zip"
    tables = ['Table_6_03.xlsx', 'Table_6_05.xlsx']

    for year, r in years:
        for month in range(r[0],r[1]):
            date = dt.date(year, month, 1)
            print(date)
            r = requests.get(base_url % date.strftime("%B%Y").lower())
            if r.status_code != 200:
                print("got %s code, ignoring it" % (r.status_code))
                continue
            
            file = zipfile.ZipFile(io.BytesIO(r.content))
        
            for table in tables:
                zi = file.getinfo(table)
                folder = "misc/eia-data/original/%s/" % date.strftime("%Y-%m")
                file.extract(zi, folder)
    
            read_eia_data_single_month(folder)


def gen_eia_page(eia_data, projects: Iterable[BatteryProject]):

    gen_ids_from_projects = {p.csv.external_id:p.csv.id for p in projects}

    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'
    template_name = "eia.jinja.html"
    
    extra = {
        "now": dt.datetime.utcnow(),
        "summary": eia_data,
        "gen_ids_from_projects": gen_ids_from_projects,
    }

    template = env.get_template(template_name)
    output = template.render(extra=extra, g_l=generate_link) 
    
    with open(os.path.join(output_dir, template_name.replace(".jinja", "")), 'w') as f:
        f.write(output)



def gen_raw_data_files():
    # write the raw data files
    output_dir = os.path.join('docs', "misc")
    json_projects = load_file('projects.csv')
    output_fn = 'big-battery-projects'

    with open(os.path.join(output_dir, output_fn + ".json"), 'w') as f:
        json.dump(json_projects, f)    

    csv_projects = load_file(type_="csv")

    # I think the two csv files are the same, but keep it for now.
    with open(os.path.join(output_dir, output_fn + ".csv"), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(csv_projects)

    with open(os.path.join(output_dir, output_fn + ".excel.csv"), 'w') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerows(csv_projects)
        

def gen_cars_vs_stationary():
    "prepare data to use it with bootstrap bars, a charting lib might be easier..."

    info_per_quarter = load_file(filename='cars-vs-stationary.csv')
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
            di[year] = {"sx_mwh": 0, "y3_mwh": 0, "stat_mwh":0, "year": year}
        
        sx = int(q["sx"]) * sx_avg_battery_kwh / 1000
        y3 = int(q["y3"]) * y3_avg_battery_kwh / 1000
        ess = int(q["stat_mwh"])
        di[year]["sx_mwh"] += sx
        di[year]["y3_mwh"] += y3
        di[year]["stat_mwh"] += ess

        # need to find th max for the percentages
        m = max(di[year]["sx_mwh"] + di[year]["y3_mwh"], di[year]["stat_mwh"])
        if m > max_mwh:
            max_mwh = m
        
        sum_cars += (sx + y3)
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
    perc_cars = int(sum_cars / total_mwh * 100)
    li.append({
        "year": "All Time",
        "total_gwh": total_gwh,
        "perc_cars": perc_cars,
        "perc_stat_year": 100 - perc_cars,
    })

    # electcity in 2018 https://www.statista.com/statistics/280704/world-power-consumption/
    worldwide_gwh = 23398 * 1000
    year_in_hours = 365 * 24
    worldwide_avg_cons_gw = worldwide_gwh / year_in_hours

    return {
        "list": li,
        "expl": {
            "total_gwh": total_gwh,
            # https://www.agora-energiewende.de/en/service/recent-electricity-data/
            "avg_power_germany_gw": 60,
            "hours_germany": total_gwh/60,
            "minutes_world": 60 * total_gwh / worldwide_avg_cons_gw,
        }
    }



def create_project_summaries(projects: Iterable[BatteryProject]):

    # s_ stands for summary_
    s_megapack = {
        "project_cnt": 0,
        "mp_count": 0,
        "gwh":0,
    }

    s_totals_row = {
        "count": 0,
        "mwh":0,
        "mw":0,
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

        # add to summary
        if p.in_operation and p.is_megapack:
            s_megapack["project_cnt"] += 1
            s_megapack["mp_count"] +=  p.no_of_battery_units
            s_megapack["gwh"] += p.mwh / 1000
        

        if p.status not in s_by_status:
            s_by_status[p.status] = {"count": 0, "gwh":0, "gw":0}
        
        s_by_status[p.status]["count"] += 1
        s_by_status[p.status]["gwh"] += p.mwh / 1000
        s_by_status[p.status]["gw"] += p.mw / 1000

        if p.in_operation:
            year = p.csv.start_operation[:4]
            if year not in s_yearly_op:
                s_yearly_op[year] = {"year": year, "gwh": 0, "perc": None}
            s_yearly_op[year]["gwh"] += p.mwh / 1000
        
        s_totals_row["count"] += 1
        s_totals_row["mwh"] += p.mwh
        s_totals_row["mw"] += p.mw
        
        if p.csv.country not in s_by_country:
            
            s_by_country[p.csv.country] = {
                "flag": p.flag, 
                "gwh":0
            }
        if p.in_operation:
            s_by_country[p.csv.country]["gwh"] += p.mwh / 1000

    
    for year in s_yearly_op.values():
        year["perc"] = 100 * year["gwh"] / s_by_status["operation"]["gwh"]
    
    s_yearly_op = sorted(s_yearly_op.values(), key=lambda x:x["year"])
    s_by_country = sorted(s_by_country.values(), key=lambda x:x["gwh"], reverse=True)

    return {
        "megapack": s_megapack,
        "totals_row": s_totals_row,
        "by_status": s_by_status,
        "yearly_operation": s_yearly_op,
        "emoji_legend": emoji_legend,
        "by_country": s_by_country,
    }


def gen_projects_template(projects, template_name):
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    # generate the index template
    summary = create_project_summaries(projects)
    extra = {
        "now": dt.datetime.utcnow(),
        "cars": gen_cars_vs_stationary(),
        "summary": summary,
        "projects": projects,
        "projects_json": json.dumps([p.to_dict() for p in projects])
    }

    template = env.get_template(template_name)
    output = template.render(extra=extra, g_l=generate_link) 
    
    with open(os.path.join(output_dir, template_name.replace(".jinja", "")), 'w') as f:
        f.write(output)
    

def gen_individual_pages(projects: Iterable[BatteryProject]):
    # generate the individual pages
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    fn = 'single.jinja.html' 
    template = env.get_template(fn)

    for p in projects:
        output_fn = os.path.join(output_dir, "projects", p.csv.id + ".html")
        with open(output_fn, 'w') as f:
            f.write(template.render(p=p, g_l=generate_link))


def match_eia_projects_with_mpt_projects(eia_data, projects):
    """ match by state and then print in desceding order of capacity"""

    pr_by_state = defaultdict(lambda: {"eia": [], "mpt": []})

    mpt_plant_ids = set([p["eia_plant_id"] for p in projects])

    for v in eia_data["projects"].values():
        # ignore if there are multiple generator codes
        pr = list(v.values())[0]["current"]
        if pr["plant id"] not in mpt_plant_ids:
            pr_by_state[pr["plant state"]]["eia"].append(pr)
    
    for pr in projects:
        if pr["country"] != "usa":
            continue
        if not pr["state"]:
            continue
        
        if not pr["eia_plant_id"]:
            state_short = US_STATES_LONG_TO_SHORT.get(pr["state"])
            if state_short:
                pr_by_state[state_short]["mpt"].append(pr)
            else:
                print("could not find state", pr["state"])
            
    
    for state, projects in sorted(pr_by_state.items()):
        print("\n\n")
        print(state)
        print("eia projects:")
        eia = sorted(projects["eia"], key=lambda x:x["mw"], reverse=True)
        for p in eia:
            print(p["mw"], p["plant name"], p["plant id"], p["status_simple"])
        
        print("\nmpt projects:")
        mpt = sorted(projects["mpt"], key=lambda x:x["mw_int"], reverse=True)
        for p in mpt:
            print(p["mw_int"], p["name"], p["id"], p["status"])

    # list that can be inserted into projects.csv
    # TODO: probably should try and ignore the ones that I had in the US that are not covered here. 
    print("\n\n")
    for state, projects in sorted(pr_by_state.items()):
        eia = sorted(projects["eia"], key=lambda x:x["mw"], reverse=True)
        start_id = 143
        for p in eia:
            # estimate a two hour system
            mwh_estimate = str(p["mw"] * 2)

            # set different dates
            start_operation = ""
            start_estimated = ""

            if p["status_simple"] == "operation":
                start_operation = p["date"] + "-01"
            else:
                start_estimated = p["date"]

            li = [
                p["plant name"], "", str(start_id), p["plant id"], "1",
                US_STATES_SHORT_TO_LONG[state], "usa", "", mwh_estimate,
                str(p["mw"]), "", p["entity name"], 
                "", "", "", "", "",
                p["status_simple"], 
                "", "",
                start_operation, start_estimated, 
            ]
            print(";".join(li))
            start_id += 1


    
def main():
    
    # 1) Load an prepare data
    csv_projects = load_file("projects.csv")
    eia_data = stats_eia_data()
    projects = []
    for p in csv_projects:
        # skip for an empty row (sometimes the case at the end)
        if p["name"] == "":
            continue

        gov = None
        if p["country"] == "usa" and p["external_id"]:
            gov = eia_data["projects"][p["external_id"]]

        projects.append(BatteryProject(p, gov))

    tesla_projects = [p for p in projects if p.is_tesla]
    
    # 2) Generate the pages
    gen_projects_template(tesla_projects, 'index.jinja.html')
    gen_projects_template(projects, 'all-big-batteries.jinja.html')
    gen_individual_pages(projects)
    gen_eia_page(eia_data, projects)
    gen_raw_data_files()
    gen_blog()

    ajax_data = {
        "project_length": {
            "tesla_str": "(%d)" % len(tesla_projects),
            "all_str": "(%d)" % len(projects),
        },
        # TODO: can move the static site generated at into here also
        # "generated_at": 
    }
    # load some data via ajax to keep the commit history of the individual project html files cleaner
    with open("docs/ajax-data.json", "w") as f:
        json.dump(ajax_data, f)

    # this does not have to be run every time, just for manual assignment
    # match_eia_projects_with_mpt_projects(eia_data, projects)


if __name__ == "__main__":
    # to download a new report, need to enable those two lines and make sure the month is correct
    # download_and_extract_eia_data()
    # read_eia_data_all_months()
    main()

    
