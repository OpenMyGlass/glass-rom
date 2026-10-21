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


def add_file(entries: list, name: str, data: bytes, mode: int = 0o100644) -> list:
    """Return entries with the regular file `name` added (or replaced), plus missing parent dirs.

    New entries go just before the trailer, parent directories first, so a cpio
    extractor creates each directory before the files in it.
    """
    if name.startswith("/") or not name or ".." in name.split("/"):
        raise RamdiskError(f"bad ramdisk path {name!r}")
    if any(not part for part in name.split("/")) or "." in name.split("/"):
        raise RamdiskError(f"bad ramdisk path {name!r}")
    modes = {e.name: e.mode for e in entries}
    out = [e for e in entries if e.name not in (name, TRAILER)]
    trailer = [e for e in entries if e.name == TRAILER]
    parts = name.split("/")
    for i in range(1, len(parts)):
        d = "/".join(parts[:i])
        if d in modes and modes[d] & 0o170000 != 0o040000:
            raise RamdiskError(f"{d!r} exists in the ramdisk and is not a directory")
        if d not in modes:
            out.append(Entry(name=d, mode=0o040755, data=b"", nlink=2))
    out.append(Entry(name=name, mode=mode, data=data))
    return out + trailer


def replace_line(entries: list, name: str, old: str, new: str) -> list:
    """Return entries with the one line of file `name` whose text is `old` replaced by `new`.

    Leading whitespace is ignored when matching and kept in the result. Exactly one
    line must match, so a changed stock file fails loudly instead of being half-edited.
    """
    out, found = [], False
    for e in entries:
        if e.name == name:
            found = True
            try:
                lines = e.data.decode("utf-8").split("\n")
            except UnicodeDecodeError as err:
                raise RamdiskError(f"{name}: not UTF-8 text: {err}") from None
            hits = [i for i, line in enumerate(lines) if line.strip() == old]
            if len(hits) != 1:
                raise RamdiskError(f"{name}: expected one line {old!r}, found {len(hits)}")
            i = hits[0]
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = indent + new + ("\r" if lines[i].endswith("\r") else "")
            e = replace(e, data="\n".join(lines).encode("utf-8"))
        out.append(e)
    if not found:
        raise RamdiskError(f"ramdisk has no {name}")
    return out
