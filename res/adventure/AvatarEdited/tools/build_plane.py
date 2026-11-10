"""Regenerate enemy, encounter and reward overrides from the installed Adventure resources."""
import argparse
import hashlib
import json
import math
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PLANE = Path(__file__).resolve().parents[1]
COMMON = PLANE.parent / 'common'
ORIGINAL = PLANE.parent / 'Shandalar'
CONFIG = json.loads((PLANE / 'config.json').read_text())
SETS = CONFIG['allowedEditions']
if PLANE.name != 'AvatarEdited' or SETS != ['TLA','TLE']:
    raise ValueError('Rebuild requires the AvatarEdited plane and the approved TLA + TLE pool')
PACKS = ['TLA']
TOWN_COLORS = {'plains':'White','island':'Blue','swamp':'Black','mountain':'Red',
               'forest':'Green','waste':'Colorless'}

def limit_town_shops(root, filename):
    terrain=filename.split('_')[0]
    color=TOWN_COLORS[terrain]
    land=terrain.title() if terrain!='waste' else 'AvatarTownEquipment'
    singles='AvatarTown'+color+('Creatures' if '_tribal' in filename else '')
    group=next(g for g in root.iter('objectgroup') if any(o.get('template','').endswith('/shop.tx') for o in g))
    shops=[o for o in group.findall('object') if Path(o.get('template','')).stem in ('shop','RotatingShop')]
    def pool(o):
        return ' '.join(p.get('value','') for p in o.findall('properties/property') if p.get('name') in ('commonShopList','shopList'))
    # Keep landmark locations and object IDs used by previously visited towns.
    land_shop=next((o for o in shops if pool(o) in (land,'Equipment')),shops[-1])
    others=[o for o in shops if o is not land_shop]
    booster=next((o for o in others if 'BoosterPackShop' in pool(o)),others[-1])
    vendor=next(o for o in others if o is not booster)
    keep={land_shop:land,booster:'AvatarTownBooster',vendor:singles}
    for shop in shops:
        if shop not in keep:
            group.remove(shop)
            continue
        props=shop.find('properties')
        if props is None:props=ET.SubElement(shop,'properties')
        for prop in list(props):
            if prop.get('name','').endswith('ShopList') or prop.get('name') in ('shopList','rotation','noRestock'):props.remove(prop)
        ET.SubElement(props,'property',name='commonShopList',value=keep[shop])
        ET.SubElement(props,'property',name='noRestock',type='bool',value='true')

