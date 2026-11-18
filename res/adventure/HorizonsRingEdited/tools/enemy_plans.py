"""Reviewed encounter plans: independent threats, finite curves, supported abilities."""
from collections import Counter

COLORS={'Nissa':'G','Vorinclex':'G','Jin-Gitaxias':'U','Urabrask':'R','Kozilek':'C'}
# Quantities are deliberately below tournament playsets for most rare finishers.
PLANS={
'Nissa': '''
3 Arboreal Grazer
3 Llanowar Tribe
3 Springbloom Druid
3 Tireless Provisioner
3 Bannerhide Krushok
3 Trumpeting Herd
3 Yavimaya Elder
2 Generous Ent
2 Titania, Protector of Argoth
1 Avenger of Zendikar
2 Ent's Fury
2 Savage Swipe
2 Clear Shot
2 Timeless Witness
2 Many Partings
''',
'Vorinclex': '''
3 Duskshell Crawler
3 Scurry Oak
3 Deepwood Denizen
3 Bannerhide Krushok
3 Herd Baloth
2 Urban Daggertooth
2 Champion of Lambholt
1 Branching Evolution
3 Rift Sower
3 Smell Fear
2 Fangs of Kalonia
2 Gift of the Viper
3 Generous Ent
3 Evolution Witness
''',
'Jin-Gitaxias': '''
3 Faerie Seer
3 Watcher for Tomorrow
3 Man-o'-War
3 Serum Visionary
2 Oneirophage
1 The Watcher in the Water
2 Junk Winder
1 Quantum Riddler
1 Murktide Regent
3 Counterspell
2 Prohibit
3 Hard Evidence
3 Lórien Revealed
2 Fact or Fiction
4 String of Disappearances
''',
'Urabrask': '''
3 Monastery Swiftspear
3 Battle-Scarred Goblin
3 Erebor Flamesmith
3 Viashino Lashclaw
2 Seasoned Pyromancer
2 Laelia, the Blade Reforged
2 Goblin Traprunner
2 Rapacious Dragon
3 Lightning Bolt
3 Firebolt
2 Abrade
2 Reckless Charge
2 Rising of the Day
2 Rally at the Hornburg
2 Fable of the Mirror-Breaker
''',
'Kozilek': '''
3 Universal Automaton
3 Ornithopter of Paradise
3 Liquimetal Torque
3 Glaring Fleshraker
3 Worn Powerstone
3 Cathodion
2 Myr Battlesphere
2 Breaker of Creation
1 Kozilek, the Broken Reality
2 Eldrazi Ravager
2 Kozilek's Command
2 Duplicant
2 Expedition Map
2 Nettlecyst
2 Millikin
1 Sandstone Oracle
''',
'Griselbrand': '''
2 Griselbrand
2 Archon of Cruelty
3 Vile Entomber
3 Putrid Goblin
3 Nested Shambler
2 Young Necromancer
2 Bone Shredder
3 Bone Shards
2 Buried Alive
2 Victimize
2 Persist
2 Goryo's Vengeance
2 Unearth
3 Ransack the Lab
2 Defile
1 Unmarked Grave
''',
'Teferi': '''
3 Faerie Seer
3 Watcher for Tomorrow
3 Man-o'-War
3 Errand-Rider of Gondor
2 Flickerwisp
2 Timeless Dragon
1 Quantum Riddler
1 Teferi, Time Raveler
3 Ephemerate
3 Counterspell
3 Reprieve
2 Prismatic Ending
2 Piercing Rays
2 Fact or Fiction
1 Wrath of the Skies
2 Soul of Migration
''',
'Jace': '''
3 Faerie Seer
3 Fallaji Archaeologist
3 Watcher for Tomorrow
3 Man-o'-War
2 Quantum Riddler
2 Timeless Dragon
2 Oneirophage
1 Jace, the Mind Sculptor
3 Counterspell
3 Reprieve
3 Lórien Revealed
2 Fractured Sanity
2 Fact or Fiction
2 Piercing Rays
2 Ephemerate
''',
'Kiora': '''
3 Arboreal Grazer
3 Wose Pathfinder
3 Springbloom Druid
3 Tireless Provisioner
3 Shardless Agent
3 Trumpeting Herd
2 Junk Winder
2 Quantum Riddler
2 Generous Ent
2 Timeless Witness
3 Ent's Fury
3 Recalibrate
2 Lórien Revealed
2 Many Partings
''',
'Sliver Queen': '''
3 Universal Automaton
3 Impostor of the Sixth Pride
3 Enduring Sliver
3 Ornithopter of Paradise
3 Dregscape Sliver
3 Tempered Sliver
3 Cleaving Sliver
2 Cloudshredder Sliver
2 First Sliver's Chosen
2 Lancer Sliver
1 The First Sliver
2 Lavabelly Sliver
2 Pillage
2 Unearth
2 Reprieve
''',
'Fog Trap': '''
3 Spore Frog
3 Yavimaya Elder
3 Springbloom Druid
3 Samwise the Stouthearted
2 Timeless Witness
2 Generous Ent
2 Timeless Dragon
2 Soul of Migration
3 Blessed Respite
2 Orim's Chant
2 Wrath of God
3 Piercing Rays
3 Trumpeting Herd
3 Many Partings
''',
'Bandit Archer#2': '''
3 Orcish Hellraiser
3 Battle-Scarred Goblin
3 Easterling Vanguard
3 Haradrim Spearmaster
2 Éomer of the Riddermark
2 First-Sphere Gargantua
3 Firebolt
3 Lightning Bolt
3 Abrade
3 Terminal Agony
2 Quarrel's End
2 Urza's Rage
2 Reckless Charge
2 Unearth
''',
'Hellion': '''
3 Orcish Hellraiser
3 Battle-Scarred Goblin
3 Viashino Lashclaw
3 Thopter Engineer
3 Rapacious Dragon
2 Sneak Attack
2 Warbeast of Gorgoroth
2 Oliphaunt
2 Obsidian Charmaw
2 Riders of the Mark
2 Gargadon
3 Firebolt
2 Abrade
2 Rally at the Hornburg
2 There and Back Again
''',
}

