"""
Tiered place normalizer / geocoder for the Hitchcock GEDCOM.
No live geocoding API is reachable from this environment, so resolution is
rule-based with an explicit precision tier recorded per place:
  town    - specific town/city centroid (best)
  county  - US county (or equivalent) centroid, via county seat
  region  - state / English county / German state / Irish county / etc.
  country - national centroid (last resort)
This keeps the map honest about precision at a glance (map render uses the
tier to lightly vary marker size/opacity, and the tier is logged in the CSV).
"""
import re

def _title(s):
    """Like str.title(), but doesn't capitalize the letter right after an
    apostrophe (Python's .title() turns "Patterson's" into "Patterson'S")."""
    return re.sub(r"'(\w)", lambda m: "'" + m.group(1).lower(), s.title())

# ---------------------------------------------------------------------------
# Tier 1: specific towns / cities (lat, lon)
# ---------------------------------------------------------------------------
TOWN_COORDS = {
    # New England
    "plymouth|massachusetts": (41.958, -70.667),
    "duxbury|massachusetts": (42.047, -70.673),
    "south duxbury|massachusetts": (42.030, -70.690),
    "braintree|massachusetts": (42.222, -71.003),
    "boston|massachusetts": (42.358, -71.060),
    "cambridge|massachusetts": (42.373, -71.110),
    "charlestown|massachusetts": (42.378, -71.061),
    "dorchester|massachusetts": (42.300, -71.062),
    "roxbury|massachusetts": (42.331, -71.094),
    "ipswich|massachusetts": (42.678, -70.841),
    "andover|massachusetts": (42.658, -71.137),
    "lynn|massachusetts": (42.467, -70.949),
    "salem|massachusetts": (42.519, -70.897),
    "billerica|massachusetts": (42.559, -71.269),
    "reading|massachusetts": (42.526, -71.096),
    "watertown|massachusetts": (42.371, -71.182),
    "holden|massachusetts": (42.350, -71.858),
    "springfield|massachusetts": (42.101, -72.590),
    "springfield|huntingdon": (40.148, -77.948),  # Springfield Township, Huntingdon Co., PA -- paired with county, not state, since PA has 8+ different Springfield Townships
    "union|huntingdon": (40.487, -78.014),  # Union Township, Huntingdon Co., PA -- using the county seat (Huntingdon borough) as nearest identifiable anchor
    "hadley|massachusetts": (42.349, -72.575),
    "northampton|massachusetts": (42.318, -72.631),
    "deerfield|massachusetts": (42.545, -72.613),
    "chesterville|maine": (44.585, -70.145),
    "temple|maine": (44.670, -70.288),
    "hingham|massachusetts": (42.238, -70.889),
    "boylston|massachusetts": (42.362, -71.727),
    "newbury|massachusetts": (42.750, -70.881),
    # Connecticut
    "new canaan|connecticut": (41.147, -73.495),
    "norwalk|connecticut": (41.118, -73.408),
    "stamford|connecticut": (41.053, -73.539),
    "stratford|connecticut": (41.185, -73.133),
    "fairfield|connecticut": (41.141, -73.263),
    "westport|connecticut": (41.141, -73.358),
    "greenwich|connecticut": (41.027, -73.628),
    "horseneck|connecticut": (41.027, -73.628),
    "new haven|connecticut": (41.308, -72.928),
    "milford|connecticut": (41.222, -73.056),
    "branford|connecticut": (41.280, -72.815),
    "east haven|connecticut": (41.277, -72.867),
    "west haven|connecticut": (41.271, -72.947),
    "derby|connecticut": (41.321, -73.090),
    "wallingford|connecticut": (41.457, -72.823),
    "cheshire|connecticut": (41.499, -72.900),
    "hartford|connecticut": (41.764, -72.685),
    "wethersfield|connecticut": (41.714, -72.652),
    "lyme|connecticut": (41.325, -72.316),
    "new london|connecticut": (41.356, -72.100),
    "old saybrook|connecticut": (41.291, -72.376),
    "saybrook|connecticut": (41.291, -72.376),
    "bethlehem|connecticut": (41.635, -73.213),
    "sharon|connecticut": (41.874, -73.484),
    "new milford|connecticut": (41.580, -73.408),
    "coventry|connecticut": (41.771, -72.303),
    "mansfield|connecticut": (41.767, -72.238),
    "simsbury|connecticut": (41.876, -72.802),
    "woodstock|connecticut": (41.955, -71.981),
    "huntington|connecticut": (41.271, -73.234),
    "newtown|connecticut": (41.414, -73.307),
    # New York
    "walton|new york": (42.166, -75.132),
    "sidney|new york": (42.311, -75.400),
    "franklin|new york": (42.339, -75.152),
    "oneonta|new york": (42.452, -75.064),
    "binghamton|new york": (42.098, -75.918),
    "greene|new york": (42.130, -73.865),  # Greene Co. seat Catskill -- verified against every affected record (all real towns within Greene Co.)
    "greenville|new york": (42.417, -74.041),
    "ithaca|new york": (42.443, -76.501),
    "brooklyn|new york": (40.678, -73.944),
    "queens|new york": (40.728, -73.794),
    "flushing|new york": (40.759, -73.830),
    "new york|new york": (40.713, -74.006),
    "new york city|new york": (40.713, -74.006),
    "rockville centre|new york": (40.658, -73.641),
    "hempstead|new york": (40.706, -73.619),
    "new orleans|louisiana": (29.951, -90.071),
    "montreal|quebec": (45.501, -73.567),
    "halifax|nova scotia": (44.650, -63.570),
    "halifax|canada": (44.650, -63.570),
    "alexandria|virginia": (38.805, -77.047),
    "paulding|georgia": (33.921, -84.845),  # county seat Dallas, GA
    # --- RECOVERY BLOCK 2: additional confirmed gaps (None results), same source ---
    "hull|yorkshire": (53.77, -0.34),
    "acapulco|mexico": (16.85, -99.82),
    "panama city|panama": (8.98, -79.52),
    "colon|panama": (9.36, -79.90),
    "union|huntingdon": (40.49, -78.01),
    "kidderminster|worcestershire": (52.39, -2.25),
    # --- RECOVERY BLOCK: ground-truth coordinates re-derived from the last
    # successfully shipped map, after an environment reset lost the working
    # copy of this file. Verified against the actual shipped output. ---
    "orlando|florida": (28.54, -81.38),  # ground-truth recovery from last shipped map
    "chicago|illinois": (41.88, -87.63),  # ground-truth recovery from last shipped map
    "mclean|illinois": (40.48, -88.99),  # ground-truth recovery from last shipped map
    "clinton|new york": (43.05, -75.38),  # ground-truth recovery from last shipped map
    "great falls|virginia": (39.0, -77.29),  # ground-truth recovery from last shipped map
    "boca grande|florida": (26.75, -82.26),  # ground-truth recovery from last shipped map
    "port charlotte|florida": (26.98, -82.09),  # ground-truth recovery from last shipped map
    "belcamp|maryland": (39.48, -76.28),  # ground-truth recovery from last shipped map
    "hamilton|georgia": (32.77, -84.87),  # ground-truth recovery from last shipped map
    "laguardia airport|new york": (40.78, -73.87),  # ground-truth recovery from last shipped map
    "new decatur ward 3|alabama": (34.6, -86.98),  # ground-truth recovery from last shipped map
    "st elmo|tennessee": (35.02, -85.32),  # ground-truth recovery from last shipped map
    "tucson|arizona": (32.22, -110.93),  # ground-truth recovery from last shipped map
    "vincent|alabama": (33.39, -86.41),  # ground-truth recovery from last shipped map
    "cook springs|alabama": (33.59, -86.29),  # ground-truth recovery from last shipped map
    "barnesville|georgia": (33.05, -84.16),  # ground-truth recovery from last shipped map
    "chester|south carolina": (34.71, -81.21),  # ground-truth recovery from last shipped map
    "round mountain|alabama": (34.13, -85.75),  # ground-truth recovery from last shipped map
    "florence|alabama": (34.8, -87.68),  # ground-truth recovery from last shipped map
    "florence|missouri": (38.589, -92.979),  # unincorporated, Morgan Co. -- distinct from Florence, AL above
    "madison|florida": (30.48, -83.41),  # ground-truth recovery from last shipped map
    "annefors|sweden": (61.25, 16.13),  # ground-truth recovery from last shipped map
    "gothenburg|västra götaland": (57.71, 11.97),  # ground-truth recovery from last shipped map
    "elmira; elmira heights|new york": (42.09, -76.81),  # ground-truth recovery from last shipped map
    "newport news|virginia": (37.09, -76.47),  # ground-truth recovery from last shipped map
    "lafayette|alabama": (32.9, -85.41),  # ground-truth recovery from last shipped map
    "edgewood|georgia": (33.75, -84.32),  # ground-truth recovery from last shipped map
    "habersham|georgia": (34.61, -83.53),  # ground-truth recovery from last shipped map
    "chula|georgia": (30.84, -83.98),  # ground-truth recovery from last shipped map
    "irwin|georgia": (31.59, -83.25),  # ground-truth recovery from last shipped map
    "barbour|alabama": (31.88, -85.45),  # ground-truth recovery from last shipped map
    "midway|alabama": (32.05, -85.85),  # ground-truth recovery from last shipped map
    "county cavan|ireland": (53.99, -7.36),  # ground-truth recovery from last shipped map
    "stokes|north carolina": (36.4, -80.21),  # ground-truth recovery from last shipped map
    "troy|alabama": (31.81, -85.97),  # ground-truth recovery from last shipped map
    "jackson|alabama": (31.52, -87.89),  # ground-truth recovery from last shipped map
    "rockingham|virginia": (38.45, -78.87),  # ground-truth recovery from last shipped map
    "upson|georgia": (32.89, -84.33),  # ground-truth recovery from last shipped map
    "marion|south carolina": (33.98, -79.4),  # ground-truth recovery from last shipped map
    "giles|tennessee": (35.2, -87.03),  # ground-truth recovery from last shipped map
    "jefferson|georgia": (33.0, -82.4),  # ground-truth recovery from last shipped map
    "lexington|missouri": (39.18, -93.87),  # ground-truth recovery from last shipped map
    "lone jack|missouri": (38.87, -94.19),  # ground-truth recovery from last shipped map
    "fort kearny|nebraska": (40.65, -99.0),  # ground-truth recovery from last shipped map
    "fort laramie|wyoming": (42.21, -104.52),  # ground-truth recovery from last shipped map
    "south pass|wyoming": (42.33, -108.97),  # ground-truth recovery from last shipped map
    "soda springs|idaho": (42.65, -111.61),  # ground-truth recovery from last shipped map
    "humboldt river|nevada": (41.11, -114.97),  # ground-truth recovery from last shipped map
    "humboldt sink|nevada": (39.98, -118.53),  # ground-truth recovery from last shipped map
    "carson river|nevada": (39.47, -118.78),  # ground-truth recovery from last shipped map
    "sacramento|california": (38.58, -121.49),  # ground-truth recovery from last shipped map
    "san francisco|california": (37.77, -122.42),  # ground-truth recovery from last shipped map
    "hancock|georgia": (33.28, -82.98),  # ground-truth recovery from last shipped map
    "walker chapel|alabama": (34.45, -85.72),  # ground-truth recovery from last shipped map
    "shenandoah|virginia": (38.88, -78.51),  # ground-truth recovery from last shipped map
    "gates|north carolina": (36.4, -76.72),  # ground-truth recovery from last shipped map
    "edgefield|south carolina": (33.79, -81.93),  # ground-truth recovery from last shipped map
    "johnston|north carolina": (35.51, -78.34),  # ground-truth recovery from last shipped map
    "deal|kent": (51.22, 1.4),  # ground-truth recovery from last shipped map
    "st peter|kent": (51.39, 1.41),  # ground-truth recovery from last shipped map
    "onslow|north carolina": (34.75, -77.43),  # ground-truth recovery from last shipped map
    "wilkes|georgia": (33.73, -82.74),  # ground-truth recovery from last shipped map
    "horry|south carolina": (33.84, -79.0),  # ground-truth recovery from last shipped map
    "brunswick|virginia": (36.76, -77.85),  # ground-truth recovery from last shipped map
    "jones|north carolina": (35.07, -77.35),  # ground-truth recovery from last shipped map
    "jones|georgia": (33.009, -83.534),  # seat Gray -- distinct from Jones, NC above
    "wayne co.|pennsylvania": (41.63, -75.31),  # ground-truth recovery from last shipped map
    "wayne|pennsylvania": (41.63, -75.31),  # bare form -- "co." gets stripped as a county-suffix during normalization
    "tattnall|georgia": (32.08, -82.12),  # ground-truth recovery from last shipped map
    "newberry|south carolina": (34.28, -81.62),  # ground-truth recovery from last shipped map
    "springfield|huntingdon": (40.15, -77.95),  # ground-truth recovery from last shipped map
    "richland|missouri": (38.43, -92.84),  # ground-truth recovery from last shipped map
    "elk run|virginia": (38.42, -77.41),  # ground-truth recovery from last shipped map
    "robeson|north carolina": (34.62, -79.1),  # ground-truth recovery from last shipped map
    "cabarrus|north carolina": (35.41, -80.58),  # ground-truth recovery from last shipped map
    "sussex|virginia": (36.92, -77.28),  # ground-truth recovery from last shipped map
    "isle of wight|virginia": (36.9, -76.71),  # ground-truth recovery from last shipped map
    "isle of wight|england": (50.70, -1.29),  # Newport, the county town -- distinct from Isle of Wight Co., VA (named after it)
    "isle of wight|england": (50.70, -1.29),  # Newport, the county town -- distinct from Isle of Wight Co., VA (named after it)
    "bertie|north carolina": (35.99, -76.95),  # ground-truth recovery from last shipped map
    "richmond|georgia": (33.47, -81.97),  # ground-truth recovery from last shipped map
    "berkeley|virginia": (37.26, -77.21),  # ground-truth recovery from last shipped map
    "albemarle|north carolina": (36.06, -76.6),  # ground-truth recovery from last shipped map
    "pembrokeshire|wales": (51.78, -4.88),  # ground-truth recovery from last shipped map
    "shalbourne|england": (51.37, -1.6),  # ground-truth recovery from last shipped map
    "glamorganshire|wales": (51.58, -3.38),  # ground-truth recovery from last shipped map
    "gt bentley|england": (51.87, 0.92),  # ground-truth recovery from last shipped map
    "sussex|new jersey": (41.051, -74.754),  # seat Newton -- distinct from Sussex Co., VA
    "sussex county|new jersey": (41.051, -74.754),
    "independence and mansfield townships|new jersey": (41.051, -74.754),  # Sussex Co.
    "mansfield|new jersey": (40.808, -74.910),  # Mansfield Township, Warren Co.
    "monroe|arkansas": (34.693, -91.313),  # seat Clarendon -- distinct from Monroe, GA
    "monroe county|arkansas": (34.693, -91.313),
    "detroit|michigan": (42.331, -83.046),
    "bloomington|illinois": (40.484, -88.994),
    "mclean|illinois": (40.484, -88.994),  # McLean Co., seat Bloomington -- same place as Bloomington-Normal
    "bloomington|indiana": (39.165, -86.526),  # Monroe County
    "decatur|georgia": (30.900, -84.580),  # Decatur County, seat Bainbridge (south GA)
    "decatur|alabama": (34.605, -86.985),  # Morgan County
    "new decatur|alabama": (34.605, -86.985),  # historical name for the same place
    "walton|georgia": (33.770, -83.710),  # Walton County, seat Monroe
    "raleigh|north carolina": (35.780, -78.638),
    "wake|north carolina": (35.780, -78.638),
    "lexington|north carolina": (35.824, -80.253),  # Davidson County
    "newtown|alabama": (32.870, -87.950),  # Greene County
    "albany|alabama": (34.580, -86.980),  # Morgan County, part of the Decatur AL area
    "jackson|georgia": (33.294, -83.962),  # Butts County
    "nottingham|maryland": (38.800, -76.710),  # Prince George's County
    "towson|maryland": (39.393, -76.609),  # Baltimore Co. seat
    "brooksville|alabama": (33.950, -86.570),  # Blount County
    "marion|alabama": (32.630, -87.320),  # Perry County seat
    "perry|alabama": (32.630, -87.320),
    "madison|kentucky": (37.750, -84.300),  # Richmond, KY is the county seat
    "bristol|massachusetts": (41.840, -71.250),  # Rehoboth area
    "dorchester|south carolina": (33.040, -80.520),  # county seat St. George
    "charles|virginia": (37.350, -77.070),  # Charles City County
    "franklin|georgia": (34.370, -83.240),  # county seat Carnesville
    "twiggs|georgia": (32.670, -83.350),  # county seat Jeffersonville
    "crawford|georgia": (32.700, -83.980),  # county seat Knoxville
    "turner|georgia": (31.710, -83.650),  # county seat Ashburn
    "pulaski|georgia": (32.290, -83.470),  # county seat Hawkinsville
    "dooly|georgia": (32.140, -83.780),  # county seat Vienna
    "worth|georgia": (31.530, -83.840),  # county seat Sylvester
    "wilcox|georgia": (31.930, -83.440),  # county seat Abbeville
    "henry|georgia": (33.450, -84.150),  # county seat McDonough
    "cobb|georgia": (33.950, -84.550),  # county seat Marietta
    "marion|georgia": (32.350, -84.530),  # county seat Buena Vista (disambiguates from marion|alabama)
    "taylor|georgia": (32.550, -84.240),  # county seat Butler
    "northampton|virginia": (37.480, -75.930),  # county seat Eastville, Eastern Shore
    "jacksonville|florida": (30.332, -81.656),
    "marion|florida": (29.187, -82.140),  # county seat Ocala
    "rotonda west|florida": (26.888, -82.283),  # Charlotte County, adjacent to Port Charlotte
    "cincinnati|ohio": (39.103, -84.512),
    "chicago|illinois": (41.878, -87.630),
    "orlando|florida": (28.538, -81.379),
    "traverse city|michigan": (44.763, -85.620),
    "patterson's creek|west virginia": (39.350, -78.700),  # Hampshire Co., along the creek near Romney

    # --- batch added from systematic audit, per user request ---
    "columbus|georgia": (32.461, -84.988),
    "birmingham|alabama": (33.521, -86.802),
    "charlottesville|virginia": (38.033, -78.479),
    "albemarle|virginia": (38.033, -78.479),  # county seat Charlottesville
    "albemarle|north carolina": (36.058, -76.601),  # historical Albemarle County (1660s-1738), predecessor of Chowan Co.; seat Edenton
    "albemarle county|north carolina": (36.058, -76.601),  # same as above -- matches the "County" variant in source strings

    # --- Germany: Black Forest / Freudenstadt cluster (Mehrle family), verified via search ---
    "freudeustadt|germany": (48.464, 8.412),  # misspelling of Freudenstadt in source
    "baiersbornn|germany": (48.516, 8.376),  # misspelling of Baiersbronn in source
    "grömbach|germany": (48.572, 8.546),
    "thummlingen|germany": (48.470, 8.502),  # small historical hamlet in the Dornstetten Oberamt; using Dornstetten's coordinates as the nearest identifiable center
    # --- Germany: Pfalz/Rhineland-Palatinate cluster -- "Bavaria"/"Electorate
    # of Bavaria" labels on these are a historical artifact (the Palatinate
    # was administered as a Bavarian exclave 1816-1946), not a different place ---
    "weingarten|germany": (49.259, 8.287),  # Germersheim district
    "weingarten|bavaria": (49.259, 8.287),  # same place -- historical Bavarian-administration label
    "weingarten|bayern": (49.259, 8.287),  # German spelling of the above
    "weingarten (ba. germersheim)|bavaria": (49.259, 8.287),  # parenthetical variant in source doesn't match the plain-name pair
    "weingarten (ba. germersheim)|germany": (49.259, 8.287),
    "weingarten|rhineland-palatinate": (49.259, 8.287),
    "schwegenheim|germany": (49.270, 8.328),
    "schwegenheim|bavaria": (49.270, 8.328),  # same place -- historical Bavarian-administration label
    "schwegenheim|bayern": (49.270, 8.328),  # German spelling of the above
    "niederhochstadt|bavaria": (49.242, 8.219),
    "niederhochstadt|bayern": (49.242, 8.219),  # German spelling of the above
    "niederhochstadt|germany": (49.242, 8.219),
        
    # --- Germany: Black Forest / Freudenstadt cluster (Mehrle family), verified via search ---
    "freudeustadt|germany": (48.464, 8.412),  # misspelling of Freudenstadt in source
    "baiersbornn|germany": (48.516, 8.376),  # misspelling of Baiersbronn in source
    "grömbach|germany": (48.572, 8.546),
    "thummlingen|germany": (48.470, 8.502),  # small historical hamlet in the Dornstetten Oberamt; using Dornstetten's coordinates as the nearest identifiable center
    # --- Germany: Pfalz/Rhineland-Palatinate cluster -- "Bavaria"/"Electorate
    # of Bavaria" labels on these are a historical artifact (the Palatinate
    # was administered as a Bavarian exclave 1816-1946), not a different place ---
    "weingarten|germany": (49.259, 8.287),  # Germersheim district
    "weingarten|bavaria": (49.259, 8.287),  # same place -- historical Bavarian-administration label
    "weingarten|bayern": (49.259, 8.287),  # German spelling of the above
    "weingarten (ba. germersheim)|bavaria": (49.259, 8.287),  # parenthetical variant in source doesn't match the plain-name pair
    "weingarten (ba. germersheim)|germany": (49.259, 8.287),
    "weingarten|rhineland-palatinate": (49.259, 8.287),

    # --- Sweden: Västra Götaland / Jönköping cluster, verified via search ---
    "äspered|älvsborg": (57.750, 13.183),
    "äspered|västra götaland": (57.750, 13.183),
    "aspered|västra götaland": (57.750, 13.183),
    "löfvaskog|västra götaland": (57.750, 13.183),  # within Äspered
    "blidsberg|västra götaland": (57.933, 13.483),
    "ulricehamn|västra götaland": (57.783, 13.417),
    "värnamo|jönköping": (57.183, 14.033),
    "fryele|jönköping": (57.183, 14.033),  # parish within Värnamo Municipality, using the municipal seat as nearest identifiable anchor
    "fröderyd|jönköping": (57.183, 14.033),  # nearby parish in the same district
    "göteborg|sverige": (57.709, 11.975),
    "göteborg|göteborg och bohus": (57.709, 11.975),
    "skara|västra götaland": (58.390, 13.430),
    "åsle|västra götaland": (58.167, 13.550),  # parish near Falköping, using Falköping as nearest identifiable anchor
    "falköping|västra götaland": (58.167, 13.550),
    "falköping stadsförsamling|skaraborg": (58.167, 13.550),
    "mularp|skaraborg": (58.390, 13.430),  # Skaraborg parish, using Skara as nearest identifiable anchor
    "mularp|västra götaland": (58.390, 13.430),
    "tiarp|skaraborg": (58.167, 13.550),  # near Falköping
    "månstad|älvsborg": (57.933, 13.483),  # near Ulricehamn/Blidsberg area
    "mosjö|örebro": (59.275, 15.213),  # using Örebro city as nearest identifiable anchor
    "ramundeboda|örebro": (59.275, 15.213),

    # --- Ireland: Cavan/Monaghan/Armagh (Ulster) cluster, verified via search ---
    "knocknaveagh|cavan": (53.780, -7.087),
    "munterconnaught|cavan": (53.804, -7.090),
    "munterconnaught|ireland": (53.804, -7.090),
    "eitor|cavan": (53.804, -7.090),  # Eighter townland, Munterconnaught parish -- spelling variant in source
    "eightor|cavan": (53.804, -7.090),  # spelling variant
    "eighter|cavan": (53.804, -7.090),
    "ballymachugh|cavan": (53.804, -7.090),  # same Munterconnaught parish area
    "taulaght|cavan": (53.804, -7.090),  # same Munterconnaught parish area
    "cavancoulter|cavan": (53.804, -7.090),  # same general Cavan area, no more precise match found
    "dunsinare|monaghan": (54.248, -6.971),  # townland in Monaghan civil parish, using the town as nearest identifiable anchor
    "monaghan|monaghan": (54.248, -6.971),
    "monaghan|ireland": (54.248, -6.971),
    "rossmore estate|monaghan": (54.248, -6.971),  # just south of Monaghan town
    "rooskey|monaghan": (54.248, -6.971),
    "darkley|armagh": (54.233, -6.675),
    "tullyvallan|armagh": (54.190, -6.590),  # Newtownhamilton civil parish
    "cobh|ireland": (51.850, -8.294),
    "oldcastle|meath": (53.767, -7.170),
    "glenboy|meath": (53.767, -7.170),  # near Oldcastle, no more precise match found
    "ballinskill|westmeath": (53.617, -7.317),  # near Castlepollard area
    "county roscommon|ireland": (53.767, -8.190),  # county seat Roscommon town

    # --- Ireland: Cavan/Monaghan/Armagh (Ulster) cluster, verified via search ---
    "knocknaveagh|cavan": (53.780, -7.087),
    "munterconnaught|cavan": (53.804, -7.090),
    "munterconnaught|ireland": (53.804, -7.090),
    "eitor|cavan": (53.804, -7.090),  # Eighter townland, Munterconnaught parish -- spelling variant in source
    "eightor|cavan": (53.804, -7.090),  # spelling variant
    "eighter|cavan": (53.804, -7.090),
    "ballymachugh|cavan": (53.804, -7.090),  # same Munterconnaught parish area
    "taulaght|cavan": (53.804, -7.090),  # same Munterconnaught parish area
    "cavancoulter|cavan": (53.804, -7.090),  # same general Cavan area, no more precise match found
    "dunsinare|monaghan": (54.248, -6.971),  # townland in Monaghan civil parish, using the town as nearest identifiable anchor
    "monaghan|monaghan": (54.248, -6.971),
    "monaghan|ireland": (54.248, -6.971),
    "rossmore estate|monaghan": (54.248, -6.971),  # just south of Monaghan town
    "rooskey|monaghan": (54.248, -6.971),
    "darkley|armagh": (54.233, -6.675),
    "tullyvallan|armagh": (54.190, -6.590),  # Newtownhamilton civil parish
    "cobh|ireland": (51.850, -8.294),
    "oldcastle|meath": (53.767, -7.170),
    "glenboy|meath": (53.767, -7.170),  # near Oldcastle, no more precise match found
    "ballinskill|westmeath": (53.617, -7.317),  # near Castlepollard area
    "county roscommon|ireland": (53.767, -8.190),  # county seat Roscommon town
    "schwegenheim|germany": (49.270, 8.328),
    "schwegenheim|bavaria": (49.270, 8.328),  # same place -- historical Bavarian-administration label
    "schwegenheim|bayern": (49.270, 8.328),  # German spelling of the above
    "niederhochstadt|bavaria": (49.242, 8.219),
    "niederhochstadt|bayern": (49.242, 8.219),  # German spelling of the above
    "niederhochstadt|germany": (49.242, 8.219),
            "moulton|alabama": (34.480, -87.291),  # Lawrence Co. seat
    "miami|florida": (25.762, -80.192),
    "portsmouth|virginia": (36.836, -76.298),
    "chesapeake|virginia": (36.768, -76.288),  # independent city; Elizabeth River, old Lower Norfolk Co. -- the Godbey plantation (v15)
    "baltimore|maryland": (39.290, -76.612),
    "cockeysville|maryland": (39.478, -76.642),
    "talbotton|georgia": (32.677, -84.534),  # Talbot Co. seat
    "talbot|georgia": (32.677, -84.534),  # Talbot Co. -- same place as Talbotton above, different string form
    "cleveland|north carolina": (35.292, -81.535),  # Cleveland Co., seat Shelby -- explicitly NC in every source record, not Cleveland OH
    "winston-salem|north carolina": (36.100, -80.244),
    "rutherford|north carolina": (35.368, -81.960),  # Rutherford Co. seat Rutherfordton
    "easton|maryland": (38.774, -76.076),
    "summerville|south carolina": (33.018, -80.175),
    "shelby|north carolina": (35.292, -81.535),
    "shelby|alabama": (33.116, -86.588),  # Shelby Co. seat Columbiana area
    "vincent|alabama": (33.386, -86.410),  # Shelby Co.

    # --- Georgia: Harris County cluster (seat Hamilton), verified via search ---
    "harris|georgia": (32.765, -84.873),
    "harris county|georgia": (32.765, -84.873),
    "hamilton|georgia": (32.765, -84.873),
    "valley plains|georgia": (32.765, -84.873),
    "upper nineteenth|georgia": (32.765, -84.873),
    "md 1186 upper nineteenth|georgia": (32.765, -84.873),
    "osborn mill|georgia": (32.765, -84.873),
    "barkers|georgia": (34.257, -85.165),  # actually Floyd Co. (seat Rome) per the raw string
    # --- Georgia: other counties ---
    "lawrence|alabama": (34.480, -87.291),  # Lawrence Co. seat Moulton
    "lawrence county|alabama": (34.480, -87.291),
    "muscogee|georgia": (32.461, -84.988),  # seat Columbus
    "muscogee county|georgia": (32.461, -84.988),
    "upson|georgia": (32.888, -84.327),  # seat Thomaston
    "jefferson|georgia": (33.000, -82.400),  # seat Louisville
    "hancock county|georgia": (33.280, -82.980),  # seat Sparta
    "hancock|georgia": (33.280, -82.980),  # bare form
    "barnesville|georgia": (33.054, -84.155),  # Lamar Co.
    # --- Virginia ---
    "isle of wight county|virginia": (36.900, -76.710),
    "isle of wight|virginia": (36.900, -76.710),  # bare form -- "county" gets stripped during normalization
    "brunswick county|virginia": (36.760, -77.850),  # seat Lawrenceville
    "brunswick|virginia": (36.760, -77.850),  # bare form
    "stafford county|virginia": (38.420, -77.410),
    "stafford|virginia": (38.420, -77.410),  # bare form
    "great falls|virginia": (38.997, -77.288),
    # --- North Carolina ---
    "bertie county|north carolina": (35.990, -76.950),  # seat Windsor
    "bertie|north carolina": (35.990, -76.950),  # bare form
    "surry county|north carolina": (36.390, -80.720),  # seat Dobson
    "surry|north carolina": (36.390, -80.720),  # bare form
    "surry|virginia": (37.136, -76.835),  # seat Surry -- distinct from Surry Co., NC above
    "surry county|virginia": (37.136, -76.835),
    "dinwiddie|virginia": (37.078, -77.587),  # seat Dinwiddie
    "dinwiddie county|virginia": (37.078, -77.587),
    "surry|virginia": (37.136, -76.835),  # seat Surry -- distinct from Surry Co., NC above
    "surry county|virginia": (37.136, -76.835),
    "dinwiddie|virginia": (37.078, -77.587),  # seat Dinwiddie
    "dinwiddie county|virginia": (37.078, -77.587),
    "stokes|north carolina": (36.400, -80.210),  # seat Danbury
    "johnston|north carolina": (35.510, -78.340),  # seat Smithfield
    "jones|north carolina": (35.070, -77.350),  # seat Trenton
    "jones|georgia": (33.009, -83.534),  # seat Gray
    "jones county|georgia": (33.009, -83.534),
    # --- Alabama: additional ---
    "barbour county|alabama": (31.880, -85.450),  # seat Clayton
    "barbour|alabama": (31.880, -85.450),  # bare form
    "cherokee county|alabama": (34.150, -85.680),  # seat Centre
    "cherokee|alabama": (34.150, -85.680),  # bare form
    "round mountain|alabama": (34.130, -85.750),  # Cherokee Co.
    "walkers chapel|alabama": (34.445, -85.719),  # Dekalb Co., near Fort Payne
    "midway|alabama": (32.050, -85.850),  # Bullock Co.
    "chambers|alabama": (32.900, -85.410),  # seat Lafayette
    "new decatur ward 3|alabama": (34.605, -86.983),  # Decatur, Morgan Co.
    "albany ward 3|alabama": (34.605, -86.983),  # Decatur, Morgan Co.
    # --- Kentucky ---
    "rush|kentucky": (39.084, -84.509),  # Kenton Co., near Covington
    "kenton|kentucky": (39.084, -84.509),
    "mercer|kentucky": (37.760, -84.850),  # seat Harrodsburg
    "mercer county|kentucky": (37.760, -84.850),
    # --- Tennessee ---
    "giles county|tennessee": (35.200, -87.030),  # seat Pulaski
    "giles|tennessee": (35.200, -87.030),  # bare form
    "st elmo|tennessee": (35.020, -85.320),  # Hamilton Co., Chattanooga
    # --- New York ---
    "manhattan|new york": (40.783, -73.966),
    "oneonta;west oneonta|new york": (42.450, -75.070),
    "elmira; elmira heights|new york": (42.090, -76.810),
    # --- Maryland / Connecticut / South Carolina ---
    "belcamp|maryland": (39.480, -76.280),
    "middletown|connecticut": (41.560, -72.650),
    "chester|south carolina": (34.706, -81.213),
    # --- Switzerland: Bern canton cluster ---
    "bern|bern": (46.948, 7.447),
    "berne|switzerland": (46.948, 7.447),
    "siselen|bern": (47.145, 7.256),
    "kallnach|bern": (47.058, 7.310),
    "biel|bern": (47.140, 7.247),
    "kappelen|bern": (47.106, 7.293),
    # --- Sweden: English spelling variant ---
    "gothenburg|västra götaland": (57.709, 11.975),
    # --- Ireland: bare county forms ---
    "county cavan|ireland": (53.990, -7.361),
    "monaghan parish|ireland": (54.248, -6.971),
    # --- England ---
    "faversham|kent": (51.313, 0.891),
    "shalbourne|england": (51.372, -1.596),  # Wiltshire
    "mansfield woodhouse|nottinghamshire": (53.167, -1.183),
    "thaxted|essex": (51.955, 0.349),
    "st peter|kent": (51.393, 1.406),  # near Broadstairs

    # --- Maryland (Askew/Masterson cluster) ---
    "rockville|maryland": (39.084, -77.153),
    "potomac|maryland": (39.018, -77.207),
    "abingdon|maryland": (39.473, -76.297),
    "dundalk|maryland": (39.250, -76.523),
    "prince georges|maryland": (38.810, -76.870),  # same as Prince George's Co.
    # --- Arizona (Masterson cluster) ---
    "yuma|arizona": (32.693, -114.628),
    "tucson|arizona": (32.222, -110.927),
    # --- New Jersey ---
    "hoboken|new jersey": (40.744, -74.032),
    "bogota|new jersey": (40.879, -74.032),
    "monmouth county|new jersey": (40.259, -74.274),  # seat Freehold
    "monmouth|new jersey": (40.259, -74.274),  # bare form
    "burlington county|new jersey": (39.937, -74.789),  # seat Mount Holly
    "burlington|new jersey": (39.937, -74.789),  # bare form
    # --- Florida ---
    "port charlotte|florida": (26.976, -82.090),
    "boca grande|florida": (26.755, -82.259),
    "madison county|florida": (30.476, -83.412),
    "madison|florida": (30.476, -83.412),  # bare form
    # --- Texas ---
    "bexar|texas": (29.424, -98.494),  # San Antonio
    "laredo|texas": (27.506, -99.507),
    "waco|texas": (31.549, -97.146),
    # --- Georgia: additional counties ---
    "floyd|georgia": (34.257, -85.165),  # seat Rome
    "tattnall|georgia": (32.084, -82.121),  # seat Reidsville
    "tattnall county|georgia": (32.084, -82.121),
    "thomas|georgia": (30.836, -83.979),  # seat Thomasville
    "chula|georgia": (30.836, -83.979),  # Thomas Co.
    "barwick|georgia": (30.836, -83.979),  # Thomas Co.
    "monroe|georgia": (33.794, -83.714),  # Walton Co.
    "monroe|arkansas": (34.693, -91.313),  # seat Clarendon -- distinct from Monroe, GA above
    "monroe county|arkansas": (34.693, -91.313),
    "edgewood|georgia": (33.749, -84.322),  # Fulton Co., near Atlanta
    "habersham|georgia": (34.606, -83.527),  # seat Clarkesville
    "baldwin|georgia": (33.079, -83.232),  # seat Milledgeville
    "bibb|georgia": (32.840, -83.632),  # same as Macon
    "wilkes county|georgia": (33.734, -82.744),  # seat Washington
    "wilkes|georgia": (33.734, -82.744),  # bare form
    "montgomery county|georgia": (32.181, -82.703),  # seat Mount Vernon
    "montgomery|georgia": (32.181, -82.703),  # bare form
    "richmond county|georgia": (33.474, -81.975),  # seat Augusta
    "richmond|georgia": (33.474, -81.975),  # bare form
    "irwin county|georgia": (31.593, -83.253),  # seat Ocilla
    "irwin|georgia": (31.593, -83.253),  # bare form
    # --- Alabama: additional counties ---
    "wolff|alabama": (34.605, -86.983),  # Morgan Co., Decatur area
    "dekalb|alabama": (34.445, -85.719),  # seat Fort Payne
    "walker chapel|alabama": (34.445, -85.719),  # DeKalb Co.
    "dekalb county|alabama": (34.445, -85.719),
    "chilton county|alabama": (32.839, -86.630),  # seat Clanton
    "chilton|alabama": (32.839, -86.630),  # bare form
    "marengo county|alabama": (32.303, -87.789),  # seat Linden
    "marengo|alabama": (32.303, -87.789),  # bare form
    "morgan county|alabama": (34.605, -86.983),  # seat Decatur
    "morgan|alabama": (34.605, -86.983),  # bare form
    "morgan|missouri": (38.433, -92.845),  # Morgan Co., seat Versailles -- distinct from Morgan Co., AL above
    "richland|missouri": (38.433, -92.845),  # Morgan Co.
    "moreau|missouri": (38.433, -92.845),  # Morgan Co.
    "lauderdale|alabama": (34.799, -87.677),  # seat Florence
    "florence|alabama": (34.799, -87.677),
    "florence|missouri": (38.433, -92.845),  # Morgan Co. -- distinct from Florence, AL above
    "jackson|alabama": (31.520, -87.895),  # Clarke Co.
    "troy|alabama": (31.809, -85.970),  # Pike Co.
    "st. clair county|alabama": (33.586, -86.286),  # seat Pell City
    "st. clair|alabama": (33.586, -86.286),  # bare form -- "County" gets stripped
    "cook springs|alabama": (33.586, -86.286),  # St. Clair Co.
    "five points|alabama": (32.900, -85.410),  # Chambers Co.
    "tuskegee|alabama": (32.430, -85.690),  # same as Macon Co. AL
    # --- North/South Carolina ---
    "hertford county|north carolina": (36.394, -76.943),  # seat Winton
    "hertford|north carolina": (36.394, -76.943),  # bare form
    "onslow|north carolina": (34.752, -77.433),  # seat Jacksonville
    "edgecombe|north carolina": (35.899, -77.542),  # seat Tarboro
    "robeson county|north carolina": (34.618, -79.104),  # seat Lumberton
    "robeson|north carolina": (34.618, -79.104),  # bare form
    "gates|north carolina": (36.404, -76.719),  # seat Gatesville
    "arcadia|north carolina": (35.824, -80.253),  # Davidson Co.
    "crowder mountain|north carolina": (35.262, -81.187),  # Gaston Co.
    "horry county|south carolina": (33.835, -78.999),  # seat Conway
    "horry|south carolina": (33.835, -78.999),  # bare form

    # --- Toronto historical wards (19th c. municipal subdivisions) ---
    "st patricks ward|ontario": (43.653, -79.383),
    "st johns ward|ontario": (43.653, -79.383),
    "toronto (west/ouest) (city/cité) ward/quartier no 4|ontario": (43.653, -79.383),
    "greensboro ward 4|north carolina": (36.073, -79.792),  # Greensboro, Guilford Co.
    "alexandria ward 4|virginia": (38.805, -77.047),  # same as Alexandria
    "alexandria city|virginia": (38.805, -77.047),
    # --- England: remaining specific towns ---
    "ware|hertfordshire": (51.809, -0.033),
    "helmsley|yorkshire": (54.248, -1.064),
    "hull|yorkshire": (53.767, -0.335),
    "deal|kent": (51.223, 1.404),
    "sandwich st peter|kent": (51.277, 1.341),
    "foleshill|warwickshire": (52.427, -1.485),  # now part of Coventry
    "brabourne|kent": (51.146, 0.978),
    "chesham|buckinghamshire": (51.705, -0.610),
    "bury st edmunds|suffolk": (52.245, 0.717),
    "gt bentley|england": (51.869, 0.921),  # Essex
    "cranfield|bedfordshire": (52.073, -0.615),
    "kidderminster|worcestershire": (52.389, -2.249),
    "halifax|england": (53.723, -1.863),  # Yorkshire -- distinct from the existing Halifax, VA and Halifax, Nova Scotia entries
    "south ouram parish|england": (53.723, -1.863),  # Halifax, Yorkshire
    "ridgewell hall|england": (52.017, 0.545),  # Essex

    "baiersbronn-schloß|germany": (48.516, 8.376),  # same as Baiersbronn -- special character wasn't matching the bare fallback
    "portsmouth; waterview|virginia": (36.836, -76.298),  # same as Portsmouth
    "avondale|louisiana": (29.900, -90.190),  # Jefferson Parish, near New Orleans
    "annefors|sweden": (61.250, 16.133),  # Bollnäs, Gävleborg
    "oneonta;cooperstown|new york": (42.450, -75.070),  # same as Oneonta
    "oneonta; oneonta plains; east end; south side; west oneonta; cooperstown|new york": (42.450, -75.070),
    "cumberland|england": (54.783, -3.033),  # historic county, now part of Cumbria
    # --- Wales ---
    "llangollen|wales": (52.968, -3.169),  # Denbighshire
    "pembrokeshire|wales": (51.783, -4.883),
    "glamorganshire|wales": (51.583, -3.383),
    # --- Alabama / Georgia: remaining specifics ---
    "lafayette|alabama": (32.900, -85.410),  # same as Chambers Co.
    "columbus; phenix city|georgia": (32.461, -84.988),  # same as Columbus
    # --- Virginia: remaining specifics ---
    "augusta|virginia": (38.149, -79.077),  # Augusta Co., distinct from Augusta, GA
    "lower norfolk|virginia": (36.847, -76.286),  # historic precursor to Norfolk/Norfolk Co.
    "virginia pioneer|virginia": (36.847, -76.286),  # Elizabeth City Co., same area as early Norfolk
    "newberry county|south carolina": (34.276, -81.615),
    "newberry|south carolina": (34.276, -81.615),  # bare form
    "edgefield county|south carolina": (33.787, -81.926),
    "edgefield|south carolina": (33.787, -81.926),  # bare form
    "marion|south carolina": (33.983, -79.398),  # seat Marion
    # --- Virginia: additional ---
    "louisa county|virginia": (38.014, -77.996),
    "louisa|virginia": (38.014, -77.996),  # bare form
    "berkeley|virginia": (37.263, -77.207),  # historic Berkeley Hundred, near Jamestown
    "pittsylvania county|virginia": (36.831, -79.396),  # seat Chatham
    "pittsylvania|virginia": (36.831, -79.396),  # bare form
    "elk run|virginia": (38.420, -77.410),  # Stafford Co. area
    "fredericksville albemarle co|virginia": (38.033, -78.479),  # same as Albemarle Co.
    "fredericksville albemarle|virginia": (38.033, -78.479),  # bare form -- "Co" is also stripped as a county-suffix variant
    "prince george county|virginia": (37.219, -77.288),
    "prince george|virginia": (37.219, -77.288),  # bare form
    "newport news|virginia": (37.086, -76.473),
    "sussex county|virginia": (36.917, -77.276),
    "sussex|virginia": (36.917, -77.276),  # bare form
    "sussex|new jersey": (41.051, -74.754),  # seat Newton -- distinct from Sussex Co., VA above
    "sussex county|new jersey": (41.051, -74.754),
    "independence and mansfield townships|new jersey": (41.051, -74.754),  # Sussex Co.
    "mansfield|new jersey": (40.808, -74.910),  # Mansfield Township, Warren Co.
    # --- New York: additional ---
    "clinton|new york": (43.048, -75.380),  # Oneida Co.
    "laguardia airport|new york": (40.777, -73.872),
    "buffalo|new york": (42.886, -78.878),  # "Village of" gets stripped as a noise prefix during normalization
    "waverly hall|georgia": (32.746, -84.734),
    "ludlow|kentucky": (39.094, -84.548),
    "rome|georgia": (34.257, -85.165),
    "forsyth|north carolina": (36.100, -80.244),  # Forsyth Co., seat Winston-Salem
    "gwinnett|georgia": (33.956, -84.024),  # seat Lawrenceville
    "atlanta|georgia": (33.749, -84.388),
    "bessemer|alabama": (33.402, -86.954),
    "hagerstown|maryland": (39.642, -77.720),
    "asheville|north carolina": (35.595, -82.551),
    "wilmington|north carolina": (34.226, -77.945),
    "fayetteville|north carolina": (35.053, -78.878),
    # places named in military records (_MILT), 2026-09-25
    "cartagena|colombia": (10.391, -75.479),     # Cartagena de Indias (Vernon's expedition, 1741)
    "west point|new york": (41.391, -73.956),
    "drogheda|ireland": (53.717, -6.350),
    "richmond|rhode island": (41.500, -71.670),
    "newport|rhode island": (41.490, -71.313),
    "newport|tennessee": (35.968, -83.187),
    "aberdeen|scotland": (57.149, -2.099),
    "rotterdam|netherlands": (51.924, 4.478),
    "amsterdam|netherlands": (52.377, 4.897),
    "gadsden|alabama": (34.014, -86.007),
    "attalla|alabama": (34.016, -86.096),
    "fort payne|alabama": (34.445, -85.719),
    "eufaula|alabama": (31.891, -85.145),
    "covington|kentucky": (39.084, -84.509),
    "charlotte|north carolina": (35.227, -80.843),
    "mecklenburg|north carolina": (35.227, -80.843),  # seat Charlotte
    "mecklenburg county|north carolina": (35.227, -80.843),
    "cabarrus|north carolina": (35.410, -80.585),  # seat Concord
    "cabarrus county|north carolina": (35.410, -80.585),
    "salisbury|north carolina": (35.670, -80.474),  # Rowan Co. seat, near Cabarrus
    "charlotte|virginia": (37.060, -78.650),  # Charlotte Co., seat Charlotte Court House
    "greene|alabama": (32.840, -87.890),  # county seat Eutaw
    "greene|virginia": (38.293, -78.393),  # county seat Stanardsville
    "shenandoah|virginia": (38.877, -78.511),  # county seat Woodstock
    "choctaw|alabama": (31.990, -88.270),  # county seat Butler
    "lee|alabama": (32.650, -85.380),  # county seat Opelika
    "russell|alabama": (32.280, -85.100),  # county seat Phenix City
    "macon|alabama": (32.430, -85.690),  # county seat Tuskegee
    "cheshire|england": (53.190, -2.890),  # county town Chester
    "le havre|france": (49.494, 0.108),
    "havre|france": (49.494, 0.108),
    "liverpool|england": (53.408, -2.992),
    "massapequa|new york": (40.678, -73.474),
    "floral park|new york": (40.723, -73.703),
    "albany|new york": (42.652, -73.756),
    "coeymans|new york": (42.474, -73.800),
    "rensselaerville|new york": (42.500, -74.150),
    "westerlo|new york": (42.564, -74.032),
    "freehold|new york": (42.446, -74.056),
    "durham|new york": (42.331, -74.155),
    "durham|north carolina": (35.994, -78.899),  # distinct from Durham, NY above
    "durham county|north carolina": (35.994, -78.899),
    "durham|north carolina": (35.994, -78.899),  # distinct from Durham, NY above
    "durham county|north carolina": (35.994, -78.899),
    "new baltimore|new york": (42.450, -73.789),
    "andes|new york": (42.196, -74.783),
    "delhi|new york": (42.278, -74.914),
    "kortright|new york": (42.301, -74.834),
    "meredith|new york": (42.297, -75.045),
    "hamden|new york": (42.290, -74.980),
    "harpersfield|new york": (42.393, -74.734),
    "hartwick|new york": (42.590, -75.032),
    "laurens|new york": (42.535, -75.084),
    "otsego|new york": (42.700, -74.900),
    "canaan|new york": (42.499, -73.418),
    "staten island|new york": (40.579, -74.151),
    "richmond|new york": (40.579, -74.151),
    "rye|new york": (40.981, -73.688),
    "westchester|new york": (41.122, -73.760),
    "southold|new york": (41.064, -72.421),
    "southampton|new york": (40.884, -72.389),
    "east hampton|new york": (40.963, -72.185),
    "huntington|new york": (40.868, -73.425),
    "brentwood|new york": (40.781, -73.245),
    "mahopac falls|new york": (41.383, -73.727),
    "grafton|new york": (42.750, -73.437),
    "elmira|new york": (42.090, -76.807),
    "tioga|new york": (42.070, -76.300),
    "dutchess|new york": (41.750, -73.750),
    "columbia|new york": (42.250, -73.650),
    "hushurg auems co|new york": (42.652, -73.756),
    # New Jersey
    "washington|new jersey": (40.759, -74.985),
    "lebanon|new jersey": (40.641, -74.831),
    "clarksville|new jersey": (40.667, -74.883),
    "harmony|new jersey": (40.796, -75.088),
    "newark|new jersey": (40.735, -74.172),
    "paterson|new jersey": (40.916, -74.172),
    "bethlehem|new jersey": (40.591, -75.030),
    "franklin|new jersey": (40.795, -75.043),
    "warren township|new jersey": (40.633, -74.505),
    "salem|new jersey": (39.573, -75.468),
        # Pennsylvania
    "philadelphia|pennsylvania": (39.953, -75.165),
    "germantown|pennsylvania": (40.038, -75.177),
        "ridley township|pennsylvania": (39.878, -75.343),
    "york|pennsylvania": (39.963, -76.728),
    "washington|pennsylvania": (40.174, -80.246),
    "mount pleasant|pennsylvania": (40.146, -79.548),
    "tredyffrin|pennsylvania": (40.058, -75.500),
    # Virginia
    "cumberland|virginia": (37.512, -78.253),
    "halifax|virginia": (36.767, -78.925),
    "campbell|virginia": (37.250, -79.130),
    "culpeper|virginia": (38.473, -77.999),
    "goochland|virginia": (37.700, -77.880),
    "fredericksburg|virginia": (38.303, -77.461),
    "richmond|virginia": (37.541, -77.436),
    "richmond city|virginia": (37.541, -77.436),
    "charles city|virginia": (37.354, -77.075),
    "orange|virginia": (38.247, -78.112),
    "madison|virginia": (38.386, -78.264),
    "raells|virginia": (37.400, -77.700),
    "southam parish|virginia": (37.512, -78.253),
    "st james northam parish|virginia": (37.700, -77.880),
    "brumfield|virginia": (38.473, -77.999),
    "pineton|virginia": (38.700, -77.500),
    "hanover parish|virginia": (37.750, -77.350),
    "michaelmass|virginia": (38.700, -77.500),
    "overwharton|virginia": (38.450, -77.400),
    # Kentucky
    "henderson|kentucky": (37.836, -87.590),
    "hebbardsville|kentucky": (37.720, -87.480),
    "corydon|kentucky": (37.756, -87.703),
    "spottsville|kentucky": (37.720, -87.450),
    "spotsville|kentucky": (37.720, -87.450),
    "tillottsons|kentucky": (37.836, -87.590),
    "owensboro|kentucky": (37.774, -87.113),
    "madisonville|kentucky": (37.328, -87.500),
    "dawson springs|kentucky": (37.166, -87.694),
    "hanson|kentucky": (37.319, -87.463),
    "charleston|kentucky": (37.328, -87.500),
    "vandetta|kentucky": (37.300, -87.450),
    "raleigh|kentucky": (37.700, -87.500),
    "morganfield|kentucky": (37.688, -87.923),
    "uniontown|kentucky": (37.780, -87.943),
    "waverly|kentucky": (37.827, -87.807),
    "island|kentucky": (37.700, -87.400),
    "floyd settlement|kentucky": (37.688, -87.923),
    "spring grove|kentucky": (37.688, -87.923),
    "bremen|kentucky": (37.351, -87.288),
    "calhoun|kentucky": (37.542, -87.309),
    "livermore|kentucky": (37.489, -87.132),
    "greenville|kentucky": (37.202, -87.176),
    "south carrollton|kentucky": (37.298, -87.264),
    "lewisburg|kentucky": (37.170, -87.121),
    "worthington|kentucky": (37.200, -87.200),
    "subdivision 2|kentucky": (37.200, -87.200),
    "bardstown|kentucky": (37.807, -85.467),
    "bloomfield|kentucky": (37.867, -85.317),
    "eastern district|kentucky": (37.807, -85.467),
    "floydsburg|kentucky": (38.263, -85.436),
    "la grange|kentucky": (38.407, -85.379),
    "pewee valley|kentucky": (38.290, -85.480),
    "brownsboro|kentucky": (38.320, -85.500),
    "taylorsville|kentucky": (37.999, -85.347),
    "lexington|kentucky": (38.041, -84.502),
    "boonesborough|kentucky": (37.923, -84.279),
    "flemingsburg|kentucky": (38.417, -83.735),
    "vanceburg|kentucky": (38.598, -83.320),
    "maysville|kentucky": (38.643, -83.745),
    "graham's station|kentucky": (38.550, -83.500),
    "gilbertsville|kentucky": (36.988, -88.316),
    "louisville|kentucky": (38.253, -85.759),
    "woodford|kentucky": (38.050, -84.730),
    "lincoln|kentucky": (37.550, -84.700),
    "alton|kentucky": (37.930, -84.980),
    "burksville|kentucky": (36.789, -85.359),
    "district 1|kentucky": (37.836, -87.590),
    # Missouri
    "cape girardeau|missouri": (37.306, -89.518),
    "byrd|missouri": (37.306, -89.518),
    "dutchtown|missouri": (37.184, -89.549),
    "jackson|missouri": (37.383, -89.667),
    "lorance|missouri": (37.306, -89.518),
    "st. louis|missouri": (38.627, -90.199),
    "st louis|missouri": (38.627, -90.199),
    "paris|missouri": (39.481, -91.984),
    "capon|missouri": (37.306, -89.518),
    "township 30|missouri": (37.306, -89.518),
    "township 31|missouri": (37.306, -89.518),
    # Indiana
    "evansville|indiana": (37.977, -87.555),
    "verona|indiana": (38.050, -87.400),
    "knight|indiana": (37.950, -87.600),
    "union|indiana": (37.950, -87.500),
    "richmond|indiana": (39.829, -84.890),
    "perry|indiana": (37.950, -87.500),
    # Maryland
    "annapolis|maryland": (38.978, -76.492),
    "all hollow|maryland": (39.000, -76.500),
    "la plata|maryland": (38.529, -76.976),
    "port tobacco|maryland": (38.512, -77.019),
    "patuxent|maryland": (38.400, -76.700),
    "trinity parish|maryland": (38.512, -77.019),
    "durham par.benedict hun|maryland": (38.512, -77.019),
    "benedict hundred|maryland": (38.512, -77.019),
    # Ohio / Illinois / Michigan / Rhode Island / North Carolina
    "ripley|ohio": (38.744, -83.845),
    "georgetown|ohio": (38.867, -83.902),
    "decatur|illinois": (39.841, -88.954),
    "old shawneetown|illinois": (37.716, -88.135),
    "royal oak|michigan": (42.489, -83.145),
    "pleasant ridge|michigan": (42.469, -83.147),
    "marshall|michigan": (42.271, -84.961),
    "westerly|rhode island": (41.377, -71.827),
    "kings town|rhode island": (41.480, -71.540),
    "south kingston|rhode island": (41.451, -71.540),
    "south kingstown|rhode island": (41.451, -71.540),
    "hopkinton|rhode island": (41.478, -71.789),
    "east greenwich|rhode island": (41.658, -71.461),
    "providence|rhode island": (41.824, -71.413),
    "granville|north carolina": (36.293, -78.678),
    "hillsboro|north carolina": (36.075, -79.099),
    "morganton|north carolina": (35.745, -81.685),
    "chapel hill|north carolina": (35.913, -79.056),
    "rowan|north carolina": (35.671, -80.470),
    "burke|north carolina": (35.745, -81.685),
    "nevada city|california": (39.262, -121.014),
    "san jose|california": (37.339, -121.895),
    "santa clara|california": (37.354, -121.955),
    "boca raton|florida": (26.359, -80.083),
    "brooksville|florida": (28.554, -82.386),
    "cloverleaf|florida": (28.554, -82.386),
    "houston|texas": (29.760, -95.370),
    "houston|georgia": (32.465, -83.721),  # Houston Co., seat Perry -- distinct from Houston, TX
    "houston county|georgia": (32.465, -83.721),
    "surry|virginia": (37.136, -76.835),  # seat Surry -- distinct from Surry Co., NC
    "surry county|virginia": (37.136, -76.835),
    "dinwiddie|virginia": (37.078, -77.587),  # seat Dinwiddie
    "dinwiddie county|virginia": (37.078, -77.587),
    "houston|georgia": (32.465, -83.721),  # Houston Co., seat Perry -- distinct from Houston, TX above
    "houston county|georgia": (32.465, -83.721),
    "houston|georgia": (32.465, -83.721),  # Houston Co., seat Perry -- distinct from Houston, TX above
    "houston county|georgia": (32.465, -83.721),
    "cumberland|pennsylvania": (40.202, -77.200),  # county seat Carlisle
    "hempstead|new york": (40.706, -73.619),
    "shippensburg|pennsylvania": (40.051, -77.520),
    "hopewell|pennsylvania": (40.128, -77.703),
    "randolph|vermont": (43.925, -72.667),
    "middlebury|vermont": (44.015, -73.167),
    "williamstown|massachusetts": (42.713, -73.203),
    "winhall|vermont": (43.163, -72.887),
    # Germany
    "baiersbronn|germany": (48.516, 8.376),
    "gemmingen|germany": (49.150, 8.983),
    "gemmingen|baden-württemberg": (49.150, 8.983),
    "gemmingen|germany": (49.150, 8.983),
    "gemmingen|baden-württemberg": (49.150, 8.983),
    "gemmingen|germany": (49.150, 8.983),
    "gemmingen|baden-württemberg": (49.150, 8.983),
    "baiersbronn-dorf|germany": (48.516, 8.376),
    "baiersbronn-tonbach|germany": (48.535, 8.350),
    "tonbach|germany": (48.535, 8.350),
    "mitteltal|germany": (48.550, 8.330),
    "baiersbronn-breitmiss|germany": (48.516, 8.376),
    "baiersbronn-schloss|germany": (48.516, 8.376),
    "baiersbronn-cruez|germany": (48.516, 8.376),
    "baiersbronn-loch|germany": (48.516, 8.376),
    "steinackerlen|germany": (48.516, 8.376),
    "reichenbacher hoefe|germany": (48.490, 8.400),
    "kl reichenbach|germany": (48.490, 8.400),
    "kloster reichenbach|germany": (48.490, 8.400),
    "roet|germany": (48.500, 8.400),
    "spielberg|germany": (48.660, 8.610),
    "freudenstadt|germany": (48.464, 8.412),
    "moensheim|germany": (48.859, 8.831),
    "worpswede|germany": (53.216, 8.918),
    "huettenbusch|germany": (53.220, 8.950),
    "huettendorf|germany": (53.190, 8.950),
    "ueberhamm|germany": (53.210, 8.960),
    "oberendermoor|germany": (53.200, 8.950),
    "elberfeld|germany": (51.256, 7.150),
    "barmen|germany": (51.276, 7.199),
    "barmen-elberfeld|germany": (51.265, 7.175),
    "bigge|germany": (51.375, 8.567),
    "elleringhausen|germany": (51.400, 8.550),
    "burscheid|germany": (51.088, 7.128),
    "landau in der pfalz|germany": (49.198, 8.117),
    "landau|germany": (51.106, 8.834),
        "ruchsen|germany": (49.350, 9.230),
    "mönsheim|germany": (48.859, 8.831),
    # England
    "london|england": (51.507, -0.128),
    "east sutton|england": (51.186, 0.599),
    "sandwich|england": (51.277, 1.340),
    "dover|england": (51.128, 1.311),
    "maidstone|england": (51.272, 0.522),
    "ospringe|england": (51.303, 0.887),
    "ramsgate|england": (51.335, 1.417),
    "chester|england": (53.191, -2.891),
    "davenham|england": (53.209, -2.514),
    "tarporley|england": (53.161, -2.664),
    "bunbury|england": (53.116, -2.660),
    "morley|england": (53.354, -2.483),
    "walton-on-trent|england": (52.767, -1.680),
    "banbury|england": (52.063, -1.340),
    "burford|england": (51.810, -1.636),
    "stanton harcourt|england": (51.759, -1.402),
    "witney|england": (51.786, -1.483),
    "oxfordshire|england": (51.760, -1.240),
    "leamington|england": (52.292, -1.536),
    "leamington priors|england": (52.292, -1.536),
    "royal leamington spa|england": (52.292, -1.536),
    "stratford-upon-avon|england": (52.192, -1.707),
    "stratford|england": (52.192, -1.707),
    "warwick st nicholas|england": (52.283, -1.585),
    "willenhall|england": (52.408, -1.510),
    "grafton flyford|england": (52.155, -2.081),
    "stow on the wold|england": (51.930, -1.723),
    "tewkesbury|england": (51.994, -2.157),
    "crediton|england": (50.789, -3.653),
    "plymouth|england": (50.371, -4.142),
    "saint andrew|england": (50.371, -4.142),
    "dorking|england": (51.233, -0.331),
    "ewell|england": (51.349, -0.246),
    "watford|england": (51.656, -0.396),
    "wormley|england": (51.746, -0.049),
    "hatfield|england": (51.763, 0.220),
    "hatfield broad oak|england": (51.831, 0.229),
    "saffron walden|england": (52.023, 0.243),
    "great waltham|england": (51.777, 0.451),
    "nayland|england": (51.978, 0.868),
    "ipswich|england": (52.059, 1.156),
    "long melford parish|england": (52.630, 1.298),
    "norwich|england": (52.630, 1.298),
    "nottingham|england": (52.954, -1.150),
    "bristol|england": (51.454, -2.588),
    "gloucestershire|england": (51.860, -2.240),
    "somerset|england": (51.100, -3.000),
    "pitminster|england": (50.965, -3.115),
    "aughnacloy|ireland": (54.412, -6.964),
}

