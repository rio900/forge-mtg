#!/bin/zsh
set -eu
plane=${0:A:h}
root=${plane:h:h:h}
mobile=( "$root"/forge-gui-mobile*.jar )
work=$(mktemp -d "${TMPDIR:-/tmp}/avatar-launch.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
classes="$work/classes"
mkdir -p "$classes"
export_asm=( --add-exports java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED )
javac "${export_asm[@]}" -encoding UTF-8 -cp "$mobile[1]" -d "$classes" "$plane"/tools/chaos/{PrepareLauncher,AvatarStarters}.java
java "${export_asm[@]}" -cp "$classes" PrepareLauncher "$mobile[1]" "$classes"
opens=()
for package in java.desktop/{java.beans,javax.swing.border,javax.swing.event,sun.swing,java.awt.image,java.awt.color,sun.awt.image,javax.swing,java.awt,java.awt.font} java.base/{java.util,java.lang,java.lang.reflect,java.text,jdk.internal.misc,sun.nio.ch,java.nio,java.math,java.util.concurrent,java.net}; do
    opens+=( --add-opens "$package=ALL-UNNAMED" )
done
cd "$root"
classpath="$classes:$mobile[1]"
entry=forge.app.Main
case "${1:-}" in
    --verify-chaos|--verify-chaos-menu)
        testmode=$1
        shift
        cd "$work"
        mkdir -p home user/adventure user/preferences decks cache
        ln -s "$root/res" res
        printf 'userDir=%s/user\ncacheDir=%s/cache\ndecksDir=%s/decks\n' "$PWD" "$PWD" "$PWD" > forge.profile.properties
        echo '{"plane":"AvatarEdited"}' > user/adventure/settings.json
        opens+=( "-Duser.home=$PWD/home" )
        if [[ "$testmode" == --verify-chaos ]]; then
            desktop=( "$root"/forge-gui-desktop*.jar )
            classpath="$classpath:$desktop[1]"
            entry=AvatarStarterProbe
            opens+=( -Djava.awt.headless=true )
        else
            entry=AvatarMenuProbe
        fi
        javac -encoding UTF-8 -cp "$classpath" -d "$classes" "$plane/tools/TestProfile.java" "$plane/tools/chaos/$entry.java"
        ;;
esac
java -Xmx4096m "${opens[@]}" -Dio.netty.tryReflectionSetAccessible=true -Dfile.encoding=UTF-8 -cp "$classpath" "$entry" "$@"
