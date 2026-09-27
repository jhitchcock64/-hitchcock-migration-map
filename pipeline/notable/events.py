"""
Notable events in the family's history: hand-authored, from James's "Our
American History" (2026) and research with him (September 2026).
build2/build_notable.py adds every documented ocean arrival (from the
migrations) and writes notable_prepared.json -> NOTABLE in data.js.

Each event:
  pids    the ancestors it's about (GEDCOM individual IDs); the page shows an
          event when any of them is an ancestor of the current target, and says
          how the first is related to the target ("11th great-grandfather")
  date    as the source gives it; year for sorting
  text    neutral wording: no "your" (the target changes)
  place, lat, lon
  kind    'event', 'arrival' (a landing: shown as its own pin and still drawn as
          a movement) or 'story' (family tradition)
  source  what it rests on
  ship    for an arrival: the ship, where known (joins the automatic arrival
          of the same person and year instead of adding a second pin)

Military service lives in pipeline/military/itineraries.py, not here.
Genealogical facts belong in James's tree; corrections to the source
document are noted per event.
"""

DOC = '"Our American History" (family history, 2026)'

# People whose ocean crossing in the migrations should not get an arrival pin
# (James, 2026-09-27: Margaret Barker's "1600" arrival is not an arrival).
NO_ARRIVAL = {'@I242789067812@'}


def E(pids, date, year, text, place, lat, lon, kind='event', source=DOC, ship=None, on=None):
    """on=(pid, year, fraction): the event happened partway along that person's move
    in that year (a birth at sea); the page pins it on the move as drawn, and
    lat/lon is only a fallback."""
    return dict(pids=pids if isinstance(pids, list) else [pids], date=date, year=year, text=text,
                place=place, lat=lat, lon=lon, kind=kind, source=source, ship=ship, on=on)


