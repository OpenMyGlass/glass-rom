# Track B: lean Android 6.0.1 — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Android 6.0.1 system for Glass Explorer from source that runs today's apps better than KitKat can (API 23, ART with moving GC), uses less CPU and RAM and runs cooler, and is the bridge towards the mainline kernel. It runs Glass's KitKat-era binaries, the PowerVR SGX540 user space above all, with the open compatibility layer that CyanogenMod and LineageOS 13 and Unlegacy-Android used on other OMAP4 devices.

**Architecture:**
- Base: AOSP `android-6.0.1_r*` and the device tree's default branch, `android-6.0.1_r31` of `android_device_glass_glass-1`. The device tree already targets 6.0.1 and has the clean-room `rootdir/`, `system.prop` and `proprietary-files.txt`.
- OMAP4 hardware projects and the graphics compatibility patches come from the LineageOS cm-13.0 / omap4-aosp `aosp-6.0` work for tuna and espresso (Task 1).
- Kernel now: glass-kernel `tuned-stable` (3.4.113), the same as Track A. Every other Android 6/7 OMAP4 port stayed on a vendor kernel (3.0.101 for tuna, espresso and the Nooks; 3.4.112 in omap4-aosp's common kernel), with ION, `dsscomp` and `omaplfb`. That is the proven configuration.
- Kernel later: mainline, see "Android 6 on mainline" below and the roadmap's kernel tracks. It is a long-term task, not part of this plan's first release.
- AOSP patches live in forks under OpenMyGlass pinned by a manifest, as in Track A (owner's decision on where).

**Tech stack:** AOSP 6.0 make build (Ubuntu 14.04 container, OpenJDK 7, Python 2.7), GCC 4.9 and the clang of 6.0.

**Spec:** glass-rom roadmap, "Android tracks", Track B.

## Facts this plan rests on

**How other OMAP4 ports ran Android 6 and 7 with the 1.9 PowerVR binaries:**
- **Blobs.** omap4-aosp's vendor tree started from PVR DDK `1.9@2291151` user space (`omap4-aosp/proprietary_vendor_ti`, branch `aosp-6.0`, commit e0169827, November 2015). The LineageOS cm-13.0 and cm-14.1 kernel module is the same build (`pvr-source/include4/pvrversion.h` in `LineageOS/android_hardware_ti_omap4`).
- **No symbol shims for graphics.** Unlegacy-Android has no `TARGET_LD_SHIM_LIBS` for graphics. The graphics work was:
  - **An open `libEGL_POWERVR` wrapper** that forwards each `eglX` call to the blob's `IMGeglX`. It works around `eglChooseConfig` with `EGL_RECORDABLE_ANDROID` and `EGL_FRAMEBUFFER_TARGET_ANDROID`. Kyle Repinski, March 2016, `libEGL_POWERVR/egl.c` in `LineageOS/android_hardware_ti_omap4` cm-13.0. With it, the vendor tree dropped the `libEGL_POWERVR_SGX*` blobs ("all they are is shims anyway", `Unlegacy-Android/proprietary_vendor_ti`, commit b3147202).
  - **Framework patches** in `frameworks/native`: "Add back support for glReadPixels screenshot path", and "egl: Add back b/10194508 workaround" (`BOARD_EGL_WORKAROUND_BUG_10194508`) (`omap4-aosp/android_frameworks_native`, `aosp-6.0`).
  - The TI colour format in `frameworks/av` (`omap4-aosp/android_frameworks_av`).
  - Non-graphics shims seen: `libsecril-shim` (tuna RIL) and `libgpsd-compat` (espresso GPS).
- **Properties** from `hardware/ti/omap4`'s `omap4.mk`: `ro.hwui.disable_scissor_opt=true`, `debug.hwui.render_dirty_regions=false`, `debug.hwui.swap_with_damage=false`, `ro.egl.destroy_after_detach=true`, `camera2.portability.force_api=1`. Espresso adds `ro.bq.gpu_to_cpu_unsupported=1` and `dalvik.vm.dex2oat-flags=--no-watch-dog` (`LineageOS/android_device_samsung_espresso-common` cm-13.0).
- **Glass's GPU binaries fit this path.** XE24 has `libIMGegl_SGX540_120.so` (`1.4 build 1.9@2166536`) next to `libEGL_POWERVR_SGX540_120.so` (`docs/xe24-blobs.md`), which is the layout the open wrapper expects. Glass is on `1.9@2166536`, not `2291151`, so the wrapper and framework patches must be checked against our build. glass-kernel builds the matching kernel module (`1.9@2166536`).
- **hwcomposer.** XE24 has no `hwcomposer` blob in our list. The open HWC 1.0 composer (`HWC_DEVICE_API_VERSION_1_0`) in `hardware/ti/omap4` `hwc/` (commit a3c66065) is roadmap R3's hwcomposer. Unlegacy later replaced it with a proprietary composer (46ffaa04).
- **Problems the tuna cm-13.0 port hit** (`LineageOS/android_device_samsung_tuna`, cm-13.0 log):
  - dexpreopt was turned off for `/system` space and later turned back on;
  - zRAM was turned off;
  - SELinux was permissive at first and enforcing by July 2016;
  - camera TILER memory leaks.
- **A later binary set exists.** Unlegacy moved to DDK `1.14@4081762` for SGX540_120 and SGX544_112 (user space, a proprietary `hwcomposer.omap4.so` and memtrack; kernel module source with "update KM sources for K4.4"; `Unlegacy-Android/proprietary_vendor_ti` and `android_hardware_ti_omap4`, branch `stable`, commits 3c4458e5 and c09738f9, 2017). These are not from the owner's Glass image. Using them breaks the rule that binaries come only from the owner's own image, and their licence is unclear. **Decision for the owner;** this plan does not use them.

**Android 6 on mainline: the realistic path.**
- **The kernel side of the SGX driver is open and has been ported to mainline.** `openpvrsgx-devgroup/linux_openpvrsgx` (active; last push 2026-10-19; default branch `linux+pvrsgx`, branches up to `pvrsrvkm-7.3`) carries many DDK kernel trees under `drivers/gpu/drm/pvrsgx/`: 1.7, 1.8.869593 (Kconfig: "should work on OMAP4430/4460/4470"), 1.9.2188537, 1.9.2204701, 1.9.2253347, 1.10, and 1.12 through 1.17.4948957.
  - **There is no `1.9.2166536`.**
  - Tony Lindgren ran DDK `1.9.2253347` on the OMAP4 Droid 4, with module `pvrsrvkm_omap4_sgx540_120`, "probably only needed for omap4 until the ddk 1.17 branch is usable". He needed omapdrm-to-PVR ioctl proxy changes that stay outside the mainline-bound tree (https://lists.dyne.org/lurker/message/20200314.184317.ae6d5d92.el.html). That system used TI's Linux user space, not Android (https://leste.maemo.org/Motorola_Droid_4/PowerVR).
- **Our path:**
  - Port DDK `1.9@2166536`'s kernel module, which glass-kernel already builds for 3.4, to mainline. Use openpvrsgx's 1.9.2188537 and 1.9.2253347 trees as the guide: same 1.9 branch, close builds.
  - The kernel module and the user space must be the same DDK build. The bridge ABI is build-specific; openpvrsgx's Kconfig says its ABI options "must match your usermode libraries".
  - **Effort:** months. Diff 2166536 against 2188537 to separate DDK changes from mainline API changes, carry the mainline changes over, then debug on hardware.
- **The harder part is the display path, not the GPU module:**
  - Glass's `gralloc.omap4430.so` and the TI hwcomposer expect ION, TILER and `dsscomp`. Mainline has `omapdrm` with dma-buf and no `dsscomp` or `omaplfb`.
  - So Android on mainline needs a new gralloc and composer. One option is AOSP's `external/drm_hwcomposer`: in 6.0.1 it is HWC 1.x and expects a DRM-aware gralloc, which TI's ION gralloc is not.
  - It also needs the ioctl-proxy work Lindgren described, and the Glass panel FPGA and glasshub drivers that route 3 needs anyway.
  - No Android user space on mainline OMAP4 was found. The closest relative is TI's Processor SDK Android for AM57xx: Android 6 up to 04.01.00, on kernel 4.4 LTS.
- **Risks:**
  - the 2166536 user space may rely on interfaces of TI's 3.4 display stack that no shim can recreate;
  - every step needs hardware, and probably a serial console;
  - the work overlaps with route 3 and glass-xec-mainline, so it should be done there.
- **Fallback: software rendering.**
  - 6.0's own software GL, `libagl`, is GLES 1.x only, and HWUI needs GLES 2.
  - 6.0's manifest has `external/mesa3d` but no SwiftShader (SwiftShader appears in AOSP's manifest only by 8.1).
  - So software rendering on Android 6 means Mesa softpipe/llvmpipe on a 1 GHz A9: probably too slow for HWUI, unverified.
  - On plain Linux (route 2) software rendering is already the baseline.
- **No open user-space SGX driver exists.**
  - Mesa's PowerVR driver covers Rogue (Series 6 and later) only. Mesa's docs say GPUs before Series 6 "do not have the hardware capabilities" for its Vulkan driver (https://docs.mesa3d.org/drivers/powervr.html).
  - The only related effort found is one reverse-engineered DRI driver that pairs with the DDK 1.17 blobs (Ivaylo Dimitrov, 2021, https://lists.goldelico.com/pipermail/openpvrsgx-devgroup/2021-October/000472.html). It still uses Imagination's closed shader compiler and libraries.
  - Writing a fully open SGX540 user-space driver (compiler, GLES, command stream) is a multi-year reverse-engineering project. **Not planned.**

**Doze and App Standby in 6.0** (`frameworks/base/services/core/java/com/android/server/DeviceIdleController.java`, `android-6.0.1_r81`):
- Both are off unless the device overlay sets `config_enableAutoPowerModes=true` (default `false`).
- Deep idle starts only with the screen off and no charger. The states run:
  - INACTIVE, 30 min;
  - IDLE_PENDING, 30 min, significant motion armed;
  - SENSING, 4 min, the accelerometer through `AnyMotionDetector`;
  - LOCATING, 30 s;
  - IDLE, 1 h, doubling up to 6 h, with maintenance windows of 5-10 min.
- **Without a `TYPE_SIGNIFICANT_MOTION` sensor, `DeviceIdleController` schedules no alarms.** The source says this "effectively turns off normal execution of device idling". Glass's sensors HAL must therefore expose a significant-motion sensor, for instance a virtual one fed by the MPU accelerometer or by glasshub.
- A phone's "stationary for 30 minutes" is the wrong signal for a head-worn device. Glass is either on the head (it moves all the time, so it never dozes) or off the head on a table. The better signal is glasshub's on-head detector. Two options:
  - a sensor-HAL significant-motion sensor that stays quiet while Glass is off-head;
  - shorter `DeviceIdleController` constants through `Settings.Global.device_idle_constants`, a 6.0 setting.

  Both need the R4 glasshub spec.
- Light Doze (screen off, still moving) arrived only in 7.0.

**Runtime permissions** (`DefaultPermissionGrantPolicy.java`, 6.0.1):
- 6.0 grants runtime permissions automatically only to:
  - packages with a uid below 10000;
  - apps that are privileged, persistent and platform-signed;
  - hard-coded default handlers (dialer, camera and so on).
- `/system/etc/default-permissions` arrived in 7.1. Apps with `targetSdkVersion < 23` keep install-time grants.
- For Glass, which has no touchscreen dialog flow worth having: our own system services run as system uid or platform-signed privileged apps and get their grants that way. A small patch to `DefaultPermissionGrantPolicy` covers our Glass apps. User-installed apps that target 23 show the standard dialog, which must be answerable with the touchpad. Otherwise the companion app sends `pm grant` over adb as a fallback.

**Low-RAM and ART knobs in 6.0:**
- `ro.config.low_ram`: `isHighEndGfx()` becomes false, recent tasks go from 100 to 50, and background service starts from 8 to 1 (`ro.config.max_starting_bg` overrides) (`ActivityManager.java`, `ActiveServices.java`).
- LMK `minfree`: `ProcessList.java` scales between a low table (12-48 MB) and a high table (72-180 MB) by memory (350-700 MB) and display size (480x800 to 1280x800). A 1 GB device lands on the high table.
  - Overlays: `config_lowMemoryKillerMinFreeKbytes*`, `config_extraFreeKbytes*`.
- dex2oat filters (`art/dex2oat/dex2oat.cc`): `verify-none`, `interpret-only`, `verify-at-runtime`, `space`, `balanced`, `speed`, `everything`, `time`.
- installd (`frameworks/native/cmds/installd/commands.cpp`) reads:
  - `dalvik.vm.dex2oat-filter`, `dex2oat-flags`, `dex2oat-Xms`/`-Xmx`;
  - `dex2oat-threads`, `boot-dex2oat-threads`, `image-dex2oat-threads`;
  - `dex2oat-swap` (a swap file is on by default in 6.0: `kDefaultProvideSwapFile = true`);
  - `ro.config.low_ram`.
- Build flags: `WITH_DEXPREOPT`, `WITH_DEXPREOPT_BOOT_IMG_ONLY` (tuna used it), `WITH_DEXPREOPT_PIC` (espresso used it; saves `/data`), `DONT_DEXPREOPT_PREBUILTS` (https://source.android.com/docs/core/runtime/configure).
- `build/core/combo/arch/arm/armv7-a-neon.mk` (6.0.1) still has no `cortex-a9` case: the A9 variant gets `-march=armv7-a` and `--fix-cortex-a8`. `bionic/libc/arch-arm/cortex-a9/` has A9 `memcpy`, `memset`, `stpcpy`, `strcat`, `strcmp`, `strcpy` and `strlen`.
- `SystemServer.java` (6.0.1) still honours `config.disable_storage`, `_bluetooth`, `_location`, `_systemui`, `_noncore`, `_network` and `_networktime`. `config.disable_telephony` and `config.disable_media` are gone.

**HAL changes from 4.4 to 6.0** (`hardware/libhardware/include/hardware`, 4.4.4_r2 against 6.0.1_r81):

| HAL | 4.4.4 | 6.0.1 | For Glass |
|---|---|---|---|
| Audio | 2.0 | adds 3.0 | the 2.0 HAL still loads; R3 audio targets 6.0 already (`android-6.0.1_r31-audio`) |
| Sensors | 1.1 | adds 1.2-1.4 | 1.0/1.1 still work; SensorService emulates batch/flush below 1.1 and adds virtual fusion sensors when missing; add significant motion (Doze) |
| Camera | up to 3.1 | 3.2/3.3 | HAL1 still supported, with the camera2 "HAL1 shim"; TI's OMX HAL1 over Ducati stays |
| hwcomposer | up to 1.3 | 1.4/1.5 | the TI HWC 1.0 composer still loads |
| Power | 0.2 | 0.3 | `POWER_HINT_LOW_POWER` (from 5.0) and `setFeature` (0.3) |

- Bluetooth moved from `external/bluetooth/bluedroid` to `system/bt`. The vendor `libbt-vendor` interface is the same family; rebuild it.
- SELinux: 6.0's init only warns when a service has no domain, but enforcing is expected from 5.0 on. The device tree boots permissive now (`androidboot.selinux=permissive`); writing the policy is a task here.
- fstab: 6.0 has `voldmanaged=`, `zramsize=`, `swapprio=`, `notrim`, `formattable`, `forceencrypt=` and `verify`. init.rc adds `writepid`, `exec`, `restorecon_recursive` and `load_persist_props` (`system/core/init/readme.txt`).

## Global constraints

The same as Track A's:
- no Google file in any repository;
- no change to voltages, frequencies, thermal limits or charging;
- kernel work only through glass-kernel's variants;
- device tree changes only through that repository's own pull requests;
- small pinned AOSP patches;
- nothing tested on hardware: device checks marked **not run**;
- `fastboot boot` only, never `bootloader`, `xloader` or `fpga`;
- English.

Binaries come only from the owner's XE24 image. Unlegacy's 1.14 set is not used unless the owner decides otherwise.

## Review focus

1. Graphics compatibility: do the open `libEGL_POWERVR` wrapper and the two `frameworks/native` patches fit DDK `1.9@2166536`, and is nothing else needed? (Task 2)
2. Doze on a head-worn device: is the significant-motion source sound, and can Doze never trigger while Glass is on the head and in use? (Task 4)
3. Permissions: do our system services get every runtime permission they need without dialogs? (Task 5)
4. SELinux policy: no `allow` wider than the device needs. (Task 6)
5. Nothing touches power or thermal limits. (All tasks)

---

### Task 1: Base, manifest and OMAP4 projects

**Files:**
- Create (in the repository the owner picks): `manifests/glass-6.0.1.xml`, `docs/marshmallow-base.md`.

- [ ] **Step 1:** Pin AOSP `android-6.0.1_r81`, the last 6.0.1 release, or keep `r31` if the device tree's branch name binds it. Record the choice.
- [ ] **Step 2:** Take `hardware/ti/omap4` from `LineageOS/android_hardware_ti_omap4` cm-13.0, or omap4-aosp `aosp-6.0`, at a pinned commit. Remove the `pvr-source` (2291151) kernel module: glass-kernel builds ours.
- [ ] **Step 3:** Minimal manifest as in Track A, Task 1, Step 3.
  - Verification: `repo sync -c --depth=1` succeeds; record the size.
- [ ] **Step 4:** Commit: `Marshmallow 6.0.1 manifest and base choice`.

### Task 2: Graphics on KitKat-era binaries

**Files:**
- Modify (fork): `frameworks/native` (screenshot through `glReadPixels`, b/10194508 workaround), `frameworks/av` (TI colour format).
- Modify (device tree, own pull request): `BoardConfig.mk` (`BOARD_EGL_WORKAROUND_BUG_10194508 := true`), `device.mk` (`libEGL_POWERVR_SGX540_120` built from source in place of the blob; `omap4.mk` properties), `proprietary-files.txt` (drop the `libEGL_POWERVR_SGX540_120.so` blob only after the device check).

- [ ] **Step 1:** Cherry-pick the patches with their authorship, and record each commit in `docs/marshmallow-base.md`.
- [ ] **Step 2: Static check.** The open wrapper calls `IMGegl*` symbols. Run `readelf --dyn-syms` on the owner's `libIMGegl_SGX540_120.so` (`1.9@2166536`, on the owner's machine only) to check that every symbol the wrapper imports exists. Record the result as facts (symbol names only) in `docs/marshmallow-base.md`.
  - If any symbol is missing: stop and report.
- [ ] **Step 3: Static check of the other blobs.** For every extracted ELF, list `NEEDED` libraries and undefined symbols, and resolve them against the 6.0.1 build output. Every unresolved symbol needs a shim library. AOSP 6.0 has no shim mechanism: either port CyanogenMod cm-13.0's `LD_SHIM_LIBS` linker patch, or add the shim to the blob's `NEEDED` list by other means; choose when the list is known.
  - Expected: a short list, mostly in `libgui`/`libui`/`libbinder` for camera and audio blobs. Write it down before writing any shim.
- [ ] **Step 4:** Build. Expected: the build passes and `libEGL_POWERVR_SGX540_120.so` comes from source.
- [ ] **Device checks (not run):**
  - SurfaceFlinger starts with GLES 2;
  - HWUI draws;
  - `screencap` works;
  - the camera preview works;
  - no `PVRSRV_ERROR_BUILD_MISMATCH` in `logcat`.

### Task 3: Lean system

The same items as Track A, Task 4, with these 6.0 differences:

| Item | 6.0 specifics | Expected effect | Risk |
|---|---|---|---|
| Unused services | `config.disable_telephony`/`_media` are gone in 6.0; remove telephony by not building `TeleService`/`TelephonyProvider` and setting `config_voice_capable=false`, `config_sms_capable=false`; `config.disable_networktime` if time comes from the phone link | fewer threads in system_server | apps calling `TelephonyManager` must get "no phone" |
| Unused apps | as Track A; 6.0 also adds `PrintSpooler`, `Telecom`, `ExternalStorageProvider`, `BasicDreams`, `PhotoTable`, `WallpaperCropper`: drop what Glass does not use; keep `Telecom` only if Bluetooth audio needs it (check) | smaller image and first boot | same as Track A |
| dex2oat policy | `WITH_DEXPREOPT := true` with `WITH_DEXPREOPT_PIC := true` (already set): the system is compiled at build time with the filter of `PRODUCT_DEX_PREOPT_DEFAULT_FLAGS` (`speed`), so first boot is short; `dalvik.vm.dex2oat-filter` is one global value for what installd compiles on the device, `space` (or `interpret-only`); keep `dex2oat-swap`. A per-package override needs an installd patch as in Track A | shorter install, less `/data` | `interpret-only` costs CPU at run time; a global filter also applies to system apps updated on the device |
| Heap for 640x360 | `dalvik.vm.heap*` as in Track A; 6.0's ART has the moving collector, so fragmentation is lower and smaller heaps hold up better | more processes cached | large bitmaps fail as in Track A |
| `ro.config.low_ram` | in 6.0 it also cuts background service starts to 1 | less background work at boot and on network changes | slower to deliver push messages to apps; measure |
| LMK | 1 GB lands on the high `minfree` table (72-180 MB); for a 640x360 device lower `config_lowMemoryKillerMinFreeKbytesAdjust` after measurement | more processes cached | jank if free memory runs out; measure |
| JobScheduler | in 6.0 already: our services schedule through it, not raw alarms, so the system batches them with everything else | fewer wakeups | none |
| Cortex-A9 code generation | as Track A (the 6.0.1 `armv7-a-neon.mk` has the same gap), plus `TARGET_CPU_VARIANT := cortex-a9` | as Track A | as Track A |
| Log reduction | 6.0 has `logd`: keep `persist.logd.size` at 6.0's 256K default or lower, and no kernel log reader in logd | less RAM and CPU | harder debugging |
| SystemUI minimal | as Track A; 6.0 SystemUI also hosts the volume dialog, quick settings, screen pinning and doze UI; hide the status and navigation bars through overlays, keep power warnings and volume | less RAM | as Track A |
| Wi-Fi and Bluetooth | as Track A; turn off `wifi_scan_always_enabled` (there since 4.3, so Track A too) | less idle drain | none known |
| zRAM, KSM | as Track A; tuna cm-13.0 turned zRAM off at one point, so measure before keeping it | as Track A | as Track A |

- [ ] **Step 1:** Apply the property and makefile rows through the device tree's own pull requests, one topic each.
- [ ] **Step 2:** Build. Expected: `build.prop` shows each property; `system.img` size recorded.
- [ ] **Device checks (not run):**
  - boot;
  - no crash loop with the removed packages;
  - low-battery warning;
  - Wi-Fi and Bluetooth reconnect after screen-off.

### Task 4: Doze on a head-worn device

**Files:**
- Modify (device tree, own pull request): `overlay/frameworks/base/core/res/res/values/config.xml` (`config_enableAutoPowerModes=true`).
- Create (R3 sensors HAL, its own plan): a significant-motion sensor.

- [ ] **Step 1:** Write the Doze design into the R3 sensors plan and the R4 services plan:
  - significant motion reports "moved" whenever Glass is on the head (glasshub on-head), so Doze cannot start while Glass is worn. Significant motion is a one-shot trigger sensor: this relies on `DeviceIdleController` re-arming it each time it enters IDLE_PENDING, an assumption to check in the source and on the device;
  - off the head, it reports only real motion.
- [ ] **Step 2:** Set `device_idle_constants` for a device that is either worn or lying on a table:
  - `inactive_to` 10 min instead of 30;
  - `sensing_to` 1 min;
  - `locating_to` 0, since there is no GPS fix indoors and a location is not needed for this.

  6.0's `SettingsProvider` has no default for `device_idle_constants` (`DatabaseHelper.java` never loads it), so this needs a small `loadSetting` patch in our fork, or the R4 service writes it at first boot.
- [ ] **Step 3:** Until the sensor exists, Doze cannot start on its own, as the source says. Do not enable `config_enableAutoPowerModes` before Step 1 is done, or App Standby alone runs without Doze.
- [ ] **Device checks (not run):**
  - `dumpsys deviceidle` shows the states advancing off-head with the screen off;
  - on the head, the state stays ACTIVE;
  - the OpenMyGlass phone link still delivers notifications in IDLE: it must be whitelisted (`dumpsys deviceidle whitelist +<pkg>`, or a `sysconfig` `allow-in-power-save` entry).

### Task 5: Runtime permissions

- [ ] **Step 1:** List the permissions each of our services and apps needs (camera, microphone, location, storage, Bluetooth).
- [ ] **Step 2:** Run the services as platform-signed privileged system apps, and add a small `DefaultPermissionGrantPolicy` patch for our Glass app packages, since 6.0 has no `default-permissions` XML.
- [ ] **Step 3:** Check that the standard permission dialog can be answered with the touchpad (swipe and tap), for user-installed apps.
- [ ] **Device checks (not run):** `dumpsys package <pkg>` shows the runtime permissions granted after first boot without any dialog.

### Task 6: HALs, SELinux and init for 6.0

- [ ] **Step 1:** The power, lights, audio, sensors and camera HALs come from R3, which already targets 6.0 on the device tree's default branch. Here, only check API versions: power 0.2 is fine; sensors exactly 1.1, the newest 4.4 loads, if one HAL serves both tracks (1.3 would need a separate Track B build); HWC 1.1.
- [ ] **Step 2:** Bluetooth: rebuild `libbt-vendor` for `system/bt`; check the device tree's `bluetooth/` config.
- [ ] **Step 3:** SELinux:
  - write `sepolicy/` for the device nodes in `docs/hardware-facts.md` (pvrsrvkm, dsscomp, tiler, rpmsg, glasshub, IIO, si114x);
  - collect denials in permissive mode on the device;
  - go enforcing only after a clean run.
- [ ] **Step 4:** Build. Expected: `sepolicy` compiles; `checkpolicy` has no neverallow violation.
- [ ] **Device checks (not run):** `getenforce`; no `avc: denied` during boot, camera, audio, Wi-Fi and Bluetooth use.

### Task 7: Towards mainline (long-term, not in the first release)

Belongs to the kernel's mainline track (roadmap, "Kernel versions"), together with route 3 and glass-xec-mainline. Listed here because Android 6 is the Android version meant to run on it.

- [ ] **Step 1:** Port the DDK `1.9@2166536` kernel module (glass-kernel) to mainline, using openpvrsgx's `1.9.2188537` and `1.9.2253347` trees as the guide. Keep the user-space ABI unchanged.
- [ ] **Step 2:** A display path for Android on mainline:
  - a gralloc on dma-buf and omapdrm, plus `drm_hwcomposer` or a small HWC 1.x of our own;
  - the omapdrm-to-PVR glue that Lindgren needed on the Droid 4.
- [ ] **Step 3:** Fallback when hardware rendering does not work: Mesa softpipe/llvmpipe for Android (expected too slow), or plain Linux (route 2).
- [ ] **Start condition:** a Glass with a reachable serial console, and mainline booting past the current reset. Not before.

### Task 8: Measurement on hardware

Shared with Track A: see the roadmap's "Measurement plan". This track adds:
- the time and storage of build-time dexpreopt;
- Doze state transitions.

## Decisions for the owner

1. AOSP release to pin: `r81` (last) or `r31` (the device tree's branch name).
2. Unlegacy's DDK `1.14@4081762` binaries: not used, which keeps the rule that binaries come only from the owner's image, unless the owner decides otherwise after weighing licence and gain.
3. Doze: enable only after a significant-motion source exists (Task 4), or leave it off.
4. Where the forks and manifest live, and the build machine: as in Track A.
