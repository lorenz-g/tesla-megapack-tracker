
# when using links need to prefix that everywhere
# for github pages
BASE_URL = "/tesla-megapack-tracker/"
# locally
# BASE_URL = "/"

def generate_link(ip):
    return BASE_URL + ip.lstrip("/")


VALID_STATUS = ("planning", "construction", "operation")

COUNTRY_EMOJI_DI = {
    "usa": "🇺🇸", 
    "australia": "🇦🇺",
    "uk": "🇬🇧",
    "korea": "🇰🇷",
    "philippines": "🇵🇭",
    "germany": "🇩🇪",
    "france": "🇫🇷",
    "italy": "🇮🇹",
}

US_STATES_LONG_TO_SHORT = {
    "alabama" :"AL",
    "alaska" :"AK",
    "arizona" :"AZ",
    "arkansas" :"AR",
    "california" :"CA",
    "colorado" :"CO",
    "connecticut" :"CT",
    "delaware" :"DE",
    "florida" :"FL",
    "georgia" :"GA",
    "hawaii" :"HI",
    "idaho" :"ID",
    "illinois" :"IL",
    "indiana" :"IN",
    "iowa" :"IA",
    "kansas" :"KS",
    "kentucky" :"KY",
    "louisiana" :"LA",
    "maine" :"ME",
    "maryland" :"MD",
    "massachusetts" :"MA",
    "michigan" :"MI",
    "minnesota" :"MN",
    "mississippi" :"MS",
    "missouri" :"MO",
    "montana" :"MT",
    "nebraska" :"NE",
    "nevada" :"NV",
    "new hampshire" :"NH",
    "new jersey" :"NJ",
    "new mexico" :"NM",
    "new york" :"NY",
    "north carolina" :"NC",
    "north dakota" :"ND",
    "ohio" :"OH",
    "oklahoma" :"OK",
    "oregon" :"OR",
    "pennsylvania" :"PA",
    "rhode island" :"RI",
    "south carolina" :"SC",
    "south dakota" :"SD",
    "tennessee" :"TN",
    "texas" :"TX",
    "utah" :"UT",
    "vermont" :"VT",
    "virginia" :"VA",
    "washington" :"WA",
    "west virginia" :"WV",
    "wisconsin" :"WI",
    "wyoming" :"WY",
}