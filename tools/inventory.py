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
    """Regular files from `debugfs -R "ls -l DIR"`, as (name, size).

    KitKat keeps apps flat in /system/app and /system/priv-app (no per-app dirs).
    """
    out = []
    for line in text.splitlines():
        m = LS_LINE.match(line)
        if m and m.group(1).startswith("100"):
            out.append((m.group(3), int(m.group(2))))
    return out


def apps_in(files: list) -> list:
    """(apk name, apk size, size of its .odex or 0) for each APK; odexed images ship both."""
    sizes = dict(files)
    return [(name, size, sizes.get(name[:-4] + ".odex", 0))
            for name, size in files if name.endswith(".apk")]


def check_debugfs_stderr(text: str) -> None:
    """debugfs exits 0 on errors; anything besides its version banner is one."""
    errors = [l for l in text.splitlines() if l.strip() and not l.startswith("debugfs ")]
    if errors:
        raise InventoryError("debugfs: " + "; ".join(errors))


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
    result = subprocess.run([tool, "-R", command, image], capture_output=True, text=True)
    check_debugfs_stderr(result.stderr)
    if result.returncode:
        raise InventoryError(f"debugfs exited with {result.returncode}")
    return result.stdout


def badging(tool: str, apk: str, name: str) -> dict:
    result = subprocess.run([tool, "dump", "badging", apk], capture_output=True, text=True)
    try:
        return parse_badging(result.stdout)
    except InventoryError:
        raise InventoryError(f"aapt2 could not read {name}: {result.stderr.strip()}") from None


def inventory(image: str, dfs: str, aapt2: str) -> list:
    if not os.path.isfile(image):
        raise InventoryError(f"{image}: no such file")
    apps = []
    with tempfile.TemporaryDirectory() as tmp:
        local = os.path.join(tmp, "app.apk")
        for d in APP_DIRS:
            found = apps_in(parse_ls(debugfs(dfs, image, f"ls -l {d}")))
            if not found:
                raise InventoryError(f"no APKs found in {d}")
            for name, size, odex_size in found:
                if '"' in name:
                    raise InventoryError(f"unsupported file name {name!r}")
                debugfs(dfs, image, f'dump "{d}/{name}" "{local}"')
                if not os.path.isfile(local):
                    raise InventoryError(f"debugfs did not extract {d}/{name}")
                info = badging(aapt2, local, name)
                info.update(path=f"/system{d}/{name}", size=size, odex_size=odex_size)
                apps.append(info)
                os.remove(local)
    return sorted(apps, key=lambda a: a["path"])


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    image, out_path = argv
    try:
        dfs = find_tool("debugfs", ["/opt/homebrew/opt/e2fsprogs/sbin/debugfs",
                                    "/usr/local/opt/e2fsprogs/sbin/debugfs", "/sbin/debugfs"])
        aapt2 = find_tool("aapt2", ["~/Library/Android/sdk/build-tools/*/aapt2",
                                    "~/Android/Sdk/build-tools/*/aapt2"])
        apps = inventory(image, dfs, aapt2)
    except InventoryError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    with open(out_path, "w") as f:
        json.dump(apps, f, indent=2)
        f.write("\n")
    print(f"{len(apps)} apps written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
