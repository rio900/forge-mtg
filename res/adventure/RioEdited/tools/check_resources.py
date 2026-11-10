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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loot", type=Path, help="Write distinct rules for VerifyPlane")
    args = parser.parse_args()
    cfg = json.loads((PLANE / "config.json").read_text())
    banned = set(cfg["restrictedCards"])
    for f in PLANE.rglob("*.json"):
        json.loads(f.read_text())
    for f in PLANE.rglob("*.dck"):
        counts = Counter()
        for line in f.read_text().splitlines():
            if line[:1].isdigit():
                quantity, entry = line.split(" ", 1)
                name, edition, art = entry.split("|")
                assert edition in cfg["allowedEditions"] and name not in banned and int(art) > 0, (f, entry)
                counts[name] += int(quantity)
        assert all(n in BASICS or q <= 4 for n, q in counts.items()), f
    mappings = list(csv.DictReader((PLANE / "tools/enemy-mapping.tsv").open(), delimiter="\t"))
    refs = {r["local"] for r in mappings}
    assert len(refs) == len(mappings) and all((PLANE / r).is_file() for r in refs)
    enemies = json.loads((PLANE / "world/enemies.json").read_text())
    assert next(e for e in enemies if e["name"] == "Slobad")["gamesPerMatch"] == 1
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
            assert len(vendors) == 3 and sum(o.get("template", "").endswith("/inn.tx") for o in objects) == 1, rel
            names = [o.find("properties/property[@name='commonShopList']").get("value") for o in vendors]
            assert all(n in shops for n in names) and "RioTownBooster" in names, (rel, names)
            singles = [shops[n] for n in names if n.startswith("RioTown") and n not in ("RioTownEquipment", "RioTownBooster")]
            assert len(singles) == 1, rel
            slots = singles[0]["rewards"]
            assert [rule["count"] for rule in slots] == [1, 1, 1, 1], rel
            assert all(r["type"] == "Union" and r["cardUnion"] for r in slots[:3]), rel
            assert (PLANE / slots[3]["sourceDeck"]).is_file(), rel
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
            if key == "reward" or '"grantRewards"' in value:
                # Forge's libGDX reader accepts trailing commas and line-separated properties.
                value = re.sub(r",\s*([}\]])", r"\1", value)
                value = re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)', r'\1,\n\2', value)
                obj=json.loads(value)
                def editions(o):
                    if isinstance(o,dict):
                        assert set(o.get("editions",[]))<=set(cfg["allowedEditions"]), (rel,o)
                        for v in o.values():editions(v)
                    elif isinstance(o,list):
                        for v in o:editions(v)
                editions(obj)
                collect_rewards(obj, str(rel), rules,prop in chest_props)
    collect_rewards(json.loads((PLANE / "world/quests.json").read_text()), "quests", rules)
    if args.loot:
        args.loot.write_text("".join(f"{'chest/' if chest else ''}{source}\t{rule}\n" for (chest,rule), source in sorted(rules.items())))
    print(f"Validated {len(refs)} enemy deck references, {len(maps)} maps ({len(reachable)} reachable from POIs) and {len(rules)} distinct loot rules.")


if __name__ == "__main__":
    main()
