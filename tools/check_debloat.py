#!/usr/bin/env python3
"""Check that a debloat list covers every package of an inventory.

Usage: check_debloat.py INVENTORY.json debloat/xe24-packages.tsv
Exit status 1 when a package is unlisted or a listed package is not in the image.
"""
import json
import sys

DECISIONS = ("keep", "remove", "unknown")


class DebloatError(Exception):
    pass


def parse(text: str) -> dict:
    """package -> (decision, reason), from tab-separated lines; # starts a comment."""
    rows = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3 or not fields[2].strip():
            raise DebloatError(f"line {n}: expected package<TAB>decision<TAB>reason")
        package, decision, reason = (f.strip() for f in fields)
        if decision not in DECISIONS:
            raise DebloatError(f"line {n}: decision must be one of {', '.join(DECISIONS)}")
        if package in rows:
            raise DebloatError(f"line {n}: {package} is listed twice")
        rows[package] = (decision, reason)
    return rows


def compare(rows: dict, packages: list):
    """(packages missing from the list, listed packages missing from the image)."""
    return sorted(set(packages) - set(rows)), sorted(set(rows) - set(packages))


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0]) as f:
        packages = [a["package"] for a in json.load(f)]
    with open(argv[1]) as f:
        rows = parse(f.read())
    unlisted, stale = compare(rows, packages)
    for p in unlisted:
        print(f"not in the list: {p}")
    for p in stale:
        print(f"not in the image: {p}")
    counts = {d: sum(1 for v in rows.values() if v[0] == d) for d in DECISIONS}
    print(", ".join(f"{n} {d}" for d, n in counts.items()))
    return 1 if unlisted or stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