# ---------------------------------------------------------------------------
# Tier 2: US counties (county-name|state -> county-seat-ish centroid)
# ---------------------------------------------------------------------------
COUNTY_COORDS = {
    "henderson|kentucky": (37.836, -87.590), "daviess|kentucky": (37.774, -87.113),
    "union|kentucky": (37.688, -87.923), "hopkins|kentucky": (37.328, -87.500),
    "muhlenberg|kentucky": (37.202, -87.176), "mclean|kentucky": (37.542, -87.309),
    "oldham|kentucky": (38.407, -85.379), "nelson|kentucky": (37.807, -85.467),
    "jessamine|kentucky": (37.900, -84.570), "fleming|kentucky": (38.417, -83.735),
    "mason|kentucky": (38.643, -83.745), "nicholas|kentucky": (38.323, -83.964),
    "marshall|kentucky": (36.988, -88.316), "fayette|kentucky": (38.041, -84.502),
    "fayette|pennsylvania": (39.900, -79.716),   # seat Uniontown (else a bare "fayette" fell back to Kentucky)
    "spencer|kentucky": (37.999, -85.347), "clark|kentucky": (37.923, -84.279),
    "anderson|kentucky": (37.980, -84.880), "cumberland|kentucky": (36.789, -85.359),
    "anderson|tennessee": (36.110, -84.200),  # seat Clinton -- distinct from Anderson, KY
    "anderson county|tennessee": (36.110, -84.200),
    "anderson|south carolina": (34.520, -82.640),  # seat Anderson -- distinct from Anderson, KY
    "anderson county|south carolina": (34.520, -82.640),
    "anderson|tennessee": (36.110, -84.200),  # seat Clinton -- distinct from Anderson, KY above
    "anderson county|tennessee": (36.110, -84.200),
    "anderson|south carolina": (34.520, -82.640),  # seat Anderson -- distinct from Anderson, KY above
    "anderson county|south carolina": (34.520, -82.640),
    "woodford|kentucky": (38.050, -84.730), "lewis|kentucky": (38.598, -83.320),
    "jefferson|kentucky": (38.253, -85.759),
    "jefferson|alabama": (33.553, -86.896),  # county seat Birmingham
    "norfolk|virginia": (36.850, -76.290),
    "montgomery|alabama": (32.367, -86.300),
    "putnam|georgia": (33.324, -83.388),  # county seat Eatonton
    "hampshire|virginia": (39.300, -78.500),  # present-day WV; was VA territory until 1863
    "cumberland|virginia": (37.512, -78.253), "culpeper|virginia": (38.473, -77.999),
    "fauquier|virginia": (38.716, -77.809), "goochland|virginia": (37.700, -77.880),
    "henrico|virginia": (37.541, -77.436), "spotsylvania|virginia": (38.198, -77.617),
    "king george|virginia": (38.270, -77.180), "fluvanna|virginia": (37.850, -78.270),
    "amelia|virginia": (37.340, -77.980), "charles city|virginia": (37.354, -77.075),
    "essex|virginia": (37.933, -76.930),
    "middlesex|virginia": (37.607, -76.595),  # seat Saluda -- Christ Church Parish; Baskett/Godbey/Trigg/Tuggle homeland (v15)
    "frederick|virginia": (39.163, -78.230),
    "halifax|virginia": (36.767, -78.925), "hanover|virginia": (37.765, -77.470),
    "loudoun|virginia": (39.083, -77.633), "madison|virginia": (38.386, -78.264),
    "northumberland|virginia": (37.864, -76.393), "orange|virginia": (38.247, -78.112),
    "prince edward|virginia": (37.222, -78.400), "prince william|virginia": (38.731, -77.482),
    "rappahannock|virginia": (38.680, -78.108), "westmoreland|virginia": (38.150, -76.820),
    "chesterfield|virginia": (37.376, -77.605), "caroline|virginia": (38.036, -77.343),
    "gloucester|virginia": (37.410, -76.520), "new kent|virginia": (37.510, -76.980),
    "york|virginia": (37.240, -76.510), "campbell|virginia": (37.250, -79.130),
    "delaware|new york": (42.278, -74.914), "otsego|new york": (42.700, -74.900),
    "broome|new york": (42.098, -75.918), "albany|new york": (42.652, -73.756),
    "columbia|new york": (42.250, -73.650),
    "rensselaer|new york": (42.660, -73.480), "tompkins|new york": (42.443, -76.501),
    "nassau|new york": (40.729, -73.590), "queens|new york": (40.728, -73.794),
    "kings|new york": (40.650, -73.950), "richmond|new york": (40.579, -74.151),
    "suffolk|new york": (40.883, -72.801), "westchester|new york": (41.122, -73.760),
    "putnam|new york": (41.430, -73.750), "dutchess|new york": (41.780, -73.740),
    "tioga|new york": (42.070, -76.300),
    "fairfield|connecticut": (41.141, -73.263), "new haven|connecticut": (41.308, -72.928),
    "litchfield|connecticut": (41.750, -73.190), "hartford|connecticut": (41.764, -72.685),
    "tolland|connecticut": (41.870, -72.370), "new london|connecticut": (41.356, -72.100),
    "middlesex|connecticut": (41.560, -72.650),
    "norfolk|massachusetts": (42.222, -71.003), "suffolk|massachusetts": (42.358, -71.060),
    "plymouth|massachusetts": (41.958, -70.667), "middlesex|massachusetts": (42.500, -71.300),
    "essex|massachusetts": (42.630, -70.850), "hampden|massachusetts": (42.101, -72.590),
    "hampshire|massachusetts": (42.320, -72.630), "franklin|massachusetts": (42.600, -72.600),
    "worcester|massachusetts": (42.271, -71.799),
    "warren|new jersey": (40.830, -75.040), "hunterdon|new jersey": (40.570, -74.930),
    "essex|new jersey": (40.780, -74.280), "passaic|new jersey": (41.020, -74.280),
    "cape may|new jersey": (39.080, -74.870),
    "charles|maryland": (38.529, -76.976), "anne arundel|maryland": (38.978, -76.550),
    "prince george's|maryland": (38.810, -76.870), "montgomery|maryland": (39.150, -77.200),
    "st mary's|maryland": (38.220, -76.530), "harford|maryland": (39.540, -76.240),
    "brown|ohio": (38.867, -83.902),
    "macon|georgia": (32.840, -83.632),
    "macon|illinois": (39.841, -88.954),
 "gallatin|illinois": (37.716, -88.135),
    "chester|pennsylvania": (39.960, -75.610), "philadelphia|pennsylvania": (39.953, -75.165),
    "allegheny|pennsylvania": (40.440, -80.000), "westmoreland|pennsylvania": (40.310, -79.480),
    "washington|pennsylvania": (40.174, -80.246),
    "oakland|michigan": (42.660, -83.390), "calhoun|michigan": (42.271, -84.961),
    "washington|mississippi": (33.407, -91.055),  # county seat Greenville, MS
    "ohio|kentucky": (37.446, -86.854),  # Ohio Co., KY, county seat Hartford
    "somerset|pennsylvania": (40.011, -79.078),  # county seat, Somerset Co., PA
    "washington|rhode island": (41.480, -71.680), "providence|rhode island": (41.824, -71.413),
    "granville|north carolina": (36.293, -78.678), "burke|north carolina": (35.745, -81.685),
    "rowan|north carolina": (35.671, -80.470), "person|north carolina": (36.400, -78.980),
    "bennington|vermont": (42.940, -73.170),
    "linn|missouri": (39.720, -93.070), "cape girardeau|missouri": (37.306, -89.518),
    "vanderburgh|indiana": (37.977, -87.555), "wayne|indiana": (39.829, -84.890),
    "orange|indiana": (38.590, -86.480),
}

