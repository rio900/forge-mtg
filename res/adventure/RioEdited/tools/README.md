# RioEdited для MTG Forge Adventure

Выберите RioEdited в настройках Adventure, создайте новую кампанию и выберите Standard, Constructed, Pile или Commander. Мир, задания и прогрессия взяты из Shandalar. Мод рассчитан на установленную сборку Forge 2.0.16-SNAPSHOT-11.08 и использует её ресурсы common.

## Карточный пул и колоды

Разрешены DMU, BRO, NEO, MID, VOW, SNC, ONE, MOM, MAT, WOE и AFR. Для готовых колод указаны имя, издание и номер иллюстрации каждой карты. 464 противника включают 40 боссов. У 38 противников несколько вариантов колоды. Отдельно обработаны вторая стадия Goblin Pack и прямые ссылки из карт подземелий. Итоговые 576 боевых колод записаны в формате DCK. Во время игры генератор мода не нужен.

Соответствие прежних и новых путей, включая происхождение турнирных колод, указано в [enemy-mapping.tsv](enemy-mapping.tsv). 17 назначений используют списки 13 участников чемпионата мира 2023 года. Остальные опираются на исходные карты, цвета, типы существ, стоимость заклинаний и роль противника. Для Emrakul собрана бесцветная колода, которая наращивает ману под Cityscape Leveler и Portal to Phyrexia. У Слобада бой до одной победы из-за ошибки Forge при подготовке следующей партии на фабрике. В обычных городах одна таверна и три торговца. У продавца одиночных карт три обычные и одна необычная карта, у продавца бустеров один пакет. В городах пустошей третья лавка продаёт снаряжение, в остальных — земли. При загрузке старого мира у ранее посещённых городов меняется ключ локального состояния, поэтому могут сброситься местные покупки и флаги.

Сохранены параметры жизни, сложности, ИИ, экипировки, появления исходных противников. Результаты боёв зависят от новых составов. [Колоды чемпионата](https://mtg-jp.com/coverage/mtgwc29th/decklist/0037242/)

У Standard есть 30 фиксированных стартов для NEO, VOW, SNC, WOE, AFR и MAT. Старт MAT дополняется картами MOM. Остальные пять изданий используют пакеты установленной игры. Для Constructed подготовлены 15 колод, для Pile — 15 шаблонов, для Commander — пять колод с командиром. Таблица фиксированных стартов Standard общая для четырёх сложностей.

Слоты BRR, MUL и WOT заменены картами основного выпуска. Draft и Sealed получают блоки Rio для десяти выпусков с полноценными бустерами. MAT доступен в колодах и общем пуле. Для Jumpstart-событий указаны четыре штатных блока. Торговцы и задания с альбомами земель открывают издания разрешённого пула. Если в колоде противника отсутствует требуемая редкость, соответствующий трофей выбирается из общего пула с исходной редкостью. Исправления пустых условий перечислены в [encounter-rewards.json](encounter-rewards.json). Полный перечень именных наград приведён в [reward-mapping.tsv](reward-mapping.tsv).

## Границы кампании

Chaos и импорт Custom управляются штатным клиентом и могут добавить карты из других выпусков. Doppelganger по правилам Shandalar способен копировать колоду игрока. Существующие сохранения могут содержать ранее полученные карты, товары, альбомы земель или события. Эффекты экипировки, эмблемы боссов, токены и карты, созданные эффектом во время боя, остаются игровыми объектами Shandalar. Например, экипированный предмет Black Lotus может создать перманент на поле боя. Награда со свитка, напротив, выдаёт карту из разрешённого выпуска.

## Воспроизведение проверок

Для проверки нужны Java 21, Python 3, оба JAR из этой сборки и отдельный профиль. Пример для macOS и zsh. Начните в папке res.

```sh
resources="$PWD"
mobile=( "$resources"/../forge-gui-mobile*.jar )
desktop=( "$resources"/../forge-gui-desktop*.jar )
scratch=$(mktemp -d)
cd "$scratch"
mkdir -p home user cache decks
ln -s "$resources" res
printf 'userDir=%s/user\ncacheDir=%s/cache\ndecksDir=%s/decks\n' "$PWD" "$PWD" "$PWD" > forge.profile.properties
toolsdir="$resources/adventure/RioEdited/tools"
cp_jars=".:${mobile[1]}:${desktop[1]}"
javac -d . -cp "$cp_jars" "$toolsdir"/{ExportCardIndex,VerifyPlane,Starts}.java
python3 "$toolsdir/check_resources.py" --loot "$PWD/loot.tsv"
java -Xmx3g -Duser.home="$PWD/home" -Djava.awt.headless=true -cp "$cp_jars" VerifyPlane loot.tsv
java -Xmx3g -Duser.home="$PWD/home" -Djava.awt.headless=true -cp "$cp_jars" Starts RioEdited true
java -Xmx3g -Duser.home="$PWD/home" -Djava.awt.headless=true -cp "$cp_jars" Starts RioEdited false
```

VerifyPlane проверяет содержимое DCK после загрузки, печати карт в наградах, магазины, допустимые блоки, бустеры и земли в редакторе. Варианты оформления карт проверяются двумя запусками Starts. Для ручной проверки после обновления создайте новый мир, получите задание, войдите в подземелье, завершите бой и загрузите сохранение после перезапуска.

## Обновление сетов и Forge

1. Сохраните копию RioEdited. Измените allowedEditions, starterEditions и starterEditionNames в config.json. Проверьте defaultBasicLandSet, starterDecksByEdition и штатные Jumpstart-пакеты нового состава.
2. В отдельном профиле из примера экспортируйте актуальные правила и пересоберите ресурсы. Аргумент экспортера должен совпадать с allowedEditions.
3. При удалении выпуска замените его карты в турнирных списках, стартовых и пяти вручную подготовленных колодах, а также в списках ключевых карт боссов и земель build_plane.py. При добавлении выпуска проверьте его имя в BOOK_SETS, слоты бонусного листа, поддержку Draft и Jumpstart. Для малого выпуска без обычного бустера обновите PACKS. Обновите локальные названия альбомов и награды с ними, если их выпуск больше не используется.
4. Сверьте обновлённую таблицу enemy-mapping.tsv с прежней и удалите устаревшие файлы по этой разнице. Проверьте оставшиеся overrides editions, blockdata и maps. При обновлении Forge повторно сравните местные world и languages с Shandalar, выполните обе проверки и испытайте новую кампанию. Генератор берёт исходники противников и карт из common, магазинов из Shandalar и пишет только в RioEdited.

```sh
codes=$(python3 -c 'import json;print(",".join(json.load(open("res/adventure/RioEdited/config.json"))["allowedEditions"]))')
java -Xmx3g -Duser.home="$PWD/home" -Djava.awt.headless=true -cp "$cp_jars" ExportCardIndex index.tsv "$codes"
python3 "$toolsdir/build_plane.py" index.tsv
python3 "$toolsdir/check_resources.py" --loot loot.tsv
```

[Результаты испытаний](validation.md) · [Перечень файлов и их назначение](manifest.tsv)
