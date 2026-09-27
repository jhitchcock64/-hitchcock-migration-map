"""
Hand-written life stories for the profiles (stage 11, build_profiles.py).

Everyone gets a short summary generated from the tree's facts on the page;
a story here replaces it. Stories are drafted from the person's records and
sources and approved by James. Write them without "your": the page names the
relationship to whoever is the current target.

  pid: dict(title='a few words', text=['paragraph', ...], note='optional research note')
"""

STORIES = {
    '@I242209901667@': dict(   # William Worthington (1761-1848)
        title='Frontier ranger, prisoner of war, Kentucky pioneer',
        text=[
            'William was born on 1 May 1761 in Frederick County, Virginia, and grew up on the Pennsylvania '
            'frontier in Westmoreland County. At twenty he went down the Ohio with Col. Archibald Lochry\'s '
            'rangers to join George Rogers Clark. The column was destroyed below the Great Miami on 24 August '
            '1781, and he was taken prisoner.',
            'His captivity took him to Upper Sandusky and Detroit, across Lake Erie to Fort Niagara, to a prison '
            'island in the St. Lawrence and finally to the Montreal jail. He broke out in the autumn of 1782, '
            'most likely with his fellow captive Manasseh Coyle, and was home in Westmoreland by 20 December, '
            'by way of Lake Champlain and Philadelphia.',
            'He married Mary Meason about 1783. In February 1786 the family left for Kentucky, reaching Vienna, '
            'on the Green River in what is now McLean County, that March. They raised nine children there and '
            'in Muhlenberg County, where the census finds him from 1810 to 1840. Mary died in 1827. Late in life '
            'William went to Washington County, Mississippi, where his sons Isaac and William Waring also '
            'settled; he died there on 5 June 1848 and was buried at Island, McLean County.',
        ]),
}
