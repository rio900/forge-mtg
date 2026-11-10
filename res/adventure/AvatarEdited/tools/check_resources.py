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
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}


CARD_REWARDS = {"card", "randomCard", "Union", "deckCard", "cardPack", "cardPackShop", "rewardDeckCard"}
OTHER_REWARDS = {"gold", "shards", "life", "item", "landSketchbookShop"}


def collect_rewards(obj, source, rules, in_reward=False):
    if isinstance(obj, list):
        for child in obj:
            collect_rewards(child, source, rules, in_reward)
    elif isinstance(obj, dict):
        if in_reward:
            kind = obj.get("type", "card")
            assert kind in CARD_REWARDS | OTHER_REWARDS, (source, obj)
            if kind in CARD_REWARDS and kind != "deckCard":
                rules.setdefault(json.dumps(obj, sort_keys=True), source)
            if kind == "Union":
                for choice in obj["cardUnion"]:
                    single = {"type": "Union", "count": 1, "cardUnion": [choice]}
                    rules.setdefault(json.dumps(single, sort_keys=True), source)
        for key, child in obj.items():
            if key != "cardUnion":
                collect_rewards(child, source, rules, key in {"rewards", "grantRewards", "rotation"})


def check_reward_sources(obj, source, printings, allowed, banned):
    if isinstance(obj, list):
        for entry in obj:
            check_reward_sources(entry, source, printings, allowed, banned)
    elif isinstance(obj, dict):
        if obj.get("cardName"):
            name, edition = obj["cardName"].rsplit("|", 1)
            assert (name, edition) in printings and name not in banned, (source, obj)
        if "editions" in obj:
            assert set(obj["editions"]) <= allowed, (source, obj)
        if obj.get("sourceDeck"):
            path = (PLANE / obj["sourceDeck"]).resolve()
            assert path.is_relative_to(PLANE) and path.is_file(), (source, obj)
        for value in obj.values():
            check_reward_sources(value, source, printings, allowed, banned)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loot", type=Path, help="Write distinct rules for VerifyPlane")
    args = parser.parse_args()
    cfg = json.loads((PLANE / "config.json").read_text())
    assert PLANE.name == "AvatarEdited" and set(cfg["allowedEditions"]) == {"TLA", "TLE"}
    assert cfg["defaultBasicLandSet"] == "TLA" and cfg["allowedEvents"] == ["TLA"]
    printings = {(r["name"], r["edition"], r["art_index"]) for r in csv.DictReader(
        (PLANE / "tools/avatar-printings.tsv").open(), delimiter="\t")}
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
                assert (name, edition, art) in printings, (f, entry)
                counts[name] += int(quantity)
        if f.parent.name != "shop":
            assert all(n in BASICS or q <= 4 for n, q in counts.items()), f
    mappings = list(csv.DictReader((PLANE / "tools/enemy-mapping.tsv").open(), delimiter="\t"))
    refs = {r["local"] for r in mappings}
    assert len(refs) == len(mappings) and all((PLANE / r).is_file() for r in refs)
    enemies = json.loads((PLANE / "world/enemies.json").read_text())
    assert next(e for e in enemies if e["name"] == "Slobad")["gamesPerMatch"] == 1
    assert not any(e.get("copyPlayerDeck") for e in enemies), "Native mirror rewards bypass allowedEditions"
    shops = {s["name"]: s for s in json.loads((PLANE / "world/shops.json").read_text())}
    points = json.loads((PLANE / "world/points_of_interest.json").read_text())
    for point in points:
        ref = point.get("map", "")
        if "/towns/" in ref:
            assert (COMMON / ref).resolve().is_relative_to(PLANE) and (COMMON / ref).is_file(), ref
    rules = {}
    maps = sorted((COMMON / "maps").rglob("*.tmx"))
    for f in maps + sorted((COMMON / "maps/obj").glob("*.tx")):
        rel = f.relative_to(COMMON)
        effective = PLANE / rel if (PLANE / rel).exists() else f
        root = ET.parse(effective)
        if f.parent.name == "towns":
            objects = list(root.iter("object"))
            vendors = [o for o in objects if Path(o.get("template", "")).stem in ("shop", "RotatingShop")]
            assert len(vendors) == 3 and sum(o.get("template", "").endswith("/inn.tx") for o in objects) == 1, rel
            assert all(o.find("properties/property[@name='noRestock']").get("value") == "true" for o in vendors), rel
            names = [o.find("properties/property[@name='commonShopList']").get("value") for o in vendors]
            assert all(n in shops for n in names) and "AvatarTownBooster" in names, (rel, names)
            singles = [shops[n] for n in names if n.startswith("AvatarTown") and n not in ("AvatarTownEquipment", "AvatarTownBooster")]
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
        for prop in root.iter("property"):
            key = prop.get("name")
            value = prop.get("value", prop.text or "").strip()
            if not value:
                continue
            if key == "deckOverride":
                assert value in refs, (rel, value)
            if key == "reward" or '"grantRewards"' in value:
                # Forge's libGDX reader accepts trailing commas and line-separated properties.
                value = re.sub(r",\s*([}\]])", r"\1", value)
                value = re.sub(r'([\]"\d}])\s*\n(\s*"\w+"\s*:)', r'\1,\n\2', value)
                collect_rewards(json.loads(value), str(rel), rules, key == "reward")
    collect_rewards(json.loads((PLANE / "world/quests.json").read_text()), "quests", rules)
    for f in (PLANE/"languages").glob("quests*.json"):
        collect_rewards(json.loads(f.read_text()),str(f.relative_to(PLANE)),rules)
    for enemy in enemies:
        collect_rewards(enemy, enemy["name"], rules)
    catalog = {(name, edition) for name, edition, _ in printings}
    allowed = set(cfg["allowedEditions"])
    for rule, source in rules.items():
        check_reward_sources(json.loads(rule), source, catalog, allowed, banned)
    check_reward_sources(enemies, "enemies", catalog, allowed, banned)
    check_reward_sources(list(shops.values()), "shops", catalog, allowed, banned)
    world=json.loads((PLANE/"world/world.json").read_text())
    base=json.loads((PLANE.parent/"Shandalar/world/world.json").read_text())
    assert world==base
    poi_names={name for f in world["biomesNames"] for name in json.loads((COMMON/f).read_text()).get("pointsOfInterest",[])}
    pending=[point["map"] for point in points if point["name"] in poi_names]
    visited=set()
    while pending:
        ref=pending.pop()
        if ref in visited:continue
        visited.add(ref)
        dest=(COMMON/ref).resolve()
        assert dest.is_relative_to(PLANE) and dest.is_file(),ref
        for prop in ET.parse(dest).iter("property"):
            v=prop.get("value","")
            if prop.get("name")=="teleport" and v.endswith(".tmx"):pending.append(v)
    print(f"Verified {len(visited)} reachable map paths.")
    if args.loot:
        args.loot.write_text("".join(f"{source}\t{rule}\n" for rule, source in sorted(rules.items())))
    print(f"Validated {len(refs)} enemy deck references, {len(maps)} maps and {len(rules)} distinct loot rules.")


if __name__ == "__main__":
    main()
