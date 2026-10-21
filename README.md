# glass-rom

Tools to build a cloud-free, debloated system for Google Glass Explorer Edition on its final firmware, XE24, **from the owner's own copy of Google's factory image**. Part of [OpenMyGlass](https://github.com/OpenMyGlass/OpenMyGlass).

## What this repository contains, and what it does not

- It contains scripts, patches and package lists, all GPL-3.0.
- It contains **no Google files**: no images, APKs, libraries or anything extracted from them. The scripts download the factory image from Google, check its SHA-256 and work on it locally. Precedent: LineageOS `extract-files.sh`.

## Status

Phase 2: an offline inventory of the system apps plus a draft debloat list. See [`docs/xe24-packages.md`](docs/xe24-packages.md) and [`debloat/xe24-packages.tsv`](debloat/xe24-packages.tsv): 37 keep, 3 remove, 5 to check on a device; dependencies in [`docs/xe24-manifests.md`](docs/xe24-manifests.md).

Phase 1: fetching and verifying the factory image, plus boot image tools. These cover unpacking and repacking an Android boot image and making an "insecure" boot image (root adb) from the stock one. Google's rooted XE24 `boot.img` is no longer downloadable. Nothing here has been run on hardware yet.

## Usage

```sh
tools/fetch-factory.sh factory/                       # download and verify (442 MB)
tools/make_insecure_boot.py factory/boot.img out/boot-insecure.img [--kernel zImage --pvr-module pvrsrvkm_sgx540_120.ko]
tools/fastboot-guard.sh boot out/boot-insecure.img    # RAM only: nothing is written
```

Inventory (needs `debugfs` from e2fsprogs and `aapt2` from the Android SDK build-tools):

```sh
tools/sparse.py factory/system.img factory/system.raw
tools/inventory.py factory/system.raw factory/inventory.json
tools/check_debloat.py factory/inventory.json debloat/xe24-packages.tsv
tools/render_packages.py factory/inventory.json debloat/xe24-packages.tsv docs/xe24-packages.md
```

Vendor extraction (needs `debugfs`; takes the raw system image from above):

```sh
tools/extract_vendor.py factory/system.raw $AOSP/device/glass/glass-1/proprietary-files.txt $AOSP/vendor/glass/glass-1
```

The output contains Google binaries and stays on the owner's machine.

A kernel from [glass-kernel](https://github.com/OpenMyGlass/glass-kernel) needs the GPU module from the same build (the `kernel-<variant>` CI artifact holds both `zImage` and `pvrsrvkm_sgx540_120.ko`). The stock XE24 module does not load into the `tuned` and `tuned-stable` kernels: 90 CRCs of the symbols it imports differ. `--pvr-module` puts our module in the ramdisk at `/lib/modules/pvrsrvkm_sgx540_120.ko` and changes the one `insmod /system/lib/modules/pvrsrvkm_sgx540_120.ko` line of `init.omap4430.rc` to load it from there. It refuses a file that is not a kernel module of DDK `1.9@2166536` (the build of XE24's user-space libraries), refuses the stock module itself, and fails if any `.rc` file still names the stock path. `--kernel` without `--pvr-module` is refused; `--keep-stock-pvr` overrides that, for glass-kernel's `stock` variant only, whose CRCs match the stock module's.

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
