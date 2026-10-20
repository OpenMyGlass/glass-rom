#!/usr/bin/env python3
"""Render docs/xe24-packages.md from an inventory and the debloat list.

Usage: render_packages.py INVENTORY.json debloat/xe24-packages.tsv docs/xe24-packages.md
"""
import json
import sys

import check_debloat

ORDER = {"remove": 0, "unknown": 1, "keep": 2}

INTRO = """\
# XE24 system apps

Inventory of `/system/app` and `/system/priv-app` in Google's XE24 factory image (`glass_1-img-5585826`, SHA-256 `76a9d382…2363`). It was produced offline:

```sh
tools/fetch-factory.sh factory/
tools/sparse.py factory/system.img factory/system.raw
tools/inventory.py factory/system.raw factory/inventory.json
tools/check_debloat.py factory/inventory.json debloat/xe24-packages.tsv
tools/render_packages.py factory/inventory.json debloat/xe24-packages.tsv docs/xe24-packages.md
```

The decisions come from [`debloat/xe24-packages.tsv`](../debloat/xe24-packages.tsv), which is the source of truth. They are a **draft**:
- every *remove* is first disabled on a device (`pm disable`, reversible) and checked before anything is deleted;
- every *unknown* needs that check before it gets a decision.

Notes:
- The image is odexed: each APK has its `.odex` next to it, and removing an app means deleting both files.
- The Glass apps report version `XE22.0`, while the system is XE24 (`4.4.4-5585826`).
- The Glass-specific framework libraries, `/system/framework/glass-core.jar` and `glass-services.jar` (permission file `glass-core.xml`), stay.
- *Net* means the app requests `android.permission.INTERNET`.
"""


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|")


def table(apps: list, rows: dict) -> list:
    out = []
    for a in sorted(apps, key=lambda a: (ORDER[rows[a["package"]][0]], a["package"])):
        decision, reason = rows[a["package"]]
        net = "✓" if "android.permission.INTERNET" in a["permissions"] else ""
        out.append(f"| **{decision}** | `{a['package']}` | {_cell(a['label'])} | {_cell(a['version_name'])} "
                   f"| `{a['path']}` | {a['size'] // 1024} KiB | {a['odex_size'] // 1024} KiB | {net} "
                   f"| {_cell(reason)} |")
    return out


def summary(apps: list, rows: dict) -> str:
    counts = {d: sum(1 for a in apps if rows[a["package"]][0] == d) for d in check_debloat.DECISIONS}
    freed = sum(a["size"] + a["odex_size"] for a in apps if rows[a["package"]][0] == "remove")
    return (f"{len(apps)} apps: " + ", ".join(f"{n} {d}" for d, n in counts.items())
            + f". Removing every *remove* frees {freed // 1024} KiB.")


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0]) as f:
        apps = json.load(f)
    with open(argv[1]) as f:
        rows = check_debloat.parse(f.read())
    unlisted, stale = check_debloat.compare(rows, [a["package"] for a in apps])
    if unlisted or stale:
        print("error: run check_debloat.py first", file=sys.stderr)
        return 1
    lines = [INTRO, summary(apps, rows), "",
             "| Decision | Package | Label | Version | Path | APK | Odex | Net | Reason |",
             "|---|---|---|---|---|---:|---:|:-:|---|", *table(apps, rows)]
    with open(argv[2], "w") as f:
        f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