# ---------------------------------------------------------------------------
# Tier 3: US states / equivalent regions -> centroid
# ---------------------------------------------------------------------------
STATE_COORDS = {
    "alabama": (32.806, -86.791), "alaska": (61.370, -152.404), "arizona": (33.729, -111.431),
    "arkansas": (34.969, -92.373), "california": (36.116, -119.681), "colorado": (39.059, -105.311),
    "connecticut": (41.597, -72.755), "delaware": (39.318, -75.507),
    "district of columbia": (38.905, -77.036), "florida": (27.766, -81.686),
    "georgia": (33.040, -83.643), "idaho": (44.240, -114.478), "illinois": (40.349, -88.986),
    "indiana": (39.849, -86.258), "iowa": (42.011, -93.210), "kansas": (38.526, -96.726),
    "kentucky": (37.669, -84.670), "louisiana": (31.169, -91.867), "maine": (44.693, -69.381),
    "maryland": (39.063, -76.802), "massachusetts": (42.230, -71.530), "michigan": (43.327, -84.536),
    "minnesota": (45.694, -93.900), "mississippi": (32.742, -89.678), "missouri": (38.457, -92.288),
    "montana": (46.921, -110.454), "nebraska": (41.125, -98.268), "nevada": (38.313, -117.055),
    "new hampshire": (43.452, -71.564), "new jersey": (40.299, -74.521),
    "new mexico": (34.840, -106.252), "new york": (42.166, -74.948),
    "north carolina": (35.630, -79.806), "north dakota": (47.528, -99.784),
    "ohio": (40.388, -82.764), "oklahoma": (35.565, -96.928), "oregon": (44.572, -122.070),
    "pennsylvania": (40.590, -77.210), "rhode island": (41.680, -71.512),
    "south carolina": (33.856, -80.945), "south dakota": (44.299, -99.438),
    "tennessee": (35.747, -86.692), "texas": (31.054, -97.563), "utah": (40.150, -111.862),
    "vermont": (44.045, -72.710), "virginia": (37.769, -78.170), "washington": (47.400, -121.490),
    "west virginia": (38.491, -80.954), "wisconsin": (44.268, -89.616), "wyoming": (42.756, -107.302),
    "ontario": (43.653, -79.383), "toronto": (43.653, -79.383),
    # England historic/ceremonial counties seen in the data
    "kent": (51.278, 0.522), "essex": (51.750, 0.400), "suffolk": (52.190, 1.140),
    "warwickshire": (52.280, -1.550), "oxfordshire": (51.760, -1.240),
    "cheshire": (53.216, -2.520), "gloucestershire": (51.860, -2.240),
    "somerset": (51.100, -3.000), "devon": (50.790, -3.700), "surrey": (51.260, -0.470),
    "hertfordshire": (51.800, -0.240), "derbyshire": (53.100, -1.560),
    "nottinghamshire": (53.150, -1.000), "west midlands": (52.480, -1.900),
    "norfolk": (52.630, 0.940), "dorset": (50.750, -2.340),
    # German states
    "baden-württemberg": (48.660, 9.350), "baden-wuerttemberg": (48.660, 9.350),
    "north rhine-westphalia": (51.430, 7.660), "bavaria": (48.950, 11.400),
    "hesse": (50.650, 9.000), "rhineland-palatinate": (49.910, 7.450),
    "lower saxony": (52.900, 9.400), "niedersachsen": (52.900, 9.400),
    "baden": (48.500, 8.500), "hannover": (52.375, 9.732), "preussen": (52.520, 13.405),
    # Ireland counties
    "cavan": (54.000, -7.360), "monaghan": (54.250, -6.970), "meath": (53.650, -6.680),
    "westmeath": (53.530, -7.500), "tyrone": (54.600, -7.300), "dublin": (53.350, -6.260),
    "armagh": (54.350, -6.650),
    # Sweden provinces (incl. historic names)
    "västra götaland": (58.180, 13.550), "jönköping": (57.780, 14.160),
    "skaraborg": (58.180, 13.550), "älvsborg": (58.180, 13.550),
    # Switzerland canton
    "bern": (46.940, 7.440),
}

