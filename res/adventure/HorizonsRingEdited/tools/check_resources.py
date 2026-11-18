"""Validate effective Adventure maps, card printings, deck references and loot rules."""
import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

PLANE = Path(__file__).resolve().parents[1]
COMMON = PLANE.parent / "common"
CHEST_RARITIES = {"Uncommon", "Rare", "Mythic Rare"}
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}


def collect_rewards(obj, source, rules, chest=False):
    if isinstance(obj, dict):
        if obj.get("type","card" if chest else None) in {"card", "cardPack", "randomCard", "Union", "cardPackShop", "rewardDeckCard"}:
            if chest:
                assert obj.get("type") not in ("cardPack","cardPackShop"), source
                for member in obj.get("cardUnion",[obj]):
                    assert member.get("rarity") and set(member["rarity"]) <= CHEST_RARITIES, (source, member)
            rules.setdefault((chest,json.dumps(obj, sort_keys=True)), source)
        else:
            for child in obj.values():
                collect_rewards(child, source, rules, chest)
    elif isinstance(obj, list):
        for child in obj:
            collect_rewards(child, source, rules, chest)


def check_quest_translation(original, translated):
    if isinstance(original, list):
        assert len(original) == len(translated)
        for source, target in zip(original, translated):
            check_quest_translation(source, target)
    elif isinstance(original, dict):
        assert original.keys() == translated.keys()
        for key, source in original.items():
            target = translated[key]
            if key in {"name", "text", "description", "rewardDescription"} and isinstance(source, str):
                tokens = r"\$\([^)]*\)|\{[^{}]*\}"
                assert Counter(re.findall(tokens, source)) == Counter(re.findall(tokens, target)), source
                assert bool(source.strip()) == bool(target.strip()), source
            else:
                check_quest_translation(source, target)
    else:
        assert original == translated, (original, translated)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loot", type=Path, help="Write distinct rules for VerifyPlane")
    args = parser.parse_args()
    check_quest_translation(json.loads((PLANE/"world/quests.json").read_text()),
                            json.loads((PLANE/"languages/quests-ru-RU.json").read_text()))
    cfg = json.loads((PLANE / "config.json").read_text())
    assert set(cfg["allowedEditions"]) == {"MH1","MH2","LTR","MH3","2XM"}
    def audit_rules(obj, source):
        if isinstance(obj,list):
            for v in obj:audit_rules(v,source)
        if not isinstance(obj,dict):return
        assert set(obj.get("editions",[])) <= set(cfg["allowedEditions"]), (source,obj)
        if obj.get("cardName"):
            entry=obj["cardName"].split("|")
            assert len(entry)>=2 and entry[1] in cfg["allowedEditions"],(source,entry)
        for v in obj.values():audit_rules(v,source)
    for path in [*(PLANE/"world").glob("*.json"),*(PLANE/"languages").glob("*.json"),*(PLANE/"decks").rglob("*.json")]:
        audit_rules(json.loads(path.read_text()),path)
    modern={tuple(line.split("|")[:2]) for line in (PLANE/"tools/modern-cards.txt").read_text().splitlines()}
    assert len(modern)==54
    banned = set(cfg["restrictedCards"])
    for f in PLANE.rglob("*.json"):
        json.loads(f.read_text())
    for f in PLANE.rglob("*.dck"):
        counts = Counter()
        for line in f.read_text().splitlines():
            if line[:1].isdigit():
                quantity, entry = line.split(" ", 1)
                name, edition, art = entry.split("|")
                if edition not in cfg["allowedEditions"]:
                    assert (name,edition) in modern and (f.is_relative_to(PLANE/"decks/shop") or f.parent.name in ("arena","converted") or
                        (f.name=="liliana.dck" and name=="Sheoldred, the Apocalypse") or
                        (f.name=="griselbrand-1.dck" and name in ("Griselbrand","Goryo's Vengeance"))), (f,entry)
                assert name not in banned and int(art) > 0, (f, entry)
                counts[name] += int(quantity)
        assert f.is_relative_to(PLANE/"decks/shop") or f.parent.name=="arena" or all(n.removeprefix("Snow-Covered ") in BASICS or q <= 4 for n, q in counts.items()), f
    mappings = list(csv.DictReader((PLANE / "tools/enemy-mapping.tsv").open(), delimiter="\t"))
    refs = {r["local"] for r in mappings}
    assert len(refs) == len(mappings) and all((PLANE / r).is_file() for r in refs)
    enemies = json.loads((PLANE / "world/enemies.json").read_text())
    stock=json.loads((COMMON/"world/enemies.json").read_text())
    from enemy_plans import COLORS
    def encounter_properties(enemy):
        result={k:v for k,v in enemy.items() if k not in ("deck","rewards","nextEnemy")}
        if enemy["name"] in COLORS:result["colors"]=COLORS[enemy["name"]]
        if enemy.get("nextEnemy"):result["nextEnemy"]=encounter_properties(enemy["nextEnemy"])
        return result
    assert list(map(encounter_properties,enemies))==list(map(encounter_properties,stock))
    from encounters import PACKAGES
    def bounded_rewards(enemy):
        if enemy.get("boss") or enemy["name"] in PACKAGES:
            cards=[r for r in enemy["rewards"] if r.get("type", "card").lower() in
                   {"card","randomcard","deckcard","rewarddeckcard","union","cardpack","cardpackshop"}]
            assert len(cards)==3 and sum(r["count"] for r in cards)==4,(enemy["name"],cards)
            assert all(r.get("addMaxCount",0)==0 and r["type"]=="card" for r in cards)
            assert cards[0]["sourceDeck"].endswith("Support.dck") and cards[0]["count"]==2
            assert cards[1]["sourceDeck"].endswith("Premium.dck") and cards[1]["count"]==1
            assert cards[2]["sourceDeck"].endswith("Any.dck") and cards[2]["count"]==1
            assert cards[2]["probability"]==(.35 if enemy.get("boss") else .05)
        if enemy.get("nextEnemy"):bounded_rewards(enemy["nextEnemy"])
    for enemy in enemies:bounded_rewards(enemy)
    shops = {s["name"]: s for s in json.loads((PLANE / "world/shops.json").read_text())}
    points = json.loads((PLANE / "world/points_of_interest.json").read_text())
    for point in points:
        ref = point.get("map", "")
        actual=(COMMON/ref).resolve()
        assert actual.is_file(), ref
        if actual.is_relative_to(COMMON):assert not (PLANE/actual.relative_to(COMMON)).exists(), ref
    pending=[(COMMON/p["map"]).resolve() for p in points]
    reachable=set()
    while pending:
        path=pending.pop()
        if path in reachable:continue
        reachable.add(path)
        for prop in ET.parse(path).iter("property"):
            ref=prop.get("value","")
            if prop.get("name")=="teleport" and ref.endswith(".tmx"):
                target=(PLANE/ref).resolve()
                assert target.is_file(), (path,ref)
                pending.append(target)
    rules = {}
    maps = sorted((COMMON / "maps").rglob("*.tmx"))
    for f in maps + [COMMON / "maps/obj" / (name+".tx") for name in ("scroll","treasure","booster")]:
        rel = f.relative_to(COMMON)
        effective = PLANE / rel if (PLANE / rel).exists() else f
        root = ET.parse(effective)
        if f.parent.name == "towns":
            objects = list(root.iter("object"))
            vendors = [o for o in objects if Path(o.get("template", "")).stem in ("shop", "RotatingShop")]
            assert len(vendors) == (3 if f.stem.startswith("waste_") else 4) and sum(o.get("template", "").endswith("/inn.tx") for o in objects) == 1, rel
            assert all(Path(o.get("template")).name=="shop.tx" and o.find("properties/property[@name='noRestock'][@value='true']") is None for o in vendors), rel
            names = [o.find("properties/property[@name='commonShopList']").get("value") for o in vendors]
            assert all(n in shops for n in names) and "RingTownBooster" in names, (rel, names)
            singles = [shops[n] for n in names if n.startswith("RingTown") and not n.startswith("RingTownLands") and n not in ("RingTownEquipment", "RingTownBooster")]
            assert len(singles) == 1, rel
            slots = singles[0]["rewards"]
            assert [rule["count"] for rule in slots] == [1]*6, rel
            color=singles[0]["name"].removeprefix("RingTown").removesuffix("Creatures")
            assert [r["sourceDeck"] for r in slots] == [f"decks/shop/{color}.dck"]*3+["decks/shop/GeneralWeighted.dck"]*3, rel
            assert all((PLANE/r["sourceDeck"]).is_file() for r in slots), rel
        if f.stem.endswith("_capital"):
            vendors=[o for o in root.iter("object") if Path(o.get("template","")).stem in ("shop","RotatingShop")]
            assert len(vendors)==16, (rel,len(vendors))
            original_vendors=[o for o in ET.parse(f).iter("object") if Path(o.get("template", "")).stem in ("shop","RotatingShop")]
            assert {(o.get("id"),o.get("x"),o.get("y")) for o in vendors}=={(o.get("id"),o.get("x"),o.get("y")) for o in original_vendors},rel
            for vendor in vendors:
                for prop in vendor.findall("properties/property"):
                    if prop.get("name", "").endswith("ShopList") or prop.get("name")=="rotation":
                        for name in prop.get("value", "").split(","):
                            assert name in shops,(rel,name)
                            if name.startswith(("CapitalSmall","CapitalLands","CapitalBooster")):
                                shop=shops[name]
                                assert not shop["unlimited"],name
                                expected=6
                                assert sum(r["count"] for r in shop["rewards"])==expected,name

            assert sum(Path(o.get("template","")).stem=="RotatingShop" for o in vendors)==3, rel
            assert sum(o.find("properties/property[@name='rareShopList']") is not None for o in vendors)==7, rel
        if effective != f:
            original = ET.parse(f)
            assert [n.text for n in root.iter("data")] == [n.text for n in original.iter("data")], rel
            for node in root.iter():
                for key in ("template", "source"):
                    if key in node.attrib:
                        assert (effective.parent / node.get(key)).is_file(), (rel, node.get(key))
        chest_props=set()
        for obj in root.iter("object"):
            ref=obj.get("template","")
            if ref:
                template=(effective.parent/ref).resolve()
                if template.is_relative_to(COMMON):
                    assert not (PLANE/template.relative_to(COMMON)).is_file(), (rel,ref)
            if Path(ref).name=="treasure.tx" or f.name=="treasure.tx":
                chest_props.update(obj.findall("properties/property[@name='reward']"))
        for prop in root.iter("property"):
            key = prop.get("name")
            value = prop.get("value", prop.text or "").strip()
            if not value:
                continue
            if key == "teleport" and value.endswith(".tmx"):
                actual=(PLANE/value).resolve()
                if actual.is_file() and actual.is_relative_to(COMMON):
                    assert not (PLANE/actual.relative_to(COMMON)).is_file(), (rel,value)
                if not actual.is_file():
                    # Only tolerate a missing destination already missing in stock Forge.
                    assert not (COMMON/value).is_file() and not list((COMMON/"maps").rglob(Path(value).name)), (rel,value)
            if key == "deckOverride":
                assert value in refs, (rel, value)
            if key in ("reward", "arena") or '"grantRewards"' in value:
                # Forge's libGDX reader accepts trailing commas and line-separated properties.
                value = re.sub(r",\s*([}\]])", r"\1", value)
                value = re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)', r'\1,\n\2', value)
                obj=json.loads(value)
                if key=="arena" and f.stem.endswith("_capital"):
                    original_value=ET.parse(f).find(".//property[@name='arena']").text
                    original_arena=json.loads(re.sub(r",\s*([}\]])",r"\1",original_value))
                    color={"plains":"White","island":"Blue","swamp":"Black","mountain":"Red","forest":"Green"}[f.stem.split("_")[0]]
                    final=original_arena["rewards"][-1]
                    premium=next(rule for rule in final if rule.get("rarity")==["Mythic Rare"])
                    premium.clear()
                    premium.update(type="card",count=1,sourceDeck="decks/arena/Premium.dck")
                    final.append({"type":"card","count":1,"sourceDeck":f"decks/arena/{color}.dck"})
                    assert obj==original_arena,(rel,"arena round or prize changed")
                def editions(o):
                    if isinstance(o,dict):
                        assert set(o.get("editions",[]))<=set(cfg["allowedEditions"]), (rel,o)
                        for v in o.values():editions(v)
                    elif isinstance(o,list):
                        for v in o:editions(v)
                editions(obj)
                audit_rules(obj,rel)
                collect_rewards(obj, str(rel), rules,prop in chest_props)
    collect_rewards(json.loads((PLANE / "world/quests.json").read_text()), "quests", rules)
    if args.loot:
        args.loot.write_text("".join(f"{'chest/' if chest else ''}{source}\t{rule}\n" for (chest,rule), source in sorted(rules.items())))
    print(f"Validated {len(refs)} enemy deck references, {len(maps)} maps ({len(reachable)} reachable from POIs) and {len(rules)} distinct loot rules.")


if __name__ == "__main__":
    main()
