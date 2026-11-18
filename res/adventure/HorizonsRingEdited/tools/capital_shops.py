"""Six independently weighted singles at each small capital card counter."""
import math
from collections import Counter, defaultdict

WEIGHTS = {'C':550,'U':400,'R':45,'M':5}
# Per-slot odds: 1-(1-p)^6 ~= 70% Rare / 40% Mythic per stock.
ROTATING_WEIGHTS = {'C':2366,'U':5000,'R':1818,'M':816}

def stock(builder, name, rules, rotating=False, city_mask=None, lands=False, entries=None):
    from build_plane import PLANE, emit
    supplied = entries is not None
    entries = set() if entries is None else set(entries)
    for rule in ([] if supplied else rules):
        for line in (PLANE/rule['sourceDeck']).read_text().splitlines():
            if line[:1].isdigit():
                entry=line.split(' ',1)[1]
                card,edition,art=entry.split('|')
                entries.add((card,edition))
    if lands:
        entries={(n,ed) for (n,ed,mask) in builder.shop_prints
                 if 'Land' in builder.db[n].kinds and 'Basic' not in builder.db[n].types}
    if city_mask is not None:
        entries={key for key in entries if not builder.db[key[0]].mask or builder.db[key[0]].mask & city_mask}
    prints={(n,ed):variants for (n,ed,mask),variants in builder.shop_prints.items()}
    # Keep the theme wherever its pool has cards. Fill missing tiers in the city
    # color so a narrow tribal shop remains usable and clock-shop odds stay exact.
    available={r for key in entries if len({r for art,r in prints[key]})==1 for art,r in prints[key]}
    needed=set() if supplied else (({'C','U','R','M'}-available) if rotating else (set() if available & {'C','U'} else {'C','U'}))
    if supplied:
        assert {'C','U','R','M'} <= available, (name, available)
    for card in builder.legal.values():
        if card.rarity in needed and card.mask==city_mask and not card.removed and 'Land' not in card.kinds:
            entries.add((card.name,card.edition))
    assert entries,name
    single=defaultdict(list);fixed=Counter();reserved=Counter()
    for card,edition in sorted(entries):
        variants=prints[card,edition]
        rs={r for art,r in variants}
        if len(rs)==1:
            art,r=min(variants);single[r].append(f'{card}|{edition}|{art}')
        else:
            for art,r in variants:
                fixed[f'{card}|{edition}|{art}']+=1;reserved[r]+=1
    target=ROTATING_WEIGHTS if rotating else WEIGHTS
    weights={r:w for r,w in target.items() if single[r] or reserved[r]}
    assert any(r in weights for r in ('C','U')),name
    lowest=next(iter(weights))
    weights[lowest]+=sum(target.values())-sum(weights.values())
    scale=max(math.ceil((len(single[r])+reserved[r])/w) for r,w in weights.items())
    bonus=sum(w*scale-reserved[r] for r,w in weights.items() if not single[r])
    recipient=next(r for r in ('C','U') if single[r])
    for r,w in weights.items():
        remaining=w*scale-reserved[r]+(bonus if r==recipient else 0)
        pool=single[r]
        if not pool:continue
        q,extra=divmod(remaining,len(pool))
        for i,entry in enumerate(pool):fixed[entry]=q+(i<extra)
    ref=f'decks/shop/capital/{name}.dck'
    emit(PLANE/ref,'[metadata]\nName='+name+'\n[Main]\n'+''.join(f'{q} {n}\n' for n,q in sorted(fixed.items()) if q))
    return [{'type':'card','count':6,'sourceDeck':ref}]
