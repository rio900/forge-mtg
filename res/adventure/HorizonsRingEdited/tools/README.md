# HorizonsRingEdited

Для старта **Chaos** на macOS откройте [HorizonsRingEdited.command](../HorizonsRingEdited.command), выберите **HorizonsRingEdited** в настройках Adventure и начните новое приключение. Запуск требует JDK 21. Chaos случайно выбирает цветовой шаблон текущей сложности и собирает 60 карт с печатями MH1, MH2, MH3, LTR и 2XM. Обычный запуск Forge использует прежний генератор Chaos. Для закрытой кампании при любом запуске также подходят Standard, Constructed, Pile и Commander. Отдельная папка Plane содержит карту и сценарии Shandalar, локальные переопределения и готовые деклисты. Генератор нужен только при пересборке.

## Пул и старт

Основной язык заданий HorizonsRingEdited — русский. При английском интерфейсе Forge журнал и сюжетные реплики мода тоже выводятся по-русски. Шесть городских поручений написаны для этого приключения: «Колокол без языка», «Чернила отлива», «Долг погребального огня», «Искра в шлаке», «Память семени» и «Кубок из мифрила». Их предлагают те же городские заказчики, что и другие местные поручения. Исходный русский каталог для пересборки находится в `languages/quests-ru-RU.json`.

MH1, MH2, MH3, LTR и 2XM можно сочетать. Запись DCK содержит количество, имя, код и номер иллюстрации. В именных наградах и Pile Forge принимает имя с кодом и может случайно выбрать оформление внутри выпуска. В случайных наградах действуют фильтры изданий. Цифровые A-варианты карт исключены. У стандартного старта MH1, MH2 и MH3 есть по пять фиксированных одноцветных колод на 40 карт с 17 землями. Бустер MH3 в приключении содержит 15 карт выпуска, включая базовую землю и карту из списка New to Modern. Старт LTR использует штатные полупакеты. Constructed сохраняет пары цветов разных сложностей, Pile случайно наполняет шаблоны, у Commander пять колод на 100 карт.

## Городские магазины

В обычном городе продаются шесть карт из MH1, MH2, MH3, LTR, 2XM и выбранных внешних печатей из [списка Modern](modern-cards.txt). Каждое место разыгрывается независимо. Таблица ниже описывает базовое распределение.

| Места | Цветовая идентичность | Common | Uncommon | Rare | Mythic |
|---|---|---:|---:|---:|---:|
| Три местных | Точно совпадает с городом | 30% | 50% | 18% | 2% |
| Три общих | Любая | 0% | 80% | 19% | 1% |

Для общих мест 99,25% выбора приходится на базовый пул, ещё 0,30% — на Atraxa, Grand Unifier, по 0,15% — на Quantum Riddler, Griselbrand и Sheoldred, the Apocalypse. В местных местах синего города добавка Quantum Riddler составляет 0,50%; в чёрном городе по 0,50% отведено Griselbrand и Sheoldred, the Apocalypse. Карты также могут выпасть из базового пула. Эти добавки относятся только к основной шестикарточной витрине RingTown (в том числе в столицах), а не к специализированным лавкам или наградам.

Итоговый шанс хотя бы одной копии за шесть мест: Atraxa — 0,9387% во всех городах; Quantum Riddler — 2,7094% в синем и 0,4908% в остальных; Griselbrand — 2,7718% в чёрном и 0,4908% в остальных; Sheoldred — 2,5071% в чёрном и 0,4908% в остальных. Проверка по сгенерированным пулам: `python3 -B tools/check_featured_shops.py` из папки Plane.

В базовом пуле выбранные карты из списка Modern получают приоритет внутри своей редкости. Вес Common — 6, Uncommon — 4, Rare и Mythic — 2; вес обычной карты пула — 1. Остатки целочисленного распределения выдаются по наибольшей дробной части, поэтому одинаковые веса различаются максимум на одну копию в пуле. Common выпадают в трёх местных местах.

