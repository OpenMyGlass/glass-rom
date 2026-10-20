# glass-rom

Tools to build a cloud-free, debloated system for Google Glass Explorer Edition on its final firmware, XE24, **from the owner's own copy of Google's factory image**. Part of [OpenMyGlass](https://github.com/OpenMyGlass/OpenMyGlass).

## What this repository contains, and what it does not

- It contains scripts, patches and package lists, all GPL-3.0.
- It contains **no Google files**: no images, APKs, libraries or anything extracted from them. The scripts download the factory image from Google, check its SHA-256 and work on it locally. Precedent: LineageOS `extract-files.sh`.

## Status

Phase 1: fetching and verifying the factory image, plus boot image tools. These cover unpacking and repacking an Android boot image and making an "insecure" boot image (root adb) from the stock one. Google's rooted XE24 `boot.img` is no longer downloadable. Nothing here has been run on hardware yet.

## Usage

```sh
tools/fetch-factory.sh factory/                       # download and verify (442 MB)
tools/make_insecure_boot.py factory/boot.img out/boot-insecure.img [--kernel zImage]
tools/fastboot-guard.sh boot out/boot-insecure.img    # RAM only: nothing is written
```

`tools/bootimg.py info|unpack|pack` handles any Android v0 boot image. The stock XE24 `boot.img`, unpacked and repacked, comes out byte-identical.

**Untested on hardware:** this boot image only changes `default.prop` (`ro.secure=0`, `ro.adb.secure=0`, `ro.debuggable=1`). If the stock XE24 `adbd` was built to always drop root, as KitKat `user` builds usually are, `adb root` will still be refused. A patched `adbd` is then needed, which is a later step.

## Safety

- Every device step is opt-in, run by the owner, and printed before it runs.
- Boot tests use `fastboot boot` (RAM only, nothing written) before any `fastboot flash`.
- `tools/fastboot-guard.sh` lets through only RAM-only and read-only commands. Writes need `--i-understand` and are limited to `boot`, `recovery`, `system`, `cache` and `userdata`. It always refuses `bootloader`, `xloader`, `fpga`, `update`, `flashall` and options such as `-w`. Use it instead of calling `fastboot` directly. No public way to recover a Glass with those damaged is known.
- `fastboot oem unlock` wipes user data.

## Factory image

XE24 (`glass_1-img-5585826`), published by Google:

| | |
|---|---|
| URL | `https://storage.googleapis.com/support-kms-prod/bTh25b2gcZx5f7apQdJU3lULYTTBoZDHqdsr` |
| Size | 442,720,482 bytes |
| SHA-256 | `76a9d3822077e993bba62c586e5e7cbb1217a81171d78033ff7c06ba285f2363` |
| SHA-1 (as listed by Google) | `46430bc827267796566f0a73d9b503059759561c` |

## Related

- Kernel: [OpenMyGlass/glass-kernel](https://github.com/OpenMyGlass/glass-kernel) (GPL-2.0-only).
- Reference: [Lasimeri/glass-xec-mainline](https://github.com/Lasimeri/glass-xec-mainline), whose safety tooling (partition allowlist, backups) we follow.