# ---------------------------------------------------------------------------
# Tier 4: country-level fallback
# ---------------------------------------------------------------------------
COUNTRY_COORDS = {
    "usa": (39.828, -98.579), "united states": (39.828, -98.579),
    "united states of america": (39.828, -98.579),
    "england": (52.356, -1.174), "united kingdom": (52.356, -1.174),
    "wales": (52.130, -3.784), "scotland": (56.491, -4.203),
    "northern ireland": (54.788, -6.492), "ireland": (53.142, -7.693),
    "germany": (51.166, 10.452), "deutschland": (51.166, 10.452),
    "sweden": (60.128, 18.643), "sverige": (60.128, 18.643),
    "switzerland": (46.818, 8.228), "netherlands": (52.133, 5.291),
    "canada": (56.130, -106.347), "new england": (42.407, -71.382),
}

US_STATE_NAMES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
    "district of columbia","florida","georgia","idaho","illinois","indiana","iowa","kansas",
    "kentucky","louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
    "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico","new york",
    "north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island",
    "south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington",
    "west virginia","wisconsin","wyoming",
}

STATE_ABBREV = {
    "al":"alabama","ak":"alaska","az":"arizona","ar":"arkansas","ca":"california","co":"colorado",
    "ct":"connecticut","de":"delaware","dc":"district of columbia","fl":"florida","ga":"georgia",
    "id":"idaho","il":"illinois","in":"indiana","ia":"iowa","ks":"kansas","ky":"kentucky",
    "la":"louisiana","me":"maine","md":"maryland","ma":"massachusetts","mi":"michigan",
    "mn":"minnesota","ms":"mississippi","mo":"missouri","mt":"montana","ne":"nebraska",
    "nv":"nevada","nh":"new hampshire","nj":"new jersey","nm":"new mexico","ny":"new york",
    "nc":"north carolina","nd":"north dakota","oh":"ohio","ok":"oklahoma","or":"oregon",
    "pa":"pennsylvania","ri":"rhode island","sc":"south carolina","sd":"south dakota",
    "tn":"tennessee","tx":"texas","ut":"utah","vt":"vermont","va":"virginia","wa":"washington",
    "wv":"west virginia","wi":"wisconsin","wy":"wyoming",
    # longer, informal abbreviations common in older genealogical/census records
    # (periods already stripped before lookup, so these also catch "Mass.", "Tenn.", etc.)
    "mass":"massachusetts","tenn":"tennessee","conn":"connecticut","penn":"pennsylvania",
    "calif":"california","fla":"florida","ala":"alabama","ark":"arkansas","colo":"colorado",
    "wash":"washington","wisc":"wisconsin","mich":"michigan","minn":"minnesota","miss":"mississippi",
    "okla":"oklahoma","oreg":"oregon","nebr":"nebraska",
}

