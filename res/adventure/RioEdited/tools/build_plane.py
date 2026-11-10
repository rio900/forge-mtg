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
PACKS = [code for code in SETS if code != 'MAT']
TOWN_COLORS = {'plains':'White','island':'Blue','swamp':'Black','mountain':'Red',
               'forest':'Green','waste':'Colorless'}

def limit_town_shops(root, filename):
    terrain=filename.split('_')[0]
    color=TOWN_COLORS[terrain]
    land=terrain.title() if terrain!='waste' else 'RioTownEquipment'
    singles='RioTown'+color+('Creatures' if '_tribal' in filename else '')
    group=next(g for g in root.iter('objectgroup') if any(o.get('template','').endswith('/shop.tx') for o in g))
    shops=[o for o in group.findall('object') if Path(o.get('template','')).stem in ('shop','RotatingShop')]
    def pool(o):
        return ' '.join(p.get('value','') for p in o.findall('properties/property') if p.get('name') in ('commonShopList','shopList'))
    # Keep landmark locations and object IDs used by previously visited towns.
    land_shop=next((o for o in shops if pool(o) in (land,'Equipment')),shops[-1])
    others=[o for o in shops if o is not land_shop]
    booster=next((o for o in others if 'BoosterPackShop' in pool(o)),others[-1])
    vendor=next(o for o in others if o is not booster)
    keep={land_shop:land,booster:'RioTownBooster',vendor:singles}
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
DUALS = dict(zip(['WU','WB','WR','WG','UB','UR','UG','BR','BG','RG'],
                 ['Idyllic Beachfront','Sunlit Marsh','Sacred Peaks','Radiant Grove','Contaminated Aquifer',
                  'Molten Tributary','Tangled Islet','Geothermal Bog','Haunted Mire','Wooded Ridgeline']))
WASTELANDS = ["Mishra's Foundry",'Mirrex','Hall of Tagsin','Demolition Field','Roadside Reliquary',
              "Tocasia's Dig Site",'Crystal Grotto','Field of Ruin','The Monumental Facade','Blast Zone']
PROTOTYPES = {'Barbarian','Big Zombie','Elf','Ashmouth Devil','Chandra'}
# Keep multi-list opponents' original variation. Direct tournament imports are limited to thematic matches.
TOURNAMENT = {'Dark Enchanter':'Pedro Mocelin','Human Captain':'Autumn Burchett','Dimir Faerie':'Théo Jacques-Griffin',
              'Faerie':'Shota Yasooka','Guardian Angel':'Reid Duke','Challenger 20':None,
              'Challenger 21':None,'Challenger 22':None}
SIGNATURES = {
 'Emrakul':['Cityscape Leveler','Portal to Phyrexia','Thran Spider','The Mightstone and Weakstone'],
 'Myr Superion':['Cityscape Leveler','Steel Exemplar','Thran Spider'],
 'Ghalta':['Tyrranax Rex','Defiler of Vigor'], 'Akroma':['Sanctuary Warden','Giada, Font of Hope'],
 'Liliana':['Liliana of the Veil','Headless Rider','Champion of the Perished'],
 'Garruk':['Glissa Sunslayer','Mosswood Dreadknight'], 'Jace':['Jace, the Perfected Mind','Memory Deluge'],
 'Teferi':['Teferi, Temporal Pilgrim','Sunfall'], 'Nahiri':['Nahiri, Forged in Fury','Bladehold War-Whip'],
 'Slobad':['Slobad, Iron Goblin','Twinshot Sniper'], 'Slimefoot':['Deathbonnet Sprout','Cult Conscript'],
 'Kiora':['Kiora, Sovereign of the Deep','Hullbreaker Horror'], 'Griselbrand':['Dreadfeast Demon','Infernal Grasp'],
 'Lorthos':['Hullbreaker Horror','Tolarian Terror'], 'Lathliss':['Shivan Devastator','Invasion of Tarkir'],
 'Grolnok':['Grolnok, the Omnivore'], 'Tibalt':['Burn Down the House','Stensia Uprising'],
 'Sorin':['Sorin the Mirthless','Glissa Sunslayer'], 'Elesh Norn':['Elesh Norn, Mother of Machines'],
 'Plaguelord':['Voidwing Hybrid','Blightbelly Rat','Pestilent Syphoner','Drown in Ichor','Experimental Augury'],
 'Sliver Queen':['Jodah, the Unifier','Raffine, Scheming Seer','Halana and Alena, Partners'],
 'Scarecrow Captain':['Graaz, Unstoppable Juggernaut','Steel Exemplar'],
}
SKETCHBOOK = 'Landscape Sketchbook - '
BOOK_SETS = {'DMU':'Dominaria United','BRO':'The Brothers War','NEO':'Kamigawa Neon Dynasty',
             'MID':'Innistrad: Midnight Hunt','VOW':'Innistrad: Crimson Vow','SNC':'Streets of New Capenna',
             'ONE':'Phyrexia: All Will Be One','MOM':'March of the Machine','WOE':'Wilds of Eldraine',
             'AFR':'Dungeons & Dragons: Adventures in the Forgotten Realms'}
