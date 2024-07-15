import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List

# when using links need to prefix that everywhere
# for github pages
BASE_URL = "/tesla-megapack-tracker/"
# locally
# BASE_URL = "/"


def pick_first(first, second):
    "pickt the first acceptable value"
    if first not in (None, ""):
        return first
    else:
        return second


def find_duplicates(lst):
    # from chat gpt
    seen = set()
    duplicates = set(x for x in lst if x in seen or seen.add(x))
    return sorted(list(duplicates))


def generate_link(ip):
    return BASE_URL + ip.lstrip("/")


def date_to_quarter(ip):
    """
    >>> date_to_quarter("2022-12")
    '2022-Q4'

    >>> date_to_quarter(dt.date(2022, 12, 12))
    '2022-Q4'

    """
    if type(ip) == str:
        ip = dt.datetime.strptime(ip, "%Y-%m").date()

    return "%d-Q%d" % (ip.year, int(ip.month / 4) + 1)


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
    # TODO: probably good to add last heard of here
    date_first_heard: str
    start_construction: str
    start_operation: str
    start_estimated: str
    month_disappeared: str = ""

    # default arguments (need be be after the default arguments)
    lat: str = ""
    long: str = ""
    coords_hint: int = 0  # check the COORDS_EXACT_DICT for the values
    has_multiple_projects: bool = False
    pr_url: str = ""


@dataclass
class GovMonthlyChanges:
    month: str
    new: list[dict] = field(default_factory=list)
    disappeared: list[dict] = field(default_factory=list)

    updated_timing: list[list] = field(default_factory=list)
    updated_status: list[list] = field(default_factory=list)
    updated_misc: list[list] = field(default_factory=list)

    count_updated_projects: int = 0

    def sort_lists_by_descending_mw(self):
        self.new = sorted(self.new, key=lambda x: x["mw"], reverse=True)
        self.disappeared = sorted(self.disappeared, key=lambda x: x["mw"], reverse=True)

        # careful about the extra x[0] in here
        self.updated_timing = sorted(
            self.updated_timing, key=lambda x: x[0]["mw"], reverse=True
        )
        self.updated_status = sorted(
            self.updated_status, key=lambda x: x[0]["mw"], reverse=True
        )
        self.updated_misc = sorted(
            self.updated_misc, key=lambda x: x[0]["mw"], reverse=True
        )

    def add_updated_project(self, project, changes):
        if "status" in [i["change_type"] for i in changes]:
            self.updated_status.append([project, changes])
        elif "timing" in [i["change_type"] for i in changes]:
            self.updated_timing.append([project, changes])
        else:
            self.updated_misc.append([project, changes])

        self.count_updated_projects += 1

    def get_all_updated_projects(self):
        return [
            {
                "name": "Status",
                "projects": self.updated_status,
                # only this one is open on the accordion
                "collapse": "show",
                "html_id": f"acc-{self.month}-status",
            },
            {
                "name": "Timing",
                "projects": self.updated_timing,
                "collapse": "",
                "html_id": f"acc-{self.month}-timing",
            },
            {
                "name": "Other",
                "projects": self.updated_misc,
                "collapse": "",
                "html_id": f"acc-{self.month}-misc",
            },
        ]


def check_di_difference(old, new, ignore=None):
    """only focus on single level dicts and assume they have the same keys"""
    # TODO: this line is wrong, fix it eventually, but code will probably break
    assert sorted(old.keys()) == sorted(old.keys())

    if ignore is None:
        ignore = []

    li = []
    for k, v in old.items():
        if k in ignore:
            continue

        # either misc, timing or status
        change_type = "misc"
        extra = ""
        if k == "date":
            change_type = "timing"
            from_date = dt.datetime.strptime(v, "%Y-%m")
            to_date = dt.datetime.strptime(new[k], "%Y-%m")
            month_delta = (to_date.year - from_date.year) * 12 + (
                to_date.month - from_date.month
            )
            pill_bg = "danger" if month_delta > 0 else "success"
            word = "delayed" if month_delta > 0 else "accelerated"
            month = "month" if abs(month_delta) == 1 else "months"
            extra = '%s by <span class="badge rounded-pill bg-%s">%d</span> %s' % (
                word,
                pill_bg,
                abs(month_delta),
                month,
            )

        if k == "status":
            change_type = "status"
            if new[k] == "operation":
                # celebrate
                extra = "🍾 🎉 🍸"
            elif new[k] == "construction":
                extra = "🏗️"

        # had some issues with, e.g. Installed Capacity (MWelec): 40.00 -> 40
        # to prevent that just compare the int statements
        if k == "Installed Capacity (MWelec)":
            if int(float(new[k])) == int(float(v)):
                continue

        if k in new:
            if new[k] != v:
                li.append(
                    {
                        "name": k,
                        "from": v,
                        "to": new[k],
                        "extra": extra,
                        "change_type": change_type,
                    }
                )
    return li


def diff_month(d1, d2) -> int:
    # from https://stackoverflow.com/questions/4039879/best-way-to-find-the-months-between-two-dates
    return (d1.year - d2.year) * 12 + d1.month - d2.month


def construction_time(start_construction: str, start_operation: str) -> int:
    # for now the input is strings
    if start_construction == "" or start_operation == "":
        return None

    if len(start_construction) == 7:
        format = "%Y-%m"
    else:
        format = "%Y-%m-%d"
    start_c = dt.datetime.strptime(start_construction, format)

    if len(start_operation) == 7:
        format = "%Y-%m"
    else:
        format = "%Y-%m-%d"
    start_o = dt.datetime.strptime(start_operation, format)

    return diff_month(start_o, start_c)


def create_summary_for_gov_projects(projects: List[GovShortData]) -> dict:
    # generate the statistics for all the gov projects based on their status
    summary = defaultdict(lambda: {"count": 0, "gw": 0, "gwh": 0})
    for p in projects:
        summary[p.status]["count"] += 1
        summary[p.status]["gw"] += p.power_mw / 1000
        summary[p.status]["gwh"] += p.mwh / 1000

    return summary
