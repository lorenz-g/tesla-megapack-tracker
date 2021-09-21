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

VALID_STATUS = ("planning", "construction", "operation")

COUNTRY_EMOJI_DI = {
    "usa": "🇺🇸", 
    "australia": "🇦🇺",
    "uk": "🇬🇧",
    "korea": "🇰🇷",
    "philippines": "🇵🇭",
    "germany": "🇩🇪",
    "france": "🇫🇷",
}




def generate_link(ip):
    return BASE_URL + ip.lstrip("/")



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


def prepare_projects(projects):
    
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

    use_case_emoji_li = [
        # these just used for the legend
        ["📍", "📍", "location not exactly known"],
        ["⚡", "⚡", "more than 100 MWh"],
        # below for legend and use case
        ["solar", "☀️", "attached to solar farm"],
        ["wind", "🌬️", "attached to wind farm"],
        ["island", "🏝️", "island installation"],
        ["bus", "🚌", "at bus depot"],
        ["ev", "🚗", "EV charging support"],
        # these just used for the legend
        ["🚨", "🚨", "incident reported"],
    ]

    emoji_legend = []
    for _, emoji, explanation in use_case_emoji_li:
        emoji_legend.append("%s %s" % (emoji, explanation))
    emoji_legend = ", ".join(emoji_legend)


    # augment raw projects data
    for p in projects:

        # some error checks first
        
        # skip for an empty row (sometimes the case at the end)
        if p["name"] == "":
            continue

        status = p["status"]
        assert status in VALID_STATUS, "status is not valid '%s' - %s" % (status, p['name'])

        p["status_class"] = "badge rounded-pill bg-success" if status == "operation" else ""
        p["notes_split"] = p["notes"].split("**")
        
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

        
        # the order in which the if cases happen matters as that is the order of the emojis
        if p["coords exact"] != "1":
            smileys.append("📍")
        
        if mwh >= 100:
            smileys.append("⚡")

        use_case_lower = p["use case"].lower()
        for keyword, emoji, _ in use_case_emoji_li:
            if keyword in use_case_lower:
                smileys.append(emoji)

        if "incident" in p["notes"].lower():
            smileys.append("🚨")
            
        p["smileys"] = "".join(smileys)


        # add to summary
        if status == "operation" and p["type"] == "megapack":
            s_megapack["project_cnt"] += 1
            s_megapack["mp_count"] +=  0 if p["no of battery units"] == "" else int(p["no of battery units"])
            s_megapack["gwh"] += mwh / 1000
        

        if status not in s_by_status:
            s_by_status[status] = {"count": 0, "gwh":0, "gw":0}
        
        s_by_status[status]["count"] += 1
        s_by_status[status]["gwh"] += mwh / 1000
        s_by_status[status]["gw"] += 0 if p["power mw"] == "" else float(p["power mw"]) / 1000

        if status == "operation":
            year = p["start operation"][:4]
            if year not in s_yearly_op:
                s_yearly_op[year] = {"year": year, "gwh": 0, "perc": None}
            s_yearly_op[year]["gwh"] += mwh / 1000
        
        s_totals_row["count"] += 1
        s_totals_row["mwh"] += mwh
        s_totals_row["mw"] += 0 if p["power mw"] == "" else float(p["power mw"])


        if p["country"] not in s_by_country:
            s_by_country[p["country"]] = {
                "flag": COUNTRY_EMOJI_DI.get(p["country"],p["country"]), 
                "gwh":0
            }
        if status == "operation":
            s_by_country[p["country"]]["gwh"] += mwh / 1000

    
    for year in s_yearly_op.values():
        year["perc"] = 100 * year["gwh"] / s_by_status["operation"]["gwh"]
    
    s_yearly_op = sorted(s_yearly_op.values(), key=lambda x:x["year"])
    s_by_country = sorted(s_by_country.values(), key=lambda x:x["gwh"], reverse=True)

    summaries = {
        "megapack": s_megapack,
        "totals_row": s_totals_row,
        "by_status": s_by_status,
        "yearly_operation": s_yearly_op,
        "emoji_legend": emoji_legend,
        "by_country": s_by_country,
    }

    return projects, summaries




def gen_projects_template(projects, template_name, pr_len):
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    # generate the index template
    projects, summary = prepare_projects(projects)
    extra = {
        "now": dt.datetime.utcnow(),
        "cars": gen_cars_vs_stationary(projects),
        "summary": summary,
        "pr_len": pr_len,
    }

    template = env.get_template(template_name)
    output = template.render(projects=projects, extra=extra, g_l=generate_link) 
    
    with open(os.path.join(output_dir, template_name.replace(".jinja", "")), 'w') as f:
        f.write(output)
    

def gen_individual_pages(projects, pr_len):
    # generate the individual pages
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    fn = 'single.jinja.html' 
    template = env.get_template(fn)

    extra = {
        "pr_len": pr_len, 
    }

    for p in projects:
        if p["name"] == "":
            continue
        output_fn = os.path.join(output_dir, "projects", p["id"] + ".html")
        with open(output_fn, 'w') as f:
            f.write(template.render(p=p, g_l=generate_link, extra=extra))

    
def main():
    # load them twice to have different objects with different pointers
    projects = load_file("projects.csv")

    tesla_projects = load_file("projects.csv")
    tesla_projects = [r for r in tesla_projects if r["manufacturer"] == "tesla"]

    # needed for the menu in the base templat
    pr_len = {
        "tesla": len(tesla_projects),
        "all": len(projects)
    }

    gen_projects_template(tesla_projects, 'index.jinja.html', pr_len)
    gen_projects_template(projects, 'all-big-batteries.jinja.html', pr_len)
    
    gen_individual_pages(projects, pr_len)
    gen_raw_data_files()


if __name__ == "__main__":
    main()

