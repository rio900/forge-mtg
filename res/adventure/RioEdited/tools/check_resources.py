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


def collect_rewards(obj, source, rules):
    if isinstance(obj, dict):
        if obj.get("type") in {"card", "cardPack", "randomCard", "Union", "cardPackShop", "rewardDeckCard"}:
            rules.setdefault(json.dumps(obj, sort_keys=True), source)
        else:
            for child in obj.values():
                collect_rewards(child, source, rules)
    elif isinstance(obj, list):
        for child in obj:
            collect_rewards(child, source, rules)


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
        if "/towns/" in ref:
            assert (COMMON / ref).resolve().is_relative_to(PLANE) and (COMMON / ref).is_file(), ref
    rules = {}
    maps = sorted((COMMON / "maps").rglob("*.tmx"))
    for f in maps + [COMMON / "maps/obj/scroll.tx"]:
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
            assert len(singles) == 1 and [(r["count"], r["rarity"]) for r in singles[0]["rewards"]] == [(3, ["Common"]), (1, ["Uncommon"])], rel
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
                collect_rewards(json.loads(value), str(rel), rules)
    collect_rewards(json.loads((PLANE / "world/quests.json").read_text()), "quests", rules)
    if args.loot:
        args.loot.write_text("".join(f"{source}\t{rule}\n" for rule, source in sorted(rules.items())))
    print(f"Validated {len(refs)} enemy deck references, {len(maps)} maps and {len(rules)} distinct loot rules.")


if __name__ == "__main__":
    main()
