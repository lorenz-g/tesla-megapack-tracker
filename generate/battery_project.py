from dataclasses import asdict, dataclass
import copy
import sys
import math

from generate.utils import COUNTRY_EMOJI_DI, US_STATES_TO_EIA_COORDINATES

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
        ["📏", "📏", "mwh estimate based on mw"],
    ]

# in case the state does not have default coords
EIA_COORDS_USA = (39.613588, -101.337891)

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
    radius = (int(id_/10) - 13) * scaling_factor
    angle = (id_ % 10) / 10 * 2 * math.pi

    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    return str(coords[0] + y), str(coords[1] + x) 







# good link about dataclasses
@dataclass
class CsvProjectData:
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
    coords_exact: str
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

    def __init__(self, csv_di, gov):
        pass
        # the dict from the projects.csv file and turn into dataclass for type hints
        csv = CsvProjectData(**csv_di)
        
        # government data dict
        self.gov = gov

        self.status = csv.status
        assert self.status in VALID_STATUS, "status is not valid '%s' - %s" % (self.status, csv_di['name'])

        self.status_class = "badge rounded-pill bg-success" if self.status == "operation" else ""
        notes_split = csv.notes.split("**")
        
        # merge the start operation and estimated start here
        if csv.start_operation:
            self.go_live = csv.start_operation
            self.go_live_year_int = int(self.go_live[:4])
        elif csv.start_estimated:
            self.go_live = "0 ~  " + csv.start_estimated
            self.go_live_year_int = int(csv.start_estimated[:4])
        else:
            self.go_live = ""
            self.go_live_year_int = None

        
        self.mw = csv_int(csv.power_mw)
        # include the estimate here
        self.mwh = csv_int(csv.capacity_mwh)
        self.mwh_is_estimate = False

        # TODO: add an emoji for estimate
        if self.mwh == 0 and csv_int(csv.estimate_mwh) > 0:
            self.mwh = csv_int(csv.estimate_mwh)
            self.mwh_is_estimate = True
            
        self.no_of_battery_units = csv_int(csv.no_of_battery_units)

        # coordinate overwrites
        if csv.overwrite == "1" and csv.lat == "":
            self.lat, self.long = eia_location_estimate(csv.id, csv.state)
            self.coords_exact = "0"
        else:
            self.lat = csv.lat
            self.long = csv.long
            self.coords_exact = csv.coords_exact

        # https://stackoverflow.com/questions/2660201/what-parameters-should-i-use-in-a-google-maps-url-to-go-to-a-lat-lon
        # zoom z=20 is the maximum, but not sure if it is working
        # TODO: I think this google maps link format is old https://developers.google.com/maps/documentation/urls/get-started
        self.google_maps_link = "http://maps.google.com/maps?z=19&t=k&q=loc:%s+%s" % (self.lat, self.long)


        emojis = []        
        # the order in which the if cases happen matters as that is the order of the emojis
        if self.coords_exact != "1":
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
        
        if self.mwh_is_estimate:
            emojis.append("📏")
            
        self.emojis = "".join(emojis)

        self.flag = COUNTRY_EMOJI_DI.get(csv.country, csv.country)
        
        self.links = [csv.link1, csv.link2, csv.link3, csv.link4]
        self.links = [l for l in self.links if l != ""]

        


        
        self.csv = csv


        # some helper variables
        self.in_operation = self.status == "operation"
        self.in_construction = self.status == "construction"
        self.in_planning = self.status == "planning"

        self.is_tesla = self.csv.manufacturer == "tesla"
        self.is_megapack = self.csv.type == "megapack"


    def __repr__(self) -> str:
        return "<BatteryProject %s - %s>" % (self.csv.id, self.csv.name)


    def to_dict(self):
        # need this detour aus the dataclass does not automatically convert to json
        # as vars returns the __dict__ of the class, the deepcopy here is very important
        di = copy.deepcopy(vars(self))
        di["csv"] = copy.deepcopy(asdict(self.csv))
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


        