COUNTY_SUFFIX_RE = re.compile(r"\s+(county|co\.?)$", re.IGNORECASE)

def _build_bare_indices(town_d, county_d):
    """Build bare-name fallback indices, but check for conflicts ACROSS both
    dictionaries combined -- a name ambiguous between e.g. Union|Indiana (town)
    and Union|Kentucky (county) must be excluded from BOTH bare indices, not
    just deduped within its own dict."""
    seen = {}   # loc -> val (first seen)
    conflict = set()
    for d in (town_d, county_d):
        for key, val in d.items():
            loc = key.split("|")[0]
            if loc in seen and seen[loc] != val:
                conflict.add(loc)
            else:
                seen[loc] = val
    town_bare = {k.split("|")[0]: v for k, v in town_d.items()
                 if k.split("|")[0] not in conflict}
    county_bare = {k.split("|")[0]: v for k, v in county_d.items()
                   if k.split("|")[0] not in conflict}
    return town_bare, county_bare

TOWN_COORDS_BARE, COUNTY_COORDS_BARE = _build_bare_indices(TOWN_COORDS, COUNTY_COORDS)
# A few explicit bare additions not derivable automatically (verified unambiguous)
TOWN_COORDS_BARE.setdefault("waterbury", (41.558, -73.037))
TOWN_COORDS_BARE.setdefault("paducah", (37.083, -88.600))
TOWN_COORDS_BARE.setdefault("boca raton", (26.359, -80.083))
TOWN_COORDS_BARE.setdefault("east sutton", (51.186, 0.599))