EVENTS = [
    # ------------------------------------------------ landings (also on the migrations)
    E('@I242790089255@', '10 June 1610', 1610,
      'William Coxe arrives at Jamestown aboard the Godspeed, the earliest known arrival in the family.',
      'Jamestown, VA', 37.209, -76.778, 'arrival', ship='Godspeed'),
    E('@I242798835405@', 'May 1610', 1610,
      'Thomas Godbey Sr. reaches Jamestown aboard the Deliverance, built on Bermuda by the survivors of the '
      'Sea Venture, wrecked there in 1609.',
      'Jamestown, VA', 37.209, -76.778, 'arrival', source='James\'s research (Sea Venture and Deliverance)',
      ship='Deliverance'),
    E('@I242798835405@', 'July 1609', 1609,
      'The Sea Venture, carrying Thomas Godbey Sr. to Virginia, is wrecked on Bermuda in a hurricane. The '
      'survivors build two small ships, the Deliverance and the Patience, and sail on to Jamestown in 1610.',
      'Bermuda', 32.36, -64.68, source='James\'s research (Sea Venture and Deliverance)'),
    E('@I242215851600@', 'February 1613', 1613,
      'John Clay arrives at Jamestown aboard the Treasurer.',
      'Jamestown, VA', 37.209, -76.778, 'arrival', ship='Treasurer'),
    E(['@I240016598442@', '@I240016598449@', '@I240016598649@'], '21 November 1620', 1620,
      'John Alden, Priscilla Mullins and her father William Mullins arrive at Plymouth aboard the Mayflower.',
      'Plymouth, MA', 41.958, -70.662, 'arrival', ship='Mayflower'),
    E('@I240016598649@', '1621', 1621,
      'William Mullins and his wife Alice die in the first winter at Plymouth, leaving their daughter '
      'Priscilla the family\'s only survivor.',
      'Plymouth, MA', 41.958, -70.662),
    E('@I240015598370@', 'Spring 1635', 1635,
      'Matthias Hitchcock, a Puritan, presumably, arrives in Massachusetts Bay aboard the Susan and Ellen.',
      'Boston, MA', 42.360, -71.058, 'arrival', ship='Susan and Ellen'),
    E(['@I242216133556@', '@I242649435364@'], 'about June 1635', 1635,
      'Thomas "the Seagull" Green is born at sea aboard the Speedwell, which sailed from Southampton in May '
      '1635 with his parents and reached Virginia in July.',
      'At sea, bound for Virginia', 37.5, -50.0, 'arrival', ship='Speedwell',
      on=('@I242649435364@', 1635, 0.5)),

    # ------------------------------------------------ colonial New England
    E('@I240015598370@', '4 June 1639', 1639,
      'Matthias Hitchcock signs New Haven\'s Fundamental Agreement, the colony\'s founding constitution of '
      'self-government.',
      'New Haven, CT', 41.308, -72.928),
    E('@I242580129689@', '1655', 1655,
      'Thomas Welles is elected governor of Connecticut Colony. He remains the only person in the state\'s history '
      'to hold all four of its senior offices: governor, deputy governor, treasurer and secretary.',
      'Hartford, CT', 41.766, -72.673),
    E('@I242178845880@', '1659', 1659,
      'Andrew Warner moves into the wilderness at Hadley, part of a migration up the Connecticut River with '
      'several early New England families.',
      'Hadley, MA', 42.341, -72.588),
    E('@I240015598365@', '7 April 1689', 1689,
      'Eliakim Hitchcock is baptized as an adult at the First Congregational Society in New Haven.',
      'New Haven, CT', 41.308, -72.928),
    E('@I240020574041@', '1707', 1707,
      'John Bostwick Jr. arrives at New Milford, Connecticut, its second settler, and is soon elected to several '
      'town offices.',
      'New Milford, CT', 41.577, -73.408),

    # ------------------------------------------------ Virginia and the South
    E('@I242611467041@', '1663', 1663,
      'Vestryman Henry Pitt hires John Askew, a hog farmer, tanner and carpenter on Reynolds Creek, to build the '
      'church at Pagan Point, Isle of Wight County. Askew is soon charged with stealing the lumber, and his '
      'neighbors\' testimony, full of cider and quarrels, opens a 2006 study of class in early Virginia.',
      'Pagan Point, Isle of Wight Co., VA', 36.983, -76.633,
      source='Peter Thompson, "The Thief, the Householder, and the Commons," William and Mary Quarterly 63:2 (2006)'),
    E('@I242214328536@', 'About 1795', 1795,
      'Henry Floyd, a Welsh immigrant born about 1692, dies in Fauquier County, Virginia, reportedly about 100 years old.',
      'Fauquier Co., VA', 38.714, -77.795),
    E('@I242272662756@', '25 December 1775', 1775,
      'William Williams dies after a Shawnee attack at Fort Boonesborough, Kentucky.',
      'Boonesborough, KY', 37.897, -84.263),
    E('@I242079830703@', '1781', 1781,
      'Margaret Cloyd Speer is at a Presbyterian service when a messenger bursts in: the British are crossing the '
      'Yadkin. She rushes home to scatter the livestock and hide the valuables from the Redcoats.',
      'The Yadkin River, Rowan Co., NC', 35.720, -80.400, 'story'),
    E('@I240015602549@', '18 June 1779', 1779,
      'Blackleach Burritt is imprisoned by the British, whose press calls him that "most pestiferous rebel priest '
      'and preacher of sedition."',
      'New York (British prison)', 40.713, -74.006),
    E(['@I242209901667@', '@I242209903698@', '@I242209900843@'], 'May 1786', 1786,
      'William Worthington and Mary Meason flee to Fort Vienna (now Calhoun), Kentucky, for refuge from Indian '
      'attacks; weeks later their son Thomas is born at the fort.',
      'Fort Vienna (Calhoun), KY', 37.539, -87.258),
    E('@I242225030233@', '1787', 1787,
      'Joseph McDowell signs the petition to form Allegheny County, Pennsylvania. He built Fort McDowell, one of a '
      'chain of forts in western Pennsylvania, before moving to Mason County, Kentucky, in the 1790s.',
      'Allegheny Co., PA', 40.440, -79.996),
    E('@I242144606130@', 'About 1787', 1787,
      'Marston Clay migrates with his family from Cumberland County, Virginia, to Jessamine County, Kentucky.',
      'Jessamine Co., KY', 37.872, -84.580),
    E('@I240024526553@', 'About 1794', 1794,
      'Jesse Baskett migrates with his family from Fluvanna County, Virginia, to Nicholas County, Kentucky.',
      'Nicholas Co., KY', 38.311, -84.029),
    E('@I242144606130@', '1803', 1803,
      'Marston Clay sells his mill in Lexington and moves his family to Henderson County, Kentucky.',
      'Henderson, KY', 37.836, -87.590),
    E('@I240022524382@', '3 March 1805', 1805,
      'Nancy Helm Floyd, dying at the very end of her family\'s migration from Virginia, becomes the first white '
      'woman buried in Union County, Kentucky.',
      'Union Co., KY', 37.683, -87.917),
    E('@I240180933204@', 'About 1807', 1807,
      'Abby Leonard (later Locke, then McDowell) begins the long migration from Franklin County, Maine, to '
      'Henderson, Kentucky, with her husband and children.',
      'Henderson, KY', 37.836, -87.590),
    E(['@I242214311115@', '@I242214311430@'], 'About 1809', 1809,
      'Thomas Robertson and Susannah Letchworth move with their children from Port Tobacco, Maryland, to Kentucky.',
      'Woodford Co., KY', 38.052, -84.730),
    E('@I242209897536@', 'About 1835', 1835,
      'Perrin Cardwell Howell, a Methodist preacher, buys one of the first cookstoves owned in western Kentucky.',
      'Hopkins Co., KY', 37.328, -87.499),
    E('@I240016590471@', 'October 1839', 1839,
      'John Grove Speer loses a lawsuit in which Abraham Lincoln is opposing counsel. The two, born on the very '
      'same day, keep up a friendship for years.',
      'Decatur, IL', 39.840, -88.955),
    E('@I242209901667@', 'June 1848', 1848,
      'William Worthington\'s remains are packed in salt and shipped up the river from Mississippi to Kentucky '
      'for burial.',
      'Washington Co., MS', 33.410, -91.060),
    E('@I240022524222@', '6 September 1850', 1850,
      'Henry Helm Floyd, a Revolutionary veteran, dies in Union County, Kentucky. His son Henry Crosby plants a '
      'cedar to mark the grave; decades later the local DAR chapter is named for him.',
      'Waverly, KY', 37.710, -87.815),
    E('@I240016590471@', '1851', 1851,
      'John Grove Speer leaves Kentucky for the California Gold Rush. He comes home on a Pacific steamer and '
      'across Central America.',
      'Nevada City, CA', 39.262, -121.016),
    E('@I242213411128@', 'About 1851', 1851,
      'James Howell, already 67, sets out west for San Jose, California, where he spends the rest of his life.',
      'San Jose, CA', 37.338, -121.886),
    E(['@I240015597693@', '@I240015597747@'], 'About 1852', 1852,
      'Lewis Raymond Sr. and Anna Eells Raymond move from upstate New York to Michigan.',
      'Marshall, MI', 42.272, -84.963),
    E('@I240016443118@', '23 October 1855', 1855,
      'Currence Hard Bostwick, a Revolutionary War widow, dies at 102.',
      'Meredith, NY', 42.362, -74.933),
    E('@I242209858787@', '18 November 1861', 1861,
      'Joseph L. Gregory, a Methodist preacher, is McLean County\'s delegate to the Russellville convention, which '
      'declares that Kentucky will join the Confederacy.',
      'Russellville, KY', 36.845, -86.887),
    E('@I240024525859@', '7 March 1863', 1863,
      'Robert Jesse Baskett dies of pneumonia, a young father of three, as his father Robert L. had before him '
      'and his son Robert Lee would after.',
      'Henderson, KY', 37.836, -87.590),
    E('@I240015675115@', 'About 1864', 1864,
      'Soldiers from both armies pass through the Baskett farm looking for food. Walker Baskett later says he '
      'preferred the Union visits: their scrip turned into real dollars, unlike Confederate graybacks.',
      'Spottsville, KY', 37.846, -87.425, 'story'),
    E('@I240014571694@', '30 June 1868', 1868,
      'Albert Demetrius Hitchcock founds The Franklin Register.',
      'Franklin, NY', 42.341, -75.166),
    E('@I240014481746@', 'Spring 1898', 1898,
      'Albert Lucius Hitchcock graduates from the State Normal School at Oneonta; in 1905 he goes to Flushing to '
      'teach at the Murray Hill School.',
      'Oneonta, NY', 42.453, -75.064),
    E('@I240014571714@', '27 May 1898', 1898,
      'Daisy Swenson graduates from Manhattan\'s School of Ethical Culture, to teach kindergarten.',
      'New York, NY', 40.772, -73.979),
    E('@I240014571802@', 'October 1900', 1900,
      'James Sherwood drills with the Baptist Boys\' Brigade, which he helps lead in Brooklyn.',
      'Brooklyn, NY', 40.678, -73.944),
    E('@I240014571845@', '1903', 1903,
      'Lily Trinder, daughter of English and Irish immigrants to Canada, moves from Toronto to Brooklyn.',
      'Brooklyn, NY', 40.678, -73.944),
    E(['@I240014481746@', '@I240014571714@'], 'Summer 1906', 1906,
      'Albert Lucius Hitchcock and Daisy Swenson honeymoon in the Adirondacks after a joint wedding with Daisy\'s '
      'sister Selma.',
      'The Adirondacks, NY', 44.112, -74.206),
    E('@I240014481745@', '1 June 1927', 1927,
      'Albert Carl Hitchcock, 17, comes home from a voyage around South America aboard the SS Vauban.',
      'New York, NY', 40.700, -74.020),
    E('@I240015673788@', 'About 1938', 1938,
      'After Robert Baskett\'s heart attack, his doctors ban any mention of President Roosevelt in the house, '
      'for fear of his blood pressure.',
      'Knight Township, IN', 37.980, -87.520, 'story'),
    E('@I240014571792@', 'About 1948', 1948,
      'Doris Sherwood sings with the Robert Shaw Chorale.',
      'New York, NY', 40.763, -73.983),
    E(['@I240014481745@', '@I240014571792@'], '25 March 1950', 1950,
      'Albert Carl Hitchcock and Doris Sherwood marry in New York City.',
      'New York, NY', 40.713, -74.006),

    # ------------------------------------------------ Jennie Askew's side
    E('@I242611467113@', '26 August 1911', 1911,
      'J. M. Lawson, a prosperous farmer and church deacon, is shot and killed at a country church near Ashburn '
      'by R. G. Whidden, a fellow deacon who had fallen out with the pastor and the congregation. Whidden goes '
      'home and kills himself.',
      'Near Ashburn, Turner Co., GA', 31.706, -83.653,
      source='The Atlanta Journal, 27 Aug 1911, p. 1 ("Church Quarrel Ends in Murder and Suicide")'),
    E('@I242611466175@', 'World War II', 1943,
      'Harvey Masterson works on the Manhattan Project. (He was living in Tucson in 1942; where he worked isn\'t known.)',
      'Tucson, AZ', 32.222, -110.975, 'story', source='Family account (James)'),
    E('@I242611466189@', '1965', 1965,
      'Lee McBride White Sr. marches for civil rights in Selma, Alabama.',
      'Selma, AL', 32.407, -87.021, 'story', source='Family tradition (James)'),
    E('@I242608012288@', 'About 1980', 1980,
      'James Masterson serves as a legislative aide to Speaker Tip O\'Neill.',
      'The U.S. Capitol, Washington', 38.890, -77.009, source='Family account (James)'),
    E('@I242611471046@', 'About 1840', 1840,
      'William Calmes Buck, a Baptist minister, founds East Baptist Church in Louisville and is its first pastor; '
      'he also edits the state Baptist newspaper and compiles a hymnal.',
      'Louisville, KY', 38.253, -85.759, source='Wikipedia, "William Calmes Buck"'),
    E('@I242611471046@', '1858', 1858,
      'William Calmes Buck becomes pastor of the First Baptist Church of Selma, Alabama; the next year he founds '
      'The Baptist Correspondent.',
      'Selma, AL', 32.407, -87.021, source='Wikipedia, "William Calmes Buck"'),
    E('@I242611467681@', '1890s', 1895,
      'Banks Shifflett leaves Greene County for Hopkins Gap in Rockingham County, the first of several Greene County '
      'families to settle there.',
      'Hopkins Gap, Rockingham Co., VA', 38.660, -78.950, 'story',
      source='"The Red Flannel Rag" (family memoir), pp. 42-43'),
    # ------------------------------------------------ later arrivals, with the document's details
    E(['@I240016223846@', '@I240016223863@'], 'About 1832', 1832,
      'George Palmer Watts Sr. and Margaretta Hills arrive in New York from England. George is a tinsmith, a trade '
      'he passes to his children and, indirectly, to his grandson-in-law Andrew Swenson.',
      'New York, NY', 40.700, -74.020, 'arrival'),
    E(['@I240014573258@', '@I240014573249@'], '22 August 1846', 1846,
      'John Henry Monsees and Imogene MacClellan, German and Irish immigrants, marry in a Lutheran church in New York City.',
      'New York, NY', 40.713, -74.006),
    E(['@I242386742138@', '@I242386742140@'], '18 November 1853', 1853,
      'Benedict Graden and Maria Schwaab, Swiss immigrants, arrive at New Orleans with several children aboard the '
      'Friendship Le Ferriere, and move up the Mississippi to farm in southeast Missouri.',
      'New Orleans, LA', 29.951, -90.071, 'arrival', ship='Friendship Le Ferriere'),
    E(['@I240014572013@', '@I240014572017@'], '20 May 1854', 1854,
      'James Sherwood and Susan Strong emigrate with several of their children from County Cavan, Ireland, to New York.',
      'New York, NY', 40.700, -74.020, 'arrival'),
    E('@I240014571958@', 'Spring 1869', 1869,
      'Andrew John Swenson emigrates from Sweden to New Jersey.',
      'New York, NY', 40.700, -74.020, 'arrival'),
    E(['@I240181210562@'], '20 September 1882', 1882,
      'Jakob Mehrle and Franziska Fahrner arrive in New York with their children from Baiersbronn, Germany.',
      'New York, NY', 40.700, -74.020, 'arrival'),
]