# These have delayed loss triggers. Keep them in player loot, not untested AI lists.
UNTESTED_PACTS={"Summoner's Pact",'Pact of Negation'}
DEPENDENCIES={
 'Planebound Accomplice':('Planeswalker',1),
 'Godo, Bandit Warlord':('Equipment',2),
 'Dread Return':('Creature',10),
 'Persist':('nonlegendary creature',8),
 'Victimize':('Creature',12),
 'Sylvan Might':('Creature',10),
}

def supports(b, rows, kind):
    if kind=='nonlegendary creature':
        return sum(q for n,q in rows.items() if 'Creature' in b.db[n].kinds and 'Legendary' not in b.db[n].types)
    return sum(q for n,q in rows.items() if kind in b.db[n].types.split())

def failures(b, rows):
    return [n for n in rows if rows[n] and (n in UNTESTED_PACTS or
            (n in DEPENDENCIES and supports(b,rows,DEPENDENCIES[n][0])<DEPENDENCIES[n][1]))]

def repair(b, rows, mask, seed):
    """Replace unsupported effects with castable, independently useful cards."""
    rows=Counter(rows)
    spells={n:q for n,q in rows.items() if 'Land' not in b.db[n].kinds}
    total=sum(spells.values())
    average=sum(b.db[n].cost*q for n,q in spells.items())/max(1,total)
    cheap=sum(q for n,q in spells.items() if b.db[n].cost<=2)
    ramp=sum(rows[n] for n in ('Ornithopter of Paradise','Liquimetal Torque','Worn Powerstone','Llanowar Tribe','Wose Pathfinder','Rift Sower'))
    if average>4 and (cheap<6 or ramp<4):
        # Costly threats need early plays and mana, not more expensive replacements.
        for name in ('Ornithopter of Paradise','Liquimetal Torque'):
            while rows[name]<3:
                donors=[n for n,q in rows.items() if q and 'Land' not in b.db[n].kinds and b.db[n].cost>=5]
                if not donors:break
                donor=max(donors,key=lambda n:(rows[n],b.db[n].cost,n))
                rows[donor]-=1;rows[name]+=1
    for n in failures(b,rows):
        quantity=rows.pop(n)
        old=b.db[n]
        for i in range(quantity):
            choices=[c for c in b.candidates(mask) if c.name not in DEPENDENCIES
                     and c.name not in UNTESTED_PACTS and rows[c.name]<3
                     and ('Creature' in c.kinds)==('Creature' in old.kinds)]
            if 'Creature' not in old.kinds:
                # Removal, draw and token spells remain useful without a combo.
                choices=[c for c in choices if any(w in c.text.lower() for w in
                         ('draw','destroy target','exile target','create','deals'))]
            chosen=b.close(old,choices,set(),seed+n+str(i),min(old.cost,4))
            rows[chosen.name]+=1
    assert not failures(b,rows),(seed,failures(b,rows))
    return +rows