Для каждой редкости доступны карты любого типа, в том числе в городах с тематикой существ. Бесцветный местный пул включает артефакты и земли с бесцветной идентичностью. Редкости и названия могут повторяться в одной витрине. Обновление за 2 кристалла заново разыгрывает все шесть мест.

Редкость в магазине определяется выбранной печатью. Lightning Bolt (M11) и Monastery Swiftspear (2X2) выпадают как Common в красных городах. Dismember (NPH) и Soul-Guide Lantern (THB) выпадают как Uncommon в общих местах, а также в местных местах чёрных и бесцветных городов соответственно.

В цветном обычном городе четыре торговца: одиночные карты, бустер, базовые земли и небазовые земли. В бесцветном городе остаются три торговца. Базовые земли доступны в неограниченном количестве. Отдельный продавец небазовых земель предлагает одну Common/Uncommon-землю из основных выпусков и с вероятностью 25% добавляет один шокленд цвета города. Каждый из четырёх подходящих шоклендов имеет шанс 6,25% на витрину. Покупка расходует товар.

В каждой столице сохранены 16 торговцев: общая витрина, шесть бустеров, шесть небазовых земель Exotic Lands, семь случайных тематических лавок, три элитных магазина с часами и прежние торговцы базовыми землями/предметами. В каждой тематической витрине шесть карт. Обычные лавки: 55% Common, 40% Uncommon, 4,5% Rare, 0,5% Mythic на место. Элитные: 23,66% Common, 50% Uncommon, 18,18% Rare, 8,16% Mythic на место — итоговый шанс хотя бы одной Rare около 70%, Mythic около 40% за шесть мест. Цветовая идентичность карты включает цвет столицы либо бесцветна. Все товары, кроме базовых земель, имеют конечный запас.

Специализации адаптированы к MH1/MH2/MH3/LTR/2XM и разрешённым дополнительным картам. Белая столица объединяет людей, солдат и рыцарей; синяя — магов, плутов и лазутчиков; чёрная — скелетов, зомби, вампиров и духов; красная — гоблинов, орков и воинов; зелёная — эльфов, друидов и шаманов. Другие темы: реликвии и механизмы; арсенал и артефактные существа; чудовища и дикие звери; чары и заклинания; герои и великие существа; многоцветные союзы и реликвии; небазовые земли. Узкие старые названия заменены соответствующими русскими названиями. Идентификаторы магазинов и расположение сохранены.

Каждый тематический пул содержит все подходящие разрешённые печати без добавления посторонних карт для заполнения редкостей. В каждом есть не менее восьми разных Common и восьми Uncommon; вероятность отдельного названия не превышает 8% на место. Повторы разрешены. Бывший Bob’s Bones теперь содержит 38 названий нежити, вероятность Clattering Augur — 3,4% на место вместо 95%. Проверка: `python3 -B tools/check_capital_themes.py /path/to/card-index.tsv` из папки Plane; индекс должен включать сопутствующий `.prints`.

Forge назначает стоимость обновления при загрузке объекта карты: 2–5 кристаллов у обычных и тематических торговцев, 7 у торговца с меняющейся темой. Флаг noRestock закрывает обновление у постоянных торговцев. Цена карт по редкости до скидок — 50/150/300/500 золотых для Common/Uncommon/Rare/Mythic.

## Столичные арены и боссы

Вход на арену стоит 100 золотых. За победу в третьем раунде выдаются золото, предмет, одна карта базового пула Rare/Mythic (80%/20%) цвета столицы и одна карта из списка дополнительных карт (54). Для последней половина вероятности распределена поровну между картами списка с цветом столицы в идентичности, другая половина — поровну между всеми картами списка. После расчёта двух ветвей вес Atraxa, Grand Unifier, Quantum Riddler, Griselbrand и Sheoldred, the Apocalypse умножается на два, затем весь пул нормализуется. Карты из списка выдаются с указанной печатью.

