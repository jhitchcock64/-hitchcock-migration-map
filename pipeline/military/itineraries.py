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
                 period roads, or a straight line), 'water' (rivers, lakes, coastal
                 lanes and roads), 'sea' (the same), or 'rail' (anything, railroads included)
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
                  'the fort surrendered to the French'),
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
                S('Morristown, NJ (Jockey Hollow)', 40.763, -74.543, 'winter 1779-80', 'unit'),
                S('West Point, NY', 41.392, -73.956, 'June 1783', 'record', 'discharged')]),

    dict(pid='@I242086113939@', name='Henry Burdick', war='Revolution, 1777-83',
         unit='2nd New York (Col. Philip Van Cortlandt), Capt. Jacob Wright\'s company',
         summary='Enlisted 27 May 1777 and served six years, discharged 4 June 1783. He names no battles; '
                 'the route is his regiment\'s.',
         sources=['Pension file (NARA 54107986): his 1818 declaration'],
         stops=[S('Saratoga (Bemis Heights)', 42.999, -73.637, 'Sept-Oct 1777', 'unit'),
                S('Valley Forge', 40.097, -75.440, 'winter 1777-78', 'unit'),
                S('Monmouth Court House', 40.266, -74.320, '28 June 1778', 'unit'),
                S('Newtown (Elmira), NY', 42.048, -76.720, '29 Aug 1779', 'unit', 'Sullivan\'s expedition'),
                S('Yorktown', 37.239, -76.510, 'Oct 1781', 'unit'),
                S('New Windsor cantonment, NY', 41.458, -74.060, '4 June 1783', 'record', 'discharged', by='water')]),

    dict(pid='@I240016442918@', name='William Raymond', war='Revolution, 1775-81',
         unit='Waterbury\'s regt (1775), Bradley\'s regt (1776), Webb\'s regt, Connecticut line (1777-81)',
         summary='Three enlistments: 1775 under Capt. Ichabod Doolittle (Waterbury\'s, the northern campaign), '
                 '1776 under Capt. Elijah Abel (Bradley\'s), and from January 1777 under Capt. John Mills in '
                 'Webb\'s regiment until early 1781.',
         sources=['Pension S.35,596 (NARA 196461238): his 1818 declaration'],
         stops=[S('New Canaan, CT', 41.147, -73.495, 'spring 1775', 'record'),
                S('Albany, NY', 42.653, -73.756, 'summer 1775', 'unit', by='water'),
                S('Ticonderoga', 43.842, -73.387, 'Aug 1775', 'unit', by='water'),
                S('St. Johns, Quebec (siege)', 45.307, -73.263, 'Sept-Nov 1775', 'unit', by='water'),
                S('New Canaan, CT', 41.147, -73.495, 'winter 1775-76', 'unit', 'home at the end of the term', by='water'),
                S('Bergen, NJ', 40.728, -74.078, 'summer 1776', 'unit', 'Bradley\'s battalion'),
                S('New Canaan, CT', 41.147, -73.495, 'winter 1776-77', 'unit'),
                S('Peekskill, NY (Hudson Highlands)', 41.290, -73.920, '1777', 'unit', 'Webb\'s regiment'),
                S('Rhode Island (battle, 29 Aug 1778)', 41.601, -71.260, 'Aug 1778', 'unit'),
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
         stops=[]),

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
         sources=['Pension S.1272: his declaration'],
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
                S('Westmoreland Co., PA', 40.308, -79.499, '20 Dec 1782', 'record',
                  'broke jail about 1 Nov 1782; the way home isn\'t recorded')]),

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
         stops=[]),

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
                S('Urbana, OH', 40.108, -83.752, 'Sept 1813', 'unit'),
                S('Upper Sandusky', 40.827, -83.281, 'Sept 1813', 'unit'),
                S('The Portage (Port Clinton)', 41.512, -82.938, 'Sept 1813', 'unit'),
                S('Amherstburg (by Perry\'s fleet)', 42.101, -83.108, '27 Sept 1813', 'unit', by='sea'),
                S('Sandwich (Windsor)', 42.295, -83.072, 'Sept 1813', 'unit'),
                S('Battle of the Thames (Moraviantown)', 42.570, -81.870, '5 Oct 1813', 'unit'),
                S('Detroit', 42.331, -83.046, 'Oct 1813', 'unit'),
                S('Woodford County, KY', 38.053, -84.730, 'Nov 1813', 'unit', 'discharged 12 Nov 1813')]),

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
                S('Gettysburg', 39.831, -77.231, '2 July 1863', 'unit'),
                S('Mine Run', 38.310, -77.830, 'Nov 1863', 'unit'),
                S('The Wilderness', 38.315, -77.740, '5-6 May 1864', 'family', 'badly wounded (family tradition)'),
                S('Trenton', 40.221, -74.760, '21 Sept 1864', 'record', 'mustered out')]),

    dict(pid='@I240172307606@', name='Friedrich Graden', war='Civil War, 1863',
         unit='Co. E, 8th Provisional Enrolled Missouri Militia Infantry',
         summary='His regiment served May to November 1863 on garrison duty in southeast Missouri.',
         sources=['Civil War pension index (filed 10 Mar 1892; wife Apollonia)'],
         stops=[]),

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
                 'James Henry died a prisoner at Camp Butler in 1862.',
         sources=['Don W. Hoover\'s write-up (2010); American Civil War Research Database (enlisted 13 Mar 1862)'],
         stops=[]),

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
                S('Saint-Mihiel offensive (near Xammes)', 48.969, 5.850, '12 Sept 1918', 'record'),
                S('St-Aignan (casual depot)', 47.269, 1.376, 'Dec 1918', 'record', 'casual company 406', gap=True),
                S('Saint-Nazaire', 47.274, -2.214, '28 Dec 1918', 'record', 'sailed on the Finland', by='rail'),
                S('New York', 40.713, -74.006, 'Jan 1919', 'record', by='sea',
                  way=[(47.05, -2.6), (47.6, -5.2), (48.6, -6.4)], via=['~scilly_w', 'new_york']),
                S('Cape Girardeau, MO', 37.306, -89.518, '1919', 'family', by='rail')]),
]
