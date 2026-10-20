#!/usr/bin/env python3
"""Read and write Android boot images (header version 0), as used by Glass XE24.

Usage:
  bootimg.py info IMAGE
  bootimg.py unpack IMAGE DIR     writes kernel, ramdisk, second, header.json
  bootimg.py pack DIR IMAGE
"""
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"ANDROID!"
# magic, kernel size/addr, ramdisk size/addr, second size/addr, tags addr,
# page size, two unused words, name[16], cmdline[512], id[32], extra cmdline[1024]
HEADER = struct.Struct("<8s10I16s512s32s1024s")


class BootImageError(Exception):
    pass


@dataclass
class BootImage:
    kernel: bytes
    ramdisk: bytes
    second: bytes
    kernel_addr: int
    ramdisk_addr: int
    second_addr: int
    tags_addr: int
    page_size: int
    name: bytes = b""
    cmdline: bytes = b""
    extra_cmdline: bytes = b""
    unused: tuple = (0, 0)
    trailer: bytes = b""


def _pad(n: int, page: int) -> int:
    return (n + page - 1) // page * page


def compute_id(kernel: bytes, ramdisk: bytes, second: bytes) -> bytes:
    h = hashlib.sha1()
    for part in (kernel, ramdisk, second):
        h.update(part)
        h.update(struct.pack("<I", len(part)))
    return h.digest()


def parse(data: bytes) -> BootImage:
    if len(data) < HEADER.size or data[:8] != MAGIC:
        raise BootImageError("not an Android boot image")
    (_, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page,
     u0, u1, name, cmdline, _id, extra) = HEADER.unpack_from(data)
    if page == 0 or page & (page - 1):
        raise BootImageError(f"bad page size {page}")
    offset = page
    sections = []
    for size in (ksize, rsize, ssize):
        if offset + size > len(data):
            raise BootImageError("image is truncated")
        sections.append(data[offset:offset + size])
        offset += _pad(size, page)
    if offset > len(data):
        raise BootImageError("image is truncated")
    return BootImage(
        kernel=sections[0], ramdisk=sections[1], second=sections[2],
        kernel_addr=kaddr, ramdisk_addr=raddr, second_addr=saddr, tags_addr=tags,
        page_size=page, name=name.rstrip(b"\0"), cmdline=cmdline.rstrip(b"\0"),
        extra_cmdline=extra.rstrip(b"\0"), unused=(u0, u1), trailer=data[offset:],
    )


def pack(img: BootImage) -> bytes:
    page = img.page_size
    header = HEADER.pack(
        MAGIC, len(img.kernel), img.kernel_addr, len(img.ramdisk), img.ramdisk_addr,
        len(img.second), img.second_addr, img.tags_addr, page, *img.unused,
        img.name, img.cmdline, compute_id(img.kernel, img.ramdisk, img.second),
        img.extra_cmdline,
    )
    out = bytearray(header.ljust(page, b"\0"))
    for part in (img.kernel, img.ramdisk, img.second):
        out += part.ljust(_pad(len(part), page), b"\0")
    return bytes(out) + img.trailer


_FIELDS = ("kernel_addr", "ramdisk_addr", "second_addr", "tags_addr", "page_size")


def unpack_to_dir(img: BootImage, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for part in ("kernel", "ramdisk", "second", "trailer"):
        (directory / part).write_bytes(getattr(img, part))
    meta = {f: getattr(img, f) for f in _FIELDS}
    meta.update(name=img.name.decode("latin-1"), cmdline=img.cmdline.decode("latin-1"),
                extra_cmdline=img.extra_cmdline.decode("latin-1"), unused=list(img.unused))
    (directory / "header.json").write_text(json.dumps(meta, indent=2) + "\n")


def pack_from_dir(directory: Path) -> BootImage:
    meta = json.loads((directory / "header.json").read_text())
    parts = {p: (directory / p).read_bytes() if (directory / p).exists() else b""
             for p in ("kernel", "ramdisk", "second", "trailer")}
    return BootImage(
        **parts, **{f: meta[f] for f in _FIELDS},
        name=meta["name"].encode("latin-1"), cmdline=meta["cmdline"].encode("latin-1"),
        extra_cmdline=meta["extra_cmdline"].encode("latin-1"), unused=tuple(meta["unused"]),
    )


def main(argv):
    if len(argv) == 2 and argv[0] == "info":
        img = parse(Path(argv[1]).read_bytes())
        print(f"page size {img.page_size}, kernel {len(img.kernel)} B, "
              f"ramdisk {len(img.ramdisk)} B, second {len(img.second)} B, "
              f"trailer {len(img.trailer)} B")
        print(f"cmdline: {img.cmdline.decode('latin-1')}")
    elif len(argv) == 3 and argv[0] == "unpack":
        unpack_to_dir(parse(Path(argv[1]).read_bytes()), Path(argv[2]))
    elif len(argv) == 3 and argv[0] == "pack":
        Path(argv[2]).write_bytes(pack(pack_from_dir(Path(argv[1]))))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
