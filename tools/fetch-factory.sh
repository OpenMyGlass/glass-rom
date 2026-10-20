#!/bin/sh
# Download Google's XE24 factory image into DIR, verify it, and extract the
# images these tools use. bootloader, xloader and fpga are never extracted.
set -eu

URL=https://storage.googleapis.com/support-kms-prod/bTh25b2gcZx5f7apQdJU3lULYTTBoZDHqdsr
SHA256=76a9d3822077e993bba62c586e5e7cbb1217a81171d78033ff7c06ba285f2363
ZIP=glass_1-img-5585826.zip

[ $# -eq 1 ] || { echo "usage: $0 DIR" >&2; exit 2; }
mkdir -p "$1"
cd "$1"

if [ -f "$ZIP" ] && [ "$(shasum -a 256 "$ZIP" | cut -d' ' -f1)" = "$SHA256" ]; then
    echo "$ZIP already downloaded"
else
    curl -fL -C - -o "$ZIP" "$URL"
fi
actual=$(shasum -a 256 "$ZIP" | cut -d' ' -f1)
if [ "$actual" != "$SHA256" ]; then
    echo "error: $ZIP has SHA-256 $actual, expected $SHA256; delete it and retry" >&2
    exit 1
fi
unzip -oq "$ZIP" boot.img recovery.img system.img android-info.txt
echo "verified XE24 factory image; extracted boot.img recovery.img system.img into $PWD"
