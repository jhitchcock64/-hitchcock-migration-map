"""
Military service of Margaret's ancestors: hand-authored from pension files,
service records and family histories (researched with James, 2026-09-26).
build2/build_military.py routes each leg over the historical network and
writes military_prepared.json -> MILITARY in data.js.

Each entry is one man's service in one war:
  pid      GEDCOM individual ID (stable across exports)
  war      short name shown on the map
  unit     his unit(s), as the records give them
  summary  one or two sentences for the panel
  sources  what it rests on (shown on the page)
  stops    in order; each S(label, lat, lon, date, conf, note, via=None, gap=False)
           conf: 'record'     documented for him (his declaration, his service
                              record, a court or colony record)
                 'unit'       where his regiment or company went; he isn't named
                 'family'     a family account or secondary history
                 'conjecture' a guess, flagged as one
           via:  network nodes the leg INTO this stop must pass (as in
                 network.py's FORCED); otherwise the router infers the path
           gap:  don't draw a leg into this stop (the record jumps; no path known)
           way:  [(lat, lon), ...] fixed points the leg passes first (e.g. out of the Bay of
                 Biscay, where the network has no port), then it joins the network
           by:   how the leg into this stop travelled: 'land' (the default: a march on
                 period roads, or a smooth curve), 'water' (rivers, lakes, coastal
                 lanes and roads), 'sea' (the same), 'rail' (anything, railroads included),
                 or 'arc' (not routed: a smooth curve through the way points, for a march
                 whose route is documented, or a plain arc where any route would be a guess)
  A man with no stops is shown as a note only (no route).

Genealogical facts belong in James's tree, not here: this file records only
where the service took him, with the source for each stop.
"""


def S(label, lat, lon, date, conf, note='', via=None, gap=False, by='land', way=None):
    return dict(label=label, lat=lat, lon=lon, date=date, conf=conf, note=note, via=via, gap=gap, by=by, way=way)


