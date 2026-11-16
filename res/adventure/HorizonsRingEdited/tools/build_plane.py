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
assert set(SETS)=={'MH1','MH2','LTR'}
PACKS = list(SETS)
TOWN_COLORS = {'plains':'White','island':'Blue','swamp':'Black','mountain':'Red',
               'forest':'Green','waste':'Colorless'}

def limit_town_shops(root, filename):
    terrain=filename.split('_')[0]
    color=TOWN_COLORS[terrain]
    land=terrain.title() if terrain!='waste' else 'RingTownEquipment'
    singles='RingTown'+color+('Creatures' if '_tribal' in filename else '')
    group=next(g for g in root.iter('objectgroup') if any(o.get('template','').endswith('/shop.tx') for o in g))
    shops=[o for o in group.findall('object') if Path(o.get('template','')).stem in ('shop','RotatingShop')]
    def pool(o):
        return ' '.join(p.get('value','') for p in o.findall('properties/property') if p.get('name') in ('commonShopList','shopList'))
    # Keep landmark locations and object IDs used by previously visited towns.
    land_shop=next((o for o in shops if pool(o) in (land,'Equipment')),shops[-1])
    others=[o for o in shops if o is not land_shop]
    booster=next((o for o in others if 'BoosterPackShop' in pool(o)),others[-1])
    vendor=next(o for o in others if o is not booster)
    keep={land_shop:land,booster:'RingTownBooster',vendor:singles}
    for shop in shops:
        if shop not in keep:
            group.remove(shop)
            continue
        props=shop.find('properties')
        if props is None:props=ET.SubElement(shop,'properties')
        for prop in list(props):
            if prop.get('name','').endswith('ShopList') or prop.get('name') in ('shopList','rotation','noRestock'):props.remove(prop)
        ET.SubElement(props,'property',name='commonShopList',value=keep[shop])
        if Path(shop.get('template')).stem=='RotatingShop':
            shop.set('template',str(Path(shop.get('template')).with_name('shop.tx')))
            shop.attrib.pop('type',None)