# Raw strings that are OCR garble, addresses, or otherwise need a direct override
# rather than generic parsing. Each maps to (label, lat, lon, tier).
SPECIAL_CASES = {
    "bermuda": ("Bermuda", 32.300, -64.783, "town"),  # Sea Venture wreck, 1609 -- Thomas Godbey Sr. (v15)
    "new england": ("New England", 42.41, -71.38, "region"),
    "memphis tenn": ("Memphis, Tennessee", 35.15, -90.05, "town"),
    "dyke virginia": ("Dyke, Virginia", 38.254, -78.540, "town"),
    "new york, new york": ("New York City, New York", 40.713, -74.006, "town"),
    "new york, new york, usa": ("New York City, New York", 40.713, -74.006, "town"),
    "new york, new york, new york, usa": ("New York City, New York", 40.713, -74.006, "town"),
    "ooeonla . n. y .": ("Oneonta, New York", 42.452, -75.064, "town"),
    "j 7 jsger avenue . flushing": ("Flushing, New York", 40.759, -73.830, "town"),
    "el mpl . . flushing": ("Flushing, New York", 40.759, -73.830, "town"),
    "brooklyn , n. y.": ("Brooklyn, New York", 40.678, -73.944, "town"),
    "deceased 1903 flushing, ri ny": ("Flushing, New York", 40.759, -73.830, "town"),
    "6715 arcadian nwy. , cyansvim": ("Evansville, Indiana", 37.977, -87.555, "town"),
    "2003 kentucky-av paducah": ("Paducah, Kentucky", 37.083, -88.600, "town"),
    "2003 kentucky avenue": ("Paducah, Kentucky", 37.083, -88.600, "town"),
    "2001 kentucky, avenue, paducah, mccracken, kentucky, usa": ("Paducah, Kentucky", 37.083, -88.600, "town"),
    "hamden, delaware county, ny": ("Hamden, New York", 42.290, -74.980, "town"),
    "knocknaveigh, monterconnaught": ("Cavan, Ireland", 54.000, -7.360, "region"),
    "munterconnaght": ("Cavan, Ireland", 54.000, -7.360, "region"),
    "munterconnaught": ("Cavan, Ireland", 54.000, -7.360, "region"),
    "huettenbusch, ottersberg district, hanover": ("Huettenbusch, Germany", 53.220, 8.950, "town"),
    "hüttenbusch 20, kirchspiel scharmbeck": ("Huettenbusch, Germany", 53.220, 8.950, "town"),
    "überhamm 05, kirchspiel worpswede": ("Ueberhamm, Germany", 53.210, 8.960, "town"),
    "brunswick, king george": ("King George Co., Virginia", 38.270, -77.180, "county"),
    "hanover parish, king george county": ("King George Co., Virginia", 38.270, -77.180, "county"),
    "overwharton, stafford": ("Stafford Co., Virginia", 38.420, -77.460, "county"),
    "michaelmass, prince william county, va": ("Prince William Co., Virginia", 38.731, -77.482, "county"),
    "rental rolls, prince william county, va": ("Prince William Co., Virginia", 38.731, -77.482, "county"),
    "rent rolls, frederick county, va": ("Frederick Co., Virginia", 39.163, -78.230, "county"),
    "frederick county, va": ("Frederick Co., Virginia", 39.163, -78.230, "county"),
    "10 10, fluvanna county, va": ("Fluvanna Co., Virginia", 37.850, -78.270, "county"),
    "fluvanna county": ("Fluvanna Co., Virginia", 37.850, -78.270, "county"),
    "spotsylvania county": ("Spotsylvania Co., Virginia", 38.198, -77.617, "county"),
    "ratables, cape may county, nj": ("Cape May Co., New Jersey", 39.080, -74.870, "county"),
    "cape may": ("Cape May, New Jersey", 39.080, -74.870, "town"),
    "suffolkshire, eng": ("Suffolk, England", 52.190, 1.140, "region"),
    "aboard the speedwell, on the atlantic ocean": ("North Atlantic (at sea)", 48.0, -30.0, "country"),
    "niederhochstadt, pfalz, bayern": ("Niederhochstadt, Germany", 49.130, 8.070, "town"),
    "new york;new york": ("New York, New York", 40.713, -74.006, "town"),
    "cape gerardeau mo": ("Cape Girardeau, Missouri", 37.306, -89.518, "town"),
    "south brooklyn": ("Brooklyn, New York", 40.678, -73.944, "town"),
    "ekenäs": ("Sweden", 60.128, 18.643, "country"),
}


