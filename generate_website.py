import csv
import pprint
import os
import json
from jinja2 import Environment, FileSystemLoader
import datetime as dt

def load_projects(type_="json"):
    "For now from the csv, later from the toml fils"
    with open("projects.csv") as f:
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
        json.dump(load_projects(), f)
    
    rows = load_projects("csv")
    # I think the two csv files are the same, but keep it for now.
    with open(os.path.join(output_dir, "projects.csv"), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    with open(os.path.join(output_dir, "projects.excel.csv"), 'w') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerows(rows)
        


def gen_templates(projects):
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'

    # augment raw data

    for p in projects:
        p["status_class"] = "badge rounded-pill bg-success" if p["status"] == "operation" else ""
        smileys = []
        
        try:
            mwh = int(p["capacity mwh"])
        except:
            mwh = 0
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


    # generate the index template
    fn = 'index.jinja.html' 

    extra = {
        "now": dt.datetime.utcnow()
    }

    template = env.get_template(fn)
    output = template.render(projects=projects, extra=extra)
    
    
    
    with open(os.path.join(output_dir, fn.replace(".jinja", "")), 'w') as f:
        f.write(output)
    
    # generate the individual pages
    fn = 'single.jinja.html' 
    template = env.get_template(fn)

    for p in projects:
        output_fn = os.path.join(output_dir, "projects", p["id"] + ".html")
        with open(output_fn, 'w') as f:
            f.write(template.render(p=p))

    
    







def main():
    projects = load_projects()
    gen_templates(projects)
    gen_raw_data_files()


if __name__ == "__main__":
    main()