Дополнительно доступны Moonshadow (ECL, Mythic), Abhorrent Oculus (DSK, Mythic) и Overlord of the Balemurk (DSK, Mythic). Полные сеты ECL/DSK не добавлены. Карты входят в обычные магазины, подходящие столичные специализации, финальные специальные призы арен и специальный пул наград боссов. Персональных бонусов выпадения у этих трёх карт нет; действует общий вес дополнительных карт внутри редкости. За обычную витрину из шести карт шанс Moonshadow и Overlord — по 0,5804% в чёрном городе, Oculus — 0,7857% в синем; в остальных городах — по 0,0416%. Вероятности срабатывания наград арен и боссов не изменены.

У Лилианы Marionette Apprentice дополняет жертвоприношения с Carrion Feeder и Yawgmoth. В колоде также есть Sheoldred, the Apocalypse. Гризельбранд использует Buried Alive, Vile Entomber и Bone Shards, чтобы отправить существ на кладбище, и Goryo’s Vengeance, чтобы вернуть легендарное существо с ускорением.

## Материалы

- [Отчёт об аудите, игровых сценариях и ограничениях](validation.md)
- [Пять пробных колод, деклисты и результаты боёв](pilots.md)
- [576 назначений, исходные и новые темы и заклинания](enemy-mapping.tsv)
- [Планы 40 боссов и ключевые карты](boss-plans.tsv)
- [Замены именных наград](reward-mapping.tsv) и [исправленные пустые условия трофеев](encounter-rewards.json)
- [Четыре турнирных списка для Challenger](tournament.py)

## Воспроизведение

Из этой папки выполните одну из команд. Нужны zsh, Python 3.9+ и JDK 21. Скрипт создаёт новый временный каталог, перенаправляет home, кэш, коллекции и сохранения и выводит путь. Для сборки используются JAR установленной игры. Графический прогон открывает окно Forge.

```sh
zsh test-profile.zsh check
zsh test-profile.zsh pilot
zsh test-profile.zsh play
zsh test-profile.zsh build
```

Команда build восстанавливает производные ресурсы из Shandalar, common, локальной базы карт и таблиц этого Plane. Пять DCK прототипов служат входными данными. При изменении пула FindEmpty перечисляет пустые фильтры врагов. Затем следует пересмотреть замены, вероятности и прогнать check. Только build записывает производные ресурсы мода.


## Encounter balance — 2026-11-17

`encounters.py` is called by `build_plane.py`; rebuilding preserves these rules.
All 40 bosses award two base-set C/U singles (50/50 per draw), one R/M single
(80/20), and independently a 35% chance of one card from the 51-card additions
list. The four featured cards have weight 2, others 1: each featured card has
35% × 2/55 = 1.273% per boss win. No deck-card or parallel named-card rewards
remain on bosses. Gold, items, shards and life rewards are preserved.

Capital arena round 1/2 rewards remain unchanged (including the round-2 rare).
The final awards one base-set R/M (80/20), one guaranteed additions-list card,
and its existing gold/item. Local color weighting is retained; featured weights
are 2 instead of 10. The chance of any of the four featured cards in the special
slot is White 14.42%, Blue 17.31%, Black 22.61%, Red 7.55%, Green 13.94%.
A specific Atraxa has 8.96/6.87/6.96/1.89/8.47% respectively. This is per final
win, not per round. Printed rarities are never changed.

Fourteen enemy names receive small packages (5–10 spell slots), including nine
bosses and the five Master Wizards. Existing deck sizes, difficulty, health and
early enemies are preserved. Masters award two C/U, 10% one R/M and 5% one
additions-list card, preventing their new spells from becoming unlimited loot.
Prowess, blink, reanimation and midrange are adapted to the mod's available pool;
these are not exact tournament decks. No outside sets are enabled.

References consulted: MTGO Modern Challenge 32, November 16, 2026
https://www.mtgo.com/decklist/modern-challenge-32-2026-11-1612858125
and Esper Goryo card package example:
https://mtgdecks.net/Modern/goryo-x27-s-decklist-by-markus-rynner-2976742

All shops retain the previous balance. These are resource-only changes; JARs,
other mods and saves are untouched. Existing saved encounters may retain cached
state; use newly generated encounters for checking these changes.


## Restored capital markets — 2026-11-17

