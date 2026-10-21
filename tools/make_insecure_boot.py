#!/usr/bin/env python3
"""Make a root-adb ("insecure") boot image from the stock XE24 boot.img.

Usage: make_insecure_boot.py STOCK_BOOT_IMG OUT_IMG [--kernel zImage --pvr-module KO]

--pvr-module without --kernel keeps the stock XE24 kernel; only glass-kernel's `stock`
variant module loads into that (its CRCs match).

The result is meant for `fastboot boot` (RAM only). Nothing is written to the device.

With --pvr-module, the GPU module that glass-kernel built (out/pvrsrvkm_sgx540_120.ko)
goes into the ramdisk at /lib/modules, and init.omap4430.rc loads it from there instead
of the stock module in /system/lib/modules. A kernel other than the stock one needs this:
the stock module does not load into glass-kernel's tuned or tuned-stable kernels.
"""
import argparse
import hashlib
from dataclasses import replace
from pathlib import Path

import bootimg
import ramdisk

INSECURE_PROPS = {"ro.secure": "0", "ro.adb.secure": "0", "ro.debuggable": "1"}

PVR_MODULE = "pvrsrvkm_sgx540_120.ko"
PVR_RC = "init.omap4430.rc"
STOCK_PVR_PATH = f"/system/lib/modules/{PVR_MODULE}"
RAMDISK_PVR_PATH = f"/lib/modules/{PVR_MODULE}"
# The stock XE24 module (docs/xe24-blobs.md). It is Google's: never put it in a test image.
STOCK_PVR_SHA256 = "a4a60b4e3cfd4ff010e9c3300abf484171e5f291b3b7b5fd695f74e3b3e58afc"
# XE24's user-space libraries are this DDK build; the module must be the same one.
PVR_DDK = b"1.9@2166536"
EM_ARM = 40


class PvrModuleError(Exception):
    pass


def check_pvr_module(ko: bytes) -> None:
    """Refuse anything that is not a DDK 1.9@2166536 kernel module built by us."""
    if ko[:4] != b"\x7fELF":
        raise PvrModuleError("GPU module is not an ELF file")
    if len(ko) < 20 or ko[4] != 1 or ko[5] != 1 or int.from_bytes(ko[18:20], "little") != EM_ARM:
        raise PvrModuleError("GPU module is not a 32-bit little-endian ARM ELF file")
    if b"vermagic=" not in ko:
        raise PvrModuleError("GPU module has no vermagic: not a kernel module")
    if PVR_DDK not in ko:
        raise PvrModuleError(f"GPU module is not DDK {PVR_DDK.decode()}, which XE24's libraries need")
    if hashlib.sha256(ko).hexdigest() == STOCK_PVR_SHA256:
        raise PvrModuleError("this is the stock XE24 module; pass the one glass-kernel built")


def use_pvr_module(entries: list, ko: bytes) -> list:
    """Put our GPU module in the ramdisk and make init load it instead of the stock one."""
    check_pvr_module(ko)
    entries = ramdisk.add_file(entries, RAMDISK_PVR_PATH.lstrip("/"), ko)
    entries = ramdisk.replace_line(entries, PVR_RC, f"insmod {STOCK_PVR_PATH}",
                                   f"insmod {RAMDISK_PVR_PATH}")
    left = [e.name for e in entries if e.name.endswith(".rc") and STOCK_PVR_PATH.encode() in e.data]
    if left:
        raise PvrModuleError(f"stock module path still referenced in {', '.join(left)}")
    return entries


def make(stock: bytes, kernel: bytes = None, pvr_module: bytes = None) -> bytes:
    img = bootimg.parse(stock)
    entries = ramdisk.set_props(ramdisk.read(img.ramdisk), INSECURE_PROPS)
    if pvr_module is not None:
        entries = use_pvr_module(entries, pvr_module)
    img = replace(img, ramdisk=ramdisk.write(entries))
    if kernel is not None:
        img = replace(img, kernel=kernel)
    return bootimg.pack(img)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stock")
    ap.add_argument("out")
    ap.add_argument("--kernel", help="zImage to use instead of the stock kernel")
    ap.add_argument("--pvr-module", help=f"our {PVR_MODULE} from the same glass-kernel build")
    ap.add_argument("--keep-stock-pvr", action="store_true",
                    help="with --kernel, keep loading the stock GPU module (only glass-kernel's "
                         "stock variant can load it)")
    args = ap.parse_args(argv)
    if args.kernel and not args.pvr_module and not args.keep_stock_pvr:
        ap.error("--kernel needs --pvr-module: the stock GPU module does not load into a "
                 "tuned kernel (pass --keep-stock-pvr to keep it anyway)")
    if args.pvr_module and args.keep_stock_pvr:
        ap.error("--pvr-module and --keep-stock-pvr exclude each other")
    kernel = Path(args.kernel).read_bytes() if args.kernel else None
    ko = Path(args.pvr_module).read_bytes() if args.pvr_module else None
    try:
        image = make(Path(args.stock).read_bytes(), kernel, ko)
    except (PvrModuleError, ramdisk.RamdiskError) as e:
        # Never leave an image from an earlier run where the owner expects this one.
        Path(args.out).unlink(missing_ok=True)
        ap.exit(1, f"error: {e}; {args.out} was not written\n")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_bytes(image)
    if ko is not None:
        # The module loads only into the kernel it was built with: show its vermagic to compare.
        vermagic = ko.split(b"vermagic=", 1)[1].split(b"\0", 1)[0].decode("latin-1")
        print(f"GPU module vermagic: {vermagic}")
    print(f"wrote {args.out}; test it with: fastboot boot {args.out}")


if __name__ == "__main__":
    main()
