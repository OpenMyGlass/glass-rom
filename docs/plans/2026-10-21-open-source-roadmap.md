# Open-source Glass XE: roadmap

**Goal:** build Glass Explorer Edition's system from source, with only the parts that cannot be open left as binaries, which are extracted from the owner's own factory image and never committed.

## What stays binary

These are not on the roadmap: there is no open alternative, or replacing them is not worth the risk.
- `bootloader`, `xloader` and `fpga` partitions: never written.
- Firmware that runs on other chips: Ducati (`ducati-m3-core0.xem3`, `-2gb` on XE-C), Tesla DSP (`tesla-dsp.xe64T`), BCM4330 Wi-Fi (`fw_bcmdhd.bin`) and Bluetooth (`bcm4330.hcd`), glasshub (`glasshub.s19`), touchpad and gas-gauge images.
- PowerVR SGX540 user-space libraries (`libGLES*_POWERVR_SGX540_120.so`, `libsrv_um`, `libusc`, `libglslcompiler`, `gralloc.omap4430.so` and the rest).

## Phases

Each phase gets its own plan in `docs/plans/` of the repo that owns most of its work. Nothing can be tested on hardware until a Glass is available, so every phase ends with a build check and a list of what to check on a device.

| # | Phase | Repos | Result |
|---|---|---|---|
| R1 | Vendor extraction and a device tree without Google files | glass-rom, android_device_glass_glass-1 | `extract_vendor.py` fills `vendor/glass/glass-1/` from the owner's image; the tree has new `rootdir/` files and passes its own checks. Plan: [`2026-10-21-vendor-extraction.md`](2026-10-21-vendor-extraction.md). |
| R2 | Kernel: GPU module from source, then low-risk tuning | glass-kernel | Done: `pvrsrvkm_sgx540_120.ko` is built from Imagination's DDK at XE24's exact build, `1.9@2166536` (MIT/GPL-2.0), and imports the same kernel symbols with the same CRCs as the stock module (glass-kernel phase 3). OMAP4-AOSP's `pvr-source` is `1.9@2291151` and would not match XE24's user-space libraries. With the binary module gone, the config cleanups that change struct layouts become possible. Then, from `reports/Ottimizzazioni kernel OMAP4.md`, only items rated no or low risk: interactive backports (`io_is_busy`, per-frequency `above_hispeed_delay`), the xrr02 input-boost handler, linux-3.4.y stable up to 3.4.113, and a check of the XE-C 2 GB memory map. No overclock, undervolt or raised thermal limit. |
| R3 | Open HALs | android_device_glass_glass-1 | Open on `android-6.0.1_r31`, not run on a device: power HAL (interactive values, boostpulse, screen-off cap) and lights ([#3](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/3)), sensors over IIO ([#5](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/5)), audio and audio policy ([#6](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/6)), camera from TI's OMAP4 HAL (`camera.omap4`, from source) on top of the Ducati firmware ([#11](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/11)), hardware composer (`hwcomposer.omap4`, from source, [#12](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/12)). No GPS HAL: location comes from the phone ([#4](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/4)). Power, lights, sensors and audio are ours and cross-compiled in CI; camera and hwcomposer are TI's, built from source only in a full build. Audio and sensors left `proprietary-files.txt`; the others were never on it. |
| R4 | Glass system services, clean-room | new repo | touchpad gestures, head gestures, on-head and wink detection (needs the glasshub protocol), screen wake. Spec written from observations, code written only from the spec. |
| R5 | Glass apps, clean-room | new repo | card timeline launcher at 640×360, settings, setup, camera, voice with an open hotword; dictation goes through OpenMyGlass to the phone. |

## Reverse engineering the binaries

Any binary on the "stays binary" list, and any HAL, daemon or library that a phase replaces, may be reverse engineered to learn its interfaces, for interoperability:
- **Tools:** the REA MCP server (`rea-agents`, with JADX and Ghidra as providers), plus whatever the target needs: Ghidra for ARM/Thumb `.so` files and Cortex-M3 firmware, a TI C6000 disassembler for the Tesla DSP. Install them when a phase needs them.
- **Workspace:** `_re/` in OpenMyGlass, which is not versioned. Decompiled code, disassembly and extracted files never leave it.
- **Clean room:** what reverse engineering finds goes into a spec under `docs/specs/`: interfaces, ioctls, sysfs paths, message formats, timings, and where each fact was observed. The open replacement is written from the spec only, by an implementer (person or agent) who has not read the decompiled code.
- **Order:** the targets of the next phase come first:
  1. R3: `audio.primary.glass_1.so` and `libglassalsa.so`, `sensors.glass_1.so` (InvenSense MPL). Done: both have a spec and an open HAL;
  2. Glass daemons: `sysproxyd`, `shm_service`, `bqflash`, `raft`, `bootconfig`;
  3. R4: `libglassgaze.so` and the glasshub protocol, `libglass_services_jni.so`, `libglassinputdevice.so`;
  4. the camera libraries.

  PowerVR user space and chip firmware (Ducati, Tesla, BCM4330, glasshub) come last. Reversing them documents the interfaces, but they stay binary unless a replacement turns out to be realistic.

## Which operating system

Decided with the owner on 2026-10-21: start from an open Android base, and keep a plain-Linux system possible.

| Route | What it is | For | Against |
|---|---|---|---|
| 1. Open Android (current) | AOSP built from source, with our device tree, init files, HALs and services, and only the binaries above | GPU acceleration, camera, Bluetooth and Wi-Fi stacks already exist; OpenMyGlass works on it | The system underneath is Android; ours is the UI and services |
| 2. Plain Linux on the stock kernel | The route of [glass-xec-mainline](https://github.com/Lasimeri/glass-xec-mainline): Alpine on XE24's 3.4.94 kernel, with our own minimal UI | Fully our own system, lighter, probably less battery use. Wi-Fi, display, audio, camera (through Ducati), touchpad and battery gauge are reported working on an XE-C | The PowerVR user-space libraries are built for Android (bionic); GPU rendering needs libhybris (see [Plain Linux with the GPU](#plain-linux-with-the-gpu-libhybris)). Bluetooth and sensors are untested there |
| 3. Mainline kernel | A current Linux kernel | The cleanest long-term base | Does not boot yet (resets after about a minute); no driver for the panel (iCE40 FPGA) or glasshub; months of work, each step on hardware |

How R4 and R5 are written so that route 2 stays open:
- The Glass system services and the UI are components that do not depend on Android: daemons and libraries in C or Rust, and a UI that talks to a thin graphics layer.
- This covers the glasshub protocol (wink, on-head), touchpad and head gestures, the card timeline, and voice through the phone.
- Android-specific glue (system services, intents, the launcher wrapper) stays in a separate layer.
- Once a Glass is available, battery drain, temperature and smoothness are measured on routes 1 and 2 with the same components, and the main route is picked from the measurements.

### Plain Linux with the GPU (libhybris)

Decided with the owner on 2026-10-22: plain Linux renders on the GPU through [libhybris](https://github.com/libhybris/libhybris) (Apache-2.0), not on the CPU, and without decompiling the PowerVR libraries.
- **What libhybris does:** it loads Android (bionic) libraries into a glibc or musl Linux process, so the XE24 PowerVR EGL/GLES libraries and `gralloc` run unchanged. Sailfish OS, Ubuntu Touch (Halium) and postmarketOS use it on many Android devices.
- **Step 1, on the 3.4 kernel (route 2):** glass-kernel's `tuned-stable` kernel with our PVR module, the PowerVR user space extracted from the owner's image at build time (never committed), a minimal bionic layer with `pvrsrvinit`, and libhybris. The UI from glass-apps then draws through EGL/GLES2 on the GPU. Wayland compositors that support libhybris (for example via `hwcomposer` or `fbdev` EGL platforms) are an option to evaluate, not a requirement.
- **Step 2, on mainline (route 3):** the same user space needs the 2166536 kernel module ported to mainline (see "What Android 6 on mainline needs"), plus a display path that matches what `gralloc` expects. Months of work, only with a Glass.
- **Interoperability without reverse engineering:** this route uses the binaries as they are, through their public EGL/GLES API. No decompilation is needed, so it is not limited by the clean-room rules.
- **To check first, on hardware:** that the libraries load under libhybris (their bionic version and symbol needs), `pvrsrvinit` starts, and an EGL window appears. The plan is written when a Glass is available; until then this is a direction, not a phase.

### Kernel versions

Decided with the owner on 2026-10-21:
- **Now: stay on 3.4 and merge linux-3.4.y up to 3.4.113** (end of life, October 2016). That brings bug and security fixes and nothing new, such as schedutil. Prior work exists: invisiblek merged up to 3.4.105 on the Glass kernel, and Unlegacy-Android's OMAP4 trees (Galaxy Tab 2, Nook HD) are at 3.4.113.
- **Not planned: Android 3.10 or 3.14 OMAP4 trees.** They would need all of the Glass board code, drivers and duty-cycle thermal governor ported, plus the 1.9 GPU module adapted. That costs almost as much as mainline for a much smaller gain.
- **Long-term track: mainline,** together with route 2 and with [glass-xec-mainline](https://github.com/Lasimeri/glass-xec-mainline) instead of a separate effort.
  - It is the only way to get schedutil, current power management and years of security fixes.
  - It needs a device tree description of the board, drivers for the panel FPGA and glasshub, and the out-of-tree SGX driver (openpvrsgx, DDK `1.9@2188537`). That driver does not match XE24's Android libraries but fits a plain-Linux system.
  - Boot debugging most likely needs a serial console. Whether one is reachable on the Glass is checked once a device is available, and no mainline work starts before that.

## Android tracks

Decided with the owner on 2026-10-21. This closes the earlier open question of which Android version to build. Two Android versions are built, and both are kept. Both are made as lean as possible for Glass, with three aims:
- use less CPU and RAM and run cooler on a 1 GHz dual Cortex-A9 with 1 GB (XE) or 2 GB (XE-C) of RAM, a 640×360 display, worn against the temple;
- keep as many apps working as possible;
- change nothing in voltages, frequencies or thermal limits.

| Track | Android | Runtime | Why | Plan |
|---|---|---|---|---|
| A | 4.4.4 KitKat | **ART only**: Dalvik (`libdvm`, `dexopt`) not built, everything compiled by `dex2oat` | Near-term target: Glass's binaries (PowerVR user space, audio, camera, sensors) were built for KitKat and run without shims. ART is already in XE24's image (stock runs Dalvik) | [`2026-10-21-android-lean-kitkat-art.md`](2026-10-21-android-lean-kitkat-art.md) |
| B | 6.0.1 Marshmallow | ART | The most app-compatible system that still runs Glass's binaries (as LineageOS 13 and Unlegacy-Android did on other OMAP4 devices), and the Android version meant to bridge to the mainline kernel | [`2026-10-21-android-lean-6.md`](2026-10-21-android-lean-6.md) |

Optimisations from later Android versions are backported to KitKat where the gain is worth the cost. The ranked list is in Track A's plan, Task 5. The cheap gains are planned, among them:
- a Doze-like idle service of our own, driven by glasshub's on-head signal;
- low-memory-killer and `extra_free_kbytes` tuning;
- default dex2oat filters for system and user apps, with a per-package override.

The heavy ones are **not planned**: JobScheduler and Doze in the framework, Lollipop's ART, and the 5.x/6.x memory trimming. No public port of any of them to KitKat was found.

Long-term goal: the mainline kernel and the most compatible apps, so Track B on mainline.

### Status (2026-10-22)

- **Manifest:** [OpenMyGlass/manifest](https://github.com/OpenMyGlass/manifest) holds the Track A build: AOSP `android-4.4.4_r2.0.1`, omap4-aosp's `hardware/ti/omap4`, android-security's patched `aosp-4.4` projects, and our forks, each pinned to a commit ([manifest #1](https://github.com/OpenMyGlass/manifest/pull/1)). Its `build` workflow, run by hand on the free runner, built the system image with every ART-only check green; nothing has run on a Glass.
- **Track A device tree:** branch `android-4.4.4`: kernel and SGX module from glass-kernel ([#7](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/7)), ART only with dex2oat filters ([#8](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/8)), the 4.4 emulated sdcard ([#9](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/9)), lean apps and services ([#10](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/10)), media XMLs ([#13](https://github.com/OpenMyGlass/android_device_glass_glass-1/pull/13)). Of the R3 HALs, power and lights are on it, and camera and the hardware composer come from omap4-aosp's `hardware/ti/omap4`; audio and sensors still use the stock blobs.
- **Track A ART:** [OpenMyGlass/android_art](https://github.com/OpenMyGlass/android_art) `glass-4.4` carries 16 fixes (19 commits) from later AOSP whose bugs are in KitKat's ART (JNI behaviour that differed from Dalvik, dex2oat aborts, GC card-table corruption, thread join), and the native and dex2oat compiler settings are audited: [2026-10-22-kitkat-art-fixes.md](2026-10-22-kitkat-art-fixes.md). Not run on a device.
- **Track B device tree:** branch `android-6.0.1_r31`, with the R3 HALs.

### Tracks and routes

- **Route 1 (open Android) now means both tracks.** The R3 HALs are written once, against API levels both versions load: audio 2.0, sensors exactly 1.1 (4.4 loads nothing newer), camera HAL1 over Ducati, hwcomposer 1.0 (`HWC_DEVICE_API_VERSION_1_0`, TI's `hwcomposer.omap4`), power 0.2. The R4 services and R5 apps stay independent of Android, as written above, so they also serve route 2.
- **Route 2 (plain Linux)** is unaffected. Its components are shared with both tracks.
- **Route 3 (mainline)** is where Track B is meant to go in the long term (see below).

### Which kernel each track runs

| | Now | Later |
|---|---|---|
| Track A (4.4.4) | glass-kernel `tuned-stable` (3.4.113) | stays on 3.4: KitKat is not the target for mainline |
| Track B (6.0.1) | glass-kernel `tuned-stable` (3.4.113), as every Android 6/7 OMAP4 port did on a vendor kernel (3.0.101 for tuna, espresso and the Nooks; 3.4.112 in omap4-aosp) | mainline, long-term |

### What Android 6 on mainline needs, honestly

- **GPU kernel side.** The SGX driver's kernel side is open. openpvrsgx (Letux) has ported DDK 1.9 kernel modules to mainline, among them `1.9.2188537` and `1.9.2253347`; the latter ran on the OMAP4 Droid 4 with TI's Linux user space. Our user space is `1.9@2166536`, and the kernel module must be the same build. So the path is to port the 2166536 module, which glass-kernel already builds for 3.4, to mainline, with openpvrsgx as the guide. Effort: months. This is a long-term task under the mainline track.
- **Display path.** This is the harder part. Glass's gralloc and the TI hwcomposer expect ION, TILER and `dsscomp`, and mainline has `omapdrm` with dma-buf instead. Android there needs a new gralloc and composer (`drm_hwcomposer` or our own HWC 1.x), plus the omapdrm-to-PVR glue that the Droid 4 port needed. No Android user space on mainline OMAP4 was found.
- **Decision (owner, 2026-10-22): the GPU renders, not the CPU.** Every Android track uses the XE24 PowerVR user-space libraries, extracted from the owner's image. On KitKat they load as they are; on Android 6 they load through the adapter described in Track B (an open `libEGL_POWERVR` wrapper and the `frameworks/native` patches other OMAP4 ports used). Software rendering is not a planned mode for any Android track, because it costs battery and heat on a device worn on the temple.
- **Software rendering stays only as a debugging aid.** On Android 6 that would mean Mesa softpipe/llvmpipe, since AOSP 6.0 ships no SwiftShader and its own `libagl` is GLES 1 only. It is probably too slow for HWUI on an A9 (unverified). On plain Linux (route 2) it is used only until the libhybris path below works.
- **No open user-space SGX driver exists.** Mesa's PowerVR driver is Rogue-only (Series 6 and later). The only related effort found is a reverse-engineered DRI driver that still pairs with Imagination's DDK 1.17 libraries. Writing a fully open SGX540 user space is a multi-year reverse-engineering project and is **not planned**.
- **Open SGX540 user space, effort per component:** [`gpu-open-userspace-estimate.md`](../gpu-open-userspace-estimate.md). By the owner's decision it is the last item on the roadmap, after every other component is open; a reply to the owner's request to Imagination may change that.
- **Not used.** Unlegacy-Android also ships a newer SGX540 binary set (DDK `1.14@4081762`, for Android 7+, with kernel-module source updated for Linux 4.4). It is not from the owner's image, and its licence is unclear. Whether to use it is a decision for the owner.

## Build infrastructure

Component builds need no AOSP checkout. The HALs, services and tools are checked by each repository's own CI on standard runners, as now. A full system image does need one. Requirements from Google's 2016 requirements page (`platform/docs/source.android.com`, `src/source/requirements.jd`, still matched by source.android.com's "older versions" page):
- disk: 100 GB for a checkout, 150 GB for one build, more with ccache (Google suggests `ccache -M 50G`);
- 16 GB of RAM or swap in a VM;
- Ubuntu 12.04 and Oracle JDK 6 for 4.4; Ubuntu 14.04 and OpenJDK 7 for 6.0; Python 2.7, make 3.81/3.82.

A shallow `repo sync -c --depth=1` of a trimmed manifest is smaller. Our guess is 40-50 GB of source and output for 4.4 and 60-85 GB for 6.0, unmeasured. Old containers exist (for example `kylemanna/docker-aosp`, branches `4.4-kitkat` and `6.0-marshmallow`, both on Ubuntu 14.04). The Oracle JDK 6 installer they use is gone, so the 4.4 one needs OpenJDK 6 instead (untested).

The owner's Mac has about 8 GB free, so it cannot build either version.

| Option | Disk, CPU | Cost (2026-10, excl. VAT) | Notes |
|---|---|---|---|
| GitHub standard runner (public repos) | 4 vCPU, 16 GB; 14 GB SSD by the docs, about 29 GB free in practice, up to about 60 GB after removing preinstalled tools (`jlumbroso/free-disk-space`, `easimon/maximize-build-space`) | free | 6-hour job limit. A trimmed shallow 4.4 build might just fit; 6.0 probably does not fit in disk or time. Worth one try for Track A |
| GitHub larger runners | 8-core / 32 GB / 300 GB at $0.022 per minute; 16-core / 64 GB / 600 GB at $0.042 per minute | about $3.30-3.40 per full build (an estimated 80-150 min); not free for public repositories | Team plan or higher only (the org is on Free) |
| Self-hosted runner on a dedicated server | Hetzner AX41: 6 cores, 64 GB, 2×512 GB NVMe | €59 per month, no setup fee; AX42 €99 per month plus €49 setup | GitHub advises against self-hosted runners on public repositories: anyone can open a pull request. Usable only with trusted triggers (`push` to main, `workflow_dispatch`) and ephemeral jobs |
| Hourly cloud VM started only to build, not a GitHub runner | Hetzner CCX43: 16 vCPU, 64 GB, 360 GB | €0.44 per hour, about €1.33 per 3-hour build | Created and deleted by a script; availability varies (Hetzner raised cloud prices for new orders on 2026-06-15) |
| Hourly cloud VM, spot | AWS c7a.4xlarge (16 vCPU, 32 GB) plus 250 GB of EBS | about $0.29-0.36 per hour spot, about $1 per build | Spot interruptions above 20% in us-east-1 |
| Component builds only | standard runners | free | Builds HALs and services in a trimmed tree, no full image. Not yet documented for 4.4/6.0 HALs, which link `libhardware`, `libcutils` and `libbinder` (not in the NDK) |

Sources:
- GitHub runner docs (`docs.github.com/en/actions/reference/runners/github-hosted-runners`, `.../larger-runners`, `.../billing/reference/actions-runner-pricing`, `.../security/secure-use`);
- GitHub's 2026 pricing notice, prices cut on 2026-01-01; the self-hosted fee was postponed;
- Hetzner's dedicated and cloud price pages;
- an AWS spot price tracker (2026-07).

Build times are estimates; none were measured.

**Decision for the owner:** which build machine. The cheapest safe options are:
- one try of Track A on the free runner;
- an hourly VM that is not a GitHub runner, for Track B and for releases.

## Measurement plan (on hardware, later)

Nothing is measured until a Glass is available. Then three systems are compared on the same device, the same battery and the same room temperature:
- stock XE24;
- Track A;
- Track B.

Each runs with the same kernel variant where possible (stock XE24 runs its own), Wi-Fi joined to the same network, and the phone link connected.

| Measure | How | Runs |
|---|---|---|
| Idle drain, screen off | battery percentage and gas-gauge current (`/sys/class/power_supply/…/current_now`) over 2 hours, off the head on a table, then 2 hours on the head; `dumpsys batterystats` wakeup counts | 3 per system |
| Screen-on drain | 30 minutes on the card timeline with one swipe every 10 s (scripted through `input`), then 30 minutes of a video | 3 |
| Temperature | the OMAP die sensor and the battery sensor, logged every 10 s during the screen-on runs and during a 5-minute camera recording; only read, never a limit changed | 3 |
| Boot time | `fastboot boot` to `sys.boot_completed=1`, first boot and a later boot (`logcat -b events` boot progress) | 5 |
| App start | cold and warm start of 5 test apps (`am start -W`) | 10 each |
| RAM | `dumpsys meminfo` and `procrank` after boot and after starting the test apps; `/proc/meminfo` free plus cached; zRAM use (`/sys/block/zram0/mem_used_total`) | 3 |
| Compile cost (A and B) | first-boot `dex2oat` time, `/data/dalvik-cache` size, install time of a 10 MB APK | 3 |

Before the first boot of each track, `/data` is backed up with `adb backup`/`adb pull` from stock. A track booted with `fastboot boot` still uses stock's `/data`: Track A finds Dalvik's `persist.sys.dalvik.vm.lib` and odex files in `/data/dalvik-cache`, and Track B upgrades the settings and package databases so stock may not boot on them again. So `userdata` and `cache` are wiped before each track and again to go back to stock, through `tools/fastboot-guard.sh --i-understand erase` (both partitions are on its allowlist; `-w` is refused). Never `bootloader`, `xloader` or `fpga`.

Results go into `reports/` of glass-rom with the raw logs, and the default track is chosen from them.
