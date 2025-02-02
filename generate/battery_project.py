import copy
import logging
import math
from dataclasses import asdict, dataclass

import generate.constants as constants
from generate.utils import GovShortData, construction_time, pick_first

l = logging.getLogger("battery_project")


VALID_STATUS = ("planning", "construction", "operation", "cancelled")

STATUS_CLASS_DI = {
    "operation": "badge rounded-pill bg-success",
    "construction": "badge rounded-pill bg-secondary",
    "cancelled": "badge rounded-pill bg-danger",
}


USE_CASE_EMOJI_LI = [
    # these just used for the legend
    ["📍", "📍", "location not exactly known"],
    ["❤️", "❤️", "more than 1000 MWh / 1GWh"],
    # these just used for the legend
    ["📊", "📊", "government data available"],
    ["👤", "👤", "user data available"],
    ["📏", "📏", "mwh estimate based on mw"],
]

# in case the state does not have default coords
EIA_COORDS_USA = (39.613588, -101.337891)


# TODO: would be good to get them into an ascending order so one could just compare to integers and
# the bigger one means it is more exact...
# TODO: create an enum for the integers
# use words in the csv, otherwise this is not easy. And use those names in the csv, much easier...
# e.g. country_known, state_known, city_known, site_know_1km, location_exact_50m,

# country
# state
# city_region  # city or region is known (+= 20km)
# location (+- 1km)
# location_exact (+- 50m)

COORDS_HINT_DICT = {
    -2: "📍 Coords are a guess. Only the country is known",
    -1: "📍 Coords are a guess. Only the state is known",
    0: "📍 Coords not known",
    1: "✅ Coords are exact (+/- 50m)",
    2: "✅ The site is known, coords are +/- 1 kilometer",
    3: "📍 Coords are a guess. Only the city or county is known",
}

# tesla project in construction or operation should have either of the following coords hints
COORDS_HINTS_GOOD_FOR_TESLA_PROJECTS = [1, 2, 3]


def tooltip_for_emoji(emoji_input):
    for _, emoji, text in USE_CASE_EMOJI_LI:
        if emoji == emoji_input:
            return (
                '<span data-toggle="tooltip" data-placement="top" title="%s">%s</span>'
                % (text, emoji)
            )
    raise ValueError("%s emoji not found" % emoji_input)


def format_short_name(name, limit=35):
    """
    >>> format_short_name("hello bla")
    """

    # for the mobile view, get rid of some common endings that don't add much
    # start with more words at the top as the loop breaks when sth is found
    strip_endings = [
        "battery energy storage",
        "energy storage project",
        "energy storage hybrid",
        "energy storage system",
        "battery storage facility",
        "storage facility",
        "energy storage",
        "energy center",
        "battery storage",
        "power plant",
        "project hybrid",
        "energy",
        "storage",
        "project",
        "power",
        ", llc hybrid",
        ", llc",
        "llc",
        "hybrid",
        "bess",
    ]
    for strip_ending in strip_endings:
        if name.lower().endswith(strip_ending):
            name = name[: -len(strip_ending)]
            # strip spaces or hyphens and ` and`
            name = name.rstrip(" -")

            if name.endswith(" and"):
                name = name[:-4]

            break

    if len(name) > limit:
        # todo
        # # what to extend until the next whitespace
        # extend = name[limit:]
        # extend = extend[:extend.index(" ")]
        extend = ""

        name_short = name[:limit] + extend + "..."
    else:
        name_short = name

    return name_short


def csv_int(ip):
    # TODO: enable that again if data is clean...
    # if "." in ip:
    #     raise ValueError("only integer allowed, got", ip)

    # and remove the float here again.
    return 0 if ip == "" else int(float(ip))


