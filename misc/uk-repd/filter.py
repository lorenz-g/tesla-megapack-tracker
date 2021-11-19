import csv
import pprint
from collections import defaultdict

in_filename = "original/renewable-energy-planning-database-q3-september-2021.csv"
out_filename = "filtered/2021-09.csv"

# for simplicity introducing cancelled state here but filtering it out. 
STATUS_DI = {
    "Under Construction": "construction",
    "Abandoned": "cancelled",
    "Application Submitted": "planning",
    "Application Withdrawn": "cancelled",
    "Awaiting Construction": "planning",
    "Planning Permission Expired": "cancelled",
    "Application Refused": "cancelled",
    "Operational": "operation",
}


def main():
    projects_li = []
    mw_total = 0
    i = 0

    pr_by_status = defaultdict(lambda: {"cnt": 0, "mw": 0})

    with open(in_filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            i+=1
            if row["Technology Type"].lower() != "battery":
                continue

            try:
                mw = int(float(row["Installed Capacity (MWelec)"]))
            except:
                mw = 0

            if  mw < 10:
                continue


            status = STATUS_DI[row["Development Status (short)"]]
            pr_by_status[status]["cnt"] += 1
            pr_by_status[status]["mw"] += mw
            
            if status == "cancelled":
                continue


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





if __name__ == "__main__":
    main()