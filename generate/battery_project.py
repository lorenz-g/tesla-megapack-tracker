from dataclasses import asdict, dataclass
import copy
import sys
import math
import logging

from generate.constants import COUNTRY_EMOJI_DI, US_STATES_TO_EIA_COORDINATES
from generate.utils import GovShortData, construction_time

l = logging.getLogger("battery_project")


VALID_STATUS = ("planning", "construction", "operation")

USE_CASE_EMOJI_LI = [
        # these just used for the legend
        ["📍", "📍", "location not exactly known"],
        ["⚡", "⚡", "more than 100 MWh"],
        ["❤️", "❤️", "more than 1000 MWh / 1GWh"],
        # below for legend and use case
        ["solar", "☀️", "attached to solar farm"],
        ["wind", "🌬️", "attached to wind farm"],
        ["island", "🏝️", "island installation"],
        ["bus", "🚌", "at bus depot"],
        ["ev", "🚗", "EV charging support"],
        # these just used for the legend
        ["🚨", "🚨", "incident reported"],
        ["🐌", "🐌", "slow, bureaucracy"],
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
    2: "📍 The site is known, coords are +/- 1 kilometer",
    3: "📍 Coords are a guess. Only the city is known",
}



def project_is_slow(go_live, mwh, mw):
    """ Any project that is going live in 2025 or later and that has less than 1GW / 1GWh is slow
    Might have to change that function in the future. 

    >>> project_is_slow(2025, 0, 200)
    True
    >>> project_is_slow(2025, 0, 1200)
    False
    >>> project_is_slow(2023, 0, 200)
    False
    """
    if go_live and go_live >= 2025:
        if not (mwh >= 1000 or mw >=1000):
            return True
    return False


def format_short_name(name, limit=25):
    """
    >>> format_short_name("hello bla")
    """
    if len(name) > limit:
        # todo
        # # what to extend until the next whitespace
        # extend = name[limit:]
        # extend = extend[:extend.index(" ")]
        extend = ""

        name_short = name[:limit] +  extend + "..."
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
    """ based on the id, we want to create the same coordinates every time

    x = r(cos(degrees)), y = r(sin(degrees))

    the ids start at around 140 (which is why 13 is subtracted below)
    """
    id_ = int(id_)

    coords = US_STATES_TO_EIA_COORDINATES[state] 
    if not coords:
        print("no coordinates for state:", state)
        coords = EIA_COORDS_USA
    
    scaling_factor = 0.02
    radius = (id_ % 10 + (id_ % 100) / 10) * scaling_factor
    angle = (id_ % 20) / 20 * 2 * math.pi

    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    return str(coords[0] + y), str(coords[1] + x) 


# good link about dataclasses
@dataclass
class CsvProjectData:
    """
    Data that is collected manually by users (and sometimes filled with gov data)
    """
    name: str
    city: str
    id: str
    external_id: str
    overwrite: str
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
    # for the time being, there are two, but will be 1 again soon
    coords_hint: str
    coords_hint_2: str
    use_case: str
    notes: str
    project_website: str
    link1: str
    link2: str
    link3: str
    link4: str


