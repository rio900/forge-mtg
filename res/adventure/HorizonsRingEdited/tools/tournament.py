"""In-pool sixty-card tournament lists for Shandalar's challengers."""
from collections import Counter

LISTS = [
    ('BR Goblins','BR', "Goblin Champion;Carrion Feeder;Putrid Goblin;Battle-Scarred Goblin;Moria Marauder;Goblin Matron;Munitions Expert;Sling-Gang Lieutenant;Pashalik Mons;Firebolt"),
    ('UR Tempo','UR', "Dragon's Rage Channeler;Faerie Seer;Counterspell;Unholy Heat;Firebolt;Lava Dart;Murktide Regent;Seasoned Pyromancer;Man-o'-War;Fact or Fiction"),
    ('GW Food','WG', "Meriadoc Brandybuck;Many Partings;Samwise Gamgee;Rosie Cotton of South Lane;Peregrin Took;Mushroom Watchdogs;Eastfarthing Farmer;Generous Ent;Stew the Coneys;Reprieve"),
    ('RW Modular','WR', "Arcbound Mouser;Arcbound Prototype;Zabaz, the Glimmerwasp;Barbed Spike;Arcbound Javelineer;Arcbound Tracker;Arcbound Shikari;Arcbound Slasher;Unholy Heat;Blacksmith's Skill"),
]
def tournament_deck(builder, variant, number):
    from build_plane import BITS
    title,colors,cards=LISTS[(number+variant)%len(LISTS)]
    spells=Counter(dict(zip(cards.split(';'),[4,4,4,4,4,4,3,3,3,3])))
    mask=sum(BITS[c] for c in colors)
    assert all(n in builder.legal and not builder.legal[n].mask & ~mask for n in spells),title
    spells.update(builder.lands(mask,24,spells))
    return title,spells
