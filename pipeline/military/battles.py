"""
Battles on the map (the crossed-swords symbols in the Military service layer).

Each entry names a battle and the itinerary stops that are it: a stop label
from itineraries.py and the year it's dated. Stage 9 (build_military.py) tags
every matching stop with the battle's name (`b` on the stop in MILITARY), and
the page draws one symbol per battle listing every ancestor there, with the
basis of each (documented for him, his regiment, family account, a guess).

Only fights: camps, musters, marches and captivity are not battles here, and
neither are the raids known only by conjecture (Tryon's raid, 1779).
"""

# (name as shown, date as shown, [(stop label, year), ...])
BATTLES = [
    ('Attack on the Pequot fort at Mystic', '26 May 1637', [('Pequot fort at Mystic', 1637)]),
    ('The Great Swamp Fight', '19 Dec 1675', [('Great Swamp fort, South Kingstown', 1675)]),
    ('Siege of Cartagena', 'Mar-Apr 1741', [('Cartagena de Indias', 1741)]),
    ('Battle of Fort Necessity', '3 July 1754', [('Fort Necessity (Great Meadows)', 1754)]),
    ('Siege of Fort St. Johns', 'Sept-Nov 1775', [('St. Johns, Quebec (siege)', 1775)]),
    ('Battle of Ridgefield', '27 Apr 1777', [('Ridgefield (battle)', 1777)]),
    ('Battle of Brandywine', '11 Sept 1777', [('Brandywine', 1777)]),
    ('Battle of Paoli', '20-21 Sept 1777', [('Paoli', 1777)]),
    ('Battles of Saratoga', 'Sept-Oct 1777', [('Saratoga (Bemis Heights)', 1777)]),
    ('Battle of Germantown', '4 Oct 1777', [('Germantown', 1777)]),
    ('Battle of Monmouth', '28 June 1778', [('Monmouth', 1778), ('Monmouth Court House', 1778)]),
    ('Battle of Rhode Island', '29 Aug 1778', [('Rhode Island (battle, 29 Aug 1778)', 1778)]),
    ('Battle of Newtown', '29 Aug 1779', [('Newtown (Elmira), NY', 1779)]),
    ("Lochry's Defeat", '24 Aug 1781', [('Laughery Creek (Lochry\'s defeat)', 1781)]),
    ('Battle of Green Spring', '6 July 1781', [('Jamestown (Green Spring)', 1781)]),
    ('Siege of Yorktown', 'Sept-Oct 1781', [('Yorktown', 1781), ('Yorktown (siege)', 1781)]),
    ('Battle of the Thames', '5 Oct 1813', [('Battle of the Thames (Moraviantown)', 1813)]),
    ('Battle of Sacramento', '28 Dec 1861', [('Sacramento, KY (battle)', 1861)]),
    ('Fort Donelson', 'Feb 1862', [('Fort Donelson', 1862)]),
    ('Siege of Yorktown (1862)', 'Apr-May 1862', [('Yorktown (siege)', 1862)]),
    ('Battle of Williamsburg', '5 May 1862', [('Williamsburg', 1862)]),
    ('Battle of Seven Pines', '31 May 1862', [('Seven Pines', 1862)]),
    ("Battle of Gaines' Mill", '27 June 1862', [("Gaines' Mill", 1862)]),
    ('Battle of Malvern Hill', '1 July 1862', [('Malvern Hill', 1862)]),
    ('Second Battle of Bull Run', '29-30 Aug 1862', [('Second Bull Run', 1862)]),
    ('Battle of Fredericksburg', '13 Dec 1862', [('Fredericksburg', 1862)]),
    ('Battle of Stones River', '31 Dec 1862', [('Murfreesboro', 1862)]),
    ('Battle of Chancellorsville', '2-3 May 1863', [('Chancellorsville', 1863)]),
    ('Battle of Champion Hill', '16 May 1863', [('Champion Hill', 1863)]),
    ('Battle of Gettysburg', '1-3 July 1863', [('Gettysburg', 1863)]),
    ('Battle of Chickamauga', 'Sept 1863', [('Chickamauga', 1863)]),
    ('Battle of Missionary Ridge', 'Nov 1863', [('Missionary Ridge', 1863)]),
    ('Mine Run campaign', 'Nov 1863', [('Mine Run', 1863)]),
    ('Battle of Paducah', '25 Mar 1864', [('Paducah', 1864)]),
    ('Battle of the Wilderness', '5-6 May 1864', [('The Wilderness', 1864)]),
    ('Battle of Resaca', 'May 1864', [('Resaca', 1864)]),
    ('Battle of Spotsylvania', 'May 1864', [('Spotsylvania', 1864)]),
    ("Battle of Brice's Crossroads", '10 June 1864', [("Brice's Crossroads", 1864)]),
    ('Battle of Trevilian Station', '11-12 June 1864', [('Trevilian Station', 1864)]),
    ('Battle of Kennesaw Mountain', 'June 1864', [('Kennesaw Mountain', 1864)]),
    ('Battle of Tupelo', 'July 1864', [('Tupelo', 1864)]),
    ('Battle of Atlanta', 'July 1864', [('Atlanta', 1864)]),
    ('Second Battle of Reams Station', 'Aug 1864', [('Petersburg (Reams Station)', 1864)]),
    ('Battle of Franklin', '30 Nov 1864', [('Franklin, TN', 1864)]),
    ('Battle of Nashville', 'Dec 1864', [('Nashville', 1864)]),
    ('Battle of Bentonville', 'Mar 1865', [('Bentonville, NC', 1865)]),
    ('Appomattox Court House', '9 Apr 1865', [('Appomattox Court House', 1865)]),
    ('Saint-Mihiel offensive', '12-16 Sept 1918', [('Saint-Mihiel offensive (near Xammes)', 1918)]),
]