class BatteryProject:
    """ Class for a project to add helper and styling functions 
    that make it easier to work with the projects

    not sure whether to create attributes for mw and mwh..

    can use vars(BatteryProject) to turn it into a dict, very handy. 

    TODO: don't expose the csv file (all attributes should be in this class)
    TODO: add the construction start for the EIA projects
    TODO: add identifier for location of the EIA projects
    TODO: check for the EIA data if the data is correct in the CSV sheet (and have a function to correct the data)

    """

    def __init__(self, csv_di, gov: GovShortData, gov_history):
        pass
        # the dict from the projects.csv file and turn into dataclass for type hints
        csv = CsvProjectData(**csv_di)
        self.internal_id = csv.id
        
        # government data dict
        self.gov = gov
        self.gov_history = gov_history
        self.has_gov_data = bool(gov)

        # mwh is a special case as it always comes from CSV (and might be overwritten by an estimate)
        self.mwh = csv_int(csv.capacity_mwh)
        self.mwh_is_estimate = False

        # TODO: don't use either or here, but just pick gov first and if it is not set, then pick the csv second (only relevant were manual data was filled in)
        # in that pick first function can print the the differences...
        # TODO: also add an emoji for manual data (i.e. if the project website or link is filled)
        # merge the government data        
        # TODO: if the coords are exact then use the user data (e.g. burwell in the uk)
        # if gov and csv.overwrite == "1":
        if gov:
            self.status = gov.status
            self.external_id = gov.external_id

            self.date_first_heard = gov.date_first_heard
            self.start_construction = gov.start_construction
            self.start_operation = gov.start_operation
            self.start_estimated = gov.start_estimated

            self.owner = gov.owner
            self.name = gov.name
            self.state = gov.state
            self.country = gov.country
            self.mw = gov.power_mw

            # TODO: not sure why the cast to int is needed here as it should only arrive as int by the dataclass
            mwh_estimate = csv_int(gov.estimate_mwh)

            # for germnay we get mwh
            if self.country == "germany":
                self.mwh = gov.mwh
        else:
            self.status = csv.status
            self.external_id = ""

            self.date_first_heard = csv.date_first_heard    
            self.start_construction = csv.start_construction
            self.start_operation = csv.start_operation
            self.start_estimated = csv.start_estimated

            self.owner = csv.owner
            self.name = csv.name
            self.state = csv.state
            self.country = csv.country
            self.mw = csv_int(csv.power_mw)

            mwh_estimate = csv_int(csv.estimate_mwh)
        
        
        if self.mwh == 0 and mwh_estimate > 0:
            self.mwh = mwh_estimate
            self.mwh_is_estimate = True


        assert self.status in VALID_STATUS, "status is not valid '%s' - %s" % (self.status, csv_di['name'])

        self.name_short = format_short_name(self.name)


        self.status_class = "badge rounded-pill bg-success" if self.status == "operation" else ""
        self.notes_split = csv.notes.split("**")

        self.in_operation = self.status == "operation"
        self.in_construction = self.status == "construction"
        self.in_planning = self.status == "planning"
        
        # merge the start operation and estimated start here
        # TODO: should have an indication where the data is coming from
        if self.start_operation:
            self.go_live = self.start_operation
            self.go_live_year_int = int(self.go_live[:4])
        elif self.start_estimated:
            self.go_live = "0 ~  " + self.start_estimated
            self.go_live_year_int = int(self.start_estimated[:4])
        else:
            self.go_live = ""
            self.go_live_year_int = None

        self.construction_time_month = construction_time(self.start_construction, self.start_operation)
        # TODO: there are some that are negative, look at them again
        self.construction_speed_mwh_per_month = int(self.mwh / self.construction_time_month) if self.construction_time_month else None

        self.no_of_battery_units = csv_int(csv.no_of_battery_units)

        self.lat = ""
        self.long = ""
        self.coords_hint = -2 
        
        if gov:
            if self.country == "usa":
                self.lat, self.long = eia_location_estimate(csv.id, gov.state)
            elif self.country in ("uk", "germany"):
                self.lat = gov.lat
                self.long = gov.long
            
            self.coords_hint = gov.coords_hint
        
        # for now, overwrite with user data if it exists (TODO: more finegrained overwrites here ust coords_hint)
        if csv.lat != "" and self.country != "germany":
            self.lat = csv.lat
            self.long = csv.long
            self.coords_hint = csv_int(csv.coords_hint)
        
        self.coords_exact = True if self.coords_hint == 1 else False
        self.coords_help_str = COORDS_HINT_DICT[self.coords_hint]

        # https://stackoverflow.com/questions/2660201/what-parameters-should-i-use-in-a-google-maps-url-to-go-to-a-lat-lon
        # zoom z=20 is the maximum, but not sure if it is working
        # TODO: I think this google maps link format is old https://developers.google.com/maps/documentation/urls/get-started
        self.google_maps_link = "http://maps.google.com/maps?z=19&t=k&q=loc:%s+%s" % (self.lat, self.long)

        self.links = [csv.link1, csv.link2, csv.link3, csv.link4]
        self.links = [l for l in self.links if l != ""]
        # can assume that when a link is there some user data was added
        self.user_data = bool(len(self.links) > 0) or csv.project_website != ""

        if gov and gov.pr_url:
            self.links.append(gov.pr_url)


        emojis = []        
        # the order in which the if cases happen matters as that is the order of the emojis
        if not self.coords_exact:
            emojis.append("📍")
        
        # add both heart and ⚡ for 1gwh projects so if you search for the ⚡ the massive ones will show up also
        if self.mwh >= 1000 or self.mw >= 1000:
            emojis.append("❤️")
        if self.mwh >= 100 or self.mw >= 100:
            emojis.append("⚡")

        use_case_lower = csv.use_case.lower()
        for keyword, emoji, _ in USE_CASE_EMOJI_LI:
            if keyword in use_case_lower:
                emojis.append(emoji)

        if "incident" in csv.notes.lower():
            emojis.append("🚨")

        if project_is_slow(self.go_live_year_int, self.mwh, self.mw):
            emojis.append("🐌")
        
        if csv.external_id:
            emojis.append("📊")

        if self.user_data:
            emojis.append("👤")
        
        if self.mwh_is_estimate:
            emojis.append("📏")
            
        self.emojis = "".join(emojis)

        self.flag = COUNTRY_EMOJI_DI.get(csv.country, csv.country)
        
        
        
        self.csv = csv

        # some helper variables
        self.is_tesla = self.csv.manufacturer == "tesla"
        self.is_megapack = self.csv.type == "megapack"


    def __repr__(self) -> str:
        e_id = self.gov.external_id if self.gov else ""
        return "<BatteryProject %s / %s - %s>" % (self.csv.id, e_id, self.csv.name)


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


    def data_check(self):
        """TODO: check between csv and gov data"""
        pass

    
@dataclass
class Test:
    test: int



if __name__ == "__main__":
    import json
    test = Test(**{"test": 23})
    print(test)
    print(asdict(test))
    print(type(test))


        