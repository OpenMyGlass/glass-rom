#!/bin/sh
# fastboot wrapper that allows only RAM-only and read-only commands.
# flash/erase/format/oem need --i-understand, and bootloader, xloader and
# fpga are refused always: no public way to recover a Glass with them damaged.
set -eu

FASTBOOT=${FASTBOOT:-fastboot}
understood=0
if [ "${1:-}" = "--i-understand" ]; then
    understood=1
    shift
fi
[ $# -ge 1 ] || { echo "usage: $0 [--i-understand] COMMAND [ARGS...]" >&2; exit 2; }

for arg in "$@"; do
    case "$arg" in
        bootloader|xloader|fpga|bootloader:*|xloader:*|fpga:*)
            echo "refused: never write or erase the $arg partition" >&2
            exit 1 ;;
    esac
done

case "$1" in
    boot|getvar|devices|reboot|continue) ;;
    flash|erase|format|oem|flashing|update|flashall|-w)
        if [ "$understood" -ne 1 ]; then
            echo "refused: '$1' changes the device; test with 'boot' first, then rerun with --i-understand" >&2
            exit 1
        fi ;;
    *)
        echo "refused: unknown command '$1'" >&2
        exit 1 ;;
esac

echo "+ $FASTBOOT $*"
exec "$FASTBOOT" "$@"
