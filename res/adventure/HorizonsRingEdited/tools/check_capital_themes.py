"""Check actual generated pools, including concentration, printing and city colors."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
from build_plane import Builder, PLANE, capital_shop_variants
from capital_themes import selection
from capital_shops import WEIGHTS, ROTATING_WEIGHTS

b = Builder(Path(sys.argv[1]))
prints = {(n,e,a):r for (n,e,m),variants in b.shop_prints.items() for a,r in variants}
rotating = set()
for path in (PLANE/'maps/map/main_story').glob('*_capital.tmx'):
    for p in ET.parse(path).iter('property'):
        if p.get('name') == 'rotation': rotating.update(p.get('value','').split(','))
checked = 0
for shop in json.loads((PLANE/'world/shops.json').read_text()):
    name = shop['name']
    if not name.startswith('CapitalSmall'): continue
    rules = shop['rewards']
    assert len(rules) == 1 and rules[0]['count'] == 6, name
    if rules[0]['type'] == 'cardPackShop': continue
    color,base = name.removeprefix('CapitalSmall').split('__')
    mask = dict(White=1,Blue=2,Black=4,Red=8,Green=16)[color]
    label,entries = selection(b,base,color)
    assert shop['description'] == label and not shop['unlimited'], name
    weights=Counter(); names=Counter(); rarity_names=defaultdict(set)
    for line in (PLANE/rules[0]['sourceDeck']).read_text().splitlines():
        if not line[:1].isdigit(): continue
        q,entry=line.split(' ',1); n,e,a=entry.split('|'); q=int(q)
        assert (n,e) in entries and (not b.db[n].mask or b.db[n].mask & mask), (name,entry)
        r=prints[n,e,int(a)]
        weights[r]+=q; names[n]+=q; rarity_names[r].add(n)
    total=sum(weights.values()); target=ROTATING_WEIGHTS if name in rotating else WEIGHTS
    assert all(weights[r]*sum(target.values()) == total*w for r,w in target.items()), (name,weights)
    assert len(rarity_names['C']) >= 8 and len(rarity_names['U']) >= 8, name
    assert max(names.values())/total <= .08, (name,names.most_common(1))
    checked += 1
# Regeneration must preserve generated files byte for byte.
paths=[PLANE/'world/shops.json',*(PLANE/'decks/shop/capital').glob('*.dck')]
before={p:p.read_bytes() for p in paths}
capital_shop_variants(b)
assert all(p.read_bytes()==content for p,content in before.items())
print(f'PASS: {checked} themed pools; exact rarity weights, city colors, >=8 C/U names, <=8% per name; idempotent')
