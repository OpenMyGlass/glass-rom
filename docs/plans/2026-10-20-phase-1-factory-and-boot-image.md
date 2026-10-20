# Phase 1: Factory image and boot image tools — Plan

**Goal:** From the owner's download of the XE24 factory zip, produce `boot-insecure.img`: the stock kernel and ramdisk, with `ro.secure=0`, `ro.adb.secure=0` and `ro.debuggable=1`. Optionally use a kernel from glass-kernel instead of the stock one. Everything is hardware-free and testable without Google files.

## Constraints
- No Google files in git, in test fixtures or in CI artifacts. Tests build synthetic boot images.
- Python 3 standard library only (`struct`, `gzip`, `hashlib`), so it runs on macOS and Linux without extra packages.
- GPL-3.0. English.

## Tasks
1. `tools/fetch-factory.sh DIR`: download to DIR (resumable `curl -C -`), verify the SHA-256 from the README, refuse on mismatch, then extract only `boot.img`, `system.img`, `recovery.img` and `android-info.txt`. It never extracts or uses bootloader/xloader/fpga.
2. `tools/bootimg.py` (`unpack`, `pack`, `info`): Android boot image header v0. Fields: magic, kernel/ramdisk/second size and addr, tags addr, page size, name, cmdline, id. Page-aligned sections; `id` = SHA-1 over the sections and their sizes, as mkbootimg computes it. Tests: the pack → unpack round trip is byte-identical; unpack → pack of a synthetic image reproduces it exactly; a bad magic or truncated file is rejected.
3. `tools/ramdisk.py`: read and write gzip-compressed cpio `newc`, preserving entry order, modes and the trailer; edit `default.prop` key=value lines. Tests on a synthetic ramdisk: an unchanged round trip is identical; edits replace existing keys and append missing ones; no other entry changes.
4. `tools/make-insecure-boot.sh FACTORY_DIR OUT [--kernel zImage]`: combines tasks 2 and 3. Local acceptance against the real image (not in CI): unpacking and repacking the stock `boot.img` without edits must reproduce it byte for byte, which proves the tool understands the format.
5. `tools/fastboot-guard.sh`: a wrapper that only allows `boot`, `getvar`, `devices`, `reboot` and `continue` (with an optional `-s SERIAL`). `flash`, `erase`, `format` and `oem` need `--i-understand`, and writes are limited to boot/recovery/system/cache/userdata. It always refuses bootloader/xloader/fpga, `update`, `flashall` and any other option (`-w` wipes after any command).
6. CI: GitHub Actions runs the unit tests and `shellcheck`.

## Done when
CI is green, and the stock boot.img round trip is byte-identical locally.
