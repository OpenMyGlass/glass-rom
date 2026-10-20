#!/usr/bin/env python3
"""List the apps in a raw (unsparsed) XE24 system image, without a device.

Usage: inventory.py RAW_SYSTEM_IMG OUT.json

Reads ext4 with debugfs (e2fsprogs) and app manifests with `aapt2 dump badging`.
APKs are copied to a temporary directory only for aapt2 and deleted afterwards.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

APP_DIRS = ("/app", "/priv-app")
LS_LINE = re.compile(r"^\s*\d+\s+(\d+)\s+\(\d+\)\s+\d+\s+\d+\s+(\d+)\s+\S+\s+\S+ (.+)$")


class InventoryError(Exception):
    pass


def parse_ls(text: str) -> list:
    """Regular *.apk files from `debugfs -R "ls -l DIR"`, as (name, size)."""
    out = []
    for line in text.splitlines():
        m = LS_LINE.match(line)
        if m and m.group(1).startswith("100") and m.group(3).endswith(".apk"):
            out.append((m.group(3), int(m.group(2))))
    return out


def _attr(line: str, key: str) -> str:
    m = re.search(rf"\b{key}='([^']*)'", line)
    return m.group(1) if m else ""


def parse_badging(text: str) -> dict:
    info = {"package": "", "version_code": "", "version_name": "", "label": "",
            "launchable": False, "permissions": []}
    for line in text.splitlines():
        if line.startswith("package:"):
            info.update(package=_attr(line, "name"), version_code=_attr(line, "versionCode"),
                        version_name=_attr(line, "versionName"))
        elif line.startswith("application-label:"):
            info["label"] = line.split(":", 1)[1].strip().strip("'")
        elif line.startswith("launchable-activity:"):
            info["launchable"] = True
        elif line.startswith("uses-permission:"):
            info["permissions"].append(_attr(line, "name"))
    if not info["package"]:
        raise InventoryError("no package line in aapt2 output")
    return info


def find_tool(name: str, extra_globs: list) -> str:
    found = shutil.which(name)
    if found:
        return found
    for pattern in extra_globs:
        matches = sorted(glob.glob(os.path.expanduser(pattern)))
        if matches:
            return matches[-1]
    raise InventoryError(f"{name} not found; install it or put it on PATH")


def debugfs(tool: str, image: str, command: str) -> str:
    return subprocess.run([tool, "-R", command, image], capture_output=True, text=True,
                          check=True).stdout


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    image, out_path = argv
    dfs = find_tool("debugfs", ["/opt/homebrew/opt/e2fsprogs/sbin/debugfs",
                                "/usr/local/opt/e2fsprogs/sbin/debugfs", "/sbin/debugfs"])
    aapt2 = find_tool("aapt2", ["~/Library/Android/sdk/build-tools/*/aapt2",
                                "~/Android/Sdk/build-tools/*/aapt2"])
    apps = []
    with tempfile.TemporaryDirectory() as tmp:
        for d in APP_DIRS:
            for name, size in parse_ls(debugfs(dfs, image, f"ls -l {d}")):
                local = os.path.join(tmp, "app.apk")
                debugfs(dfs, image, f'dump "{d}/{name}" {local}')
                badging = subprocess.run([aapt2, "dump", "badging", local], capture_output=True,
                                         text=True).stdout
                info = parse_badging(badging)
                info.update(path=f"/system{d}/{name}", size=size)
                apps.append(info)
                os.remove(local)
    apps.sort(key=lambda a: a["path"])
    with open(out_path, "w") as f:
        json.dump(apps, f, indent=2)
        f.write("\n")
    print(f"{len(apps)} apps written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
