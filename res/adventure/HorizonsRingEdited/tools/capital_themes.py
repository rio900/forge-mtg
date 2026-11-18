"""Capital specializations designed for MH1/MH2/MH3/LTR/2XM.

Keep map/shop IDs stable, but replace legacy tiny tribes and off-color guilds.
Every theme is selected from the whole permitted pool, without unrelated filler.
"""
import re


def creature(c):
    return 'Creature' in c.kinds


def artifact(c):
    return 'Artifact' in c.kinds


def magic(c):
    return bool(c.kinds & {'Instant', 'Sorcery', 'Enchantment'})


def champions(c):
    return 'Legendary' in c.types or 'Planeswalker' in c.kinds or (creature(c) and c.cost >= 3)


def allies(c):
    return bin(c.mask).count('1') > 1 or artifact(c)


def arsenal(c):
    return artifact(c) and (creature(c) or bool(c.tribes & {'equipment', 'vehicle'}))


THEMES = {
    'creatures': ('Существа пяти миров', creature),
    'artifacts': ('Реликвии и механизмы', artifact),
    'magic': ('Чары и заклинания', magic),
    'champions': ('Герои и великие существа', champions),
    'allies': ('Союзы и реликвии', allies),
    'arsenal': ('Арсенал и артефактные существа', arsenal),
    'wild': ('Чудовища и дикие звери', lambda c: creature(c) and not bool(c.tribes & {'human', 'elf', 'druid', 'shaman'})),
    'army': ('Люди, солдаты и рыцари', lambda c: bool(c.tribes & {'human', 'soldier', 'knight'})),
    'mages': ('Маги, плуты и лазутчики', lambda c: bool(c.tribes & {'wizard', 'rogue', 'ninja', 'faerie', 'merfolk'})),
    'undead': ('Нежить: скелеты, зомби, вампиры и духи', lambda c: bool(c.tribes & {'skeleton', 'zombie', 'vampire', 'spirit'})),
    'horde': ('Гоблины, орки и воины', lambda c: bool(c.tribes & {'goblin', 'orc', 'dwarf', 'berserker', 'warrior'})),
    'grove': ('Эльфы, друиды и шаманы', lambda c: bool(c.tribes & {'elf', 'druid', 'shaman'})),
    'lands': ('Небазовые земли', lambda c: 'Land' in c.kinds and 'Basic' not in c.types),
    'enchanted': ('Существа и чары', lambda c: creature(c) or 'Enchantment' in c.kinds),
}

TRIBAL = {'White': 'army', 'Blue': 'mages', 'Black': 'undead', 'Red': 'horde', 'Green': 'grove'}
GUILDS = {'Azorius', 'Dimir', 'Rakdos', 'Gruul', 'Selesnya', 'Orzhov', 'Izzet', 'Golgari', 'Boros', 'Simic'}


def theme_for(base, color):
    if re.fullmatch(color + '[1-6]', base):
        return ('creatures', 'artifacts', 'champions', 'magic', 'allies', 'enchanted')[int(base[-1])-1]
    if base in GUILDS or re.fullmatch('[WUBRG]{3,5}', base) or base.startswith('Multicolor'):
        return 'allies'
    if base.startswith('Land'): return 'lands'
    if base.startswith(('Artifact', 'Wand', 'Phyrexian')): return 'artifacts'
    if base.startswith('Vehicle'): return 'arsenal'
    if base.startswith(('Legend', 'Planeswalker', 'Gods')): return 'champions'
    if base.startswith(('Instant', 'Enchantment')): return 'magic'
    if base.startswith('Creature'): return 'creatures'
    if base.startswith(('Angel', 'Bird', 'Eldrazi', 'SmallCats', 'Sphinx', 'Mutants',
                        'Demon', 'Spiders', 'Devil', 'Dinosaur', 'Dragon', 'Minotaur',
                        'Ogre', 'Wolf', 'Hydra', 'Insects', 'Shapeshifter', 'Squirrel')):
        return 'wild'
    return TRIBAL[color]


def selection(builder, base, color):
    theme = theme_for(base, color)
    label, predicate = THEMES[theme]
    entries = {(n, ed) for n, ed, mask in builder.shop_prints
               if not builder.db[n].removed and predicate(builder.db[n])}
    return label, entries
