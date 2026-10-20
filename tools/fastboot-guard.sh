#!/bin/sh
# fastboot wrapper that allows only RAM-only and read-only commands.
#
#   fastboot-guard.sh [--i-understand] [-s SERIAL] COMMAND [ARGS...]
#
# flash/erase/format/oem need --i-understand, and flash/erase/format only
# accept the partitions in WRITABLE. bootloader, xloader and fpga can never
# be written: no public way to recover a Glass with them damaged is known.
# update/flashall are always refused, because what they write depends on
# the zip and the fastboot version, and the XE24 zip contains bootloader,
# xloader and fpga.
set -eu

FASTBOOT=${FASTBOOT:-fastboot}
WRITABLE="boot recovery system cache userdata"

understood=0
if [ "${1:-}" = "--i-understand" ]; then
    understood=1
    shift
fi
serial=""
if [ "${1:-}" = "-s" ]; then
    [ $# -ge 2 ] || { echo "usage: -s needs a serial" >&2; exit 2; }
    serial=$2
    shift 2
fi
[ $# -ge 1 ] || { echo "usage: $0 [--i-understand] [-s SERIAL] COMMAND [ARGS...]" >&2; exit 2; }

# fastboot accepts options anywhere on the line (-w wipes after any command).
for arg in "$@"; do
    case "$arg" in
        bootloader|xloader|fpga|bootloader:*|xloader:*|fpga:*)
            echo "refused: never write or erase the $arg partition" >&2; exit 1 ;;
        -*) echo "refused: option '$arg' is not allowed through the guard" >&2; exit 1 ;;
    esac
done

case "$1" in
    boot|getvar|devices|reboot|continue) ;;
    flash|erase|format)
        if [ "$understood" -ne 1 ]; then
            echo "refused: '$1' changes the device; test with 'boot' first, then rerun with --i-understand" >&2
            exit 1
        fi
        case " $WRITABLE " in
            *" ${2:-} "*) ;;
            *) echo "refused: '$1 ${2:-}': only $WRITABLE may be written" >&2; exit 1 ;;
        esac ;;
    oem)
        if [ "$understood" -ne 1 ]; then
            echo "refused: 'oem' changes the device; rerun with --i-understand" >&2
            exit 1
        fi ;;
    *)
        echo "refused: command '$1' is not allowed through the guard" >&2
        exit 1 ;;
esac

if [ -n "$serial" ]; then
    set -- -s "$serial" "$@"
fi
echo "+ $FASTBOOT $*"
exec "$FASTBOOT" "$@"
