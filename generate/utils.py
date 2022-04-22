from dataclasses import dataclass
import datetime as dt

# when using links need to prefix that everywhere
# for github pages
BASE_URL = "/tesla-megapack-tracker/"
# locally
# BASE_URL = "/"

def generate_link(ip):
    return BASE_URL + ip.lstrip("/")

# common dataclass for all government projects
@dataclass
class GovShortData:
    # non default arguments
    data_source: str
    name: str
    external_id: str
    state: str
    country: str
    mwh: int
    estimate_mwh: int
    power_mw: int
    owner: str
    status: str
    date_first_heard: str
    start_construction: str
    start_operation: str
    start_estimated: str
    
    # default arguments (need be be after the default arguments)
    lat: str = ""
    long: str = ""
    coords_hint: int = 0 # check the COORDS_EXACT_DICT for the values
    has_multiple_projects: bool = False
    pr_url: str = ""


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
        if k == 'status_simple' and new[k] == "operation":
            # celebrate
            extra = "🍾 🎉 🍸"

        if k == 'status_simple' and new[k] == "construction":
            extra = "🏗️"

        if new[k] != v:
            li.append({
                "name": k,
                "from": v,
                "to": new[k],
                "extra": extra,
            })
    return li



def diff_month(d1, d2):
    # from https://stackoverflow.com/questions/4039879/best-way-to-find-the-months-between-two-dates
    return (d1.year - d2.year) * 12 + d1.month - d2.month


def construction_time(start_construction: str, start_operation: str):
    # for now the input is strings
    if start_construction == "" or start_operation == "":
        return None
    
    if len(start_construction) == 7:
        format = '%Y-%m'
    else:
        format = '%Y-%m-%d'
    start_c = dt.datetime.strptime(start_construction, format)

    if len(start_operation) == 7:
        format = '%Y-%m'
    else:
        format = '%Y-%m-%d'
    start_o = dt.datetime.strptime(start_operation, format)

    return diff_month(start_o, start_c)
    