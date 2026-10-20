#!/bin/sh
# Tests for tools/fastboot-guard.sh with a fake fastboot that records its arguments.
set -u
here=$(cd "$(dirname "$0")" && pwd)
guard="$here/../tools/fastboot-guard.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf '#!/bin/sh\necho "$@" > "%s/called"\n' "$tmp" > "$tmp/fastboot"
chmod +x "$tmp/fastboot"
export FASTBOOT="$tmp/fastboot"
fail=0

allowed() {
    rm -f "$tmp/called"
    if sh "$guard" "$@" >/dev/null 2>&1 && [ -f "$tmp/called" ]; then :; else echo "FAIL: should run: $*"; fail=1; fi
}
refused() {
    rm -f "$tmp/called"
    if sh "$guard" "$@" >/dev/null 2>&1 || [ -f "$tmp/called" ]; then echo "FAIL: should refuse: $*"; fail=1; fi
}

allowed boot boot-insecure.img
allowed getvar version
allowed devices
allowed reboot
refused flash boot boot.img
refused erase userdata
refused oem unlock
refused -w
refused shell
allowed --i-understand flash boot boot.img
allowed --i-understand oem unlock
refused --i-understand flash bootloader bootloader.img
refused --i-understand flash xloader xloader.img
refused --i-understand erase fpga
refused boot bootloader

[ "$fail" -eq 0 ] && echo "fastboot-guard: all tests passed"
exit "$fail"
