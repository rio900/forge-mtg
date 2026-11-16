"""Fixed Standard, Constructed and Commander starts and edition-bound random Piles."""
import json
from collections import Counter

def build_starts(b):
    from build_plane import BASIC,BITS,PLANE,COMMON,CONFIG,SETS,emit,dump,stable
    for code, paths in CONFIG['starterDecksByEdition'].items():
        for col,ref in paths.items():
            pool=[c for c in b.spells if c.edition==code and c.mask==BITS[col]]
            rows=Counter()
            for i,cost in enumerate([1,2,2,3,3,4,5,2,3,4]):
                creature=i<7
                opts=[c for c in pool if ('Creature' in c.kinds)==creature and c.name not in rows]
                chosen=min(opts,key=lambda c:(abs(c.cost-cost),c.rarity in 'MR',stable(code+col+c.name)))
                rows[chosen.name]=[3,3,2,2,2,2,1,3,3,2][i]
            land=('Snow-Covered ' if code=='MH1' else '')+BASIC[col]
            rows[land]=17
            b.write_deck(ref,code+' '+col,{'Main':rows})
            path=PLANE/ref
            text=path.read_text().splitlines()
            text[-1]=f'17 {land}|{code}|1'
            emit(path,'\n'.join(text)+'\n')
    leaders={'W':'Boromir, Warden of the Tower','U':'Urza, Lord High Artificer','B':'Yawgmoth, Thran Physician','R':'Pashalik Mons','G':'Ayula, Queen Among Bears'}
    pairs={'Azorius':'WU','Dimir':'UB','Rakdos':'BR','Gruul':'RG','Selesnya':'WG','Orzhov':'WB','Izzet':'UR','Golgari':'BG','Boros':'WR','Simic':'UG'}
    mono=dict(zip(['White','Blue','Black','Red','Green'],'WUBRG'))
    themes={'W':'soldier','U':'flying','B':'graveyard','R':'goblin','G':'elf'}
    stock=json.loads((COMMON/'config.json').read_text())
    pack_starts={level['name']:level['starterDecks'] for level in stock['difficulties']}
    for level in CONFIG['difficulties']:
        for col,ref in level['constructedStarterDecks'].items():
            label=ref.split()[-1].split('.')[0]
            if label=='White':
                level['constructedStarterDecks'][col]='decks/pilot/starter.dck'
                continue
            if ref.endswith('/starter.dck'):continue
            colors=(mono|pairs)[label]
            mask=sum(BITS[c] for c in colors)
            pool=b.candidates(mask)
            rows=Counter()
            for i,cost in enumerate([1,2,2,3,3,4,5,2,3,4]):
                opts=[c for c in pool if c.name not in rows and c.mask and ('Creature' in c.kinds)==(i<7)]
                card=b.close(None,opts,{themes[c] for c in colors},label+str(i),cost,1,i<7)
                rows[card.name]=[3,3,2,2,2,2,1,3,3,2][i]
            rows.update(b.lands(mask,17,rows))
            b.write_deck(ref,label,{'Main':rows})
        for col,ref in level['pileDecks'].items():
            pile=json.loads((COMMON/ref).read_text())
            for rule in pile['mainDeck']:
                if 'cardName' in rule:rule['cardName']+='|LTR'
                else:rule['editions']=SETS
            emit(PLANE/ref,dump(pile))
        for col,ref in level['commanderDecks'].items():
            leader=leaders[col]
            opts=[c for c in b.spells if c.mask==BITS[col] and c.name!=leader]
            rows=Counter()
            for i in range(62):
                target=[1,2,2,3,3,3,4,4,5,6][i%10]
                c=b.close(None,[c for c in opts if c.name not in rows],{themes[col]},leader+str(i),target,1,i%3!=2)
                rows[c.name]=1
            rows[BASIC[col]]=37
            b.write_deck(ref,leader,{'Commander':{leader:1},'Main':rows})
        level['starterDecks']=pack_starts[level['name']]