All five capitals again have 16 original vendor objects: the main six-card
counter, booster and nonbasic-land counter, seven random themed counters,
three rotating counters, and the original basic-land/items/equipment merchants.
Positions and object IDs match common maps. Theme pools and rotation lists
are preserved; invalid upstream Instant6* / Shapeshifters references are
resolved to existing Instant4* / Shapeshifter stores.

CapitalSmall* shop variants cap small counters at two singles; premium-only
counters retain their one-card limit and booster counters offer one pack.
Mixed rarity pools retain 50/40/9/1 C/U/R/M (missing rarity goes to the lowest
available rarity); no more than one guaranteed premium slot per counter.
Stock is finite. Map restock categories retain engine prices: 2/3/4/5 crystals,
rotating stores 7. The six-card main counter still costs 2 crystals to refresh.
Ordinary towns, arena/boss rewards and enemy decks are unchanged by this update.


## Six-card capital counters — revised at user request

This supersedes the one/two-card limits above. All 155 CapitalSmall single-card
variants now draw SIX cards independently from decks/shop/capital. The five
booster variants still sell one booster. The 16 vendor positions per capital,
restock prices and the main six-card counter are unchanged.

Base slot weights: C 55%, U 40%, R 4.5%, M 0.5%. Thus a full pool has
26.4908% chance of at least one R/M and 2.9627% chance of at least one M across
six draws. Duplicates are allowed. Missing rarity weight goes to the lowest
available rarity, never into higher rarities. Mixed-rarity artwork retains
matched art weights; unsupported excess rare weight also goes to C/U.

Previously premium-only pools receive C/U support: same-color cards for
planeswalker shops, multicolor cards for WUBRG. Premium cards keep their printed
rarity. Existing mixed specialist pools keep their card themes. Generating capital
variants is idempotent and does not alter original non-capital shop definitions.
Implementation: capital_shops.py, called by capital_shop_variants(builder).


## Clock-shop premium (7-crystal refresh)

Capital shop variants referenced by the maps' `rotation` properties use
30% C / 50% U / 18% R / 2% M for each of six independent draws. Other small
capital shops retain 55/40/4.5/0.5. The existing 7-crystal engine refresh category
and all vendor locations are unchanged. There are 30 rotating stock variants:
28 have all four rarities; two lack mythics and use 32/50/18/0.
Full-pool probabilities per stock: at least one R/M = 73.7856%, at least one M =
11.4158%. Missing rarity weights still transfer down, not up.


## Clock shops: final stock odds (latest user revision)

Supersedes the preceding 18%/2% per-slot settings. The user's targets are separate
stock events: at least one Rare 70%, at least one Mythic 40%, with overlap allowed.
Six independent slots use C/U/R/M 23.66/50/18.18/8.16%. The inverse formula
p=1-(1-P)^(1/6) gives actual stock odds 69.99754% Rare and 39.99447% Mythic
after integer-weight rounding (less than 0.006 percentage point error).
All 30 rotation variants meet both targets. Green3 adds Hexdrinker, Thrasta,
Tempest's Roar and Last March of the Ents; White1 adds Serra the Benevolent
and Serra's Emissary, all at their legal base-set mythic printings. These additions
fill previously missing mythic tiers. Ordinary shops, stock size six, and the
7-crystal refresh category remain unchanged. VerifyPlane asserts both stock
probabilities within 0.01 percentage point for every rotating variant.


## Capital colors, six boosters and Exotic Lands

CapitalSmall<Color>__<theme> variants now bind each themed counter to its actual
capital: colorless cards or color identity containing the capital color. Other
monocolors and multicolor identities without the capital color are excluded.
The main RingTown six-card shop retains its requested three exact-identity local
plus three unrestricted general slots. Boosters retain their normal full-color
set contents. No global color restriction is applied to arena/boss rewards.

Narrow theme pools are preserved where available; missing rarity tiers use
same-color base-set support cards. All 30 clock variants retain the final
70% Rare / 40% Mythic stock odds. Non-clock rarity weighting is unchanged.

