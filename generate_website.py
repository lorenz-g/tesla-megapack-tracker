import csv
import pprint
import os
import json
from jinja2 import Environment, FileSystemLoader
import datetime as dt

# when using links need to prefix that everywhere
# for github pages
BASE_URL = "/tesla-megapack-tracker/"
# locally
# BASE_URL = "/"


def generate_link(ip):
    return BASE_URL + ip.lstrip("/")



def load_file(type_="json", filename='projects.csv'):
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


def gen_raw_data_files():
    output_dir = os.path.join('docs', "misc")
    # write the raw data files
    with open(os.path.join(output_dir, "projects.json"), 'w') as f:
        json.dump(load_file(), f)
    
    rows = load_file("csv")
    # I think the two csv files are the same, but keep it for now.
    with open(os.path.join(output_dir, "projects.csv"), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    with open(os.path.join(output_dir, "projects.excel.csv"), 'w') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerows(rows)
        

def gen_cars_vs_stationary(projects):
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




def gen_templates(projects):
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    mp_summary = {
        "project_cnt": 0,
        "mp_count": 0,
        "gwh":0,
    }

    totals_row_summary = {
        "count": 0,
        "mwh":0,
        "mw":0,
    }

    # augment raw projects data
    for p in projects:
        p["status_class"] = "badge rounded-pill bg-success" if p["status"] == "operation" else ""
        
        # https://stackoverflow.com/questions/2660201/what-parameters-should-i-use-in-a-google-maps-url-to-go-to-a-lat-lon
        # zoom z=20 is the maximum, but not sure if it is working
        # TODO: I think this google maps link format is old https://developers.google.com/maps/documentation/urls/get-started
        p["google_maps_link"] = "http://maps.google.com/maps?z=19&t=k&q=loc:%s+%s" % (p["lat"], p["long"])
        
        smileys = []        
        try:
            mwh = float(p["capacity mwh"])
        except:
            mwh = 0
        p["mwh_int"] = mwh

        if mwh >= 100:
            smileys.append("⚡")
        
        # no else if as multiple can be true
        if "solar" in p["use case"]:
            smileys.append("☀️")
        
        if "wind" in p["use case"]:
            smileys.append("🌬️")
        
        if "island" in p["use case"]:
            smileys.append("🏝️")
        
        if "bus" in p["use case"]:
            smileys.append("🚌")

        p["smileys"] = "".join(smileys)

        # add to summary
        if p["status"] == "operation" and p["type"] == "megapack":
            mp_summary["project_cnt"] += 1
            mp_summary["mp_count"] +=  0 if p["no of megapacks"] == "" else int(p["no of megapacks"])
            mp_summary["gwh"] += mwh / 1000
        
        totals_row_summary["count"] += 1
        totals_row_summary["mwh"] += mwh
        totals_row_summary["mw"] += 0 if p["power mw"] == "" else float(p["power mw"])





    # generate the index template
    fn = 'index.jinja.html' 
    extra = {
        "now": dt.datetime.utcnow(),
        "cars": gen_cars_vs_stationary(projects),
        "mp_summary": mp_summary,
        "totals_row_summary": totals_row_summary,
    }

    template = env.get_template(fn)
    output = template.render(projects=projects, extra=extra, g_l=generate_link) 
    
    with open(os.path.join(output_dir, fn.replace(".jinja", "")), 'w') as f:
        f.write(output)
    
    # generate the individual pages
    fn = 'single.jinja.html' 
    template = env.get_template(fn)

    for p in projects:
        output_fn = os.path.join(output_dir, "projects", p["id"] + ".html")
        with open(output_fn, 'w') as f:
            f.write(template.render(p=p, extra=extra, g_l=generate_link))

    
def main():
    projects = load_file()
    gen_templates(projects)
    gen_raw_data_files()


if __name__ == "__main__":
    main()

