#!/usr/bin/env python3
"""Make a root-adb ("insecure") boot image from the stock XE24 boot.img.

Usage: make_insecure_boot.py STOCK_BOOT_IMG OUT_IMG [--kernel zImage]

The result is meant for `fastboot boot` (RAM only). Nothing is written to the device.
"""
import argparse
from dataclasses import replace
from pathlib import Path

import bootimg
import ramdisk

INSECURE_PROPS = {"ro.secure": "0", "ro.adb.secure": "0", "ro.debuggable": "1"}


def make(stock: bytes, kernel: bytes = None) -> bytes:
    img = bootimg.parse(stock)
    entries = ramdisk.set_props(ramdisk.read(img.ramdisk), INSECURE_PROPS)
    img = replace(img, ramdisk=ramdisk.write(entries))
    if kernel is not None:
        img = replace(img, kernel=kernel)
    return bootimg.pack(img)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stock")
    ap.add_argument("out")
    ap.add_argument("--kernel", help="zImage to use instead of the stock kernel")
    args = ap.parse_args(argv)
    kernel = Path(args.kernel).read_bytes() if args.kernel else None
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_bytes(make(Path(args.stock).read_bytes(), kernel))
    print(f"wrote {args.out}; test it with: fastboot boot {args.out}")


if __name__ == "__main__":
    main()