BASIC = dict(zip('WUBRG', ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']))
BITS = {c: 1 << i for i, c in enumerate(BASIC)}
SKETCHBOOK = 'Landscape Sketchbook - '
BOOK_SETS = {'TLA':'Avatar: The Last Airbender'}
# Major Shandalar treasures retain a marquee payoff in their original color.
STORY_PRIZES = {
    'Black Lotus':'White Lotus Tile', 'Mox Emerald':'The Great Henge',
    'Mox Jet':'Cruel Tutor','Mox Ruby':'Dockside Extortionist',
    'Mox Pearl':"Teferi's Protection",'Mox Sapphire':'Mystic Remora',
    'Time Walk':'Force of Negation','Timetwister':'Prosperity','Ancestral Recall':'Visions of Beyond',
}
MISSING_COLORS = {'Adept Blue Wizard':'U','Cephalid':'WUB','Corrupted Blue Wizard':'U','Corrupted Cleric':'WB',
 'Corrupted Green Wizard':'G','Corrupted Red Wizard':'R','Homarid':'BG','Jellyfish':'U','Juggernaut':'C',
 'Khenra Warrior':'RG','Mummy':'WB','Nezumi Leader':'B','Nezumi Ninja':'B','Octopus':'U','Owl':'UB',
 'Pharaoh':'WB','Plant':'G','Scorpion':'BG'}
STOP = set('the this that spell spells card cards battlefield target you your creature creatures opponents opponent turn when until its with from then equal for has have may each one another end any put into and it of or to a is an by on at as in if whenever control controls deals damage their they that’s permanent nonland other only ability abilities draw owner player players text it’s mana cost cast gets counter counters enters than more additional instead under number those choose chosen owned next token'.split())
ROLES = ['flying','lifelink','deathtouch','trample','haste','vigilance','menace','sacrifice','exile target',
         'destroy target','return target','draw','graveyard','counter target','equipment','enchanted',
         'treasure','blood token','poison','toxic','proliferate','mill','discard','search','food','create',
         'whenever you cast','instant or sorcery','noncreature','attack','first strike','double strike','flash',
         'reanimate','life','landfall','scry','surveil','dies','ninjutsu','powerstone','+1/+1 counter','fight']
rarities = {'L':0,'C':0,'U':1,'R':2,'M':3}
def stable(s):
    return int.from_bytes(hashlib.blake2b(s.encode(),digest_size=4).digest(),'little')
def slug(s):
    return re.sub('[^a-z0-9]+','-',s.lower()).strip('-')
def colors(mask):
    return ''.join(c for c in BITS if mask & BITS[c])
def emit(path, text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or path.read_text()!=text: path.write_text(text)
def dump(data):
    return json.dumps(data,ensure_ascii=False,indent=2)+'\n'
@dataclass
class Card:
    name:str
    edition:str
    rarity:str
    mask:int
    cost:int
    types:str
    removed:bool
    text:str
    def __post_init__(self):
        base,_,sub=self.types.partition(' - ')
        self.kinds=set(base.split())-{'Legendary','Basic','Snow','World'}
        self.tribes=set(sub.lower().split())
        text=self.text.lower().replace(self.name.lower(),'')
        self.roles={r for r in ROLES if r in text}
        self.words=set(re.findall(r"[a-z]{3,}",text))-STOP
def read_index(path):
    data={}
    for line in path.read_text().splitlines():
        name,edition,rarity,mask,cost,types,removed,_,text=line.split('\t',8)
        data[name]=Card(name,edition,rarity,int(mask),int(cost),types,removed=='true',text)
    return data
def sections(path):
    result=defaultdict(Counter)
    if not path.exists():return result
    section='Main'
    for line in path.read_text(errors='replace').splitlines():
        if line.strip().startswith('['): section=line.strip().strip('[]').title()
        m=re.match(r'^\s*(\d+)\s+(.+)',line)
        if m and section not in ('Metadata','Avatar'):
            result[section][m[2].split('|')[0].strip()]+=int(m[1])
    return result

class Builder:
    def __init__(self,index):
        self.db=read_index(index)
        digital=sorted(n for n,c in self.db.items() if c.edition in SETS and n.startswith('A-'))
        CONFIG['restrictedCards']=list(dict.fromkeys(CONFIG['restrictedCards']+digital))
        self.legal={n:c for n,c in self.db.items() if c.edition in SETS and not n.startswith('A-') and n not in CONFIG['restrictedCards']}
        self.spells=[c for c in self.legal.values() if not c.removed and 'Land' not in c.kinds and c.kinds & {'Creature','Artifact','Enchantment','Instant','Sorcery','Planeswalker','Battle'}]
        self.reward_overrides=defaultdict(list)
        fixfile=PLANE/'tools/reward-fixes.json'
        self.fixes=json.loads(fixfile.read_text()) if fixfile.exists() else {}
        for row in json.loads((PLANE/'tools/enemy-reward-fixes.json').read_text()):
            self.reward_overrides[row['enemy']].append(row)
        self.manifest=[]
        self.replacements={}
    def write_deck(self,rel,title,parts):
        lines=['[metadata]','Name='+title]
        for section,rows in parts.items():
            if not rows: continue
            lines.append('['+section+']')
            lines.extend(f'{q} {n}|{self.legal[n].edition}|1' for n,q in rows.items() if q>0)
        emit(PLANE/rel,'\n'.join(lines)+'\n')
    @lru_cache(maxsize=None)
    def candidates(self,mask,land=False):
        pool=self.legal.values() if land else self.spells
        return [c for c in pool if c.mask & ~mask==0 and ('Land' in c.kinds)==land]
    def close(self,old,candidates,theme,seed,desired,rarity=1,creature=None):
        if old:
            rarity=rarities.get(old.rarity,1); desired=min(old.cost,8)
            creature='Creature' in old.kinds
        def value(c):
            score=-1.65*abs(c.cost-desired)-1.0*abs(rarities.get(c.rarity,1)-rarity)
            if creature is not None and creature!=('Creature' in c.kinds):score-=9
            if old:
                score+=3*len(old.kinds & c.kinds)+4.3*len(old.tribes & c.tribes)
                score+=1.65*len(old.roles & c.roles)+0.4*len(old.words & c.words)
                if old.mask==c.mask:score+=2
            score+=5*len(theme & c.tribes)+1.2*len(theme & c.words)
            return score+(stable(seed+c.name)%1000)/500
        return max(candidates,key=value)
    def strategy(self, enemy, mask, seed):
        bosses = {
            'Akroma':'Appa, Steadfast Guardian;Airbending Lesson',
            'Ancient Silver Dragon':'The Unagi of Kyoshi Island;Waterbending Lesson',
            'Chandra':'Zuko, Firebending Master;Firebending Lesson',
            'Conjurer':'Sakashima of a Thousand Faces;Clone',
            'Dark Enchanter':'Koh, the Face Stealer;Heartless Act',
            'Elesh Norn':'Aang, Airbending Master;Invasion Reinforcements',
            'Emrakul':'Cityscape Leveler;Badgermole Cub;Shared Roots',
            'Garruk':'The Earth King;Saber-Tooth Moose-Lion',
            'Ghalta':'The Boulder, Ready to Rumble;Earthbending Lesson',
            'Griselbrand':'Noxious Gearhulk;Feed the Swarm',
            'Grolnok':'The Lion-Turtle;Waterbending Lesson',
            'Guardian Angel':'Aang, Swift Savior;Airbending Lesson',
            'Jace':'Wan Shi Tong, Librarian;Accumulate Wisdom',
            'Jin-Gitaxias':'The Mechanist, Aerial Artisan;Invasion Submersible',
            'Kiora':'Koma, Cosmos Serpent;Shared Roots',
            'Kozilek':'Planetarium of Wan Shi Tong;Shared Roots;Cityscape Leveler',
            'Lathliss':'Ran and Shaw;Firebending Lesson',
            'Liliana':'Koh, the Face Stealer;Epic Downfall',
            'Lorthos':"The Terror of Serpent's Pass;Giant Koi",
            'Myr Superion':'The Mechanist, Aerial Artisan;Cityscape Leveler',
            'Nahiri':"Sokka, Swordmaster;Sokka's Sword Training;Mechanical Glider",
            'Nissa':'Toph, Earthbending Master;Earthbending Lesson',
            'Ooze Boss':'Badgermole;Rocky Rebuke',
            'Scarecrow Captain':'Lita, Mechanical Engineer;Mechanical Glider',
            'Slimefoot':'The Cabbage Merchant;Unlucky Cabbage Merchant',
            'Sliver Queen':'Rhys the Redeemed;Invasion Reinforcements;Kyoshi Warriors',
            'Slobad':'Fire Nation Turret;Meteorite;Lightning Bolt',
            'Sorin':'Mai, Scornful Striker;Heartless Act',
            'Teferi':'Katara, Waterbending Master;Waterbending Lesson',
            'The Cheff':'The Cabbage Merchant;Bosco, Just a Bear',
            'The Hydra of Shandalaar':'Bumi, Unleashed;Earthbending Lesson',
            'Tibalt':'Ozai, the Phoenix King;Firebending Student;Lightning Bolt',
            'Torturer':'Azula, Ruthless Firebender;Firebending Lesson',
            'Urabrask':'Iroh, Firebending Instructor;Fire Nation Cadets',
            'Valyx Feaster of Torment':'Fire Lord Ozai;Cruel Administrator',
            'Vorinclex':'Toph, Greatest Earthbender;Rocky Rebuke',
            'Walter, the Stray Camel':'Appa, the Vigilant;Water Tribe Captain',
            'Wounded Sliver':'Jet, Freedom Fighter;Inspired Insurgent',
            'Xira':'Phoenix Fleet Airship;Fire Nation Engineer',
            'Zedruu':'Sokka, Tenacious Tactician;Wandering Musicians',
        }
        if enemy['name'] == 'Doppelganger':
            return 'U', ['Clone', 'Sakashima of a Thousand Faces']
        if enemy['name'] in bosses:
            anchors=bosses[enemy['name']].split(';')
            identity=0
            for name in anchors:identity |= self.legal[name].mask
            return colors(identity or BITS['R']),anchors
        # Large original identities and colorless lists need a compact, castable mana base.
        palette=colors(mask) or 'UR'
        if len(palette)>2:
            pairs=[palette[i]+b for i in range(len(palette)) for b in palette[i+1:]]
            palette=pairs[stable(seed)%len(pairs)]
        signatures={
            'W':['Water Tribe Captain','Kyoshi Warriors','Invasion Reinforcements'],
            'U':['Knowledge Seeker','Forecasting Fortune Teller','Boomerang Basics'],
            'B':['Heartless Act','June, Bounty Hunter','Fire Nation Engineer'],
            'R':['Fire Nation Cadets','Firebending Lesson','Treetop Freedom Fighters'],
            'G':['Earthbending Lesson','Badgermole','Foggy Swamp Vinebender'],
        }
        return palette,[signatures[c][stable(seed+c)%3] for c in palette]

    def starts(self):
        # Materialize paired installed Jumpstart themes, repairing the three erroneous references
        # by resolving every name to the selected Avatar printing at serialization.
        sheets=dict(re.findall(r'^\[([^\]]+)\]\s*\n([^\[]*)',(PLANE.parents[1]/'blockdata/printsheets.txt').read_text(),re.M))
        themes={'W':['TLA Aang','TLA Freedom Fighters','TLA Alliance 1','TLA Warriors'],
                'U':['TLA Katara','TLA Librarian','TLA Lessons 1','JTLE Soaring 1'],
                'B':['JLTA Azula','TLA Bad Advice','TLA Hunting 1','TLA Nightmares'],
                'R':['TLA Zuko','TLA Iroh','TLA Fire Nation','TLA Firebending 1'],
                'G':['TLA Toph','TLA Bumi','TLA Earthbending 1','TLA Earth Kingdom 1']}
        def packet(key):
            rows=Counter()
            for line in sheets[key].strip().splitlines():
                count,name=line.split(' ',1)
                rows[name.split('|')[0]]+=int(count)
            assert sum(rows.values())==20,key
            return rows
        for color,keys in themes.items():
            parts=[packet(key) for key in keys]
            standard=sections(PLANE/'decks/pilot/Allies.dck')['Main'] if color=='W' else parts[0]+parts[1]
            self.write_deck('decks/starter/standard-'+color+'.dck','Allies' if color=='W' else keys[0]+' / '+keys[1],{'Main':standard})
            for i,diff in enumerate(CONFIG['difficulties']):
                for mode,second in [('constructed',parts[(i+1)%4]),('pile',parts[(i+2)%4])]:
                    first=parts[i] if mode=='constructed' else packet(themes['WUBRG'[('WUBRG'.index(color)+1)%5]][i])
                    rows=first+second
                    self.write_deck(f'decks/starter/{mode}-{diff["name"]}-{color}.dck',mode+' '+diff['name']+' '+color,{'Main':rows})
            commanders={'W':'Suki, Kyoshi Captain','U':'Katara, Waterbending Master','B':'Koh, the Face Stealer',
                        'R':'Zuko, Firebending Master','G':'Toph, Earthbending Master'}
            commander=commanders[color]
            options=[c for c in self.candidates(BITS[color]) if c.name!=commander]
            options.sort(key=lambda c:(-int(c.name in standard),-len(c.roles & self.db[commander].roles),c.mask==0,stable(c.name)))
            selected=[]
            for lo,hi,count in [(0,2,24),(3,3,15),(4,4,11),(5,20,12)]:
                selected.extend(c.name for c in [c for c in options if lo<=c.cost<=hi][:count])
            selected += [c.name for c in options if c.name not in selected]
            rows=Counter(selected[:62]);rows[BASIC[color]]=37
            self.write_deck(f'decks/starter/commander-{color}.dck',commander,{'Commander':{commander:1},'Main':rows})

    def deck(self,e,ref,index=0,owner=None):
        name=e['name']; raw=e.get('colors') or MISSING_COLORS.get(name,'')
        original=COMMON/ref
        old=sections(original) if ref.endswith('.dck') else {}
        template=json.loads(original.read_text()).get('template',{}) if ref.endswith('.json') and original.exists() else {}
        raw=raw or template.get('colors','')
        if isinstance(raw,list):raw=''.join({'white':'W','blue':'U','black':'B','red':'R','green':'G'}.get(c.lower(),c) for c in raw)
        orig=old.get('Main',{})
        if not raw:
            mask=0
            for n in orig:
                if n in self.db:mask |= self.db[n].mask
        else:mask=sum(BITS.get(c,0) for c in set(raw.upper()))
        seed=name+'|'+ref
        rel='decks/converted/'+slug(owner or name)+'-'+str(index+1)+'.dck'
        pilots={'Tibalt':'Ozai','Barbarian':'Jet','Elf':'Earth','Human Captain':'Allies','Adept Blue Wizard':'Air'}
        if index==0 and name in pilots:
            pilot=pilots[name]
            parts=sections(PLANE/'decks/pilot'/(pilot+'.dck'))
            self.write_deck(rel,name+' - '+pilot,parts)
            self.manifest.append((name,ref,rel,'prototype '+pilot))
            return rel
        # Keep legal cards first, replace out-of-pool spells by comparable role, cost and tribe.
        tags={str(t).lower() for t in e.get('questTags',[]) if t}
        tags.update(re.findall('[a-z]+',name.lower()))
        if template.get('tribe'):tags.add(template['tribe'].lower())
        plan, anchors = self.strategy(e, mask, seed)
        mask = sum(BITS[c] for c in plan)
        tags.update(word for n in anchors for word in self.legal[n].tribes if word!='human')
        if e.get('boss'):
            tags.update(word for n in anchors for word in self.legal[n].roles)
        size=max(40,template.get('count',sum(orig.values()) or 60))
        landct=round(size*.40)
        options=self.candidates(mask)
        rows=Counter()
        for n,q in orig.items():
            if n in self.legal and n in self.db and 'Land' not in self.db[n].kinds and not self.db[n].removed and not self.db[n].mask & ~mask:
                rows[n]=min(q,4)
        for n in anchors:
            rows[n]=max(rows[n], 2 if self.legal[n].cost >= 5 else 3)
        spells=size-landct
        # Preserve all retained legal spells when possible, leaving room for a working mana base.
        while sum(rows.values())>spells:
            n=max(rows,key=lambda n:(rows[n],n not in anchors,self.db[n].cost)); rows[n]-=1
            if not rows[n]:del rows[n]
        for n,q in orig.items():
            o=self.db.get(n)
            if (o and 'Land' in o.kinds) or n in rows:continue
            need=min(q,spells-sum(rows.values()))
            while need>0:
                cand=self.close(o,[c for c in options if rows[c.name]<4],tags,seed+n,3)
                count=min(need,4-rows[cand.name]);rows[cand.name]+=count;need-=count
        cycle=[(1,True),(2,True),(2,False),(3,True),(3,False),(4,True),(4,False),(5,True)]
        i=0
        while sum(rows.values())<spells:
            cost,creature=cycle[i%len(cycle)]
            rare=2 if (i%5==0 and (e.get('boss') or template.get('rares',.15)>.25)) else i%2
            cand=self.close(None,[c for c in options if rows[c.name]<3],tags,seed+str(i),cost,rare,creature)
            rows[cand.name]+=min(3-rows[cand.name],spells-sum(rows.values()));i+=1
        # Each declared color has a castable threat or interaction, including multicolor encounters.
        for col in colors(mask):
            if not any(self.db[n].mask & BITS[col] for n in rows):
                choices=[c for c in options if c.mask==BITS[col] and 'Creature' in c.kinds]
                add=self.close(None,choices,tags,seed+col,3,1,True)
                drop=max(rows,key=lambda n:(rows[n],self.db[n].cost));rows[drop]-=1;rows[add.name]+=1
        rows=+rows
        rows.update(self.lands(mask,landct,rows))
        parts={'Main':rows}
        side=Counter()
        for n,q in old.get('Sideboard',{}).items():
            o=self.db.get(n)
            if o and 'Land' in o.kinds:
                if n in self.legal and not o.mask & ~mask and (n in BASIC.values() or rows[n]+side[n]+q<=4):side[n]+=q
                else:
                    for j in range(q):
                        land=BASIC[colors(mask)[j%len(colors(mask))]] if mask else 'Mountain'
                        side[land]+=1
                continue
            for j in range(q):
                if n in self.legal and not self.db[n].mask & ~mask and rows[n]+side[n]<4:chosen=n
                else:chosen=self.close(o,[c for c in options if rows[c.name]+side[c.name]<4],tags,seed+n,3).name
                side[chosen]+=1
        if side:parts['Sideboard']=side
        self.write_deck(rel,name,parts);self.manifest.append((name,ref,rel,plan+' / '+', '.join(anchors)));return rel
    def lands(self,mask,count,spells):
        result=Counter()
        cs=colors(mask)
        duals=[c.name for c in self.legal.values() if 'Land' in c.kinds and len(colors(c.mask))==2 and c.mask & ~mask==0]
        for n in sorted(duals)[:3]:result[n]=min(3,count//6)
        weights={c:1+sum(q/max(1,len(colors(self.db[n].mask))) for n,q in spells.items() if self.db[n].mask & BITS[c]) for c in cs}
        basics=Counter()
        for _ in range(count-sum(result.values())):
            col=max(cs,key=lambda c:math.sqrt(weights[c])/(basics[c]+.5));basics[col]+=1
        for col,q in basics.items():result[BASIC[col]]+=q
        return result
    def named(self,n):
        n=n.split('|')[0].strip()
        if n in self.replacements:return self.replacements[n]
        o=self.db.get(n)
        if n.startswith('Snow-Covered ') and n[13:] in BASIC.values():rep=n[13:]
        elif n in self.legal:rep=n
        elif n in STORY_PRIZES:rep=STORY_PRIZES[n]
        elif o:
            pool=self.candidates(o.mask,'Land' in o.kinds)
            matching=[c for c in pool if c.mask==o.mask] or pool
            rep=self.close(o,matching,set(),'reward'+n,o.cost).name
        else:raise ValueError('Unknown reward '+n)
        self.replacements[n]=rep;return rep
    def reward(self,data):
        if isinstance(data,list):
            for obj in data:self.reward(obj)
        if not isinstance(data,dict):return
        for k,v in list(data.items()):
            if isinstance(v,(dict,list)):self.reward(v)
        if data.get('superTypes')==['Snow'] and data.get('type')=='randomCard':
            data.pop('superTypes');data['colors']=['blue'];data['editions']=list(SETS)
        if data.get('itemName','').startswith(SKETCHBOOK):
            data['itemName']=SKETCHBOOK+BOOK_SETS['TLA']
        if data.get('cardName'):
            n=self.named(data['cardName']);ed=self.legal[n].edition
            data['cardName']=n+'|'+ed
            if 'editions' in data:data['editions']=[ed]
        elif 'editions' in data:
            data['editions']=[c for c in data['editions'] if c in SETS] or list(SETS)
        if data.get('type')=='cardPackShop':
            for key in ('colors','startDate','endDate'):data.pop(key,None)
            data['editions']=[c for c in data.get('editions',PACKS) if c in PACKS] or list(PACKS)
        if data.get('cardText','').lower()=='infect':data['cardText']='(?i)firebending'
        if data.get('sourceDeck'):
            ref=data['sourceDeck'];low=ref.lower()
            if 'funny' in low:
                data.pop('sourceDeck');data.pop('subTypes',None);data.pop('cardText',None)
                data['cardTypes']=['Artifact'];data['editions']=list(SETS)
            elif 'warhammer' in low:
                data.pop('sourceDeck');data['editions']=list(SETS);data['cardTypes']=['Artifact','Creature']
            elif ref in self.byref:data['sourceDeck']=self.byref[ref]
            else:raise ValueError('Unmapped shop source '+ref)
        fix=self.fixes.get(json.dumps(data,sort_keys=True))
        if fix is not None:
            data.clear()
            data.update(fix)
    def enemies(self):
        src=json.loads((COMMON/'world/enemies.json').read_text())
        self.byref={}
        def convert(e,owner=None):
            if e['name'] == 'Doppelganger':
                # The native mirror encounter can award a hard-coded Unglued card.
                e['copyPlayerDeck'] = False
            if e['name']=='Slobad':e['gamesPerMatch']=1
            refs=[]
            for i,ref in enumerate(e['deck']):
                path=self.deck(e,ref,i,owner)
                self.byref.setdefault(ref,path);refs.append(path)
            e['deck']=refs
            self.reward(e.get('rewards',[]))
            for change in self.reward_overrides[e['name']]:
                for i,rule in enumerate(e.get('rewards',[])):
                    if rule==change['match']:e['rewards'][i]=change['reward'].copy()
            for rule in e.get('rewards',[]):
                if rule.get('type')=='Card':rule['type']='card'
            if e.get('nextEnemy'):convert(e['nextEnemy'],(owner or e['name'])+' stage '+e['nextEnemy']['name'])
        for e in src:convert(e)
        emit(PLANE/'world/enemies.json',dump(src))
    def maps(self):
        templates={}
        for source in sorted((COMMON/'maps/obj').glob('*.tx')):
            root=ET.parse(source).getroot()
            changed=False
            for prop in root.findall(".//property[@name='reward']"):
                raw=prop.get('value',prop.text or '')
                obj=json.loads(raw)
                original=dump(obj)
                self.reward(obj)
                if original!=dump(obj):
                    if 'value' in prop.attrib:prop.set('value',json.dumps(obj))
                    else:prop.text=json.dumps(obj)
                    changed=True
            if changed:
                target=PLANE/source.relative_to(COMMON)
                for node in root.iter('tileset'):
                    node.set('source',os.path.relpath(source.parent/node.get('source'),target.parent))
                emit(target,ET.tostring(root,encoding='unicode')+'\n')
                templates[source.resolve()]=target
        for f in sorted((COMMON/'maps').rglob('*.tmx')):
            root=ET.fromstring(f.read_bytes());changed=False
            if f.parent==COMMON/'maps/map/towns':
                limit_town_shops(root,f.name);changed=True
            for node in root.iter('property'):
                key=node.get('name');value=node.get('value',node.text or '')
                if key=='teleport' and value.startswith('../common/maps/') and value.endswith('.tmx') and (COMMON/value).is_file():
                    node.set('value',value.replace('../common/','../'+PLANE.name+'/',1));changed=True
                if key=='deckOverride' and value:
                    ref=value.replace('../common/','')
                    if ref not in self.byref:
                        encounter={'name':'Map '+Path(ref).stem}
                        self.byref[ref]=self.deck(encounter,ref)
                    node.set('value',self.byref[ref]);changed=True
                elif (key=='reward' and value.strip()) or '"grantRewards"' in value or SKETCHBOOK in value or any('"'+k+'"' in value for k in ('cardName','editions','cardPackShop','sourceDeck')):
                    try:obj=json.loads(value)
                    except ValueError:
                        value=re.sub(r',\s*([}\]])',r'\1',value)
                        repaired=re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)',r'\1,\n\2',value)
                        obj=json.loads(repaired)
                    before=dump(obj);self.reward(obj)
                    if before!=dump(obj):
                        value=json.dumps(obj,ensure_ascii=False,separators=(',',':'))
                        if 'value' in node.attrib:node.set('value',value)
                        else:node.text=value
                        changed=True
            dest=PLANE/f.relative_to(COMMON)
            for node in root.iter():
                for attr in ('source','template'):
                    if attr in node.attrib:
                        target=(f.parent/node.get(attr)).resolve()
                        if not target.is_file():
                            target=COMMON/'maps'/Path(node.get(attr)).parent.name/target.name
                        target=templates.get(target,target)
                        if target.is_file():node.set(attr,os.path.relpath(target,dest.parent))
            emit(dest,ET.tostring(root,encoding='unicode')+'\n')
        # TileMapScene prefixes POI map paths with common, even inside custom planes.
        points=json.loads((COMMON/'world/points_of_interest.json').read_text())
        for point in points:
            ref=point.get('map','')
            if ref.startswith('../common/maps/') and (COMMON/ref).is_file():
                point['map']=ref.replace('../common/','../'+PLANE.name+'/',1)
        emit(PLANE/'world/points_of_interest.json',dump(points))

    def town_rewards(self, color, creatures):
        mask={'White':1,'Blue':2,'Black':4,'Red':8,'Green':16,'Colorless':0}[color]
        pool=[c for c in self.spells if c.mask==mask and
              (not creatures or ('Artifact' if mask==0 else 'Creature') in c.kinds)]
        groups=[]
        for rarity,slots in [('C',1),('U',2)]:
            names=sorted(c.name for c in pool if c.rarity==rarity)
            width=min(3,(len(names)-1)//slots)
            assert width>=1,(color,rarity)
            groups.extend(names[i*width:(i+1)*width] for i in range(slots))
        rules=[]
        reserved=set()
        for group,rarity in zip(groups,'CUU'):
            choices=[]
            for name in group:
                card=self.legal[name]
                assert card.rarity==rarity and name not in reserved, (name,rarity)
                reserved.add(name)
                choices.append({'cardName':name+'|'+card.edition})
            rules.append({'type':'Union','count':1,'cardUnion':choices})
        mask={'White':1,'Blue':2,'Black':4,'Red':8,'Green':16,'Colorless':0}[color]
        theme=color+('Creatures' if creatures else '')
        rows=Counter()
        for rarity,count in [('C',30),('U',50),('R',18),('M',2)]:
            choices=sorted((c.name for c in pool if c.rarity==rarity and c.name not in reserved),
                        key=lambda n:(stable(theme+n),n))
            assert choices, (theme,rarity)
            rows.update(choices[i%len(choices)] for i in range(count))
        ref='decks/shop/'+theme+'.dck'
        self.write_deck(ref,theme+' shop pool',{'Main':rows})
        rules.append({'type':'card','count':1,'sourceDeck':ref})
        return rules

    def stores(self):
        shops=json.loads((ORIGINAL/'world/shops.json').read_text());self.reward(shops)
        for shop in shops:
            name=shop['name']
            for reward in shop.get('rewards',[]):
                for rule in reward.get('cardUnion',[]):
                    if name.startswith('Sliver'):
                        if 'subTypes' in rule:rule['subTypes']=['Ally']
                        if 'cardText' in rule:rule['cardText']='Ally'
                    elif name=='Squirrel':
                        if 'subTypes' in rule:rule['subTypes']=['Bear','Beast','Bird']
                        if 'cardText' in rule:rule['cardText']='Food'
                    elif name=='SnowShop':
                        rule.pop('superTypes',None)
                        rule.pop('cardText',None)
                        rule['colors']=['blue']
                        rule['editions']=list(SETS)
                    elif name=='Eldrazi':
                        if 'subTypes' in rule:rule['subTypes']=['Spirit']
                        if 'cardText' in rule:rule['cardText']='earthbend'
        by_name={shop['name']:shop for shop in shops}
        for color in TOWN_COLORS.values():
            for suffix in ('','Creatures'):
                rewards=self.town_rewards(color,bool(suffix))
                shops.append(dict(by_name[color],name='AvatarTown'+color+suffix,rewards=rewards))
        shops.append(dict(by_name['BoosterPackShop'],name='AvatarTownBooster',unlimited=False,
                          rewards=[{'type':'cardPackShop','count':1,'editions':PACKS}]))
        shops.append(dict(by_name['Equipment'],name='AvatarTownEquipment',unlimited=False,
                          rewards=[{'count':2,'subTypes':['Equipment'],'rarity':['Common','Uncommon']}]))
        emit(PLANE/'world/shops.json',dump(shops))
    def boosters(self):
        emit(PLANE/'blockdata/blocks.txt','Avatar TLA, 3/6/TLA, TLA\n')
        emit(PLANE/'config.json',dump(CONFIG))
    def items(self):
        stock=json.loads((COMMON/'world/items.json').read_text())
        books={SKETCHBOOK+name for code,name in BOOK_SETS.items() if code in PACKS}
        items=[item for item in stock if not item['name'].startswith(SKETCHBOOK) or item['name'] in books]
        for book in sorted(books-{item['name'] for item in items}):
            items.append({'name':book,'unique':True,'description':'Sketches of landscapes from '+book[len(SKETCHBOOK):]+'.','iconName':'LandscapeSketchbook'})
        emit(PLANE/'world/items.json',dump(items))
    def run(self):
        quests=json.loads((ORIGINAL/'world/quests.json').read_text())
        self.enemies();self.reward(quests);emit(PLANE/'world/quests.json',dump(quests))
        translations=ORIGINAL/'languages/quests-es-ES.json'
        localized=json.loads(translations.read_text());self.reward(localized)
        emit(PLANE/'languages/quests-es-ES.json',dump(localized))
        self.starts();self.stores();self.maps();self.boosters();self.items()
        emit(PLANE/'tools/enemy-mapping.tsv','enemy\toriginal\tlocal\torigin\n'+''.join('\t'.join(row)+'\n' for row in self.manifest))
        emit(PLANE/'tools/reward-mapping.tsv','original\treplacement\tedition\n'+''.join(f'{n}\t{v}\t{self.legal[v].edition}\n' for n,v in sorted(self.replacements.items())))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('index',type=Path);Builder(parser.parse_args().index).run()
