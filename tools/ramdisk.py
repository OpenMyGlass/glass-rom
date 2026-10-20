#!/usr/bin/env python3
"""Read and write gzip-compressed cpio (newc) ramdisks and edit default.prop."""
import gzip
from dataclasses import dataclass, replace

NEWC = b"070701"
TRAILER = "TRAILER!!!"
FIELDS = ("ino", "mode", "uid", "gid", "nlink", "mtime", "filesize",
          "devmajor", "devminor", "rdevmajor", "rdevminor", "namesize", "check")


class RamdiskError(Exception):
    pass


@dataclass
class Entry:
    name: str
    mode: int
    data: bytes
    ino: int = 0
    uid: int = 0
    gid: int = 0
    nlink: int = 1
    mtime: int = 0
    devmajor: int = 0
    devminor: int = 0
    rdevmajor: int = 0
    rdevminor: int = 0
    check: int = 0


def _align4(n: int) -> int:
    return (n + 3) & ~3


def read(data: bytes) -> list:
    """Entries in archive order, ending with the trailer entry (kept so a rewrite is faithful)."""
    try:
        raw = gzip.decompress(data)
    except OSError as e:
        raise RamdiskError(f"not gzip data: {e}") from None
    entries, pos = [], 0
    while True:
        if raw[pos:pos + 6] != NEWC or pos + 110 > len(raw):
            raise RamdiskError(f"bad cpio header at offset {pos}")
        values = dict(zip(FIELDS, (int(raw[pos + 6 + 8 * i:pos + 14 + 8 * i], 16) for i in range(13))))
        name_start = pos + 110
        name = raw[name_start:name_start + values["namesize"] - 1].decode("utf-8", "surrogateescape")
        data_start = _align4(name_start + values["namesize"])
        end = data_start + values["filesize"]
        if end > len(raw):
            raise RamdiskError(f"truncated entry {name!r}")
        entries.append(Entry(name=name, data=raw[data_start:end], **{
            k: values[k] for k in FIELDS if k not in ("filesize", "namesize")}))
        if name == TRAILER:
            return entries
        pos = _align4(end)


def _record(e: Entry) -> bytes:
    name = e.name.encode("utf-8", "surrogateescape") + b"\0"
    values = {k: getattr(e, k) for k in FIELDS if k not in ("filesize", "namesize")}
    values.update(filesize=len(e.data), namesize=len(name))
    header = NEWC + b"".join(b"%08x" % values[k] for k in FIELDS)
    out = header + name
    out += b"\0" * (_align4(len(out)) - len(out))
    out += e.data
    return out + b"\0" * (_align4(len(out)) - len(out))


def write(entries: list) -> bytes:
    if not entries or entries[-1].name != TRAILER:
        entries = list(entries) + [Entry(name=TRAILER, mode=0, data=b"")]
    raw = b"".join(_record(e) for e in entries)
    raw += b"\0" * (-len(raw) % 512)
    return gzip.compress(raw, compresslevel=9, mtime=0)


def set_props(entries: list, props: dict) -> list:
    """Return entries with default.prop keys set to the given values."""
    out, found = [], False
    for e in entries:
        if e.name == "default.prop":
            found = True
            lines = e.data.decode("utf-8").splitlines()
            pending = dict(props)
            for i, line in enumerate(lines):
                key = line.split("=", 1)[0].strip()
                if "=" in line and not line.lstrip().startswith("#") and key in pending:
                    lines[i] = f"{key}={pending.pop(key)}"
            lines += [f"{k}={v}" for k, v in pending.items()]
            e = replace(e, data=("\n".join(lines) + "\n").encode("utf-8"))
        out.append(e)
    if not found:
        raise RamdiskError("ramdisk has no default.prop")
    return out
