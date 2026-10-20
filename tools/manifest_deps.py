#!/usr/bin/env python3
"""Summarize what system apps declare and which apps depend on them, from manifests.

Usage: manifest_deps.py MANIFEST_DIR PACKAGE...

MANIFEST_DIR holds one `aapt2 dump xmltree --file AndroidManifest.xml APK` output per app
(*.txt). For each PACKAGE it prints its shared user, permissions, providers, services and
the apps that request its permissions. Only manifests are read; no code is decompiled.
"""
import glob
import os
import re
import sys

ELEMENT = re.compile(r"^(\s*)E: (\S+)")
ATTR = re.compile(r'^\s*A: (?:http://schemas\.android\.com/apk/res/android:)?(\w+)(?:\([^)]*\))?=(?:"([^"]*)"|(\S+))')


def parse(text: str) -> dict:
    m = {"package": None, "shared_user": None, "permissions": [], "uses_permissions": [],
         "providers": [], "services": [], "libraries": [], "actions": []}
    stack = []  # (indent, tag)
    for line in text.splitlines():
        e = ELEMENT.match(line)
        if e:
            depth = len(e.group(1))
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, e.group(2)))
            continue
        a = ATTR.match(line)
        if not a or not stack:
            continue
        key, value = a.group(1), a.group(2) if a.group(2) is not None else a.group(3)
        tag = stack[-1][1]
        if tag == "manifest" and key == "package":
            m["package"] = value
        elif tag == "manifest" and key == "sharedUserId":
            m["shared_user"] = value
        elif key == "name" and tag in ("permission", "uses-permission", "service", "action", "uses-library"):
            field = {"permission": "permissions", "uses-permission": "uses_permissions",
                     "service": "services", "action": "actions", "uses-library": "libraries"}[tag]
            m[field].append(value)
        elif tag == "provider" and key == "authorities":
            m["providers"].extend(value.split(";"))
    if not m["package"]:
        raise ValueError("no manifest package found")
    return m


def dependents(apps: list, package: str) -> list:
    """Other apps that request a permission the package declares."""
    target = next(a for a in apps if a["package"] == package)
    declared = set(target["permissions"])
    return sorted(a["package"] for a in apps
                  if a["package"] != package and declared & set(a["uses_permissions"]))


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    apps = []
    for path in sorted(glob.glob(os.path.join(argv[0], "*.txt"))):
        with open(path) as f:
            apps.append(parse(f.read()))
    known = {a["package"] for a in apps}
    for package in argv[1:]:
        if package not in known:
            print(f"{package}: not in {argv[0]}")
            continue
        a = next(x for x in apps if x["package"] == package)
        print(f"## {package}")
        print(f"shared user: {a['shared_user']}")
        print(f"providers: {', '.join(a['providers']) or '-'}")
        print(f"services: {', '.join(s.split('.')[-1] for s in a['services']) or '-'}")
        print(f"libraries: {', '.join(a['libraries']) or '-'}")
        print(f"apps requesting its permissions: {', '.join(dependents(apps, package)) or '-'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
