#!/bin/zsh
set -eu
plane=${0:A:h}
cd "$plane/../../.."
mobile=( "$PWD"/forge-gui-mobile*.jar )
classes=$(mktemp -d "${TMPDIR:-/tmp}/horizons-launch.XXXXXX")
trap 'rm -rf -- "$classes"' EXIT
javac -encoding UTF-8 -cp "$mobile[1]" -d "$classes" "$plane/tools/chaos/RioChaos.java"
# Classpath launch needs the module opens normally supplied by the Forge JAR manifest.
opens=()
for package in java.desktop/{java.beans,javax.swing.border,javax.swing.event,sun.swing,java.awt.image,java.awt.color,sun.awt.image,javax.swing,java.awt,java.awt.font} java.base/{java.util,java.lang,java.lang.reflect,java.text,jdk.internal.misc,java.nio,java.math,java.util.concurrent,java.net}; do
    opens+=( --add-opens "$package=ALL-UNNAMED" )
done
java -Xmx4096m "${opens[@]}" -Dio.netty.tryReflectionSetAccessible=true -Dfile.encoding=UTF-8 -cp "$classes:$mobile[1]" forge.app.Main "$@"
