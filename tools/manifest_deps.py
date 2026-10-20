#!/usr/bin/env python3
"""Summarize what system apps declare and which apps depend on them, from manifests.

Usage: manifest_deps.py MANIFEST_DIR PACKAGE...

MANIFEST_DIR holds one `aapt2 dump xmltree --file AndroidManifest.xml APK` output per app
(*.txt). For each PACKAGE it prints its shared user and same-user peers, providers, services, the
permissions guarding its components, the apps it depends on and the apps that depend on it. Only manifests are read; no code is decompiled.
"""
import glob
import os
import re
import sys

ELEMENT = re.compile(r"^(\s*)E: (\S+)")
ATTR = re.compile(r'^\s*A: (?:http://schemas\.android\.com/apk/res/android:)?(\w+)(?:\([^)]*\))?=(?:"([^"]*)"|(\S+))')


# element tag -> field collecting its android:name
NAMED = {"permission": "permissions", "permission-tree": "permission_trees",
         "uses-permission": "uses_permissions", "uses-permission-sdk-23": "uses_permissions",
         "uses-permission-sdk-m": "uses_permissions", "service": "services", "action": "actions",
         "uses-library": "libraries"}


def parse(text: str) -> dict:
    """Declarations of one manifest. `guards` are the permissions its components require."""
    m = {"package": None, "shared_user": None, "permissions": [], "permission_trees": [],
         "uses_permissions": [], "guards": [], "providers": [], "services": [], "libraries": [],
         "actions": []}
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
        elif key == "name" and tag in NAMED:
            m[NAMED[tag]].append(value)
        elif key in ("permission", "readPermission", "writePermission") and value not in m["guards"]:
            m["guards"].append(value)
        elif tag == "provider" and key == "authorities":
            m["providers"].extend(value.split(";"))
    if not m["package"]:
        raise ValueError("no manifest package found")
    return m


def _app(apps: list, package: str) -> dict:
    return next(a for a in apps if a["package"] == package)


def _covers(app: dict, permission: str) -> bool:
    """The app declares the permission, directly or through a permission tree."""
    return permission in app["permissions"] or any(
        permission.startswith(tree + ".") for tree in app["permission_trees"])


def dependents(apps: list, package: str) -> list:
    """Other apps that request a permission the package declares (or its tree covers), or one
    that guards the package's components (including framework permissions)."""
    target = _app(apps, package)
    guards = set(target["guards"])
    return sorted(a["package"] for a in apps if a["package"] != package and any(
        _covers(target, p) or p in guards for p in a["uses_permissions"]))


def depends_on(apps: list, package: str) -> list:
    """Other apps that declare a permission the package requests."""
    requested = _app(apps, package)["uses_permissions"]
    return sorted(a["package"] for a in apps if a["package"] != package and any(
        _covers(a, p) for p in requested))


def shared_user_peers(apps: list, package: str) -> list:
    """Other apps running under the same sharedUserId (one process identity)."""
    shared = _app(apps, package)["shared_user"]
    return sorted(a["package"] for a in apps
                  if shared and a["package"] != package and a["shared_user"] == shared)


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
        print(f"guarded by: {', '.join(a['guards']) or '-'}")
        print(f"same shared user: {', '.join(shared_user_peers(apps, package)) or '-'}")
        print(f"depends on: {', '.join(depends_on(apps, package)) or '-'}")
        print(f"dependents: {', '.join(dependents(apps, package)) or '-'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