QUEST_BOOKS = {"Urza's Saga":'BRO','Ixalan':'AFR','Mirage':'DMU','Coldsnap':'VOW'}
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
        self.worlds=json.loads((PLANE/'tools/worlds-2023.json').read_text())
        self.reward_overrides=defaultdict(list)
        for row in json.loads((PLANE/'tools/encounter-rewards.json').read_text()):
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
        player=TOURNAMENT.get(name) if index==0 else None
        if name.startswith('Challenger '):
            players=list(self.worlds); player=players[(int(name[-2:])*4+index)%len(players)]
        if player:
            deck=self.worlds[player];self.write_deck(rel,name+' - '+deck['archetype'],deck['sections'])
            self.manifest.append((name,ref,rel,player));return rel
        # Keep legal cards first, replace out-of-pool spells by comparable role, cost and tribe.
        tags={str(t).lower() for t in e.get('questTags',[]) if t}
        tags.update(re.findall('[a-z]+',name.lower()))
        if template.get('tribe'):tags.add(template['tribe'].lower())
        if name=='Plaguelord':tags.update(['toxic','proliferate','poison'])
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
        if name=='Emrakul':
            rows=Counter({'Automated Artificer':4,'Network Terminal':3,'Honored Heirloom':3,'Thran Spider':4,
                          'The Mightstone and Weakstone':3,'Circuit Mender':4,'Portal to Phyrexia':2,
                          'Cityscape Leveler':3,'Karn, Living Legacy':2,'Steel Exemplar':4,
                          'Graaz, Unstoppable Juggernaut':2,'The Celestus':2})
            landct=24
        elif sum(q for n,q in rows.items() if 'Creature' in self.db[n].kinds)<6 and mask==BITS['U']:
            for finisher in ['Haughty Djinn','Tolarian Terror']:
                while rows[finisher]<3:
                    drop=max((n for n in rows if n not in ('Haughty Djinn','Tolarian Terror') and rows[n]),key=lambda n:(rows[n],self.db[n].cost))
                    rows[drop]-=1
                    rows[finisher]+=1
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
                        land=BASIC[colors(mask)[j%len(colors(mask))]] if mask else next(l for l in WASTELANDS if rows[l]+side[l]<4)
                        side[land]+=1
                continue
            for j in range(q):
                if n in self.legal and not self.db[n].mask & ~mask and rows[n]+side[n]<4:chosen=n
                else:chosen=self.close(o,[c for c in options if rows[c.name]+side[c.name]<4],tags,seed+n,3).name
                side[chosen]+=1
        if side:parts['Sideboard']=side
        self.write_deck(rel,name,parts);self.manifest.append((name,ref,rel,'adapted'));return rel
    def lands(self,mask,count,spells):
        result=Counter()
        if not mask:
            for i in range(count):result[WASTELANDS[i%len(WASTELANDS)]]+=1
            return result
        cs=colors(mask)
        if len(cs)>=3:
            for _ in range(min(4,count//6)):result['Evolving Wilds']+=1
        duals=[n for k,n in DUALS.items() if all(c in cs for c in k)]
        if duals:
            for i in range(min(count//(4 if len(cs)==2 else 2),4*len(duals))):
                result[duals[i%len(duals)]]+=1
        if len(cs)>=4:
            for _ in range(min(4,count//6)):result['Crystal Grotto']+=1
        weights={c:1+sum(q/max(1,len(colors(self.db[n].mask))) for n,q in spells.items() if self.db[n].mask & BITS[c]) for c in cs}
        basics=Counter()
        for _ in range(count-sum(result.values())):
            col=max(cs,key=lambda c:math.sqrt(weights[c])/(basics[c]+.5));basics[col]+=1
        for col,q in basics.items():result[BASIC[col]]+=q
        return result
    def named(self,n):
        n=n.split('|')[0].strip()
        if n in self.replacements:return self.replacements[n]
        curated={'Black Lotus':'The Celestus','Mox Emerald':'Gala Greeters','Mox Ruby':'Urabrask’s Forge',
           'Mox Jet':'Gix, Yawgmoth Praetor','Mox Pearl':'Serra Paragon','Mox Sapphire':'The Reality Chip',
           'Time Walk':'Alchemist’s Gambit','Timetwister':'The Temporal Anchor','Ancestral Recall':'Silver Scrutiny',
           'Wastes':"Mishra's Foundry",'Griselbrand':'Dreadfeast Demon','Damnation':'Gix’s Command',
           'Gaea’s Cradle':'Boseiju, Who Endures','Chandra, Fire of Kaladesh':'Chandra, Dressed to Kill',
           'Oath of Chandra':'Light Up the Night',"Pyromancer's Goggles":"Urabrask's Forge",
           "Pyromancer's Gauntlet":'The Celestus',"Chandra's Regulator":"Chandra, Hope's Beacon",
           "Chandra's Defeat":'Flame-Blessed Bolt'}
        curated={k.replace('’',"'"):v.replace('’',"'") for k,v in curated.items()}
        o=self.db.get(n)
        if n.startswith('Snow-Covered ') and n[13:] in BASIC.values():rep=n[13:]
        elif n in self.legal:rep=n
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
        if data.get('superTypes')==['Snow'] and data.get('type')=='randomCard':
            data.pop('superTypes');data['colors']=['blue'];data['editions']=['VOW','MID']
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
        if data.get('cardText','').lower()=='infect':data['cardText']='(?i)toxic|poison'
        if data.get('sourceDeck'):
            ref=data['sourceDeck'];low=ref.lower()
            if 'funny' in low:
                data.pop('sourceDeck');data.pop('subTypes',None);data.pop('cardText',None)
                data['cardTypes']=['Artifact'];data['editions']=['BRO','NEO','ONE']
            elif 'warhammer' in low:
                data.pop('sourceDeck');data['editions']=['BRO','ONE'];data['cardTypes']=['Artifact','Creature']
            elif ref in self.byref:data['sourceDeck']=self.byref[ref]
            else:raise ValueError('Unmapped shop source '+ref)
    def enemies(self):
        src=json.loads((COMMON/'world/enemies.json').read_text())
        self.byref={}
        def convert(e,owner=None):
            if e['name']=='Slobad':e['gamesPerMatch']=1
            refs=[]
            for i,ref in enumerate(e['deck']):
                if e['name'] in PROTOTYPES:
                    path='decks/selected/'+e['name'].lower().replace(' ','_')+'.dck'
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
    def maps(self):
        scroll=COMMON/'maps/obj/scroll.tx'
        local_scroll=PLANE/scroll.relative_to(COMMON)
        template=ET.fromstring(scroll.read_bytes())
        for prop in template.findall(".//property[@name='reward']"):
            obj=json.loads(prop.get('value'));self.reward(obj);prop.set('value',json.dumps(obj))
        for node in template.iter('tileset'):
            node.set('source',os.path.relpath(scroll.parent/node.get('source'),local_scroll.parent))
        emit(local_scroll,ET.tostring(template,encoding='unicode')+'\n')
        for f in sorted((COMMON/'maps').rglob('*.tmx')):
            root=ET.fromstring(f.read_bytes());changed=any(n.get('template','').endswith('/scroll.tx') for n in root.iter())
            if f.parent==COMMON/'maps/map/towns':
                limit_town_shops(root,f.name);changed=True
            for node in root.iter('property'):
                key=node.get('name');value=node.get('value',node.text or '')
                if key=='deckOverride' and value:
                    ref=value.replace('../common/','')
                    if ref not in self.byref:
                        encounter={'name':'Map '+Path(ref).stem}
                        self.byref[ref]=self.deck(encounter,ref)
                    node.set('value',self.byref[ref]);changed=True
                elif (key=='reward' and '"Snow"' in value) or SKETCHBOOK in value or any('"'+k+'"' in value for k in ('cardName','editions','cardPackShop','sourceDeck')):
                    try:obj=json.loads(value)
                    except ValueError:
                        repaired=re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)',r'\1,\n\2',value)
                        obj=json.loads(repaired)
                    before=dump(obj);self.reward(obj)
                    if before!=dump(obj):
                        value=json.dumps(obj,ensure_ascii=False,separators=(',',':'))
                        if 'value' in node.attrib:node.set('value',value)
                        else:node.text=value
                        changed=True
            if changed:
                dest=PLANE/f.relative_to(COMMON)
                for node in root.iter():
                    for attr in ('source','template'):
                        if attr in node.attrib:
                            target=(f.parent/node.get(attr)).resolve()
                            if not target.is_file():
                                target=COMMON/'maps'/Path(node.get(attr)).parent.name/target.name
                            if target==scroll:target=local_scroll
                            if target.is_file():node.set(attr,os.path.relpath(target,dest.parent))
                emit(dest,ET.tostring(root,encoding='unicode')+'\n')
        # TileMapScene prefixes POI map paths with common, even inside custom planes.
        points=json.loads((COMMON/'world/points_of_interest.json').read_text())
        for point in points:
            ref=point.get('map','')
            if ref.startswith('../common/maps/map/towns/'):
                point['map']=ref.replace('../common/','../'+PLANE.name+'/',1)
        emit(PLANE/'world/points_of_interest.json',dump(points))

    def town_rewards(self, color, creatures):
        # Three separate shortlists keep the guaranteed offers useful and distinct.
        lists = {
            'White': [('Inspiring Overseer','Spirited Companion','Cathar Commando'),
                      ('Annex Sentry','Ambitious Farmhand','Coppercoat Vanguard'),
                      ('Illuminator Virtuoso','Jawbone Duelist','Ingenious Smith')],
            'Blue': [('Moon-Circuit Hacker','Lantern Bearer',"Malcator's Watcher"),
                     ('Faerie Vandal','Thopter Mechanic','Picklock Prankster'),
                     ('Stormchaser Drake','Prosperous Thief','Trawler Drake')],
            'Black': [('Shambling Ghast','Phyrexian Rager','Nezumi Informant'),
                      ('Fell Stinger','Morbid Opportunist','Cult Conscript'),
                      ('Dockside Chef','Gravelighter',"Knight of Dusk's Shadow")],
            'Red': [('Voldaren Epicure','Ratcatcher Trainee','Witty Roastmaster'),
                    ('Monastery Swiftspear','Phoenix Chick','Battle Cry Goblin'),
                    ('Electrostatic Infantry','Rabbit Battery','Reinforced Ronin')],
            'Green': [('Jewel Thief','Argothian Opportunist','Fang of Shigeki'),
                      ('Cankerbloom','Armored Scrapgorger','Prosperous Innkeeper'),
                      ('Tough Cookie','Kami of Whispered Hopes','Outland Liberator')],
            'Colorless': [('Iron Apprentice','Gingerbrute','Skittering Surveyor'),
                          ('Circuit Mender','Patchwork Automaton','Myr Convert'),
                          ('Containment Construct',"Atraxa's Skitterfang",'Towashi Guide-Bot')],
        }
        spells = {'White':('Destroy Evil','Ossification'), 'Blue':('Consider','Fading Hope'),
                  'Black':('Deadly Dispute','Go for the Throat'), 'Red':('Lightning Strike','Play with Fire'),
                  'Green':('Bite Down','Tail Swipe'), 'Colorless':('Energy Refractor','Levitating Statue')}
        groups=[list(group) for group in lists[color]]
        if not creatures:
            common,uncommon=spells[color]
            groups[0].append(common)
            groups[2].append(uncommon)
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
            pool=sorted((c.name for c in self.spells if c.mask==mask and c.rarity==rarity
                         and c.name not in reserved and (not creatures or 'Creature' in c.kinds)),
                        key=lambda n:(stable(theme+n),n))
            assert pool, (theme,rarity)
            rows.update(pool[i%len(pool)] for i in range(count))
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
                        if 'subTypes' in rule:rule['subTypes']=['Phyrexian']
                        if 'cardText' in rule:rule['cardText']='Phyrexian'
                    elif name=='Squirrel':
                        if 'subTypes' in rule:rule['subTypes']=['Rabbit','Fox','Rat']
                        if 'cardText' in rule:rule['cardText']='Food'
                    elif name=='SnowShop':
                        rule.pop('superTypes',None)
                        rule.pop('cardText',None)
                        rule['colors']=['blue']
                        rule['editions']=['MID','VOW']
                    elif name=='Eldrazi':
                        if 'subTypes' in rule:rule['subTypes']=['Horror']
                        if 'cardText' in rule:rule['cardText']='Powerstone'
        by_name={shop['name']:shop for shop in shops}
        for color in TOWN_COLORS.values():
            for suffix in ('','Creatures'):
                rewards=self.town_rewards(color,bool(suffix))
                shops.append(dict(by_name[color],name='RioTown'+color+suffix,rewards=rewards))
        shops.append(dict(by_name['BoosterPackShop'],name='RioTownBooster',unlimited=False,
                          rewards=[{'type':'cardPackShop','count':1,'editions':PACKS}]))
        shops.append(dict(by_name['Equipment'],name='RioTownEquipment',unlimited=False,
                          rewards=[{'count':2,'subTypes':['Equipment'],'rarity':['Common','Uncommon']}]))
        emit(PLANE/'world/shops.json',dump(shops))
    def boosters(self):
        # Explicit source-set slots also bind basic lands to the selected printing.
        edits={'BRO':('1 fromSheet("BRR cards")','1 Uncommon:fromSets("BRO")'),
               'MOM':('1 fromSheet("MUL draft booster")','1 Uncommon:fromSets("MOM")'),
               'WOE':('1 UncommonRareMythic:fromSheet("WOT cards")','1 Uncommon:fromSets("WOE")')}
        for f in (PLANE.parents[1]/'editions').glob('*.txt'):
            text=f.read_text(errors='replace')
            code=re.search(r'^Code=(.*)',text,re.M)
            if not code or code[1] not in PACKS:continue
            code=code[1];boost=re.search(r'^Booster=(.*)',text,re.M)[1]
            if code in edits:
                old,new=edits[code];assert old in boost;boost=boost.replace(old,new)
            if boost.endswith('1 BasicLand'):boost+=f':fromSets("{code}")'
            date=re.search(r'^Date=(.*)',text,re.M)[1]
            emit(PLANE/'editions'/f.name,f'[metadata]\nCode={code}\nDate={date}\nBooster={boost}\n')
        # Upstream draft blocks can open packs through their own resolver. Use a plane block per set.
        blocks=(PLANE.parents[1]/'blockdata/blocks.txt').read_text().splitlines()
        restricted=[];jump=[]
        for line in blocks:
            fields=[s.strip() for s in line.split(',')]
            if len(fields)!=3 or fields[0].startswith('#'):continue
            if fields[2] in PACKS:restricted.append(fields[0])
            if 'Jumpstart' in fields[0] and fields[1].split('/')[-1] in ('DMU','BRO','ONE','MOM'):jump.append(fields[0])
        CONFIG.update(allowedEvents=PACKS,restrictedBlocks=restricted,allowedJumpstart=jump)
        emit(PLANE/'blockdata/blocks.txt',''.join(f'Rio {c}, 3/6/{c}, {c}\n' for c in PACKS))
        emit(PLANE/'config.json',dump(CONFIG))
    def items(self):
        stock=json.loads((COMMON/'world/items.json').read_text())
        books={SKETCHBOOK+name for code,name in BOOK_SETS.items() if code in PACKS}
        items=[item for item in stock if not item['name'].startswith(SKETCHBOOK) or item['name'] in books]
        for book in sorted(books-{item['name'] for item in items}):
            items.append({'name':book,'unique':True,'description':'Sketches of landscapes from '+book[len(SKETCHBOOK):]+'.','iconName':'LandscapeSketchbook'})
        emit(PLANE/'world/items.json',dump(items))
    def run(self):
        self.enemies();self.stores();self.maps();self.boosters();self.items()
        emit(PLANE/'tools/enemy-mapping.tsv','enemy\toriginal\tlocal\torigin\n'+''.join('\t'.join(row)+'\n' for row in self.manifest))
        emit(PLANE/'tools/reward-mapping.tsv','original\treplacement\tedition\n'+''.join(f'{n}\t{v}\t{self.legal[v].edition}\n' for n,v in sorted(self.replacements.items())))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('index',type=Path);Builder(parser.parse_args().index).run()