SERVICE = [
    # ------------------------------------------------------------------ colonial
    dict(pid='@I242779439726@', name='Samuel Sherman Sr.', war='Pequot War, 1637',
         unit='Connecticut troops under Capt. John Mason',
         summary='On the Wethersfield committee that declared war on the Pequots, and in the campaign that '
                 'destroyed the Pequot fort at Mystic. The route is Mason\'s: down the river, by sea to '
                 'Narragansett Bay, and overland to Mystic.',
         sources=['Shepard, Connecticut Soldiers in the Pequot War of 1637 (1913), via WikiTree Sherman-2831'],
         stops=[S('Wethersfield, CT', 41.714, -72.653, 'May 1637', 'family'),
                S('Hartford, CT', 41.766, -72.673, '10 May 1637', 'unit', 'Mason\'s force set out'),
                S('Saybrook fort, CT', 41.291, -72.358, 'May 1637', 'unit', 'down the Connecticut River', by='water'),
                S('Narragansett Bay (landing)', 41.572, -71.446, '20 May 1637', 'unit', 'by boat along the coast', by='sea'),
                S('Pequot fort at Mystic', 41.369, -71.970, '26 May 1637', 'unit', 'the fort was burned'),
                S('Pequot Harbor (Thames River)', 41.356, -72.100, '26 May 1637', 'unit', 'to the boats'),
                S('Wethersfield, CT', 41.714, -72.653, 'June 1637', 'unit', 'home by boat', by='water')]),

    dict(pid='@I242672350676@', name='Isaac Johnson', war="King Philip's War, 1675",
         unit='Captain of a Massachusetts company (Roxbury)',
         summary='Led his company in the Great Swamp Fight and was killed entering the Narragansett fort, '
                 '19 December 1675. The route is the Massachusetts army\'s march.',
         sources=['Standard histories of the Great Swamp Fight; James\'s tree (death 19 Dec 1675, Narragansett)'],
         stops=[S('Roxbury, MA', 42.332, -71.089, 'Dec 1675', 'record'),
                S('Dedham Plain (muster)', 42.242, -71.166, '9 Dec 1675', 'unit'),
                S('Seekonk (Rehoboth)', 41.818, -71.330, 'Dec 1675', 'unit'),
                S('Providence', 41.824, -71.413, 'Dec 1675', 'unit'),
                S('Wickford (Smith\'s garrison)', 41.579, -71.453, '12-18 Dec 1675', 'unit'),
                S('Great Swamp fort, South Kingstown', 41.470, -71.586, '19 Dec 1675', 'record',
                  'killed leading his company into the fort')]),

    dict(pid='@I242551667444@', name='John Beers', war="King Philip's War, 1675",
         unit='Connecticut troops (Fairfield County)',
         summary='Severely wounded in the Great Swamp Fight, 19 December 1675; granted relief by the colony '
                 'in 1677. The route is the Connecticut contingent\'s.',
         sources=['Jacobus, History and Genealogy of the Families of Old Fairfield (1930) I:56, via WikiTree Beers-71'],
         stops=[S('Stratford, CT', 41.185, -73.133, 'Dec 1675', 'family'),
                S('New London (muster)', 41.356, -72.100, 'Dec 1675', 'unit'),
                S('Stonington', 41.336, -71.906, 'Dec 1675', 'unit'),
                S('Pettaquamscutt (joined the Massachusetts army)', 41.473, -71.487, '18 Dec 1675', 'unit'),
                S('Great Swamp fort, South Kingstown', 41.470, -71.586, '19 Dec 1675', 'record',
                  'severely wounded'),
                S('Wickford (the wounded carried back)', 41.579, -71.453, '20 Dec 1675', 'unit')]),

    dict(pid='@I242215851543@', name='Charles Clay', war="Bacon's Rebellion, 1676",
         unit='With Nathaniel Bacon\'s men (Henrico)',
         summary='A family history says he served under Bacon in 1676. Nothing places him at Jamestown; '
                 'the siege and burning of Jamestown in September 1676 is shown as a guess.',
         sources=['Clay family history, quoted at conawayblankensteinfamilies.com (Charles Clay & Hannah Wilson)'],
         stops=[S('Henrico County, VA', 37.390, -77.340, '1676', 'family'),
                S('Jamestown', 37.209, -76.778, 'Sept 1676', 'conjecture', 'siege and burning of Jamestown')]),

    dict(pid='@I242215784450@', name='George Muse', war="War of Jenkins' Ear, 1740-42",
         unit='Virginia companies of Gooch\'s American Regiment; sergeant aboard HMS Alderney',
         summary='Sailed with Lawrence Washington on the Cartagena expedition, serving aboard HMS Alderney '
                 'as a sergeant.',
         sources=['Don W. Hoover, family compilation (binder); Cartagena in James\'s tree'],
         stops=[S('Hampton Roads, VA', 36.970, -76.330, 'Oct 1740', 'unit', 'the Virginia companies sailed'),
                S('Port Royal, Jamaica', 17.937, -76.841, 'Jan 1741', 'unit', 'joined Vernon\'s fleet', by='sea'),
                S('Cartagena de Indias', 10.420, -75.550, 'Mar-Apr 1741', 'family', 'the siege', by='sea'),
                S('Port Royal, Jamaica', 17.937, -76.841, 'May 1741', 'unit', by='sea'),
                S('Hampton Roads, VA', 36.970, -76.330, '1742', 'unit', 'the survivors came home', by='sea')]),

    dict(pid='@I242215784450@', name='George Muse', war='French and Indian War, 1754',
         unit='Lt. Col., Virginia Regiment, under George Washington',
         summary='Lieutenant colonel under Washington in the 1754 campaign, at Great Meadows and Fort '
                 'Necessity (3 July 1754).',
         sources=['Don W. Hoover, family compilation (binder); standard histories of the 1754 campaign'],
         stops=[S('Alexandria, VA', 38.805, -77.047, 'Apr 1754', 'unit', 'the Virginia Regiment marched'),
                S('Winchester, VA', 39.186, -78.163, 'Apr 1754', 'unit'),
                S('Wills Creek (Cumberland, MD)', 39.652, -78.763, 'May 1754', 'unit'),
                S('Fort Necessity (Great Meadows)', 39.815, -79.587, '3 July 1754', 'family',
                  'the fort surrendered to the French; family history says his part in the debacle soured his '
                  'relations with Washington for life'),
                S('Alexandria, VA', 38.805, -77.047, 'July 1754', 'unit', 'the regiment withdrew')]),

    # ---------------------------------------------------------------- Revolution
    dict(pid='@I240014572363@', name='Jared Hitchcock', war='Revolution, 1777-83',
         unit='Connecticut line: Col. Meigs\'s, later Col. Butler\'s regiment (finally the 1st Connecticut); corporal',
         summary='Enlisted 25 April 1777 under Capt. Charles Pond for the war; a corporal under Capt. Elijah '
                 'Humphrey when discharged in June 1783. He names no battles, so the middle of the route is '
                 'where the Connecticut line camped.',
         sources=['Pension W.16601 (NARA 54887472): his 1820 declaration; widow Irene\'s 1839 declaration'],
         stops=[S('Milford, CT', 41.222, -73.057, '25 Apr 1777', 'record', 'enlisted'),
                S('Peekskill, NY (Hudson Highlands)', 41.290, -73.920, '1777', 'unit'),
                S('Redding, CT (winter camp)', 41.303, -73.383, 'winter 1778-79', 'unit'),
                S('Morristown, NJ (Jockey Hollow)', 40.763, -74.543, 'winter 1779-80', 'unit', by='arc',
                  way=[(41.270, -73.940), (41.115, -74.150), (40.995, -74.285)]),   # King's Ferry, Ramapo pass, Pompton
                S('West Point, NY', 41.392, -73.956, 'June 1783', 'record',
                  'discharged; family history says he received the Badge of Merit, signed by Washington, for six years\' service',
                  by='arc', way=[(40.995, -74.285), (41.115, -74.150), (41.320, -74.120)])]),   # Pompton, Ramapo, Smith's Clove

    dict(pid='@I242086113939@', name='Henry Burdick', war='Revolution, 1777-83',
         unit='2nd New York (Col. Philip Van Cortlandt), Capt. Jacob Wright\'s company',
         summary='Enlisted 27 May 1777 and served six years, discharged 4 June 1783. He names no battles; '
                 'the route is his regiment\'s.',
         sources=['Pension file (NARA 54107986): his 1818 declaration'],
         stops=[S('Saratoga (Bemis Heights)', 42.999, -73.637, 'Sept-Oct 1777', 'unit'),
                S('Valley Forge', 40.097, -75.440, 'winter 1777-78', 'unit', by='arc',
                  way=[(42.653, -73.756), (41.535, -73.899), (41.270, -73.940), (40.120, -75.220)]),  # Albany, Fishkill, King's Ferry, Whitemarsh
                S('Monmouth Court House', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Newtown (Elmira), NY', 42.048, -76.720, '29 Aug 1779', 'unit',
                  'Sullivan\'s expedition, with Clinton\'s brigade down the Susquehanna', by='arc',
                  way=[(41.270, -73.940), (42.653, -73.756), (42.905, -74.572), (42.700, -74.924), (41.980, -76.520)]),
                  # King's Ferry, Albany, Canajoharie, Otsego Lake, Tioga
                S('Yorktown', 37.239, -76.510, 'Oct 1781', 'unit', 'by the allied march of 1781', by='arc',
                  way=[(41.246, -75.881), (40.690, -75.210), (40.349, -74.659), (39.952, -75.165), (39.607, -75.829),
                       (38.970, -76.450), (37.950, -76.200), (37.000, -76.310), (37.215, -76.700)]),
                  # Wyoming, Easton, Princeton, Philadelphia, Head of Elk, down the Bay, up the James
                S('New Windsor cantonment, NY', 41.458, -74.060, '4 June 1783', 'record', 'discharged', by='water')]),

    dict(pid='@I240016442918@', name='William Raymond', war='Revolution, 1775-81',
         unit='Waterbury\'s regt (1775), Bradley\'s regt (1776), Webb\'s regt, Connecticut line (1777-81)',
         summary='Three enlistments: 1775 under Capt. Ichabod Doolittle (Waterbury\'s, the northern campaign), '
                 '1776 under Capt. Elijah Abel (Bradley\'s), and from January 1777 under Capt. John Mills in '
                 'Webb\'s regiment until early 1781. Family history says he was crippled for life by injuries from his service.',
         sources=['Pension S.35,596 (NARA 196461238): his 1818 declaration', '"Our American History" (family history, 2026)'],
         stops=[S('New Canaan, CT', 41.147, -73.495, 'spring 1775', 'record'),
                S('Albany, NY', 42.653, -73.756, 'summer 1775', 'unit', by='water'),
                S('Ticonderoga', 43.842, -73.387, 'Aug 1775', 'unit', by='water'),
                S('St. Johns, Quebec (siege)', 45.307, -73.263, 'Sept-Nov 1775', 'unit', by='water'),
                S('New Canaan, CT', 41.147, -73.495, 'winter 1775-76', 'unit', 'home at the end of the term', by='water'),
                S('Bergen, NJ', 40.728, -74.078, 'summer 1776', 'unit', 'Bradley\'s battalion'),
                S('New Canaan, CT', 41.147, -73.495, 'winter 1776-77', 'unit'),
                S('Peekskill, NY (Hudson Highlands)', 41.290, -73.920, '1777', 'unit', 'Webb\'s regiment'),
                S('Valley Forge', 40.097, -75.440, 'winter 1777-78', 'family',
                  'family history; his own declaration doesn\'t mention Valley Forge'),
                S('Rhode Island (battle, 29 Aug 1778)', 41.601, -71.260, 'Aug 1778', 'unit', by='arc',
                  way=[(41.270, -73.940), (41.763, -72.685), (41.824, -71.413)]),   # King's Ferry, Hartford, Providence
                S('New Canaan, CT', 41.147, -73.495, 'early 1781', 'record', 'discharged')]),

    dict(pid='@I242086358497@', name='Jeremiah Beard Eells', war='Revolution, 1776-80',
         unit='Ensign, Bradley\'s battalion (1776); lieutenant, Norwalk sea-coast guard; later Col. Mead\'s regt',
         summary='Ensign in Capt. Samuel Keeler\'s company, June 1776 to January 1777. As lieutenant of the '
                 'Norwalk coast guard he was taken prisoner on the shore the night after 14 March 1777, '
                 'carried to Long Island and held until 29 January 1779. In 1780 he rode express from '
                 'Horseneck to Hartford.',
         sources=['Connecticut Public Records (his memorial to the Assembly); U.S. Revolutionary War Rolls; '
                  'WikiTree Eells-21; DAR A036829'],
         stops=[S('New Canaan, CT', 41.147, -73.495, 'June 1776', 'record'),
                S('Bergen, NJ', 40.728, -74.078, 'summer 1776', 'unit', 'Bradley\'s battalion'),
                S('New Canaan, CT', 41.147, -73.495, 'Jan 1777', 'record'),
                S('Norwalk shore', 41.090, -73.410, '14-15 Mar 1777', 'record', 'taken prisoner by night'),
                S('Long Island (British lines)', 40.641, -73.959, 'Mar 1777 - Jan 1779', 'record',
                  'held prisoner; the place on Long Island isn\'t recorded'),
                S('New Canaan, CT', 41.147, -73.495, '29 Jan 1779', 'record', 'released'),
                S('Horseneck (Greenwich), CT', 41.026, -73.628, '1780', 'record', 'Col. Mead\'s regiment'),
                S('Hartford, CT', 41.766, -72.673, '1780', 'record', 'riding express')]),

    dict(pid='@I240020478272@', name='John Eells Sr.', war='Revolution, 1775-81',
         unit='Militia, Col. John Mead\'s regiment (Capts. Carter, Benedict, Scofield); corporal',
         summary='By his son\'s account: to New York in the winter of 1775-76 and again in summer 1776; at '
                 'Ridgefield in 1777, near Gen. Wooster when he fell; often at Horseneck, where he once '
                 'carried a flag of truce with Gen. Knyphausen\'s baggage to the British lines at Kingsbridge; '
                 'guards at Stamford and patrols on the Norwalk shore.',
         sources=['Rejected pension claim R.3268 (NARA 54500891): declaration of his son John Eells Jr., 1850'],
         stops=[S('New Canaan, CT', 41.147, -73.495, 'winter 1775-76', 'family'),
                S('New York', 40.713, -74.006, 'winter 1775-76', 'family'),
                S('New Canaan, CT', 41.147, -73.495, '1776', 'family'),
                S('New York', 40.713, -74.006, 'summer 1776', 'family'),
                S('New Canaan, CT', 41.147, -73.495, '1776', 'family'),
                S('Ridgefield (battle)', 41.282, -73.498, '27 Apr 1777', 'family'),
                S('Horseneck (Greenwich), CT', 41.026, -73.628, '1777-81', 'family', 'Col. Mead\'s lines'),
                S('Kingsbridge (British lines)', 40.878, -73.905, 'date unknown', 'family',
                  'flag of truce with Knyphausen\'s baggage'),
                S('Stamford, CT', 41.053, -73.539, 'date unknown', 'family', 'guards'),
                S('Norwalk, CT', 41.118, -73.408, '11 July 1779', 'family', 'called out when Norwalk was burned'),
                S('Middlesex (Darien), CT', 41.079, -73.469, '22 July 1781', 'family',
                  'called out when the congregation was taken prisoner')]),

    dict(pid='@I240020476667@', name='John Mead IV', war='Revolution, 1776-81',
         unit='9th Connecticut militia; colonel 1777-81; brigadier general, 4th brigade, 1781',
         summary='Commanded the 9th regiment in New York in 1776, then held the lines at Horseneck for most '
                 'of the war; brigadier general in 1781.',
         sources=['Heitman, Historical Register p. 386; S. P. Mead, Mead Family (1901) pp. 78-90; WikiTree Mead-187'],
         stops=[S('Horseneck (Greenwich), CT', 41.026, -73.628, '1776', 'record'),
                S('New York', 40.713, -74.006, '1776', 'family', 'with the 9th regiment'),
                S('Horseneck (Greenwich), CT', 41.026, -73.628, '1777-81', 'record', 'commanding the lines')]),

    dict(pid='@I240016443034@', name='David Bostwick', war='Revolution, 1779',
         unit='Connecticut militia',
         summary='Militia service 5-16 July 1779, probably the call-out against Tryon\'s raid on New Haven, '
                 'Fairfield and Norwalk. (Pension S.36,418 is another David Bostwick.)',
         sources=['Bostock family tree (bostock.net), citing "Forum 387"'],
         stops=[S('New Milford, CT', 41.577, -73.408, '5 July 1779', 'record', 'enlisted'),
                S('Fairfield, CT', 41.141, -73.263, '8 July 1779', 'conjecture', 'Tryon burned Fairfield'),
                S('Norwalk, CT', 41.118, -73.408, '11 July 1779', 'conjecture', 'Tryon burned Norwalk'),
                S('New Milford, CT', 41.577, -73.408, '16 July 1779', 'record', 'discharged')]),

    dict(pid='@I240016443308@', name='Philip Frisbee', war='Revolution, 1776-81',
         unit='17th Albany County militia (Col. William B. Whiting): captain, 3rd company; second major 1778',
         summary='From Kings District (Canaan). Captain, then second major from 16 June 1778. On the '
                 'Committee of Inspection in 1776. His regiment was at Saratoga in 1777.',
         sources=['Frisbee-Frisbie Genealogy (1926) pp. 90-92, citing Fernow and Roberts; WikiTree Frisbee-47'],
         stops=[S('Canaan (Kings District), NY', 42.407, -73.454, 'Sept 1777', 'record'),
                S('Saratoga (Bemis Heights)', 42.999, -73.637, 'Sept-Oct 1777', 'unit'),
                S('Canaan (Kings District), NY', 42.407, -73.454, 'Oct 1777', 'unit')]),

    dict(pid='@I240016443087@', name='Gideon Frisbee', war='Revolution, 1777',
         unit='17th Albany County militia (Col. William B. Whiting)',
         summary='In his father\'s regiment, the 17th Albany County militia, which was at Saratoga in 1777.',
         sources=['Roberts, New York in the Revolution: Land Bounty Rights (17th regiment), in James\'s tree'],
         stops=[S('Canaan (Kings District), NY', 42.407, -73.454, 'Sept 1777', 'record'),
                S('Saratoga (Bemis Heights)', 42.999, -73.637, 'Sept-Oct 1777', 'unit'),
                S('Canaan (Kings District), NY', 42.407, -73.454, 'Oct 1777', 'unit')]),

    dict(pid='@I242079816204@', name='John Grove', war='Revolution, 1776-81',
         unit='Captain of wagons, Continental wagon department (Gen. Hiltzheimer)',
         summary='Enlisted in 1776 at Frederick Town, Maryland, and was made a captain of wagons at '
                 'Philadelphia; served to the surrender of Cornwallis. He names Brandywine, Paoli, Germantown '
                 'and Monmouth, and a wagon train of money, provisions and clothing to White Plains.',
         sources=['Pension W.1756 (NARA 54739782): his 1833 declaration, Jefferson Co., KY'],
         stops=[S('Frederick Town, MD', 39.414, -77.411, '1776', 'record', 'enlisted at a tavern'),
                S('Philadelphia', 39.953, -75.165, '1776', 'record'),
                S('The North River (via the Jerseys)', 40.851, -73.970, '1776', 'record'),
                S('Philadelphia', 39.953, -75.165, '1776-77', 'record', 'stationed there a while'),
                S('Brandywine', 39.872, -75.591, '11 Sept 1777', 'record'),
                S('Paoli', 40.034, -75.516, '20-21 Sept 1777', 'record'),
                S('Germantown', 40.040, -75.180, '4 Oct 1777', 'record'),
                S('Monmouth', 40.266, -74.320, '28 June 1778', 'record'),
                S('White Plains, NY', 41.034, -73.763, '1778', 'record', 'wagons with money, provisions and clothing')]),

    dict(pid='@I242209901667@', name='William Worthington', war='Revolution, 1781-82',
         unit='Pennsylvania Rangers, Lochry\'s corps',
         summary='With Lochry down the Ohio to join George Rogers Clark; captured at the defeat below the '
                 'Great Miami (24 Aug 1781), held at Upper Sandusky, Detroit, an island in the St. Lawrence and '
                 'the Montreal jail; broke jail about 1 Nov 1782 and was home by 20 Dec 1782.',
         sources=['Pension S.1272: his declaration',
                  'Manasseh Coyle\'s pension declaration (a fellow Lochry captive; the way home), fishergenes.com source S410'],
         stops=[S('Westmoreland Co., PA', 40.308, -79.499, 'July 1781', 'record'),
                S('Fort Henry (Wheeling)', 40.064, -80.721, 'Aug 1781', 'record'),
                S('Laughery Creek (Lochry\'s defeat)', 39.018, -84.866, '24 Aug 1781', 'record', 'captured',
                  via=['wheeling', 'laughery_creek']),
                S('Upper Sandusky', 40.827, -83.281, 'Sept-Oct 1781', 'record', 'about six weeks',
                  via=['laughery_creek', 'upper_sandusky']),
                S('Detroit', 42.331, -83.046, 'Oct 1781', 'record', via=['upper_sandusky', 'detroit']),
                S('Fort Niagara', 43.262, -79.063, 'late 1781', 'record', 'by vessel across Lake Erie', by='water'),
                S('Island in the St. Lawrence (Coteau-du-Lac)', 45.298, -74.176, '1781-82', 'record',
                  'about 40 miles above Montreal', by='water'),
                S('Montreal (jail)', 45.504, -73.554, '1 July 1782', 'record'),
                S('Philadelphia', 39.952, -75.165, 'Dec 1782', 'unit',
                  'broke jail about 1 Nov 1782. His own declaration doesn\'t give the way home; this is the way '
                  'his fellow Lochry captive Manasseh Coyle took after breaking out of Montreal in October 1782: '
                  'some 300 miles of wilderness to the first settlements, then by Philadelphia',
                  by='arc', way=[(45.307, -73.263), (44.540, -73.330), (43.800, -73.420), (43.270, -73.580),
                                 (42.653, -73.756), (41.930, -74.000), (40.690, -75.210)]),
                  # St. Johns, Lake Champlain, Fort Edward, Albany, Kingston, Easton
                S('Westmoreland Co., PA', 40.308, -79.499, '20 Dec 1782', 'unit', 'home by 20 Dec 1782 (his declaration)')]),

    dict(pid='@I240022524222@', name='Henry Helm Floyd', war='Revolution, 1781',
         unit='Virginia militia (Col. Churchill; Capt. Grigsby, Col. Edmonds)',
         summary='Two militia tours in 1781: in the spring to the lower James and back to Richmond; in the '
                 'fall to the siege of Yorktown, discharged before the surrender.',
         sources=['Pension S.31030: his declaration (revwarapps.org)'],
         stops=[S('Fauquier Court House', 38.714, -77.795, 'spring 1781', 'record'),
                S('Stafford Court House', 38.422, -77.408, 'spring 1781', 'record'),
                S('Fredericksburg', 38.303, -77.460, 'spring 1781', 'record'),
                S('Malvern Hill', 37.413, -77.250, 'Apr 1781', 'record', 'joined Gen. Stevens'),
                S('Williamsburg (barracks)', 37.271, -76.708, 'Apr 1781', 'record', 'the British landed 20 Apr'),
                S('Richmond', 37.541, -77.436, 'May 1781', 'record', 'across the Pamunkey; discharged'),
                S('Fauquier Court House', 38.714, -77.795, 'fall 1781', 'record', 'second tour'),
                S('Yorktown (siege)', 37.239, -76.510, 'Oct 1781', 'record', 'discharged before the surrender')]),

    dict(pid='@I242213417444@', name='Lewis Howell', war='Revolution, 1776-81',
         unit='12th Virginia (Col. James Wood), Capt. Stephen Ashby; later Crockett\'s Western Battalion',
         summary='Enlisted at Wheeling in 1776; wounded in the knee at Germantown. Re-enlisted in 1778 in '
                 'Shenandoah County for three years in Col. Joseph Crockett\'s battalion guarding the western '
                 'frontier; discharged in Berkeley County.',
         sources=['Pension W.9719: his declaration; Don W. Hoover, family compilation (binder)'],
         stops=[S('Wheeling', 40.064, -80.721, '1776', 'record', 'enlisted'),
                S('Germantown', 40.040, -75.180, '4 Oct 1777', 'record', 'wounded in the knee'),
                S('Shenandoah County, VA', 38.882, -78.506, '1778', 'record', 're-enlisted'),
                S('Berkeley County, VA', 39.456, -77.964, 'about 1781', 'record', 'discharged')]),

    dict(pid='@I242228087110@', name='William Howell Jr.', war='Revolution, 1776-79',
         unit='11th Virginia (Col. Daniel Morgan), Capt. Gabriel Long; wagon master',
         summary='Enlisted 4 April 1776; a wagon master. Died of smallpox in 1779 in an army camp in '
                 'Frederick County, Virginia.',
         sources=['Don W. Hoover, family compilation (binder); DAR application 162711'],
         stops=[S('Frederick County, VA (Winchester)', 39.186, -78.163, '4 Apr 1776', 'record', 'enlisted'),
                S('Middlebrook, NJ', 40.568, -74.530, 'June 1777', 'unit'),
                S('Brandywine', 39.872, -75.591, '11 Sept 1777', 'unit'),
                S('Germantown', 40.040, -75.180, '4 Oct 1777', 'unit'),
                S('Valley Forge', 40.097, -75.440, 'winter 1777-78', 'unit'),
                S('Monmouth', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Frederick County, VA', 39.186, -78.163, '1779', 'family', 'died of smallpox in an army camp')]),

    dict(pid='@I242213416924@', name='John Cardwell Jr.', war='Revolution, 1778-81',
         unit='Capt. Thomas Hill\'s company: 7th Virginia, then 3rd & 7th, 5th, and 5th & 11th Virginia',
         summary='Enlisted 12 January 1778 for three years; on the rolls at Valley Forge (May 1778), '
                 'Middlebrook (March 1779), Ramapo (September 1779) and camp near Morristown (November 1779); '
                 'discharged at Chesterfield Court House, 12 January 1781. Monmouth is his regiment\'s.',
         sources=['Compiled service records (NARA M881; 142234579 and related); bounty-land VAS2883 (Library of Virginia)'],
         stops=[S('Goochland County, VA', 37.684, -77.885, 'Jan 1778', 'family', 'home'),
                S('Valley Forge', 40.097, -75.440, 'May 1778', 'record', 'muster roll dated 4 June 1778'),
                S('Monmouth', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Middlebrook, NJ', 40.568, -74.530, 'Mar 1779', 'record'),
                S('Ramapo', 41.102, -74.150, 'Sept 1779', 'record'),
                S('Camp near Morristown', 40.763, -74.543, 'Nov-Dec 1779', 'record'),
                S('Chesterfield Court House', 37.377, -77.505, '12 Jan 1781', 'record', 'discharged')]),

    dict(pid='@I242214651794@', name='William Spilsby Gregory', war='Revolution, 1778-82',
         unit='4th Virginia, Continental line, Capt. Thomas Minor; sergeant',
         summary='Enlisted at Fredericksburg in October 1778; a sergeant; discharged at Bowling Green in '
                 '1782. The pension office found him on the rolls and allowed two years\' service.',
         sources=['Pension S.10,775 (NARA 54728116); Nathan Gregory\'s compilation'],
         stops=[S('Fredericksburg', 38.303, -77.460, 'Oct 1778', 'record', 'enlisted'),
                S('Bowling Green, VA', 38.049, -77.347, '1782', 'record', 'discharged')]),

    dict(pid='@I242272661494@', name='Samuel Farrar Williams', war='Revolution',
         unit='North Carolina militia',
         summary='Volunteered for three months and found two substitutes for about fifteen more; recalled '
                 'Col. Daniel Morgan and Col. William Washington. His claim was rejected (under six months\' '
                 'service of his own).',
         sources=['Rejected claim R11618 (revwarapps.org)'],
         stops=[]),

    dict(pid='@I242262261004@', name='John Slaton', war='Revolution',
         unit='Virginia; ended his service as a first lieutenant',
         summary='Served in the Revolution, ending as a first lieutenant.',
         sources=['Don W. Hoover, family compilation (binder)'],
         stops=[]),

    # ------------------------------------------------------------ War of 1812
    dict(pid='@I242214311115@', name='Thomas Robertson', war='War of 1812, 1813',
         unit='Sergeant, Capt. Charles Harvey\'s company, 10th (Barbour\'s) Kentucky Mounted Volunteer Militia',
         summary='Served 20 August to 12 November 1813. Barbour\'s regiment was raised for Gov. Shelby\'s '
                 'campaign that ended at the Thames; the route is the campaign\'s.',
         sources=['Kentucky service record, in James\'s tree; Kentucky Soldiers of the War of 1812'],
         stops=[S('Woodford County, KY', 38.053, -84.730, 'Aug 1813', 'family'),
                S('Newport, KY (rendezvous)', 39.091, -84.496, 'Aug-Sept 1813', 'unit'),
                S('Urbana, OH', 40.108, -83.752, 'Sept 1813', 'unit', by='arc',
                  way=[(39.435, -84.203), (39.759, -84.192)]),                       # Lebanon, Dayton
                S('Upper Sandusky', 40.827, -83.281, 'Sept 1813', 'unit', 'by Hull\'s Trace', by='arc',
                  way=[(40.647, -83.609)]),                                          # Fort McArthur
                S('The Portage (Port Clinton)', 41.512, -82.938, 'Sept 1813', 'unit', by='arc',
                  way=[(41.210, -83.160), (41.350, -83.120)]),                       # Fort Seneca, Fort Stephenson
                S('Amherstburg (by Perry\'s fleet)', 42.101, -83.108, '27 Sept 1813', 'unit', by='sea'),
                S('Sandwich (Windsor)', 42.295, -83.072, 'Sept 1813', 'unit'),
                S('Battle of the Thames (Moraviantown)', 42.570, -81.870, '5 Oct 1813', 'unit', 'up the Thames', by='arc',
                  way=[(42.330, -82.900), (42.330, -82.450), (42.405, -82.185)]),   # the lake shore, the Thames mouth, Chatham
                S('Detroit', 42.331, -83.046, 'Oct 1813', 'unit', by='arc',
                  way=[(42.405, -82.185), (42.330, -82.450), (42.330, -82.900)]),
                S('Woodford County, KY', 38.053, -84.730, 'Nov 1813', 'unit', 'discharged 12 Nov 1813', by='arc',
                  way=[(41.512, -82.938), (40.827, -83.281), (40.108, -83.752), (39.091, -84.496)])]),
                  # home the way they came: the Portage, Upper Sandusky, Urbana, Newport

    # ------------------------------------------------------------ Civil War
    dict(pid='@I240016223823@', name='George Palmer Watts', war='Civil War, 1861-64',
         unit='Co. E, 8th New Jersey Infantry; corporal 1862-64',
         summary='Enlisted 30 August 1861; corporal from June 1862, reduced to the ranks 1 May 1864; '
                 'mustered out at Trenton 21 September 1864. Family tradition: badly wounded in the '
                 'Wilderness. The route is his regiment\'s.',
         sources=['Record of Officers and Men of New Jersey in the Civil War; NARA M550; pension index '
                  '(widow Eleanor E.); 1890 veterans\' schedule'],
         stops=[S('Washington, NJ', 40.758, -74.979, 'Aug 1861', 'family', 'home'),
                S('Trenton', 40.221, -74.760, '30 Aug 1861', 'record', 'enlisted', by='rail'),
                S('Washington, DC', 38.895, -77.036, 'autumn 1861', 'unit', by='rail'),
                S('Budd\'s Ferry, MD (winter camp)', 38.571, -77.258, 'winter 1861-62', 'unit'),
                S('Yorktown (siege)', 37.239, -76.510, 'Apr 1862', 'unit', 'by steamer to the Peninsula', by='sea'),
                S('Williamsburg', 37.271, -76.708, '5 May 1862', 'unit'),
                S('Seven Pines', 37.523, -77.300, '31 May 1862', 'unit'),
                S('Malvern Hill', 37.413, -77.250, '1 July 1862', 'unit', 'the Seven Days'),
                S('Second Bull Run', 38.813, -77.521, '29-30 Aug 1862', 'unit', 'by steamer up the bay, then marched', by='sea'),
                S('Fredericksburg', 38.303, -77.460, '13 Dec 1862', 'unit'),
                S('Chancellorsville', 38.310, -77.634, '2-3 May 1863', 'unit'),
                S('Gettysburg', 39.831, -77.231, '2 July 1863', 'unit', 'the III Corps\' march', by='arc',
                  way=[(38.750, -77.475), (39.085, -77.480), (39.414, -77.411), (39.658, -77.174), (39.704, -77.327)]),
                  # Manassas Junction, Edwards Ferry, Frederick, Taneytown, Emmitsburg
                S('Mine Run', 38.310, -77.830, 'Nov 1863', 'unit', by='arc',
                  way=[(39.414, -77.411), (39.325, -77.740), (38.920, -78.080), (38.713, -77.795), (38.500, -77.890), (38.370, -77.800)]),
                  # Frederick, Harpers Ferry, Manassas Gap (Wapping Heights), Warrenton, Brandy Station, Jacob's Ford
                S('The Wilderness', 38.315, -77.740, '5-6 May 1864', 'family', 'wounded and left for dead (family history)'),
                S('Trenton', 40.221, -74.760, '21 Sept 1864', 'record', 'mustered out')]),

    dict(pid='@I240172307606@', name='Friedrich Graden', war='Civil War, 1863',
         unit='Co. E, 8th Provisional Enrolled Missouri Militia Infantry',
         summary='His company, one of five raised in Cape Girardeau County, served from May to November 1863; where '
                 'it was posted isn\'t documented.',
         sources=['Civil War pension index (filed 10 Mar 1892; wife Apollonia)'],
         stops=[S('Cape Girardeau County, MO', 37.306, -89.518, 'May-Nov 1863', 'record', 'Co. E was raised here')]),

    dict(pid='@I242190138127@', name='William George Gregory', war='Civil War, 1861-65',
         unit='Co. D, 2nd Kentucky Mounted Infantry (Confederate); with Forrest',
         summary='Enlisted with his brother James Henry at Camp Boone, 16 July 1861. His son said he fought '
                 'at Sacramento, Kentucky, and served under Forrest; family tradition is that he got out of '
                 'Fort Donelson with Forrest (James Henry was captured and died at Camp Butler). Paroled at '
                 'Greensboro, 1865. Where he served in between isn\'t recorded.',
         sources=['Confederate service record (NARA 31764810); Don W. Hoover\'s write-up (2010), from his son '
                  'Joseph R. Gregory'],
         stops=[S('Calhoun (McLean Co.), KY', 37.539, -87.258, 'July 1861', 'family', 'home'),
                S('Camp Boone, TN', 36.630, -87.210, '16 July 1861', 'record', 'enlisted'),
                S('Sacramento, KY (battle)', 37.416, -87.265, '28 Dec 1861', 'family'),
                S('Fort Donelson', 36.490, -87.856, 'Feb 1862', 'family', 'out with Forrest (family tradition)'),
                S('Greensboro, NC', 36.073, -79.792, 'Apr-May 1865', 'record', 'paroled', gap=True)]),

    dict(pid='@I242209858787@', name='Joseph L. Gregory', war='Civil War, 1861-62',
         unit='Chaplain, 8th Kentucky Infantry (Confederate)',
         summary='A Methodist (M.E. South) preacher; McLean County\'s delegate to the Russellville secession '
                 'convention, 18-20 November 1861; regimental chaplain of the 8th Kentucky Infantry. His son '
                 'James Henry died a prisoner at Camp Butler in 1862. When he served as chaplain isn\'t recorded; '
                 'the route is the 8th Kentucky\'s from its exchange in 1862.',
         sources=['Don W. Hoover\'s write-up (2010); American Civil War Research Database (enlisted 13 Mar 1862)'],
         stops=[S('Calhoun (McLean Co.), KY', 37.539, -87.258, 'Mar 1862', 'family', 'home'),
                S('Vicksburg', 32.353, -90.878, 'Sept 1862', 'unit', 'the regiment exchanged after Donelson', by='arc'),
                S('Champion Hill', 32.323, -90.558, '16 May 1863', 'unit'),
                S('Paducah', 37.083, -88.600, '25 Mar 1864', 'unit', 'mounted, under Forrest'),
                S("Brice's Crossroads", 34.505, -88.730, '10 June 1864', 'unit'),
                S('Tupelo', 34.258, -88.703, 'July 1864', 'unit')]),

    # ------------------------------------------------------------ World War I
    dict(pid='@I240014575248@', name='Arthur John Mehrle', war='World War I, 1918',
         unit='Mechanic, 356th Infantry, 89th Division',
         summary='Sailed from New York 4 June 1918; in the Saint-Mihiel offensive (12 September). Came home '
                 'in a casual company from St-Aignan, sailing from St-Nazaire 28 December 1918 aboard the '
                 'Finland. The training and Toul-sector stops are his division\'s.',
         sources=['Army transport passenger lists (RG 92); James\'s tree'],
         stops=[S('Cape Girardeau, MO', 37.306, -89.518, '1918', 'record'),
                S('Camp Funston, KS', 39.087, -96.792, 'spring 1918', 'unit', '89th Division training', by='rail'),
                S('New York', 40.713, -74.006, '4 June 1918', 'record', 'sailed', by='rail'),
                S('Liverpool', 53.405, -2.997, 'June 1918', 'unit', by='sea'),
                S('Le Havre', 49.494, 0.107, 'June 1918', 'unit', by='rail'),
                S('Reynel (training area)', 48.298, 5.347, 'July 1918', 'unit', by='rail'),
                S('Toul sector (Lucey)', 48.725, 5.819, 'Aug 1918', 'unit'),
                S('Saint-Mihiel offensive (near Xammes)', 48.969, 5.850, '12 Sept 1918', 'record',
                  'shot in the head (family history); he survived and lived six more decades'),
                S('St-Aignan (casual depot)', 47.269, 1.376, 'Dec 1918', 'record', 'casual company 406', gap=True),
                S('Saint-Nazaire', 47.274, -2.214, '28 Dec 1918', 'record', 'sailed on the Finland', by='rail'),
                S('New York', 40.713, -74.006, 'Jan 1919', 'record', by='sea',
                  way=[(47.05, -2.6), (47.6, -5.2), (48.6, -6.4)], via=['~scilly_w', 'new_york']),
                S('Cape Girardeau, MO', 37.306, -89.518, '1919', 'family', by='rail')]),
]


# ======================== Jennie Askew's side (researched 2026-09-27) ========================
SERVICE += [
    # ---------------------------------------------------------------- Revolution
    dict(pid='@I242788703578@', name='Patrick Masterson', war='Revolution, 1780-82',
         unit='Virginia militia (Capt. William Jennings, Col. James Clark), then the Virginia line under Steuben and Lafayette',
         summary='Volunteered in Shenandoah County in the spring of 1780 and marched over the Blue Ridge to Albemarle, '
                 'where he enlisted for the war. Richmond, a winter on the Chickahominy, the battle at Jamestown '
                 '(Green Spring, July 1781), then with Washington\'s army to the siege of Yorktown; afterwards guarded '
                 'the British prisoners at Winchester until he was discharged, 19 June 1782.',
         sources=['Pension file 32,495 / R.7012 (NARA 196226034): his declaration, Morgan Co., KY, 6 June 1842'],
         stops=[S('Shenandoah County, VA', 38.881, -78.506, 'spring 1780', 'record', 'volunteered under Capt. Jennings'),
                S('Albemarle (the Barracks)', 38.080, -78.490, 'May 1780', 'record', 'over the Blue Ridge; enlisted for the war'),
                S('Richmond', 37.541, -77.436, '1780', 'record'),
                S('The Chickahominy', 37.515, -77.187, 'winter 1780-81', 'record', 'wintered there'),
                S('Jamestown (Green Spring)', 37.236, -76.795, '6 July 1781', 'record', 'in the battle, under Muhlenberg'),
                S('Williamsburg', 37.271, -76.708, 'Sept 1781', 'record', 'joined Washington\'s army'),
                S('Yorktown (siege)', 37.239, -76.510, '19 Oct 1781', 'record', 'the surrender'),
                S('Winchester', 39.186, -78.163, '19 June 1782', 'record', 'guarded the prisoners; discharged')]),

    dict(pid='@I242788441117@', name='Richard Bonner', war='Revolution, 1777-83',
         unit='2nd Virginia (Cols. Spotswood and Febiger): private, corporal 1778, sergeant 1779',
         summary='On the 2nd Virginia\'s rolls from May 1777, a corporal from 15 April 1778 and a sergeant by 1779; '
                 'received his certificate for the balance of his pay himself, 2 September 1783. The rolls give no '
                 'places, so the route is his regiment\'s.',
         sources=['Compiled service record (NARA 142176108, M881)'],
         stops=[S('Dinwiddie County, VA', 37.077, -77.587, '1777', 'family', 'home'),
                S('Brandywine', 39.872, -75.591, '11 Sept 1777', 'unit'),
                S('Germantown', 40.040, -75.180, '4 Oct 1777', 'unit'),
                S('Valley Forge', 40.097, -75.440, 'winter 1777-78', 'unit', 'present on the January 1778 roll'),
                S('Monmouth', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Middlebrook, NJ', 40.568, -74.530, 'winter 1778-79', 'unit', 'a sergeant by February 1779'),
                S('Sussex County, VA', 36.922, -77.260, '1783', 'family', 'home')]),

    dict(pid='@I242788690618@', name='Nathaniel Maynard', war='Revolution, 1778-79',
         unit='1st Virginia (Col. Richard Parker), Capt. Cummins\' and Lt. Col. Ball\'s companies',
         summary='Enlisted 4 February 1778 for one year; on the April 1778 pay roll (Valley Forge) and on the '
                 'January 1779 muster roll dated at Middlebrook, New Jersey.',
         sources=['Compiled service record (NARA 141545288, M881)'],
         stops=[S('Charles City County, VA', 37.343, -77.070, 'Feb 1778', 'family', 'home'),
                S('Valley Forge', 40.097, -75.440, 'Apr 1778', 'unit', 'on the April pay roll'),
                S('Monmouth', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Middlebrook, NJ', 40.568, -74.530, 'Feb 1779', 'record', 'muster roll dated 5 Feb 1779')]),

    dict(pid='@I242612391585@', name='Christopher Osborne', war='Revolution, 1781',
         unit='North Carolina (pay voucher)',
         summary='A North Carolina Revolutionary pay voucher of 14 June 1781, from the Salisbury District auditors. '
                 'It shows he served, not where.',
         sources=['North Carolina Revolutionary pay vouchers (FamilySearch index)'],
         stops=[]),

    # ---------------------------------------------------------------- War of 1812
    dict(pid='@I242612042157@', name='Charles Love', war='War of 1812',
         unit='Private, Capt. Walker\'s company, North Carolina Militia',
         summary='Served as a private in Capt. Walker\'s company of North Carolina militia.',
         sources=['War of 1812 service records index (NARA M602, roll 128)'],
         stops=[]),

    dict(pid='@I242611471046@', name='William Calmes Buck', war='War of 1812',
         unit='1st Lieutenant, 2nd Regiment Virginia Militia',
         summary='A first lieutenant in the 2nd Virginia Militia; licensed to preach in August 1812, he is said to '
                 'have preached his first sermon in uniform. In his seventies he was a travelling chaplain to '
                 'Confederate camps and hospitals.',
         sources=['War of 1812 service records index (NARA M602, roll 28); Wikipedia, "William Calmes Buck"'],
         stops=[]),

    # ---------------------------------------------------------------- Civil War
    dict(pid='@I242611466570@', name='Thomas J. Askew', war='Civil War, 1861-65',
         unit='Co. H, 31st Georgia Infantry (Lawton\'s, later Gordon\'s brigade)',
         summary='Enlisted at Hamilton, Harris County, 13 November 1861. Wounded at Gaines\' Mill, 27 June 1862: a '
                 'minié ball broke his right forearm and left the arm useless. Home on wounded furlough that winter; '
                 'back with the army and paroled at Appomattox, 9 April 1865. Where he was in between isn\'t recorded.',
         sources=['Compiled service record (NARA 76366097, M266); Georgia Confederate pension, Harris Co., 1887-89 '
                  '(Georgia Archives Virtual Vault)'],
         stops=[S('Hamilton, Harris Co., GA', 32.757, -84.875, '13 Nov 1861', 'record', 'enlisted'),
                S('Richmond', 37.541, -77.436, 'June 1862', 'record', 'paid at Richmond, July 1862', by='rail'),
                S('Gaines\' Mill', 37.566, -77.293, '27 June 1862', 'record', 'wounded in the right arm'),
                S('Hamilton, Harris Co., GA', 32.757, -84.875, 'Nov-Dec 1862', 'record', 'absent on wounded furlough', by='rail'),
                S('Appomattox Court House', 37.377, -78.797, '9 Apr 1865', 'record', 'paroled', gap=True)]),

    dict(pid='@I242611467606@', name='Augustine "Gustus" Snow', war='Civil War, 1861-65',
         unit='Greene Rough and Readys; Co. D, 4th Virginia Heavy Artillery; Co. D, 34th Virginia Infantry (Wise\'s brigade)',
         summary='Enrolled at Stanardsville in May 1861 and mustered in at Culpeper Court House; re-enlisted for the '
                 'war in 1862. Home on furlough in February 1863. Deserted to the Union lines at Petersburg, 21 February '
                 '1865; took the oath at Washington and was given transport to Cincinnati.',
         sources=['Compiled service record (NARA 97345344, M324)'],
         stops=[S('Stanardsville, VA', 38.297, -78.440, 'May 1861', 'record', 'enrolled'),
                S('Culpeper Court House', 38.473, -77.997, 'June 1861', 'record', 'mustered in'),
                S('Chaffin\'s Bluff (James River)', 37.400, -77.340, '1862-63', 'unit', '4th Virginia Heavy Artillery'),
                S('Petersburg lines', 37.228, -77.402, '21 Feb 1865', 'record', 'deserted to the enemy'),
                S('City Point', 37.312, -77.286, '21 Feb 1865', 'record'),
                S('Washington, DC', 38.895, -77.036, '24 Feb 1865', 'record', 'took the oath', by='sea'),
                S('Cincinnati', 39.103, -84.512, 'Mar 1865', 'record', 'transportation furnished', by='rail')]),

    dict(pid='@I242611467434@', name='Merriwether L. Snow', war='Civil War, 1864',
         unit='Co. F, 35th Battalion Virginia Cavalry (White\'s "Comanches"); 5th sergeant from 5 May 1864',
         summary='On the rolls of the 35th Battalion Virginia Cavalry (Rosser\'s Laurel Brigade) from April to August 1864; '
                 'made fifth sergeant 5 May 1864, the first day of the Wilderness. The route is his battalion\'s to the '
                 'last roll that shows him.',
         sources=['NPS Soldiers and Sailors (M382, roll 52); Virginia Regimental Histories series'],
         stops=[S('Greene County, VA', 38.297, -78.440, 'spring 1864', 'family', 'home'),
                S('The Wilderness', 38.315, -77.740, '5-6 May 1864', 'unit', 'made 5th sergeant 5 May 1864'),
                S('Spotsylvania', 38.201, -77.590, 'May 1864', 'unit'),
                S('Trevilian Station', 38.047, -78.070, '11-12 June 1864', 'unit'),
                S('Petersburg (Reams Station)', 37.138, -77.431, 'Aug 1864', 'unit', 'on the rolls 31 Aug 1864')]),

    dict(pid='@I242611467540@', name='Albert Michie Shifflett', war='Civil War, 1861-62',
         unit='Uncertain: 58th Virginia Militia, Co. A, or the White Hall Guards (Co. H, 56th Virginia)',
         summary='Two Albert Shiffletts appear: one in the 58th Virginia Militia, enlisted at Harrisonburg 12 November '
                 '1861 and on the rolls at Winchester to March 1862; one in Capt. J. Augustus Michie\'s White Hall '
                 'Guards of Albemarle, later listed as a deserter. Which is him isn\'t known.',
         sources=['Compiled service records (NARA 98452752, 98396887, M324)'],
         stops=[S('Harrisonburg, VA', 38.449, -78.869, '12 Nov 1861', 'conjecture', 'enlisted (if this is him)'),
                S('Winchester', 39.186, -78.163, 'Dec 1861', 'conjecture', 'roll dated 10 Dec 1861'),
                S('Harrisonburg, VA', 38.449, -78.869, 'Mar 1862', 'conjecture', 'the militia disbanded')]),

    dict(pid='@I242611467559@', name='Reuben Lamb', war='Civil War, 1861-62',
         unit='Co. B, 58th Virginia Militia (4th Regiment, 7th Brigade)',
         summary='Enlisted at Winchester 23 November 1861, when the 58th Militia was called out for six months; '
                 'the regiment was disbanded in March 1862.',
         sources=['Compiled service record (NARA 98451180, M324)'],
         stops=[S('Greene County, VA', 38.297, -78.440, 'Nov 1861', 'family', 'home'),
                S('Winchester', 39.186, -78.163, '23 Nov 1861', 'record', 'enlisted; roll dated 10 Dec 1861'),
                S('Greene County, VA', 38.297, -78.440, 'Mar 1862', 'unit', 'the regiment disbanded')]),

    dict(pid='@I242611467681@', name='Hiram "Harm" Banks Shifflett', war='Civil War, 1861',
         unit='Unknown (possibly the "H. B. Shifflett" of the 88th Virginia Militia)',
         summary='Family tradition, told by his granddaughter-in-law: he deserted after seeing Bull Run run red, fled '
                 'west and settled in Hopkins Gap. The author found in the census that he actually left Greene County '
                 'between 1880 and 1890.',
         sources=['"The Red Flannel Rag" (family memoir), pp. 42-43; NARA index card, H. B. Shifflett, 88th Va. Militia'],
         stops=[]),

    dict(pid='@I242611467616@', name='William Suel Morris', war='Civil War',
         unit='Possibly Co. C, 14th Virginia Infantry',
         summary='A William S. Morris served as a private in Co. C, 14th Virginia Infantry. The 14th was raised mostly '
                 'in Southside counties, so this may be another man.',
         sources=['NPS Soldiers and Sailors (M382, roll 39)'],
         stops=[]),

    dict(pid='@I242611468681@', name='Charles Willis Buck Sr.', war='Civil War, 1864',
         unit='Chaplain, 42nd Alabama Infantry',
         summary='Appointed chaplain of the 42nd Alabama 8 January 1864 (rank from 23 October 1863), delivered through '
                 'Gen. Johnston at Dalton; paid as chaplain for May 1864, as the Atlanta campaign opened. A Mobile paper '
                 'in November 1864 had him moved from the Levert officers\' hospital to Uniontown.',
         sources=['Confederate officers\' service record (NARA 51159807, M331); Army Argus and Crisis, Mobile, 12 Nov 1864; '
                  'NPS Soldiers and Sailors (M374)'],
         stops=[S('Marion, AL', 32.632, -87.319, '1863', 'family', 'home'),
                S('Dalton, GA', 34.770, -84.970, 'Jan 1864', 'record', 'appointment delivered through Gen. Johnston', by='rail'),
                S('Resaca', 34.580, -84.940, 'May 1864', 'unit'),
                S('Kennesaw Mountain', 33.983, -84.578, 'June 1864', 'unit'),
                S('Atlanta', 33.749, -84.388, 'July 1864', 'unit'),
                S('Mobile (Levert hospital)', 30.694, -88.043, '1864', 'record', by='rail'),
                S('Uniontown, AL', 32.449, -87.514, 'Nov 1864', 'record', 'moved from the hospital', by='rail')]),

    dict(pid='@I242611471538@', name='Thomas Jefferson Dismukes', war='Civil War, 1862-65',
         unit='Probably Co. K, 39th Alabama Infantry',
         summary='"Jefferson Y. Dismukes", aged 33, enlisted in Barbour County, Alabama, on the 15 May 1862 muster roll '
                 'of Co. K, 39th Alabama: very likely him. The route is the 39th Alabama\'s, through the Army of Tennessee.',
         sources=['Alabama Civil War service database (ADAH SG025049), per James; NPS index lists a T. J. Dismukes '
                  'in the 61st Alabama'],
         stops=[S('Barbour County, AL (Clayton)', 31.878, -85.450, 'May 1862', 'family', 'enlisted (if this is him)'),
                S('Murfreesboro', 35.846, -86.392, 'Dec 1862', 'unit', by='rail'),
                S('Chickamauga', 34.920, -85.260, 'Sept 1863', 'unit', by='arc',
                  way=[(35.362, -86.209), (35.164, -86.010), (35.046, -85.309), (34.705, -85.282)]),
                  # Tullahoma, Cowan, Chattanooga, LaFayette
                S('Missionary Ridge', 35.020, -85.260, 'Nov 1863', 'unit'),
                S('Atlanta', 33.749, -84.388, 'July 1864', 'unit', 'the Atlanta campaign', by='arc',
                  way=[(34.770, -84.970), (34.580, -84.940), (34.240, -84.850), (33.940, -84.790), (33.980, -84.580)]),
                  # Dalton, Resaca, Cassville, New Hope Church, Kennesaw
                S('Franklin, TN', 35.925, -86.869, '30 Nov 1864', 'unit', 'Hood\'s Tennessee campaign', by='arc',
                  way=[(33.520, -84.670), (34.770, -84.970), (34.705, -85.282), (34.014, -86.006), (34.731, -87.702),
                       (34.800, -87.677), (35.615, -87.035), (35.751, -86.930)]),
                  # Palmetto, Dalton, LaFayette, Gadsden, Tuscumbia, Florence, Columbia, Spring Hill
                S('Nashville', 36.162, -86.781, 'Dec 1864', 'unit'),
                S('Bentonville, NC', 35.300, -78.320, 'Mar 1865', 'unit', by='rail')]),

    dict(pid='@I242611471478@', name='Thomas T. Wyche', war='Civil War, 1862',
         unit='Georgia (unit not known)',
         summary='An index lists a Thomas Wyche enlisting in Georgia on 10 April 1862, with no unit. He would have been 51; '
                 'it may be another man.',
         sources=['American Civil War Research Database (Historical Data Systems)'],
         stops=[]),

    dict(pid='@I242611467268@', name='William Warren Hardin Sr.', war='Civil War, 1862',
         unit='Georgia militia, Tattnall County (unit not known)',
         summary='On a Tattnall County, Georgia, muster roll of 4 March 1862. Identity uncertain.',
         sources=['Georgia Civil War muster rolls, 1860-1864 (index)'],
         stops=[]),
]

# ======================== from "Our American History" (James's family history) ========================
SERVICE += [
    dict(pid='@I240016590578@', name='John Speer Jr.', war='War of 1812, 1812',
         unit='A Kentucky company (not named)',
         summary='After the Pigeon Roost massacre (3 September 1812), his company marched from Kentucky to Vincennes, '
                 'Indiana, on a retaliatory expedition, and met not a single Indian the whole way.',
         sources=['"Our American History" (family history, 2026)'],
         stops=[S('Kentucky (Louisville)', 38.253, -85.759, 'Sept 1812', 'family'),
                S('Pigeon Roost, IN', 38.600, -85.720, 'Sept 1812', 'family', 'the massacre site'),
                S('Vincennes, IN', 38.677, -87.528, 'autumn 1812', 'family')]),

    dict(pid='@I240023089394@', name='Frederick "Fritz" Schwab', war='Civil War, 1863',
         unit='Missouri Home Guard',
         summary='Registered for the draft 1 July 1863 and soon afterwards enlisted with the Union in the Missouri '
                 'Home Guard. (The only Home Guard record found, a Friedrich Schwab of the Gasconade County regiment, '
                 'is probably another man.)',
         sources=['"Our American History" (family history, 2026)', 'Civil War draft registrations (Cape Girardeau)'],
         stops=[]),

    dict(pid='@I242261004267@', name='Thomas Robertson', war='Revolution, about 1776',
         unit='Not known',
         summary='Family history says he came from Aberdeen to the colonies about 1776 for the express purpose of '
                 'joining the war against the British.',
         sources=['"Our American History" (family history, 2026)'],
         stops=[]),
]

# ======================== from the WikiTree survey (2026-09-28): only claims backed by a cited source ========================
SERVICE += [
    dict(pid='@I242611467697@', name='John Snow', war='Revolution, 1776-78',
         unit='2nd Virginia Continental Regiment, Capt. Francis Taylor\'s company',
         summary='Enlisted in the spring of 1776 for two years; served them out and was discharged at Valley Forge. '
                 'His 1818 pension declaration names the battles of Brandywine and Germantown; Francis Cowherd, an '
                 'officer of the regiment, swore to his service.',
         sources=['Pension declaration, 1818 (NARA M804), as transcribed on WikiTree (Snow-2968)',
                  'Revolutionary War Rolls (NARA M246)'],
         stops=[S('Orange County, VA', 38.245, -78.110, 'spring 1776', 'family', 'enlisted'),
                S('Williamsburg', 37.271, -76.707, '1776', 'unit', 'the 2nd Virginia\'s first station'),
                S('Brandywine', 39.872, -75.591, '11 Sept 1777', 'record'),
                S('Germantown', 40.040, -75.180, '4 Oct 1777', 'record'),
                S('Valley Forge', 40.097, -75.440, 'spring 1778', 'record', 'discharged at the end of his two years')]),

    dict(pid='@I242611579166@', name='Martin Johnson', war='Creek War (War of 1812), 1814',
         unit='Sergeant, Capt. James Tate\'s company, Col. Stephen Copeland\'s 3rd West Tennessee Militia (Gen. Thomas Johnson\'s brigade)',
         summary='Mustered in as a sergeant on 28 January 1814 and discharged in May 1814; the service made him '
                 'eligible for bounty land in 1850. The regiment marched from Fayetteville by Fort Deposit and Fort '
                 'Strother to Fort Williams; the route is the regiment\'s.',
         sources=['1814 muster roll of Capt. Tait\'s Warren County company, transcribed at combs-families.org',
                  'TNGenWeb, Third Regiment Tennessee Militia, War of 1812', 'WikiTree (Johnson-2448)'],
         stops=[S('Warren County, TN (McMinnville)', 35.684, -85.770, 'Jan 1814', 'family', 'home'),
                S('Fayetteville, TN', 35.152, -86.570, '28 Jan 1814', 'record', 'mustered in as a sergeant'),
                S('Fort Deposit, AL', 34.590, -86.410, 'Feb 1814', 'unit'),
                S('Fort Strother, AL', 33.895, -86.225, 'Mar 1814', 'unit'),
                S('Fort Williams, AL', 33.260, -86.340, 'Apr 1814', 'unit'),
                S('Warren County, TN (McMinnville)', 35.684, -85.770, 'May 1814', 'record', 'discharged')]),

    dict(pid='@I242087821909@', name='Samuel Eells', war='King Philip\'s War, 1675',
         unit='Captain',
         summary='Captain in King Philip\'s War. At Dartmouth, Indians who surrendered to him on a promise of fair '
                 'treatment were "carried away to Plymouth, there sold, and transported out of the country, being '
                 'about eight-score persons," as Benjamin Church recorded.',
         sources=['Benjamin Church, The History of King Philip\'s War (2nd ed., Newport, 1772)', 'WikiTree (Eells-5)'],
         stops=[S('Dartmouth (Apponagansett), MA', 41.600, -70.990, 'summer 1675', 'record',
                  'the surrendered Indians were sold into slavery at Plymouth')]),

    dict(pid='@I240021677157@', name='Gideon Welles', war='French and Indian War; Revolution',
         unit='Physician: the Connecticut hospital (French and Indian War); surgeon, Webb\'s regiment (Revolution)',
         summary='On the Connecticut rolls of the French and Indian War in 1758, when he directed the colony\'s '
                 'hospital; in the Revolution a surgeon of Webb\'s regiment (William Raymond\'s regiment), on the '
                 'rolls in 1778 and 1780. The rolls give no places.',
         sources=['Rolls of Connecticut Men in the French and Indian War (Connecticut Historical Society)',
                  'Revolutionary War Rolls, 1775-1783', 'WikiTree (Welles-631)'],
         stops=[]),

    dict(pid='@I240020573684@', name='Joseph Bostwick Jr.', war='French and Indian War, 1758',
         unit='Connecticut troops',
         summary='On the Connecticut rolls of the French and Indian War in 1758. The roll gives no places.',
         sources=['Connecticut Soldiers, French and Indian War, 1755-62 (in James\'s tree)'], stops=[]),

    dict(pid='@I242079819704@', name='John Speer Sr.', war='Revolution, 1779',
         unit='Capt. Alexander Peebles\'s company, 6th Battalion, Cumberland County (Pennsylvania) militia',
         summary='In Capt. Alexander Peebles\'s company of the 6th Battalion of Cumberland County militia in 1779, '
                 'when he lived at Hopewell. The roll gives no service places.',
         sources=['Cumberland County militia roll, 1779 (in James\'s tree)'], stops=[]),

    dict(pid='@I240022524203@', name='Henry Crosby Floyd', war='War of 1812',
         unit='Kentucky', summary='Served in the War of 1812; the index gives no unit details.',
         sources=['United States, War of 1812 Index to Service Records (NARA M602)', 'WikiTree (Floyd-1105)'], stops=[]),

    dict(pid='@I240022524290@', name='Henry Bruce Floyd', war='Revolution, 1778-79',
         unit="Lieutenant, Illinois Regiment (George Rogers Clark), Capt. Leonard Helm's company",
         summary="His sons Henry and John swore in 1834 that he had been a lieutenant in Clark's Illinois Regiment "
                 '"in the subjugation of the posts of Kaskaskia and St. Vincents," serving under his wife\'s brother, '
                 "Capt. Leonard Helm, and that he received about 2,156 acres in the Illinois Grant. The heirs' claim "
                 'for his half pay was refused because he had not served to the end of the war. Past fifty when he '
                 "went. The route to Kaskaskia is the regiment's: down the Ohio from Pittsburgh to the Falls, then "
                 'to Fort Massac and overland.',
         sources=["Heirs' half-pay claim R.14982 1/2 (Leonard Helm file), deposition of Henry and John Floyd, 18 Feb 1834 "
                  '(transcribed at revwarapps.org/r14982.5.pdf)'],
         stops=[S('Fauquier County, VA', 38.713, -77.795, 'early 1778', 'family', 'home; Helm raised his company here'),
                S('Pittsburgh', 40.441, -80.004, 'spring 1778', 'unit'),
                S('Falls of the Ohio (Corn Island)', 38.270, -85.760, 'May-June 1778', 'unit', by='water'),
                S('Fort Massac', 37.147, -88.706, 'June 1778', 'unit', by='water'),
                S('Kaskaskia', 37.921, -89.914, '4 July 1778', 'family', 'taken without a fight', by='arc'),
                S('Vincennes (Post St. Vincent)', 38.678, -87.528, '1778-79', 'family', by='arc')]),

    dict(pid='@I242212388601@', name='Henry Souther Sr.', war='War of 1812',
         unit='Kentucky', summary='A War of 1812 pension file exists for him; its contents are not yet read.',
         sources=['U.S., War of 1812 Pension Application Files Index (in James\'s tree)'], stops=[]),
]

# ======================== Benjamin Askew (James, 2026-10-02; NCGenWeb, Jones County) ========================
SERVICE += [
    dict(pid="@I242611466983@", name="Benjamin Askew", war="Revolution",
         unit="North Carolina; by family account, part of his service under Gen. Anthony Wayne",
         summary="A voucher for payment for service in the Revolution was issued to Benjamin Askew in August 1783; "
                 "descendants used it to join the Daughters of the American Revolution. His great-grandson James Henry "
                 "Askew wrote in 1926 that he served part of his time under General Anthony Wayne, once stood picket "
                 "across a river from the American camp, and was with the troops who captured a British camp and its "
                 "supplies. The account names no places or dates, and the voucher itself has not been seen for this map.",
         sources=["North Carolina Revolutionary pay voucher to Benjamin Askew, Aug 1783 (as cited in the article below; not seen)",
                  "James Henry Askew, family account written at Waldo, Arkansas, 11 Nov 1926, in \"Benjamin Askew Family\" (contributed by Margarette Stout), NCGenWeb, Jones County"],
         stops=[]),
]