BASIC = dict(zip('WUBRG', ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']))
BITS = {c: 1 << i for i, c in enumerate(BASIC)}
DUALS = dict(zip(['WU','WB','WR','WG','UB','UR','UG','BR','BG','RG'],
    ['Razortide Bridge','Goldmire Bridge','Rustvale Bridge','Thornglint Bridge','Mistvault Bridge','Silverbluff Bridge','Tanglepool Bridge','Drossforge Bridge','Darkmoss Bridge','Slagwoods Bridge']))
WASTELANDS = ["Mishra's Factory",'Cave of Temptation','Power Depot','Frostwalk Bastion',"Urza's Saga",'The Grey Havens']
PROTOTYPES = {'Goblin':'goblin','Elf':'elf',"Liliana's Alchemist":'ninja','Liliana':'liliana'}
SIGNATURES = {}
PLANS = {}
for line in (PLANE/'tools/boss-plans.tsv').read_text().splitlines():
    enemy, cards, plan = line.split('\t')
    SIGNATURES[enemy] = cards.split(';')
    PLANS[enemy] = plan
SKETCHBOOK = 'Landscape Sketchbook - '
BOOK_SETS = dict(zip(SETS, CONFIG['starterEditionNames']))
QUEST_BOOKS = {"Urza's Saga":'MH2','Ixalan':'LTR','Mirage':'LTR','Coldsnap':'MH2','Modern Horizons':'MH2'}
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
        fixes=PLANE/'tools/encounter-rewards.json'
        if fixes.exists():
            for row in json.loads(fixes.read_text()):
                self.reward_overrides[row['enemy']].append(row)
        self.shop_prints=defaultdict(list)
        for line in Path(str(index)+'.prints').read_text().splitlines():
            name,edition,art,rarity,mask=line.split('\t')
            if edition in SETS and name not in CONFIG['restrictedCards'] and not name.startswith('A-'):
                self.shop_prints[name,edition,int(mask)].append((int(art),rarity))
        self.modern={}
        for line in (PLANE/'tools/modern-cards.txt').read_text().splitlines():
            name,edition,rarity=line.split('|')
            self.modern[name]=edition
            key=(name,edition,self.db[name].mask)
            if edition not in SETS:
                self.shop_prints[key]=[(1,rarity)]
        self.manifest=[]
        self.replacements={}
    def write_deck(self,rel,title,parts):
        lines=['[metadata]','Name='+title]
        for section,rows in parts.items():
            if not rows: continue
            lines.append('['+section+']')
            for name,quantity in rows.items():
                if quantity>0:
                    edition=self.legal[name].edition if name in self.legal else self.modern[name]
                    lines.append(f'{quantity} {name}|{edition}|1')
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
        if name.startswith('Challenger '):
            from tournament import tournament_deck
            archetype,rows=tournament_deck(self,index,int(name.split()[-1]))
            self.write_deck(rel,name+' - '+archetype,{'Main':rows})
            self.manifest.append((name,ref,rel,archetype))
            return rel
        # Keep legal cards first, replace out-of-pool spells by comparable role, cost and tribe.
        tags={str(t).lower() for t in e.get('questTags',[]) if t}
        tags.update(re.findall('[a-z]+',name.lower()))
        if template.get('tribe'):tags.add(template['tribe'].lower())
        if name=='Plaguelord':tags.update(['deathtouch','spider','destroy target'])
        size=max(40,template.get('count',sum(orig.values()) or 60))
        landct=round(size*.40)
        options=self.candidates(mask)
        rows=Counter()
        for n,q in orig.items():
            if n in self.legal and n in self.db and 'Land' not in self.db[n].kinds and not self.db[n].removed and not self.db[n].mask & ~mask:
                rows[n]=min(q,4)
        for n in SIGNATURES.get(name,[]):
            if n in self.legal and not self.legal[n].mask & ~mask:rows[n]=max(rows[n],2)
        spells=size-landct
        # Preserve all retained legal spells when possible, leaving room for a working mana base.
        while sum(rows.values())>spells:
            n=max(rows,key=lambda n:(rows[n],n not in SIGNATURES.get(name,[]),self.db[n].cost)); rows[n]-=1
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
        if name=='Griselbrand':
            # Keep the mana base and deck size, and support both discard and tutoring.
            for old_card,new_card,quantity in [
                    ('Feaster of Fools','Griselbrand',3),('Echoing Return',"Goryo's Vengeance",4),
                    ('Morgul-Knife Wound','Bone Shards',4),('Headless Specter','Vile Entomber',2)]:
                assert rows[old_card]>=quantity
                rows[old_card]-=quantity
                rows[new_card]+=quantity
        parts={'Main':rows}
        side=Counter()
        for n,q in old.get('Sideboard',{}).items():
            o=self.db.get(n)
            if o and 'Land' in o.kinds:
                if n in self.legal and not o.mask & ~mask and (n in BASIC.values() or rows[n]+side[n]+q<=4):side[n]+=q
                else:
                    for j in range(q):
                        land=BASIC[colors(mask)[j%len(colors(mask))]] if mask else next(l for l in WASTELANDS if rows[l]+side[l]<4)
                        side[land]+=1
                continue
            for j in range(q):
                if n in self.legal and not self.db[n].mask & ~mask and rows[n]+side[n]<4:chosen=n
                else:chosen=self.close(o,[c for c in options if rows[c.name]+side[c.name]<4],tags,seed+n,3).name
                side[chosen]+=1
        if side:parts['Sideboard']=side
        self.write_deck(rel,name,parts);self.manifest.append((name,ref,rel,PLANS.get(name,'Подбор по типам существ, стоимости и эффектам исходной колоды')));return rel
    def lands(self,mask,count,spells):
        result=Counter()
        if not mask:
            for i in range(count):
                land=WASTELANDS[i%len(WASTELANDS)] if i<4*len(WASTELANDS) else 'Snow-Covered Island'
                result[land]+=1
            return result
        cs=colors(mask)
        if len(cs)>=3:
            for _ in range(min(4,count//6)):result['Prismatic Vista']+=1
        duals=[n for k,n in DUALS.items() if all(c in cs for c in k)]
        if duals:
            for i in range(min(count//(4 if len(cs)==2 else 2),4*len(duals))):
                result[duals[i%len(duals)]]+=1
        if len(cs)>=4:
            for _ in range(min(4,count//6)):result['Cave of Temptation']+=1
        weights={c:1+sum(q/max(1,len(colors(self.db[n].mask))) for n,q in spells.items() if self.db[n].mask & BITS[c]) for c in cs}
        basics=Counter()
        for _ in range(count-sum(result.values())):
            col=max(cs,key=lambda c:math.sqrt(weights[c])/(basics[c]+.5));basics[col]+=1
        for col,q in basics.items():result[BASIC[col]]+=q
        return result
    def named(self,n):
        n=n.split('|')[0].strip()
        if n in self.replacements:return self.replacements[n]
        curated={'Black Lotus':'Mox Tantalite',
            'Mox Emerald':'Delighted Halfling','Mox Ruby':'Ragavan, Nimble Pilferer','Mox Jet':'Grief',
            'Mox Pearl':'Esper Sentinel','Mox Sapphire':'Subtlety','Time Walk':'Echo of Eons',
            'Timetwister':'Echo of Eons','Ancestral Recall':'Fact or Fiction','Wastes':"Mishra's Factory",
            'Griselbrand':'Archon of Cruelty','Damnation':'Damn',"Gaea's Cradle":'Yavimaya, Cradle of Growth'}
        o=self.db.get(n)
        if n in self.legal:rep=n
        elif n in curated:rep=curated[n]
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
        if data.get('type')=='card' and data.get('subTypes')==['Fungus']:
            data['subTypes']=['Squirrel']
        if data.get('subTypes')==['Spider'] and data.get('colors')==['Black']:
            data.pop('colors')
        if data.get('itemName','').startswith(SKETCHBOOK):
            suffix=data['itemName'][len(SKETCHBOOK):]
            if suffix in QUEST_BOOKS:data['itemName']=SKETCHBOOK+BOOK_SETS[QUEST_BOOKS[suffix]]
        if data.get('cardName'):
            n=self.named(data['cardName']);ed=self.legal[n].edition
            data['cardName']=n+'|'+ed
            if 'editions' in data:data['editions']=[ed]
        elif 'editions' in data:
            data['editions']=[c for c in data['editions'] if c in SETS] or list(SETS)
        if data.get('type')=='cardPackShop':
            data.pop('colors',None)
            data['editions']=[c for c in data.get('editions',PACKS) if c in PACKS] or list(PACKS)
        if data.get('cardText','').lower()=='infect':data['cardText']='(?i)deathtouch'
        if data.get('sourceDeck'):
            ref=data['sourceDeck'];low=ref.lower()
            if 'funny' in low:
                data.pop('sourceDeck');data.pop('subTypes',None);data.pop('cardText',None)
                data['cardTypes']=['Artifact'];data['editions']=['MH1','MH2']
            elif 'warhammer' in low:
                data.pop('sourceDeck');data['editions']=['MH1','MH2'];data['cardTypes']=['Artifact','Creature']
            elif ref in self.byref:data['sourceDeck']=self.byref[ref]
            else:raise ValueError('Unmapped shop source '+ref)
    def enemies(self):
        src=json.loads((COMMON/'world/enemies.json').read_text())
        self.byref={}
        def convert(e,owner=None):
            refs=[]
            for i,ref in enumerate(e['deck']):
                if owner is None and e['name'] in PROTOTYPES:
                    path='decks/pilot/'+PROTOTYPES[e['name']]+'.dck'
                    self.manifest.append((e['name'],ref,path,'prototype'))
                else:path=self.deck(e,ref,i,owner)
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
    def chest_card(self,rule):
        kind=rule.get('type','card')
        if kind=='Union':
            for member in rule['cardUnion']:self.chest_card(member)
            return
        if kind not in ('card','randomCard','cardPackShop'):return
        if kind=='cardPackShop':
            # A sealed booster would still contain commons. Award a premium single instead.
            rule['type']='card'
            rule['rarity']=['Rare','Mythic Rare']
        if rule.get('cardName'):
            card=self.legal[rule['cardName'].split('|')[0]]
            if card.rarity not in ('U','R','M'):
                pool=[c for c in self.candidates(card.mask,'Land' in card.kinds) if c.rarity=='U']
                card=self.close(card,pool,set(),'chest'+card.name,card.cost)
            rule.update(cardName=card.name+'|'+card.edition,editions=[card.edition])
        allowed=['Uncommon','Rare','Mythic Rare']
        previous=[r.lower() for r in rule.get('rarity',allowed)]
        rule['rarity']=[r for r in allowed if r.lower() in previous] or ['Uncommon']

    def map_reward(self,node,chest=False,grove=False):
        value=node.get('value',node.text or '')
        # Common resources use libGDX's optional commas.
        value=re.sub(r',\s*([}\]])',r'\1',value)
        value=re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)',r'\1,\n\2',value)
        obj=json.loads(value)
        before=dump(obj)
        if grove and isinstance(obj,list):
            for rule in obj:
                if rule.get('editions')==['BBD']:rule['editions']=list(SETS)
        self.reward(obj)
        if chest:
            for rule in obj:self.chest_card(rule)
        if dump(obj)==before:return False
        value=json.dumps(obj,ensure_ascii=False,separators=(',',':'))
        if 'value' in node.attrib:node.set('value',value)
        else:node.text=value
        return True

    def maps(self):
        templates={}
        for name in ('scroll','treasure','booster'):
            f=COMMON/'maps/obj'/f'{name}.tx'
            dest=PLANE/f.relative_to(COMMON);templates[f]=dest
            root=ET.parse(f).getroot()
            self.map_reward(root.find(".//property[@name='reward']"),chest=name=='treasure')
            for node in root.iter('tileset'):
                node.set('source',os.path.relpath(f.parent/node.get('source'),dest.parent))
            emit(dest,ET.tostring(root,encoding='unicode')+'\n')
        sources=sorted((COMMON/'maps').rglob('*.tmx'))
        by_name=defaultdict(list)
        for f in sources:by_name[f.name].append(f)
        def destination(ref):
            target=(COMMON/ref).resolve()
            if target.is_file():return target
            matches=by_name[Path(ref).name]
            return matches[0] if len(matches)==1 else None
        local=set()
        trees={}
        links=defaultdict(list)
        for f in sources:
            root=ET.parse(f).getroot();trees[f]=root
            if f.parent==COMMON/'maps/map/towns':
                limit_town_shops(root,f.name);local.add(f)
            chest_props=set()
            for obj in root.iter('object'):
                ref=obj.get('template','')
                if ref and (f.parent/ref).resolve() in templates:local.add(f)
                if Path(ref).name=='treasure.tx':
                    chest_props.update(obj.findall("properties/property[@name='reward']"))
            for node in root.iter('property'):
                key=node.get('name');value=node.get('value',node.text or '')
                if key=='teleport' and value.endswith('.tmx'):
                    target=destination(value)
                    if target:
                        links[f].append((node,target))
                        if not (COMMON/value).is_file():local.add(f)
                elif key=='arena' and f.stem.endswith('_capital'):
                    color=TOWN_COLORS[f.stem.split('_')[0]]
                    mask=dict(White=1,Blue=2,Black=4,Red=8,Green=16)[color]
                    local_names={n for n in self.modern if self.db[n].mask & mask}
                    ref=f'decks/arena/{color}.dck'
                    # Total weight of the universal branch equals that of the local branch.
                    groupsize=len(local_names)
                    lines=[f'{groupsize+(len(self.modern) if n in local_names else 0)} {n}|{ed}|1'
                           for n,ed in self.modern.items()]
                    emit(PLANE/ref,'[metadata]\nName='+color+' arena prize\n[Main]\n'+'\n'.join(lines)+'\n')
                    arena=json.loads(re.sub(r',\s*([}\]])',r'\1',value))
                    final=arena['rewards'][-1]
                    mythic=next(r for r in final if r.get('rarity')==['Mythic Rare'])
                    assert mythic['count']==2
                    mythic['count']=1
                    final.append(dict(type='card',count=1,sourceDeck=ref))
                    node.text=dump(arena)
                    local.add(f)
                elif key=='deckOverride' and value:
                    ref=value.replace('../common/','')
                    if ref not in self.byref:
                        encounter={'name':'Map '+Path(ref).stem}
                        self.byref[ref]=self.deck(encounter,ref)
                    node.set('value',self.byref[ref]);local.add(f)
                elif (key=='reward' and value.strip()) or SKETCHBOOK in value or any('"'+k+'"' in value for k in ('cardName','editions','cardPackShop','sourceDeck')):
                    if self.map_reward(node,node in chest_props,f.stem=='evilgrove_1_zombie'):local.add(f)
        # A common entrance must not lead past a plane override on a later floor.
        while True:
            parents={f for f,edges in links.items() if any(t in local for _,t in edges)}
            if parents<=local:break
            local.update(parents)
        def route(target):
            base=PLANE if target in local else COMMON
            return '../'+base.name+'/'+str(target.relative_to(COMMON))
        for f in sorted(local):
            dest=PLANE/f.relative_to(COMMON);root=trees[f]
            for node,target in links[f]:node.set('value',route(target))
            for node in root.iter():
                for attr in ('source','template'):
                    if attr not in node.attrib:continue
                    target=(f.parent/node.get(attr)).resolve()
                    if not target.is_file():
                        target=COMMON/'maps'/Path(node.get(attr)).parent.name/target.name
                    assert target.is_file(), (f,target)
                    node.set(attr,os.path.relpath(templates.get(target,target),dest.parent))
            emit(dest,ET.tostring(root,encoding='unicode')+'\n')
        points=json.loads((COMMON/'world/points_of_interest.json').read_text())
        for point in points:
            target=destination(point['map'])
            assert target,point['map']
            point['map']=route(target)
        emit(PLANE/'world/points_of_interest.json',dump(points))

    def singles_pool(self, title, weights, mask=None):
        single_rarity_prints=defaultdict(list)
        fixed=Counter()
        counts=Counter()
        for (name,edition,identity),variants in sorted(self.shop_prints.items()):
            if mask is not None and identity!=mask:
                continue
            rarities={r for _,r in variants}
            if not rarities.intersection(weights):
                continue
            if len(rarities)==1:
                art,rarity=min(variants)
                single_rarity_prints[rarity].append(f'{name}|{edition}|{art}')
            else:
                # Forge can reroll art within an edition. Equal weight per art keeps
                # the rarity distribution identical with either variant setting.
                assert rarities<=weights.keys(),(name,rarities)
                for art,rarity in variants:
                    fixed[f'{name}|{edition}|{art}']+=1
                    counts[rarity]+=1
        scale=max(math.ceil((len(single_rarity_prints[r])+counts[r])/weight)
                  for r,weight in weights.items())
        for rarity,weight in weights.items():
            pool=single_rarity_prints[rarity]
            copies,extra=divmod(weight*scale-counts[rarity],len(pool))
            assert copies>=1,(title,rarity)
            for index,entry in enumerate(pool):
                fixed[entry]=copies+(index<extra)
        ref=f'decks/shop/{title}.dck'
        emit(PLANE/ref,'[metadata]\nName='+title+' shop pool\n[Main]\n'+
             ''.join(f'{qty} {entry}\n' for entry,qty in sorted(fixed.items())))
        return {'type':'card','count':1,'sourceDeck':ref}

    def stores(self):
        shops=json.loads((ORIGINAL/'world/shops.json').read_text());self.reward(shops)
        for shop in shops:
            name=shop['name']
            substitute = {
                'Ogre': {'subTypes':['Orc','Troll']}, 'Ogre4Red': {'subTypes':['Orc'],'colors':['red']},
                'FlipShop': {'cardText':'(?i)cycling|evoke'}, 'Battle': {'cardTypes':['Saga','Enchantment'],'subTypes':['Saga']},
                'Mutants': {'cardText':'(?i)modular|changeling'}
            }
            if name in substitute:
                shop['rewards']=[dict(substitute[name],count=8,editions=list(SETS))]
            for reward in shop.get('rewards',[]):
                for rule in reward.get('cardUnion',[]):
                    if name=='Eldrazi':
                        if 'subTypes' in rule:rule['subTypes']=['Construct','Golem','Horror']
                        if 'cardText' in rule:rule['cardText']='artifact'
        by_name={shop['name']:shop for shop in shops}
        general=self.singles_pool('GeneralWeighted',dict(U=80,R=19,M=1))
        for color,mask in dict(White=1,Blue=2,Black=4,Red=8,Green=16,Colorless=0).items():
            local=self.singles_pool(color,dict(C=30,U=50,R=18,M=2),mask)
            for suffix in ('','Creatures'):
                shops.append(dict(by_name[color],name='RingTown'+color+suffix,rewards=[local]*3+[general]*3))
        shops.append(dict(by_name['BoosterPackShop'],name='RingTownBooster',unlimited=False,
                          rewards=[{'type':'cardPackShop','count':1,'editions':PACKS}]))
        shops.append(dict(by_name['Equipment'],name='RingTownEquipment',unlimited=False,
                          rewards=[{'count':2,'subTypes':['Equipment'],'rarity':['Common','Uncommon']}]))
        emit(PLANE/'world/shops.json',dump(shops))
    def boosters(self):
        # Explicit source-set slots also bind basic lands to the selected printing.
        for f in (PLANE.parents[1]/'editions').glob('*.txt'):
            text=f.read_text(errors='replace')
            code=re.search(r'^Code=(.*)',text,re.M)
            if not code or code[1] not in PACKS:continue
            code=code[1];boost=re.search(r'^Booster=(.*)',text,re.M)[1]
            date=re.search(r'^Date=(.*)',text,re.M)[1]
            emit(PLANE/'editions'/f.name,f'[metadata]\nCode={code}\nDate={date}\nBooster={boost}\n')
        # Upstream draft blocks can open packs through their own resolver. Use a plane block per set.
        blocks=(PLANE.parents[1]/'blockdata/blocks.txt').read_text().splitlines()
        restricted=[];jump=[]
        for line in blocks:
            fields=[s.strip() for s in line.split(',')]
            if len(fields)!=3 or fields[0].startswith('#'):continue
            if fields[2] in PACKS:restricted.append(fields[0])
            if 'Jumpstart' in fields[0] and fields[1].split('/')[-1] =='LTR':jump.append(fields[0])
        CONFIG.update(allowedEvents=PACKS,restrictedBlocks=restricted,allowedJumpstart=jump)
        emit(PLANE/'blockdata/blocks.txt',''.join(f'Horizons {c}, 3/6/{"LTR" if c=="MH1" else c}, {c}\n'  for c in PACKS))
        emit(PLANE/'config.json',dump(CONFIG))
    def items(self):
        stock=json.loads((COMMON/'world/items.json').read_text())
        books={SKETCHBOOK+name for code,name in BOOK_SETS.items() if code in ('MH2','LTR')}
        items=[item for item in stock if not item['name'].startswith(SKETCHBOOK) or item['name'] in books]
        for book in sorted(books-{item['name'] for item in items}):
            items.append({'name':book,'unique':True,'description':'Sketches of landscapes from '+book[len(SKETCHBOOK):]+'.','iconName':'LandscapeSketchbook'})
        emit(PLANE/'world/items.json',dump(items))
    def write_mapping(self):
        rows=[]
        def describe(names):
            tribes=Counter()
            for n,q in names.items():
                card=self.db.get(n)
                if card and 'Creature' in card.kinds:
                    for tribe in card.tribes:tribes[tribe]+=q
            return ', '.join(k for k,v in sorted(tribes.items(),key=lambda x:(-x[1],x[0]))[:3])
        for enemy,old,new,plan in self.manifest:
            path=COMMON/old
            source=sections(path)['Main'] if old.endswith('.dck') else Counter()
            old_theme=describe(source)
            if old.endswith('.json') and path.exists():
                template=json.loads(path.read_text()).get('template',{})
                old_theme=template.get('tribe') or str(template.get('colors',''))
            target=sections(PLANE/new)['Main']
            selected=', '.join(n for n,q in target.most_common() if (n in self.legal or n in self.modern) and 'Land' not in self.db[n].kinds)
            unavailable=sum(q for n,q in source.items() if n not in self.legal)
            reason=(f'{unavailable} из {sum(source.values())} исходных экземпляров вне пула'
                    if source else 'Исходный шаблон заменён фиксированным деклистом с печатями')
            rows.append([enemy,old,new,PLANS.get(enemy,plan),old_theme or Path(old).stem,describe(target),reason,selected])
        emit(PLANE/'tools/enemy-mapping.tsv','enemy\toriginal\tlocal\torigin\toriginal_theme\tnew_theme\treason\tspells\n'
             +''.join('\t'.join(row)+'\n' for row in rows))
    def run(self):
        from starters import build_starts
        build_starts(self)
        for source in [ORIGINAL/'world/quests.json', *(ORIGINAL/'languages').glob('quests-*.json')]:
            quests=json.loads(source.read_text())
            self.reward(quests)
            emit(PLANE/source.relative_to(ORIGINAL),dump(quests) if quests!=json.loads(source.read_text()) else source.read_text())
        self.enemies();self.stores();self.maps();self.boosters();self.items()
        self.write_mapping()
        emit(PLANE/'tools/reward-mapping.tsv','original\treplacement\tedition\n'+''.join(f'{n}\t{v}\t{self.legal[v].edition}\n' for n,v in sorted(self.replacements.items())))
if __name__=='__main__':
    import sys
    sys.modules["build_plane"]=sys.modules[__name__]
    parser=argparse.ArgumentParser();parser.add_argument('index',type=Path);Builder(parser.parse_args().index).run()
