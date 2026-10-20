# Phase 2: Offline package inventory of the XE24 system image — Plan

**Goal:** From the owner's verified factory image, list every app in `/system/app` and `/system/priv-app` (file, package name, version, size) without a device. Then draft a debloat list in which each package is marked *keep*, *remove* or *unknown*, with the reason.

## Constraints
- Nothing from the image is committed. Only facts are: file names, package names, versions and sizes. Apps are not decompiled; only `aapt2 dump badging` (the manifest summary) is read.
- Tools: Python stdlib, plus `debugfs` (e2fsprogs) to read ext4 without mounting, plus `aapt2` (Android SDK build-tools). Both are found on PATH or in the usual Homebrew/SDK locations.
- The classification is a draft. Every *remove* needs a check on the device before it is applied (phase 3).

## Tasks
1. `tools/sparse.py`: Android sparse image → raw image. Chunk types RAW, FILL, DONT_CARE and CRC32; the header and chunk sizes are validated. Tests: synthetic sparse images built in the test, plus truncated input and bad magic. Local acceptance: same bytes as `simg2img` on the XE24 `system.img`.
2. `tools/inventory.py RAW_SYSTEM_IMG OUT.json`: list the app dirs with `debugfs -R "ls -l"`, dump each APK into a temporary dir, run `aapt2 dump badging` and collect the fields. The `debugfs`/`aapt2` output parsers are pure functions, unit-tested on short sample outputs written in the tests.
3. `docs/xe24-packages.md`, generated from OUT.json: the inventory table plus the draft keep/remove/unknown column. Keep the GDK framework (`com.google.android.glass`), the launcher/timeline (GlassHome), voice/hotword, Bluetooth, camera, settings and core Android. Candidates for removal: account/cloud sync, MyGlass sync, logging/analytics and Google Now style services, all already dead after XE24. Anything unclear stays *unknown*.

## Done when
CI is green, the sparse conversion matches `simg2img`, and the inventory covers every APK in the image.