def eia_location_estimate(id_, state):
    """based on the id, we want to create the same coordinates every time

    x = r(cos(degrees)), y = r(sin(degrees))

    the ids start at around 140 (which is why 13 is subtracted below)
    """
    id_ = int(id_)

    coords = constants.US_STATES_TO_EIA_COORDINATES[state]
    if not coords:
        print("no coordinates for state:", state)
        coords = EIA_COORDS_USA

    scaling_factor = 0.02
    radius = (id_ % 10 + (id_ % 100) / 10) * scaling_factor
    angle = (id_ % 20) / 20 * 2 * math.pi

    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    return str(coords[0] + y), str(coords[1] + x)


@dataclass
class CsvProjectData:
    """
    Data that is collected manually by users (and sometimes filled with gov data)
    """

    name: str
    city: str
    id: str
    external_id: str
    state: str
    country: str
    capacity_mwh: str
    estimate_mwh: str
    power_mw: str
    customer: str
    owner: str
    developer: str
    manufacturer: str
    type: str
    cells: str
    no_of_battery_units: str
    status: str
    date_first_heard: str
    start_construction: str
    start_operation: str
    start_estimated: str
    cost_million: str
    cost_currency: str
    cost_incl_solar: str
    lat: str
    long: str
    coords_hint: str
    use_case: str
    notes: str
    project_website: str
    link1: str
    link2: str
    link3: str
    link4: str


@dataclass
class BatteryProject:
    """All the info about a project in a single dataclass"""

    csv: CsvProjectData
    internal_id: str
    external_id: str

    has_user_data: bool
    has_gov_data: bool
    gov: GovShortData | None
    gov_history: dict | None

    mw: int
    mwh_is_estimate: bool
    mwh: int
    mwh_estimate: int

    status: str
    status_class: str

    date_first_heard: str
    start_construction: str
    start_operation: str
    start_estimated: str
    month_disappeared: str
    go_live: str
    go_live_year_int: int

    name: str
    name_short: str
    owner: str
    state: str
    country: str
    lat: str
    long: str
    coords_hint: int
    coords_exact: bool
    coords_help_str: str

    emojis: str
    emojis_with_tooltips: str
    heart_tooltip: str
    google_maps_link: str

    construction_time_month: int
    construction_speed_mwh_per_month: int
    no_of_battery_units: int
    notes_split: list
    links: list
    in_operation: bool
    in_construction: bool
    in_planning: bool

    is_active: bool
    is_tesla: bool
    is_megapack: bool

    def __repr__(self) -> str:
        e_id = self.gov.external_id if self.gov else ""
        return "<BatteryProject %s / %s - %s>" % (self.csv.id, e_id, self.csv.name)

    @property
    def flag(self):
        try:
            return constants.COUNTRY_EMOJI_DI[self.country]
        except KeyError:
            raise KeyError(
                "could not find flag for project: %s %s country: %s"
                % (self.internal_id, self.name, self.country)
            )

    @property
    def state_short(self):
        if self.country == "usa":
            return constants.US_STATES_LONG_TO_SHORT.get(self.state, "")
        elif self.country == "australia":
            return constants.AUSTRALIA_STATES_LONG_TO_SHORT.get(self.state, "")
        else:
            return ""

    def to_dict(self):
        # need this detour aus the dataclass does not automatically convert to json
        # as vars returns the __dict__ of the class, the deepcopy here is very important
        di = copy.deepcopy(vars(self))
        di["csv"] = copy.deepcopy(asdict(self.csv))
        if self.gov:
            di["gov"] = copy.deepcopy(asdict(self.gov))
        else:
            di["gov"] = {}
        return di
    
    def to_csv_row(self):
        """ this is the merged data from the user (the project.csv) and the government data"""
        li = [
            self.csv.id,
            self.name,
            self.external_id,
            self.state,
            self.country,
            self.mw,
            self.mwh,
            self.status,
            self.date_first_heard,
            self.start_construction,
            self.start_operation,
            self.start_estimated,
            self.owner,
            self.is_megapack,
            self.is_tesla,
            self.lat,
            self.long,
            self.coords_hint,
            self.has_user_data,
            self.csv.project_website,
            self.csv.link1,
            self.csv.link2,
            self.csv.link3,
            self.csv.link4,
        ]
        return [str(i) for i in li]
    
    @staticmethod
    def csv_header_row():
        return [
            "id",
            "name",
            "external_id",
            "state",
            "country",
            "mw",
            "mwh",
            "status",
            "date_first_heard",
            "start_construction",
            "start_operation",
            "start_estimated",
            "owner",
            "is_megapack",
            "is_tesla",
            "lat",
            "long",
            "coords_hint",
            "has_user_data",
            "project_website",
            "link1",
            "link2",
            "link3",
            "link4",
        ]