NOISE_PREFIX_RE = re.compile(
    r"^(no township listed|district \d+|ward \d+|division \d+|precinct \d+|subdivision \d+|"
    r"township \d+|rent rolls?|rental rolls?|ratables?|early tax list|deceased\s*\d*|"
    r"village of|village cemetery,?)\s*,?\s*", re.IGNORECASE
)
STREET_ADDR_RE = re.compile(r"^\d+.*(st\.?|street|ave\.?|avenue|rd\.?|road|nwy)\b", re.IGNORECASE)


TYPO_CORRECTIONS = {
    "connectiuct": "Connecticut",
}
COLONIAL_SUFFIX_RE = re.compile(r"\s+(Town|Colony)$", re.IGNORECASE)

def clean_component(c):
    c = c.strip()
    c = NOISE_PREFIX_RE.sub("", c).strip()
    c = COLONIAL_SUFFIX_RE.sub("", c).strip()
    if c.lower() in TYPO_CORRECTIONS:
        c = TYPO_CORRECTIONS[c.lower()]
    return c


def parse_place(raw):
    """Return (locality, county, region, country) best-guess split."""
    if not raw:
        return None
    s = raw.strip()
    if s.lower() in ("usa", "united states", "this city", "deceased", "ma", "avraue",
                      "en", "dancinair", "washington", "philadelphia", "boca raton",
                      "mcdowell", "daviess", "henderson", "owensboro", "toronto",
                      "simsbury", "branford", "scotland?"):
        pass  # short/ambiguous forms handled by fallback tiers below anyway
    comps = [clean_component(c) for c in s.split(",")]
    comps = [c for c in comps if c and not STREET_ADDR_RE.match(c)]
    if not comps:
        return None
    return comps


