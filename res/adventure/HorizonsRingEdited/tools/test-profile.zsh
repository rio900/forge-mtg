#!/bin/zsh
set -eu
toolsdir=${0:A:h}
resources=${toolsdir:h:h:h}
scratch=$(mktemp -d "${TMPDIR:-/tmp}/horizons-forge.XXXXXX")
cd -P "$scratch"
mkdir -p home user/adventure user/preferences decks cache
ln -s "$resources" res
printf 'userDir=%s/user\ncacheDir=%s/cache\ndecksDir=%s/decks\n' "$PWD" "$PWD" "$PWD" > forge.profile.properties
echo '{"plane":"HorizonsRingEdited"}' > user/adventure/settings.json
mobile=( "$resources"/../forge-gui-mobile*.jar )
desktop=( "$resources"/../forge-gui-desktop*.jar )
cp_jars=".:$mobile[1]:$desktop[1]"
print "Тестовый профиль $PWD"
javac -encoding UTF-8 -cp "$cp_jars" -d . "$toolsdir"/*.java "$toolsdir/chaos/RioChaos.java"
run=( java -Xmx3g "-Duser.home=$PWD/home" -Djava.awt.headless=true -cp "$cp_jars" )
case ${1:-check} in
  check)
    python3 "$toolsdir/check_resources.py" --loot loot.tsv
    "${run[@]}" Audit
    for variants in true false; do
      "${run[@]}" Starts HorizonsRingEdited "$variants"
      "${run[@]}" VerifyPlane loot.tsv "$variants"
    done
    "${run[@]}" Events
    "${run[@]}" ChaosProbe
    ;;
  build)
    "${run[@]}" ExportCardIndex index.tsv MH1,MH2,LTR,MH3,2XM
    python3 -B "$toolsdir/build_plane.py" index.tsv
    python3 "$toolsdir/check_resources.py"
    ;;
  pilot)
    java -Xmx3g "-Duser.home=$PWD/home" -Djava.awt.headless=true -jar "$desktop[1]" sim -D "$toolsdir/../decks/pilot" -t RoundRobin -s 917
    ;;
  play)
    java -Xmx3g "-Duser.home=$PWD/home" --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.nio=ALL-UNNAMED --add-opens java.desktop/java.awt=ALL-UNNAMED -cp "$cp_jars" Playthrough
    ;;
  *) print -u2 'Используйте check, build, pilot или play'; exit 2 ;;
esac
