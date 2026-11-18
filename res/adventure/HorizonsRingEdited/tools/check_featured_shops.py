"""Verify final six-slot featured odds, not just per-slot bonus tickets."""
import json
from collections import Counter
from pathlib import Path

plane=Path(__file__).resolve().parents[1]
names=['Atraxa, Grand Unifier','Quantum Riddler','Griselbrand','Sheoldred, the Apocalypse']
def pool(ref):
    counts=Counter()
    for line in (plane/ref).read_text().splitlines():
        if line[:1].isdigit():
            q,entry=line.split(' ',1)
            counts[entry.split('|')[0]]+=int(q)
    return counts

for shop in json.loads((plane/'world/shops.json').read_text()):
    if shop['name'] not in ['RingTown'+c for c in ['White','Blue','Black','Red','Green','Colorless']]:continue
    result={}
    for name in names:
        no_hit=1
        for rule in shop['rewards']:
            counts=pool(rule['sourceDeck'])
            no_hit*=(1-counts[name]/sum(counts.values()))**rule['count']
        chance=100*(1-no_hit)
        local=(name=='Quantum Riddler' and shop['name']=='RingTownBlue') or (name in names[2:] and shop['name']=='RingTownBlack')
        lower,upper=(.9,1.1) if name==names[0] else (2,3) if local else (.4,.6)
        assert lower<=chance<=upper,(shop['name'],name,chance)
        result[name]=round(chance,4)
    print(shop['name'],result)
print('PASS: final six-card probabilities within agreed ranges')