All six capital booster definitions (five themed, one main) sell six packs.
CapitalLands<Color> (Exotic Lands) offers six weighted nonbasic lands from allowed
sets and explicitly permitted additions, including relevant shock/tri-lands.
Lands use the same city identity check; colorless utility/fetch lands are allowed.
Ordinary-town booster and land vendors remain unchanged.

There are 191 themed single-card variants, five Exotic Lands variants and six
booster definitions. Original capital object IDs/positions and restock categories
remain. Regeneration removes obsolete generated capital pool files.


## Double Masters (2XM, 2020)

2XM is the fifth base set, alongside MH1/MH2/LTR/MH3. 336 permitted 2XM card
names add 265 new names to the legal base pool. The existing restricted-card list
remains active. Shops, generic rewards, premium boss/arena pools and regenerated
enemy decks draw from the expanded set pool while retaining their rarity weights
and capital color rules. The curated 51-card arena branch remains curated.

Five fixed mono-color Standard starts use 23 cards from 2XM and 17 basic lands
from LTR (2XM has no basics). Draft/sealed also use LTR basic lands. The local
2XM booster preserves 15 cards: 8 C, 3 U, 2 R/M and 2 foil-sheet cards.
Thoughtseize, Flickerwisp and Mishra's Bauble in the curated list now use their
2XM printings, preserving their existing rarities.

Mixed-rarity prints containing Common are excluded from U-or-higher-only slots,
because Forge may reroll artwork within an edition. Other legal prints remain
eligible. JARs, other mods and saves are unchanged.

The existing Mana Crypt restriction is also encoded in every local 2XM booster
sheet selector, including raw event boosters. Chandra's Pyromancer's otherwise
empty Uncommon deck-card reward now draws a red Uncommon from the allowed sets;
its 50% chance and 1–3-card amount are unchanged. Broad reward overrides include
2XM; named and set-specific rewards keep their intended scope.


## Enemy repair after deck review

`enemy_plans.py` provides thirteen reviewed 60-card lists (36 spells/24 lands),
including five formerly identical bosses, Griselbrand, Teferi, Jace, Kiora,
Sliver Queen, Fog Trap, the second Bandit Archer variant and Hellion.
Nissa/Vorinclex are green ramp/counters, Jin-Gitaxias blue draw-control,
Urabrask red attacking spells, and Kozilek colorless mana-ramp/Eldrazi.
Enemy health, difficulty and non-color metadata are unchanged.

Oversized lists are rebuilt to 60 with curve budgets, retained theme/signature
cards and caps on rare/mythic copies. Modern packages and special lands are
preserved during compaction. Multicolor mana bases use fewer tapped bridges
and more basics. High-curve lists lacking early mana receive affordable ramp.
Existing 40–60-card lists remain that size. Final sizes: 569×60, 4×40, 1×58,
1×59 and 1×46 across 576 unique enemy deck references; 212 files changed.

Dependency checks cover Planebound Accomplice/planeswalkers, Godo/equipment,
Dread Return/Persist/Victimize creature targets, and Sylvan Might/creatures.
The 30 Accomplice and 10 Godo unsupported cases found in review are removed.
Enemy generation rejects untested Summoner's Pact/Pact of Negation; player
shops and prizes still offer both. New encounters must pass VerifyPlane's
size, mana-ratio and dependency assertions.

Bandit Archer's empty rare deck-card reward now draws from the permitted red/black
rare pool with the same 50% chance and 1–3-card amount. Boss rewards, shops,
arena pools and starter decks were preserved. Deterministic rebuild checked
926 enemy/map/manifest files. JARs and saves were not modified.

AI smoke tests: 15 matches / 36 games, seeds 2117–2119, normal match life totals.
Group A: Chandra 3–0, Urabrask 2–1, Nissa 1–2, Jin-Gitaxias 0–3.
Group B: Vorinclex 2–0, Griselbrand 1–1, Kozilek 0–2.
Group C: Bandit Archer 3–0, Hellion/Fog Trap/white starter each 1–2.
Kozilek cast mana rocks and large threats; Griselbrand used Goryo's Vengeance
on Griselbrand and Persist on Archon of Cruelty. These tests demonstrate
functionality, not statistically established Adventure win rates or final difficulty.
