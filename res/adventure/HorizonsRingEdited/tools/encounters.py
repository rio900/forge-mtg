"""Adventure-sized Modern packages and bounded encounter card rewards."""
from collections import Counter

PACKAGES = {
    'Chandra': {'Monastery Swiftspear':2,'Lightning Bolt':3,'Slickshot Show-Off':2,'Fable of the Mirror-Breaker':1},
    'Tibalt': {'Lightning Bolt':3,'Fable of the Mirror-Breaker':2,'Seasoned Pyromancer':2},
    'Teferi': {'Ephemerate':3,'Flickerwisp':2,'Quantum Riddler':1,'Teferi, Time Raveler':1,'Errand-Rider of Gondor':2},
    'Jace': {'Ephemerate':3,'Quantum Riddler':2,'Fallaji Archaeologist':2,'Teferi, Time Raveler':1},
    'Conjurer': {'Fallaji Archaeologist':3,'Psychic Frog':2,'Quantum Riddler':1,'Thoughtseize':2},
    'Sorin': {'Sheoldred, the Apocalypse':2,'Thoughtseize':2,'Inquisition of Kozilek':2},
    'Garruk': {'Sheoldred, the Apocalypse':1,'Agatha\'s Soul Cauldron':1,'Nested Shambler':3,'Carrion Feeder':2},
    'Kiora': {'Arboreal Grazer':3,'Quantum Riddler':2,'Shardless Agent':2},
    'Guardian Angel': {'Atraxa, Grand Unifier':2,'Faithful Mending':3,"Goryo's Vengeance":3,'Ephemerate':2},
    'Master Red Wizard': {'Monastery Swiftspear':2,'Lightning Bolt':2,'Slickshot Show-Off':1},
    'Master Blue Wizard': {'Fallaji Archaeologist':2,'Quantum Riddler':1,'Mystical Dispute':2},
    'Master Black Wizard': {'Inquisition of Kozilek':2,'Dismember':1,'Not Dead After All':2},
    'Master White Wizard': {'Ephemerate':2,'Flickerwisp':2,'Errand-Rider of Gondor':2},
    'Master Green Wizard': {'Arboreal Grazer':2,'Boseiju, Who Endures':1},
}

def upgrade(builder, enemy, rows, mask):
    """Keep original size, lands and theme. Substitute at most ten spell slots."""
    package=PACKAGES.get(enemy['name'],{})
    for name in package:
        assert name in builder.legal or name in builder.modern, name
        assert not builder.db[name].mask & ~mask, (enemy['name'],name,mask)
    protected=set(package)
    for name, target in package.items():
        land='Land' in builder.db[name].kinds
        while rows[name]<target:
            choices=[n for n,q in rows.items() if q and n not in protected and ('Land' in builder.db[n].kinds)==land]
            assert choices,(enemy['name'],name)
            donor=max(choices,key=lambda n:(rows[n],builder.db[n].cost,n))
            rows[donor]-=1; rows[name]+=1
    return +rows

def reward_pools(builder):
    # Exact rarity weights, independent of the number of available names.
    for title, weights in [('Support',{'C':50,'U':50}),('Premium',{'R':80,'M':20})]:
        groups={r:sorted(c.name for c in builder.legal.values() if c.rarity==r and not c.removed) for r in weights}
        from math import lcm
        scale=lcm(*(len(g) for g in groups.values()))
        rows=Counter({n:weights[r]*scale//len(group) for r,group in groups.items() for n in group})
        # Reduce weights to keep runtime flat pools compact.
        from functools import reduce
        from math import gcd
        divisor=reduce(gcd,rows.values())
        rows=Counter({n:q//divisor for n,q in rows.items()})
        builder.write_deck(f'decks/arena/{title}.dck',title+' encounter reward',{'Main':rows})
    builder.arena_pool('Any')

def rewards(enemy):
    boss=enemy.get('boss',False)
    if not boss and enemy['name'] not in PACKAGES:return
    # No deckCard leaks: adding powerful spells to an opponent cannot multiply its loot.
    noncards=[r for r in enemy.get('rewards',[]) if r.get('type','card').lower() not in
              {'card','randomcard','deckcard','rewarddeckcard','union','cardpack','cardpackshop'}]
    enemy['rewards']=noncards+[
        {'type':'card','count':2,'sourceDeck':'decks/arena/Support.dck'},
        {'type':'card','count':1,'probability':1 if boss else .10,'sourceDeck':'decks/arena/Premium.dck'},
        {'type':'card','count':1,'probability':.35 if boss else .05,'sourceDeck':'decks/arena/Any.dck'},
    ]