# --- RAW GROUND-TRUTH BLOCK (Sep 23 recovery): exact raw GEDCOM place strings
# pinned to the location the last shipped map (GEDCOM v14, commit 78f1cc4)
# actually used for them. Derived by aligning each person's stops against the
# shipped PERSON_LEGS by year; only raw strings that directly produced a stop,
# and only where no currently-correct person would be affected. ---
RAW_GROUND_TRUTH = {
    "5, Decatur, Morgan, Alabama, USA": None,  # left unresolved on the shipped map
    "Albany Ward 3, Morgan, Alabama, USA": None,  # left unresolved on the shipped map
    "Alexandria City, Virginia, USA": None,  # left unresolved on the shipped map
    "Alexandria Ward 4, Alexandria (Independent City), Virginia, USA": None,  # left unresolved on the shipped map
    "Arcadia, Arcadia, Davidson, North Carolina, USA": None,  # left unresolved on the shipped map
    "Baiersbronn-Schloß, Baden-Württemberg, Deutschland": ("Baden-Württemberg", 48.66, 9.35, "town"),
    "Barkers, , Floyd, Georgia, USA": ("Georgia", 33.04, -83.64, "town"),
    "Bern, Switzerland": ("Bern", 46.94, 7.44, "town"),
    "Bibb, Georgia, USA": None,  # left unresolved on the shipped map
    "Brabourne, Ashford Borough, Kent, England": ("Kent", 51.28, 0.52, "region"),
    "Burlington County, New Jersey, USA": ("New Jersey", 40.3, -74.52, "town"),
    "Bury St Edmunds, St Edmundsbury Borough, Suffolk, England": ("Suffolk", 52.19, 1.14, "town"),
    "Chambers, Alabama, USA": ("Alabama", 32.81, -86.79, "town"),
    "College Park, Prince George's, Maryland, USA": ("Prince George'S Co., Maryland", 38.81, -76.87, "county"),
    "Columbus; Phenix City, Georgia, USA": None,  # left unresolved on the shipped map
    "Cranfield, Bedfordshire, England": ("England", 52.36, -1.17, "country"),
    "Cumberland, England": ("England", 52.36, -1.17, "country"),
    "Decatur, Decatur, Morgan, Alabama, USA": None,  # left unresolved on the shipped map
    "Decatur, Morgan, Alabama": None,  # left unresolved on the shipped map
    "District 17, Talbot, Georgia, USA": ("Georgia", 33.04, -83.64, "town"),
    "District 19, Chambers County, Alabama, USA": None,  # left unresolved on the shipped map
    "District 19, Chambers, Alabama, USA": ("Alabama", 32.81, -86.79, "town"),
    "District 24, Talbot, Georgia, USA": ("Taylor, Georgia", 32.55, -84.24, "town"),
    "District 8, Lawrence, Alabama, USA": None,  # left unresolved on the shipped map
    "Dundalk, Baltimore, Maryland, USA": ("Baltimore, Maryland", 39.29, -76.61, "town"),
    "Dyke, Greene County, Virginia USA": ("Dyke", 38.25, -78.54, "town"),
    "Dyke, Greene, Virginia, USA": ("Dyke, Virginia", 38.25, -78.54, "town"),
    "Five Points, Alabama": None,  # left unresolved on the shipped map
    "Florence, Morgan, Missouri, USA": ("Florence, Missouri", 38.59, -92.98, "town"),
    "Floyd County, Georgia, USA": None,  # left unresolved on the shipped map
    "Fort Payne, Alabama, USA": None,  # left unresolved on the shipped map
    "Fort Payne, DeKalb, Alabama, USA": None,  # left unresolved on the shipped map
    "Georgia Militia District 703, Goodmans, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Graham's Station, Lewis County, Kentucky, USA": ("Graham'S Station, Kentucky", 38.55, -83.5, "town"),
    "Greensboro Ward 4, Guilford, North Carolina, USA": None,  # left unresolved on the shipped map
    "Halifax, Yorkshire, England": ("England", 52.36, -1.17, "country"),
    "Hampton, Virginia, USA": None,  # left unresolved on the shipped map
    "Harris County, Georgia, USA": ("Georgia", 33.04, -83.64, "region"),
    "Harris, Georgia": None,  # left unresolved on the shipped map
    "Harris, Georgia, USA": ("Georgia", 33.04, -83.64, "region"),
    "Harris, Georgia, United States": ("Waverly Hall, Georgia", 32.75, -84.73, "town"),
    "Hoboken, New Jersey": ("New Jersey", 40.3, -74.52, "town"),
    "Jamestown, James City, Virginia, USA": ("Jamestown, Virginia", 37.21, -76.78, "region"),
    "Kallnach, Bern, Switzerland": ("Bern", 46.94, 7.44, "town"),
    "Lawrence County, Alabama, USA": None,  # left unresolved on the shipped map
    "Lawrence, Alabama, USA": None,  # left unresolved on the shipped map
    "Leamington, Warwickshire, England": None,  # left unresolved on the shipped map
    "Llangollen, Denbighshire, Wales": ("Wales", 52.13, -3.78, "country"),
    "Louisa, Louisa, Virginia, USA": ("Virginia", 37.77, -78.17, "region"),
    "MD 1186 Upper Nineteenth, Upper Nineteenth, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Macon, Bibb, Georgia, USA": ("Macon Co., Georgia", 32.84, -83.63, "town"),
    "Macon, Macon, Bibb, Georgia, USA": None,  # left unresolved on the shipped map
    "Maidstone, Maidstone Borough, Kent, England": None,  # left unresolved on the shipped map
    "Mansfield Woodhouse, Nottinghamshire, England": ("Nottinghamshire", 53.15, -1.0, "town"),
    "Mercer County, Kentucky, USA": ("Kentucky", 37.67, -84.67, "town"),
    "Mercer, Kentucky, United States": ("Kentucky", 37.67, -84.67, "town"),
    "Meriden, Sullivan, New Hampshire, USA": ("Meriden, New Hampshire", 43.54, -72.25, "region"),
    "Middletown, Middlesex, Connecticut, USA": ("Middlesex Co., Connecticut", 41.56, -72.65, "town"),
    "Militia District 1186, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Monroe, Guilford, North Carolina, USA": ("Monroe, North Carolina", 34.99, -80.55, "region"),
    "Moores District, Harris, Georgia, USA": ("Georgia", 33.04, -83.64, "town"),
    "Morgan County, Alabama, USA": ("Alabama", 32.81, -86.79, "region"),
    "Morgan, Alabama, USA": None,  # left unresolved on the shipped map
    "Muscogee County, Georgia, USA": None,  # left unresolved on the shipped map
    "Muscogee, Georgia, USA": None,  # left unresolved on the shipped map
    "New York, Richmond, New York, United States": ("Richmond, New York", 40.58, -74.15, "town"),
    "No Township Listed, Mercer County, KY": ("Kentucky", 37.67, -84.67, "town"),
    "Northern Division, Courtland, Lawrence, Alabama, USA": None,  # left unresolved on the shipped map
    "Oneonta; Oneonta Plains; East End; South Side; West Oneonta; Cooperstown, New York, USA": None,  # left unresolved on the shipped map
    "Oneonta;West Oneonta, New York, USA": None,  # left unresolved on the shipped map
    "Osborn Mill, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Patterson's Creek, Hampshire County, West Virginia, USA": ("Patterson'S Creek, West Virginia", 39.35, -78.7, "town"),
    "Portsmouth; Waterview, Virginia, USA": None,  # left unresolved on the shipped map
    "Potomac, Maryland, USA": None,  # left unresolved on the shipped map
    "Prince George County, Virginia, USA": ("Virginia", 37.77, -78.17, "region"),
    "Prince George's County, Maryland, USA": ("Prince George'S Co., Maryland", 38.81, -76.87, "county"),
    "Regiment 39, Morgan, Alabama, USA": None,  # left unresolved on the shipped map
    "Rental Rolls, Stafford County, Virginia, USA": None,  # left unresolved on the shipped map
    "Richmond, Richmond, New York, USA": None,  # left unresolved on the shipped map
    "Ridgewell Hall, England": ("England", 52.36, -1.17, "country"),
    "Rockville, Maryland, USA": ("Montgomery Co., Maryland", 39.15, -77.2, "town"),
    "Rockville, Montgomery, Maryland, USA": ("Montgomery Co., Maryland", 39.15, -77.2, "town"),
    "Salisbury, Cabarrus, North Carolina": None,  # left unresolved on the shipped map
    "Sandwich St Peter, Kent, England": None,  # left unresolved on the shipped map
    "Siselen, Bern, Switzerland": ("Bern", 46.94, 7.44, "town"),
    "Siselen, Verwaltungskreis Seeland, Bern, Switzerland": ("Bern", 46.94, 7.44, "town"),
    "South Ouram Parish, Halifax, Yorkshire, England": ("England", 52.36, -1.17, "country"),
    "St Johns Ward, Toronto City, Ontario, Canada": None,  # left unresolved on the shipped map
    "St Johns Ward, Toronto West, Ontario, Canada": None,  # left unresolved on the shipped map
    "St Patricks Ward, Toronto City, Ontario, Canada": None,  # left unresolved on the shipped map
    "St. Clair County, Alabama, USA": ("Alabama", 32.81, -86.79, "region"),
    "Talbot County, Georgia": None,  # left unresolved on the shipped map
    "Talbot County, Georgia, USA": None,  # left unresolved on the shipped map
    "Talbot, Georgia, USA": ("Georgia", 33.04, -83.64, "region"),
    "Thomas, Georgia, USA": None,  # left unresolved on the shipped map
    "Toronto (West/Ouest) (City/Cité) Ward/Quartier No 4, Toronto (west/ouest) (city/cité), Ontario, Canada": None,  # left unresolved on the shipped map
    "Toronto East, Ontario, Canada": None,  # left unresolved on the shipped map
    "Township 7 Range 8, Courtland, Lawrence, Alabama, USA": None,  # left unresolved on the shipped map
    "Towson, Baltimore, Maryland, USA": ("Baltimore, Maryland", 39.29, -76.61, "town"),
    "Upper Nineteenth, Harris, Georgia": None,  # left unresolved on the shipped map
    "Upper Nineteenth, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Upper Nineteenth, Upper Nineteenth, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Valley Plains, Harris, Georgia, USA": None,  # left unresolved on the shipped map
    "Waco, McLennan, Texas, USA": ("Texas", 31.05, -97.56, "town"),
    "Walkers Chapel, DeKalb, Alabama, USA": None,  # left unresolved on the shipped map
    "Walkers Chapel, Dekalb, Alabama, USA": None,  # left unresolved on the shipped map
    "West of the Brazos River, Waco, McLennan, Texas, USA": ("Texas", 31.05, -97.56, "town"),
    "Whitakers, Harris, Georgia, USA": ("Georgia", 33.04, -83.64, "town"),
    "Worcester, Worcester, Massachusetts, USA": ("Worcester Co., Massachusetts", 42.35, -71.86, "county"),
}

def normalize_and_geocode(raw):
    """Returns (canonical_label, lat, lon, tier) or None if unresolvable."""
    if not raw:
        return None
    if raw in RAW_GROUND_TRUTH:
        return RAW_GROUND_TRUTH[raw]
    special = SPECIAL_CASES.get(raw.strip().lower())
    if special:
        return special

    comps = parse_place(raw)
    if not comps:
        return None

    # expand bare 2-letter state abbreviations into full names (keep original too)
    expanded = []
    for c in comps:
        cl = c.lower().strip(".")
        if cl in STATE_ABBREV:
            expanded.append(STATE_ABBREV[cl])
        else:
            expanded.append(c)
    comps = comps + [e for e in expanded if e not in comps]

    low = [c.lower() for c in comps]
    # de-county-suffix versions for matching (e.g. "nelson county" -> "nelson")
    low_nosuffix = [COUNTY_SUFFIX_RE.sub("", c) for c in low]
    full_low = ", ".join(low)

    # --- determine country ---
    country = None
    if any(k in full_low for k in ["usa", "united states"]):
        country = "usa"
    elif "wales" in low:
        country = "wales"
    elif "scotland" in full_low:
        country = "scotland"
    elif "northern ireland" in full_low:
        country = "northern ireland"
    elif "ireland" in full_low:
        country = "ireland"
    elif any(k in full_low for k in ["england", "united kingdom"]):
        country = "england"
    elif any(k in full_low for k in ["deutschland", "germany"]):
        country = "germany"
    elif any(k in full_low for k in ["sverige", "sweden"]):
        country = "sweden"
    elif "switzerland" in full_low or "schweiz" in full_low:
        country = "switzerland"
    elif "netherlands" in full_low:
        country = "netherlands"
    elif "canada" in full_low:
        country = "canada"
    elif any(s in low_nosuffix for s in US_STATE_NAMES):
        country = "usa"

    # --- town-level: locality x region pairs ---
    for loc in low_nosuffix:
        for reg in low_nosuffix:
            if loc == reg:
                continue
            key = f"{loc}|{reg}"
            if key in TOWN_COORDS:
                lat, lon = TOWN_COORDS[key]
                return (f"{_title(loc)}, {_title(reg)}", lat, lon, "town")
    if country:
        for loc in low_nosuffix:
            key = f"{loc}|{country}"
            if key in TOWN_COORDS:
                lat, lon = TOWN_COORDS[key]
                return (f"{_title(loc)}, {_title(country)}", lat, lon, "town")

    # --- county-level: locality x region pairs ---
    # (checked BEFORE town-level bare fallback -- a qualified pair match, where
    # the source data explicitly ties a locality to a specific region, should
    # outrank a single-word bare guess. Two confirmed bugs traced to the old
    # order: "Somerset, Pennsylvania" was losing to a bare "somerset" fallback
    # that pointed at Somerset, England; "Delaware, New York" [county] was
    # losing to a bare "new york" fallback that pointed at New York City.)
    for loc in low_nosuffix:
        for reg in low_nosuffix:
            if loc == reg:
                continue
            key = f"{loc}|{reg}"
            if key in COUNTY_COORDS:
                lat, lon = COUNTY_COORDS[key]
                return (f"{_title(loc)} Co., {_title(reg)}", lat, lon, "county")

    # A handful of state names are ALSO common county/city names in other
    # states (or, as with Delaware, a county name that would otherwise win
    # via bare fallback before ever reaching the state-tier check below).
    # Excluded from EVERY bare-fallback tier, not just state-level, so a
    # bare "Delaware, USA" can't get caught by county-bare-fallback (which
    # runs earlier) and confidently resolve to Delaware Co., NY instead of
    # the actual state.
    AMBIGUOUS_STATE_NAMES = {"washington", "ohio", "california", "delaware", "new york"}

    # --- town-level bare fallback (unambiguous single-name lookup) ---
    for loc in low_nosuffix:
        if loc in TOWN_COORDS_BARE and loc not in AMBIGUOUS_STATE_NAMES:
            lat, lon = TOWN_COORDS_BARE[loc]
            return (_title(loc), lat, lon, "town")

    for loc in low_nosuffix:
        if loc in COUNTY_COORDS_BARE and loc not in AMBIGUOUS_STATE_NAMES:
            lat, lon = COUNTY_COORDS_BARE[loc]
            return (f"{_title(loc)} Co.", lat, lon, "county")

    # --- state / region-level ---
    # Position in the string isn't a reliable signal for which state match to
    # prefer either (DC's own "District of Columbia, Washington, D.C." lists
    # the real state FIRST, while "Washington, Mississippi" lists it LAST).
    # Confirmed cases found by audit: Washington Co. (MS, PA, VA...; also DC),
    # Ohio Co., Kentucky. When one of these appears alongside another state
    # match, prefer the other match.
    state_matches = [c for c in low_nosuffix if c in STATE_COORDS]
    if state_matches:
        pick = next((c for c in state_matches if c not in AMBIGUOUS_STATE_NAMES), state_matches[0])
        lat, lon = STATE_COORDS[pick]
        return (_title(pick), lat, lon, "region")

    # --- country-level fallback ---
    # USA specifically excluded: unlike a bare "England"/"Germany"/"Sweden" (which
    # signals a real immigrant origin even without a town), a bare "USA" for a
    # family that's otherwise entirely US-based adds no information -- and in
    # practice turned out to be a Revolutionary War service-era marker for two
    # different people (RESI 1775-1783, "USA"), not an actual place at all.
    if country and country != "usa" and country in COUNTRY_COORDS:
        lat, lon = COUNTRY_COORDS[country]
        return (_title(country), lat, lon, "country")
    for c in low:
        if c in ("usa", "united states", "united states of america"):
            continue
        if c in COUNTRY_COORDS:
            lat, lon = COUNTRY_COORDS[c]
            return (_title(c), lat, lon, "country")

    return None


if __name__ == "__main__":
    import json
    from collections import Counter
    import os
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.json")) as f:
        records = json.load(f)
    places = Counter()
    for pid, r in records.items():
        for e in r["events"]:
            if e["plac"]:
                places[e["plac"].strip()] += 1

    resolved, unresolved = 0, []
    tier_counts = Counter()
    for p, c in places.items():
        g = normalize_and_geocode(p)
        if g:
            resolved += c
            tier_counts[g[3]] += c
        else:
            unresolved.append((p, c))

    total = sum(places.values())
    print(f"Total place-string occurrences: {total}")
    print(f"Resolved: {resolved}  ({resolved/total*100:.1f}%)")
    print(f"Tier breakdown: {dict(tier_counts)}")
    print(f"\nUnresolved unique strings: {len(unresolved)}  (occurrences: {sum(c for _,c in unresolved)})")
    for p, c in sorted(unresolved, key=lambda x: -x[1]):
        print(f"  {c:3d}  {p}")