def curated(b,name,index,mask):
    key=f'{name}#{index+1}' if f'{name}#{index+1}' in PLANS else name
    if key not in PLANS:return None
    spells=Counter()
    for line in PLANS[key].strip().splitlines():
        q,n=line.split(' ',1);spells[n]+=int(q)
    assert sum(spells.values())==36,(key,sum(spells.values()))
    for n in spells:
        assert n in b.legal or n in b.modern,(key,n)
        assert not b.db[n].mask & ~mask,(key,n,mask)
    assert not failures(b,spells),(key,failures(b,spells))
    if not mask:
        lands=Counter({"Mishra's Factory":4,'Cave of Temptation':4,'Frostwalk Bastion':4,
                       'Power Depot':4,'Darksteel Citadel':4,'Buried Ruin':2,"Urza's Saga":2})
    else:lands=b.lands(mask,24,spells)
    return spells+lands

def compact(b,rows,mask,tags,seed,signatures):
    """Rebuild an oversized list by curve and theme; do not retain its first 36 spells."""
    spells={n:q for n,q in rows.items() if 'Land' not in b.db[n].kinds}
    result=Counter()
    # Retain a small signature package, not full playsets of every old bomb.
    for n in signatures:
        if n in spells and sum(result.values())<12:result[n]=min(2,spells[n])
    bands=[(2,12),(3,10),(4,8),(6,6)]
    for target,budget in bands:
        def in_band(n):
            cost=b.db[n].cost
            return cost<=2 if target==2 else cost==target if target in (3,4) else cost>=5
        count=sum(q for n,q in result.items() if in_band(n))
        while count<budget and sum(result.values())<36:
            choices=[b.db[n] for n in spells if in_band(n) and result[n]<min(spells[n],2 if b.db[n].rarity in ('R','M') else 3)]
            if not choices:break
            c=b.close(None,choices,tags,seed+str(sum(result.values())),target,1,True)
            result[c.name]+=1;count+=1
    while sum(result.values())<36:
        choices=[b.db[n] for n in spells if result[n]<min(spells[n],2 if b.db[n].rarity in ('R','M') else 3)]
        if not choices:choices=[c for c in b.candidates(mask) if result[c.name]<3 and c.cost<=4]
        c=b.close(None,choices,tags,seed+str(sum(result.values())),3,1,True)
        result[c.name]+=1
    result=repair(b,result,mask,seed)
    result+=b.lands(mask,24,result)
    for n in signatures:
        if n not in rows or 'Land' not in b.db[n].kinds:continue
        while result[n]<rows[n]:
            basics=[land for land,q in result.items() if q and 'Basic' in b.db[land].types and
                    b.db[land].mask & b.db[n].mask]
            if not basics:break
            donor=max(basics,key=lambda land:result[land]);result[donor]-=1;result[n]+=1
    return +result