def csv_data_checks(p: CsvProjectData):

    messages = []
    if p.lat and not p.long:
        messages.append("lat is set but long is not")

    if p.status not in VALID_STATUS:
        messages.append(f"status is not valid '{p.status}'")

    if messages:
        print(f"{p.name} ({p.id})")
        for m in messages:
            print(f"  {m}")


def setup_battery_project(csv_di, gov: GovShortData, gov_history) -> BatteryProject:
    """helper function to create the battery project"""

    # the dict from the projects.csv file and turn into dataclass for type hints
    csv = CsvProjectData(**csv_di)
    # to help spot errors in the csv data quickly
    csv_data_checks(csv)

    internal_id = csv.id
    has_gov_data = bool(gov)

    # mwh is a special case as it always comes from CSV (and might be overwritten by an estimate)
    mwh = csv_int(csv.capacity_mwh)
    mwh_is_estimate = False

    if gov:
        external_id = gov.external_id
        status = gov.status
        # in case the government data did not catch up fast enough, can set the data from the CSV here instead
        if csv.status == "operation" and gov.status in ("planning", "construction"):
            status = csv.status

        # in case we do have info in the csv and not in the gov data, we use it.
        date_first_heard = pick_first(gov.date_first_heard, csv.date_first_heard)
        start_construction = pick_first(gov.start_construction, csv.start_construction)
        start_operation = pick_first(gov.start_operation, csv.start_operation)
        start_estimated = pick_first(gov.start_estimated, csv.start_estimated)

        month_disappeared = gov.month_disappeared
        owner = pick_first(gov.owner, csv.owner)
        name = gov.name
        state = gov.state
        country = gov.country
        mw = gov.power_mw
        mwh_estimate = csv_int(gov.estimate_mwh)

        # for Germany we get mwh
        if country == "germany":
            mwh = gov.mwh
    else:
        external_id = ""
        status = csv.status
        date_first_heard = csv.date_first_heard
        start_construction = csv.start_construction
        start_operation = csv.start_operation
        start_estimated = csv.start_estimated
        month_disappeared = ""

        owner = csv.owner
        name = csv.name
        state = csv.state
        country = csv.country
        mw = csv_int(csv.power_mw)
        mwh_estimate = csv_int(csv.estimate_mwh)

    if mwh == 0 and mwh_estimate > 0:
        mwh = mwh_estimate
        mwh_is_estimate = True

    assert status in VALID_STATUS, "status is not valid '%s' - %s" % (
        status,
        csv.name,
    )

    name_short = format_short_name(name)

    status_class = STATUS_CLASS_DI.get(status, "")
    notes_split = csv.notes.split("**")

    in_operation = status == "operation"
    in_construction = status == "construction"
    in_planning = status == "planning"

    # merge the start operation and estimated start here
    # only show year and month
    if start_operation:
        go_live = start_operation[:7]
        go_live_year_int = int(go_live[:4])
    elif start_estimated:
        go_live = "0 ~  " + start_estimated[:7]
        go_live_year_int = int(start_estimated[:4])
    else:
        go_live = ""
        go_live_year_int = None

    construction_time_month = construction_time(start_construction, start_operation)
    # TODO: there are some that are negative, look at them again
    construction_speed_mwh_per_month = (
        int(mwh / construction_time_month) if construction_time_month else None
    )

    no_of_battery_units = csv_int(csv.no_of_battery_units)

    if gov:
        if country == "usa":
            lat, long = eia_location_estimate(csv.id, gov.state)
            coords_hint = gov.coords_hint
            # for the USA gov data, use the csv it it exists
            if csv.lat != "":
                lat = csv.lat
                long = csv.long
                coords_hint = csv_int(csv.coords_hint)
        else:
            lat = gov.lat
            long = gov.long
            coords_hint = gov.coords_hint
    else:
        lat = csv.lat
        long = csv.long
        coords_hint = csv_int(csv.coords_hint)

    coords_exact = True if coords_hint in (1, 2) else False
    coords_help_str = COORDS_HINT_DICT[coords_hint]

    # https://stackoverflow.com/questions/2660201/what-parameters-should-i-use-in-a-google-maps-url-to-go-to-a-lat-lon
    # zoom z=20 is the maximum, but not sure if it is working
    # TODO: I think this google maps link format is old https://developers.google.com/maps/documentation/urls/get-started
    google_maps_link = "http://maps.google.com/maps?z=19&t=k&q=loc:%s+%s" % (
        lat,
        long,
    )

    links = [csv.link1, csv.link2, csv.link3, csv.link4]
    links = [l for l in links if l != ""]
    # can assume that when a link is there some user data was added
    has_user_data = bool(len(links) > 0) or csv.project_website != ""

    if gov and gov.pr_url:
        links.append(gov.pr_url)

    emojis = []
    # the order in which the if cases happen matters as that is the order of the emojis
    if not coords_exact:
        emojis.append("📍")

    # add both heart for GWh projects
    heart_tooltip = ""
    if mwh >= 1000 or mw >= 1000:
        emojis.append("❤️")
        heart_tooltip = tooltip_for_emoji("❤️")

    if csv.external_id:
        emojis.append("📊")

    if has_user_data:
        emojis.append("👤")

    if mwh_is_estimate:
        emojis.append("📏")

    emojis_with_tooltips = "".join([tooltip_for_emoji(e) for e in emojis])

    is_tesla = csv.manufacturer == "tesla"

    if is_tesla:
        if mwh_is_estimate and in_operation and mw > 20:
            print(
                f"project <{internal_id} / {name_short}> is_tesla "
                "and mwh_is_estimate and in_operation -> should research proper mwh value"
            )

        if (
            in_operation
            and coords_hint not in COORDS_HINTS_GOOD_FOR_TESLA_PROJECTS
            and mw > 20
        ):
            # TODO: maybe add in_construction here as well
            print(
                f"project <{internal_id} / {name_short}> is_tesla and in_operation and "
                "coords_hint not in COORDS_HINTS_GOOD_FOR_TESLA_PROJECTS -> should research the some better coords"
            )

    return BatteryProject(
        csv=csv,
        internal_id=internal_id,
        external_id=external_id,
        has_gov_data=has_gov_data,
        has_user_data=has_user_data,
        gov=gov,
        gov_history=gov_history,
        mw=mw,
        mwh_is_estimate=mwh_is_estimate,
        mwh=mwh,
        mwh_estimate=mwh_estimate,
        status=status,
        status_class=status_class,
        date_first_heard=date_first_heard,
        start_construction=start_construction,
        start_operation=start_operation,
        start_estimated=start_estimated,
        month_disappeared=month_disappeared,
        go_live=go_live,
        name=name,
        name_short=name_short,
        owner=owner,
        state=state,
        country=country,
        lat=lat,
        long=long,
        coords_hint=coords_hint,
        coords_exact=coords_exact,
        coords_help_str=coords_help_str,
        emojis="".join(emojis),
        emojis_with_tooltips=emojis_with_tooltips,
        google_maps_link=google_maps_link,
        construction_time_month=construction_time_month,
        construction_speed_mwh_per_month=construction_speed_mwh_per_month,
        no_of_battery_units=no_of_battery_units,
        notes_split=notes_split,
        links=links,
        in_operation=in_operation,
        in_construction=in_construction,
        in_planning=in_planning,
        go_live_year_int=go_live_year_int,
        is_active=status != "cancelled",
        is_tesla=is_tesla,
        is_megapack="megapack" in csv.type.lower(),
        heart_tooltip=heart_tooltip,
    )
