# Track A: lean Android 4.4.4 KitKat, ART only — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Android 4.4.4 system for Glass Explorer from source that runs **ART only**: Dalvik (`libdvm`, `dexopt`) is not built, and all code is compiled by `dex2oat`. The system should use less CPU and RAM and run cooler than stock XE24 while keeping as many apps working as possible. This is the near-term target because Glass's binaries (PowerVR user space, audio, sensors, camera) were built for KitKat and run on it without shims.

**Architecture:**
- Base: AOSP `android-4.4.4_r2` with the OMAP4 hardware projects, plus our device tree on a KitKat branch of `android_device_glass_glass-1`. Whether `hardware/ti/omap4` comes from AOSP, CyanogenMod cm-11.0 or Unlegacy-Android is chosen in Task 1.
- Kernel: glass-kernel `tuned-stable` (3.4.113), the same as Track B. Any kernel change for this track (zRAM, KSM) goes through glass-kernel phases; this plan only says which config it needs.
- Changes to AOSP projects are small patches kept in forks under OpenMyGlass, pinned by a manifest. Where those forks and the manifest live is a decision for the owner (see "Decisions for the owner").
- Google's Java and JNI parts of the Glass system (`glass-core.jar`, `glass-services.jar`, `libglass_services_jni.so`, the Glass apps) are **not** part of this build. They are replaced by the native clean-room services and apps of roadmap phases R4 and R5. So ART compatibility matters for open-source code and for apps the user installs, not for Google's Glass code.

**Tech stack:** AOSP 4.4 make build (Ubuntu 12.04/14.04 container, JDK 6, GNU make 3.81/3.82, Python 2.7), the GCC 4.7/4.8 prebuilts of 4.4.

**Spec:** glass-rom roadmap, "Android tracks", Track A.

## Facts this plan rests on

Each fact names where it was read. AOSP paths are at tag `android-4.4.4_r2` on android.googlesource.com unless stated otherwise.

**Stock XE24** (`/system/build.prop` and `/system` of `glass_1-img-5585826`):
- XE24 ships both runtimes: `libdvm.so`, `libart.so`, `libart-compiler.so`, `dexopt`, `dex2oat`, `oatdump`, `core.jar` and `core-libart.jar`.
- It runs Dalvik: `persist.sys.dalvik.vm.lib=libdvm.so`, `dalvik.vm.dexopt-flags=m=y`, and the image is odexed.
- Heap: `heapstartsize=5m`, `heapgrowthlimit=72m`, `heapsize=192m`, `heaptargetutilization=0.75`, `heapminfree=512k`, `heapmaxfree=2m`.
- `dalvik.vm.jit.codecachesize=0`: the Dalvik JIT is off, which is the low-RAM setting.
- No `ro.config.low_ram`.
- zRAM is already configured: 128 MiB (`zramsize=134217728` in the fstab, `swapon_all` in `init.omap4430.rc`; see the device tree's `docs/hardware-facts.md`).

**How 4.4 selects a runtime:**
- `build/target/product/core_minimal.mk` sets `PRODUCT_RUNTIMES := runtime_libdvm_default` and then `+= runtime_libart`. `core/product_config.mk` includes one makefile per runtime; the `OVERRIDE_RUNTIMES` environment variable replaces the list.
- `runtime_libart_default.mk` sets `persist.sys.dalvik.vm.lib=libart.so` and includes `runtime_libart.mk`. That file adds `core-libart libart dex2oat oatdump` and sets `DEX_PREOPT_DEFAULT := nostripping` ("We currently don't suport DEX_PREOPT for art").
- `runtime_libdvm.mk` adds `core libdvm dexopt`. `runtime_common.mk` (`dalvikvm`, `libnativehelper`, `libjavacore`, dexdump) is shared.
- **ART-only product:** `PRODUCT_RUNTIMES := runtime_libart_default`, set after inheriting `core_minimal.mk`.

**Three places fall back to Dalvik and need a patch:**
- `libnativehelper/JniInvocation.cpp`: `kLibraryFallback = "libdvm.so"`. It is used when the property is unset or `dlopen("libart.so")` fails. Without libdvm, zygote then dies, so the failure is at least loud.
- `frameworks/native/cmds/installd/commands.c`: `dexopt()` reads `persist.sys.dalvik.vm.lib` with default `libdvm.so`. It runs `/system/bin/dexopt` for `libdvm*` and `dex2oat` for `libart*`, and exits 69 otherwise.
- `frameworks/base/services/java/com/android/server/SystemServer.java` writes `persist.sys.dalvik.vm.lib` back from `VMRuntime.vmLibrary()`. The runtime picker in Settings, developer options (`select_runtime`), writes the same property; it must be hidden.
- In 4.4, `dalvikvm` comes from `art/dalvikvm` and loads the runtime through JniInvocation. The `Android.mk` files of `frameworks/base/core/jni`, `cmds/app_process`, `media/jni` and `services/jni` do not link libdvm. The `platform/dalvik` project stays, because it also provides `dx`, `libdex` and `dexdump`; only the `libdvm` and `dexopt` modules go.

**Pre-optimisation does not exist for ART in 4.4:**
- `core/dex_preopt.mk`, `java_library.mk` and `package.mk` only run the host `dexopt`, which writes Dalvik `.odex` files.
- `core/main.mk` turns `WITH_DEXPREOPT` on for `user` builds on Linux unless `DISABLE_DEXPREOPT=true`. With ART only, those odex files are dead weight. The device tree's `BoardConfig.mk` currently sets `WITH_DEXPREOPT := true` (`WITH_DEXPREOPT_PIC` is a 5.0+ variable).
- Everything is therefore compiled **on the device**:
  - `boot.art` and `boot.oat` at first boot (`art/runtime/gc/space/image_space.cc`, `GenerateImage()`, into `/data/dalvik-cache`, with `-Xms64m -Xmx64m` and `--image-classes=preloaded-classes`, and the `everything` filter by default for the image, `dex2oat.cc`);
  - then every APK, by installd at first boot and at install.

**dex2oat controls in 4.4:**
- None of the 5.0 properties exist: no `dalvik.vm.dex2oat-flags`, `image-dex2oat-flags` or `-Xcompiler-option` (`AndroidRuntime.cpp` reads only the Dalvik-era `dalvik.vm.*` properties).
- installd's `run_dex2oat()` passes only the zip and oat file descriptors and locations.
- Filters parsed by `art/runtime/runtime.cc`: `-compiler-filter:interpret-only|space|balanced|speed|everything`, and thresholds such as `-small-method-max:`.
- The default is `speed`, or `interpret-only` when ART is built with `WITH_ART_SMALL_MODE=true` (`art/build/Android.common.mk`, `runtime.h`).
- dex2oat compiles apps of 900 methods or fewer with `speed` anyway, unless the filter is `interpret-only`.

**The 4.4 ART was a preview:**
- Only non-moving collectors (mark-sweep, partial and sticky; `-Xgc:concurrent|noconcurrent`). The moving collectors (semi-space, mark-compact, concurrent copying) came in 5.0. So 4.4 ART does not break JNI code that keeps raw object pointers, the most common cause of 5.0 breakage.
- Google's own list of what ART checks more strictly than Dalvik: CheckJNI errors, `NoSuchFieldError`/`NoSuchMethodError` instead of NULL from `GetFieldID`/`GetMethodID`, a unified 16 KiB-checked stack, and obfuscator output that dex2oat rejects (unbalanced monitors, bad control flow). Source: https://developer.android.com/guide/practices/verifying-apps-art
- Apps reported broken under 4.4 ART in 2013-2014: WhatsApp and Titanium Backup (https://infinum.com/blog/art-vs-dalvik-introducing-the-new-android-runtime-in-kit-kat/), several games and emulators with crashes or install failures (https://nerdschalk.com/google-working-fix-art-android-runtime-module-resolve-force-close-installation-failures-apps/). Xposed never supported ART on KitKat. Most were fixed later by the apps themselves, but old APK versions stay broken.
- The same infinum article measured app install time on a Nexus 4 going from about 17 s to about 25 s.
- ART fixes between 4.4 releases (`platform/art` `+log`):
  - 4.4.1/4.4.2: monitor-check verifier errors became warnings, the verifier uses the exception type when a class is unresolved, compiler blacklist updates, a JDWP line-table fix.
  - 4.4.3: NewLocalRef/NewGlobalRef on cleared weak globals, `FindFieldID` with the class's own loader, miranda methods, a proxy stack-trace fix, a stack overflow on mutual recursion.
  - 4.4.4: no ART change.
  - So `android-4.4.4_r2` already carries every ART fix Google shipped for KitKat.

**What other ROMs did:**
- CyanogenMod cm-11.0 (`CyanogenMod/android_art`, branch `cm-11.0`) carried no large ART backports from AOSP master: AOSP tags plus dalvik-cache on `/cache` (`dalvik.vm.dexopt-data-only`), zygote descriptor-leak fixes, and `SetTargetMinHeapFree`/`SetTargetHeapConcurrentStart`. CM-11 kept Dalvik as the default (`android_build` cm-11.0, `core_minimal.mk`), and no official CM-11 device defaulting to ART was found.
- OmniROM android-4.4 added "verifier: Bypass monitor-{enter,exit} depth checks" and nothing else of note.
- No public ART-only KitKat ROM was found, so we are first. Expect to find bugs no one has reported.

**What 4.4 already has for low RAM** ("Running Android with low RAM", the 4.4 page of source.android.com, now kept only in `platform/docs/source.android.com`, branch `lollipop-release`, `src/devices/low-ram.jd`):
- `ro.config.low_ram`, `ActivityManager.isLowRamDevice()`, procstats, the memtrack HAL, ArrayMap, a trimmed system_server and SystemUI, and validated KSM and zRAM.
- `ro.config.low_ram` is aimed at 512 MB devices.
- KSM: `CONFIG_KSM`, plus `pages_to_scan 100`, `sleep_millisecs 500`, `run 1` under `/sys/kernel/mm/ksm/`.
- zRAM: `CONFIG_ZRAM` and swap, the fstab `zramsize=`, `/proc/sys/vm/page-cluster 0`. The page expects 30-50% compression and recommends no size.
- The `extra_free_kbytes` kernel patch with `config_extraFreeKbytes*` and `config_lowMemoryKillerMinFreeKbytes*` in `config.xml`.
- No heap-size recommendations.

**Other facts:**
- Alarm batching is already in 4.4: `AlarmManager` makes `set()`/`setRepeating()` inexact and batched for apps with `targetSdkVersion >= 19`; older apps keep exact alarms (`frameworks/base/core/java/android/app/AlarmManager.java`).
- `SystemServer.java` (4.4) skips groups of services when these properties are true: `config.disable_storage`, `config.disable_media`, `config.disable_bluetooth`, `config.disable_location`, `config.disable_systemui`, `config.disable_noncore`, `config.disable_network`. It also declares `config.disable_telephony` but never reads it, so it does nothing.
- `bionic/libc/arch-arm/cortex-a9/cortex-a9.mk` provides A9-tuned `memcpy`, `memset`, `strcat`, `strcmp`, `strcpy` and `strlen`, selected by `TARGET_CPU_VARIANT := cortex-a9`.
- `build/core/combo/arch/arm/armv7-a-neon.mk` has no `cortex-a9` case. For that variant it emits `-march=armv7-a -mfpu=neon` (not `-mcpu=cortex-a9`) and links with `-Wl,--fix-cortex-a8`, a workaround for a Cortex-A8 erratum that the A9 does not have.
- Heap presets in `frameworks/native/build/` (4.4): `phone-hdpi-512` is 5m/48m/128m with maxfree 2m; `phone-xhdpi-1024`, which the device tree inherits now, is 8m/96m/256m with maxfree 8m.

## Global constraints

- No Google file, and nothing copied or decompiled from one, in any repository, CI artifact or pull request. Glass binaries come only from the owner's image through `extract_vendor.py`.
- No change to voltages, OPPs, thermal limits, charging or fuel-gauge settings, in the kernel or through init scripts or the power HAL. Glass sits against the temple. "Cooler" comes from doing less work, never from moving limits.
- Kernel changes go through glass-kernel's own phases and variants (`stock`, `tuned`, `tuned-stable`); this plan only lists what it needs.
- The device tree (`android_device_glass_glass-1`) is changed only by its own pull requests, one topic each, on a KitKat branch. Its default branch stays Android 6.0.1, which is Track B.
- Every AOSP patch is small and in a fork pinned by commit. No vendoring of whole AOSP projects into OpenMyGlass repositories.
- Nothing is tested on hardware until a Glass is available. Every task ends with a build or static check plus device checks marked **not run**.
- Device tests use `fastboot boot` only. Never write `bootloader`, `xloader` or `fpga`.
- English.

## Review focus

1. The ART-only switch: is every Dalvik fallback patched (JniInvocation, installd, SystemServer, Settings), and does nothing else in the tree or in the extracted binaries link `libdvm.so`? (Task 2)
2. First boot: is compile time on a 1 GHz A9 bounded, and is there enough `/data` space for the boot image plus all apps? (Task 3)
3. Each lean item: is the claimed effect plausible, the risk stated, and does it stay reversible by one property or one makefile line? (Task 4)
4. Nothing in this plan touches power or thermal limits. (All tasks)
5. Compatibility: is every removed service or app something no supported app calls? (Tasks 4 and 6)

---

### Task 1: The base tree and the manifest

**Files:**
- Create (in the repository the owner picks): `manifests/glass-4.4.4.xml` (or `local_manifests/`) pinning AOSP `android-4.4.4_r2`, the OMAP4 hardware projects, our forks and the device tree's KitKat branch.
- Create: `docs/kitkat-base.md` in the same repository.

- [ ] **Step 1: Pick the OMAP4 hardware base.** Compare AOSP 4.4's `hardware/ti/omap4xxx` (Galaxy Nexus, `tuna`), CyanogenMod cm-11.0's `android_hardware_ti_omap4` and Unlegacy-Android's KitKat branches for: hwcomposer, camera HAL (OMX/Ducati), `libion_ti`, `libtiutils`, domx, and which PVR DDK 1.9 build each expects. Pick the one whose user-space expectations match XE24's DDK `1.9@2166536` and whose license is clear. Record why in `docs/kitkat-base.md`.
- [ ] **Step 2: Branch the device tree for KitKat.** The 2016 `android-4.4.4_r2.0.1` branch of `android_device_glass_glass-1` is Justin Driggers' initial commit, with `proprietary-blobs.txt`. Port the current clean-room `rootdir/`, `system.prop`, `proprietary-files.txt` and `tools/check_tree.py` from the 6.0.1 branch to a new KitKat branch. Note 4.4 vs 6.0 differences: the init.rc syntax is close, and SELinux is permissive in 4.4 by default; record the differences in that tree's docs. This happens in the device tree repository through its own pull request, coordinated with the agent working there.
- [ ] **Step 3: Minimal manifest.** Remove projects not needed for one ARM device: other devices, x86/MIPS prebuilts, darwin prebuilts, CTS and SDK. Use `repo init -g default,-device,-darwin,-mips,-x86` and `remove-project` entries.
  - Verification: `repo sync -c --depth=1` succeeds. Record the checkout size in `docs/kitkat-base.md`.
- [ ] **Step 4:** Commit: `KitKat 4.4.4 manifest and base choice`.

### Task 2: ART only

**Files (forks pinned in the manifest):**
- Modify: `build` (product makefile only if not done in the device tree), `libnativehelper/JniInvocation.cpp`, `frameworks/native/cmds/installd/commands.c`, `frameworks/base/services/java/com/android/server/SystemServer.java`, `packages/apps/Settings` (hide `select_runtime`).
- Modify (device tree, KitKat branch): `full_glass_1.mk` / `device.mk` (`PRODUCT_RUNTIMES := runtime_libart_default`), `BoardConfig.mk` (`DISABLE_DEXPREOPT := true`, drop `WITH_DEXPREOPT`, `WITH_DEXPREOPT_PIC`).

- [ ] **Step 1: Product.** After inheriting the AOSP product makefiles, set `PRODUCT_RUNTIMES := runtime_libart_default`. Expected: `out/target/product/glass_1/system/lib/` has `libart.so` and `libart-compiler.so` but no `libdvm.so`; `system/bin/` has `dex2oat` but no `dexopt`; `build.prop` has `persist.sys.dalvik.vm.lib=libart.so`.
- [ ] **Step 2: Fallbacks.**
  - JniInvocation: change `kLibraryFallback` to `libart.so`.
  - installd: change the default to `libart.so` and run `dex2oat` for any value.
  - SystemServer: keep the write-back, which now always writes `libart.so`.
  - Settings: remove the runtime picker.
  - Each is a one-line or few-line patch.
- [ ] **Step 3: No libdvm consumers.** Two static checks, wired into CI on the manifest repository:
  - `grep -r "libdvm" --include=Android.mk` over the synced tree;
  - `readelf -d` over every ELF in the build output and in the owner's extracted `vendor/glass/glass-1/proprietary/`, looking for `NEEDED libdvm.so`.

  The second check runs only on the owner's machine, since the binaries are never committed. Expected: no hits outside `dalvik/vm`. If a Glass binary needs libdvm, stop and report.
- [ ] **Step 4: Pre-optimisation off.** `DISABLE_DEXPREOPT := true`. Expected: no `.odex` in `system/`, and every APK and jar still holds `classes.dex`.
- [ ] **Step 5:** Build `aosp_glass_1-userdebug`. Expected: the build passes, and the image is smaller than an odexed build (record both sizes).
- [ ] **Device checks (not run):**
  - first boot completes;
  - `getprop persist.sys.dalvik.vm.lib` gives `libart.so`;
  - `/data/dalvik-cache` holds `system@framework@boot.art` and `boot.oat`;
  - `logcat` has no `JniInvocation` fallback warning;
  - `dumpsys meminfo` works.

### Task 3: Compile cost: first boot, install, storage

**Files:**
- Modify (fork): `frameworks/native/cmds/installd/commands.c`. `run_dex2oat` passes `--runtime-arg -compiler-filter:<filter>`, which 4.4's dex2oat accepts. The filter comes from `persist.glass.d2o.sys` for packages under `/system` and `persist.glass.d2o.usr` for the others. These are our own properties, since 4.4 has no `dalvik.vm.dex2oat-filter`. They are `persist.`, so they change without a rebuild, and short, since 4.4 limits property names to 31 characters (`PROP_NAME_MAX` 32). Per-package overrides cannot fit in a property name, so installd reads them from `/data/system/glass-dex2oat-filters`, one `package filter` line each.
- Modify (device tree): `system.prop` (the defaults of those properties).

- [ ] **Step 1: Filter policy.**
  - Boot image: keep `speed`, or `everything` as now. It is compiled once, and every process maps it.
  - System apps: `speed`.
  - User apps: `space` by default; `setprop persist.glass.d2o.usr speed` switches back.
  - `interpret-only`, through a line in the override file, is the fallback for an app that dex2oat fails on or that takes too long. Size it against `/data`: Glass has a 16 GB eMMC (`BOARD_USERDATAIMAGE_PARTITION_SIZE` is about 13 GiB), so storage is not tight, but compile time on the device is.
  - Do not build ART in small mode globally: it would make everything interpreted, which costs CPU at run time.
- [ ] **Step 2: Bound the first boot.** Show "optimising apps" progress (4.4 already does, through `PackageManagerService` `performBootDexOpt`). Keep the system image small (Task 4) so there is less to compile.
  - Target: first boot under 10 minutes on the device. This is unverified: nothing was measured on an A9 at 1 GHz.
- [ ] **Step 3: Optionally compile at build time** with a host `dex2oat`. 4.4's build cannot do this (no `dex_preopt_libart.mk`); a backport of 5.0's would take changes in `build/core` and `art/build`.
  - Mark as **not planned now**: first boot happens once, and 5.0's ART preopt depends on 5.0's image layout.
  - Revisit if the measured first boot is over 15 minutes.
- [ ] **Step 4:** Build. Expected: installd compiles, and `build.prop` sets the two default filter properties.
- [ ] **Device checks (not run):**
  - first-boot time (from `fastboot boot` to `sys.boot_completed=1`);
  - `/data/dalvik-cache` size;
  - time to install a 10 MB APK with `space` and with `speed`;
  - `boot.oat` size.

### Task 4: Lean system

Each item is one property or one makefile line and can be reverted alone. The "Effect" column is what the item is expected to do. Nothing is measured yet; Task 7 measures it.

| Item | How | Expected effect | Risk |
|---|---|---|---|
| Remove unused services | Glass is Wi-Fi only: do not build `TeleService`/`Phone`, `TelephonyProvider` or `Mms`, and set `config_voice_capable=false` and `config_sms_capable=false` (4.4's `config.disable_telephony` does nothing); `config.disable_media` stays false (camera, audio); drop wallpaper services, `DreamManager` users, print spooler, NFC | fewer threads and binder objects in system_server, roughly a few MB of RAM | an app that calls `TelephonyManager` must get "no phone", not a crash; check with a few apps |
| Remove unused apps | Build only what the Glass system needs: no Browser, Calendar, Contacts UI, Email, Gallery, Launcher2/3, Music, live wallpapers, Camera2, DeskClock, LatinIME (input comes from the phone) | smaller system image, less to dex2oat at first boot, less RAM | an app that expects a stock intent handler (`ACTION_VIEW` for a URL) finds none; keep `PackageInstaller`, `DocumentsUI`, `DownloadProvider` |
| `ro.config.low_ram=true` | `system.prop` | fewer cached processes, smaller recents, no live wallpapers, some system UI drawn in software | Aimed at 512 MB. On 1 GB it may cost smoothness (persistent processes lose hardware acceleration). Try it and measure; it is one property. Decision for the owner after measurement |
| zRAM | already 128 MiB in stock XE24; keep, `page-cluster 0`, try 25% of RAM (256 MiB on 1 GB, 512 MiB on XE-C) | more apps stay cached, fewer cold starts | compression costs CPU; LZO on an A9 is cheap but not free; measure swap-in rates |
| KSM | `CONFIG_KSM` (glass-kernel, `tuned` config), `run 1`, `pages_to_scan 100`, `sleep_millisecs 500` | a few MB saved across zygote children | the scanner thread wakes every 500 ms and costs battery; turn it off if idle drain grows |
| Preloaded classes trimming | Ship a `preloaded-classes` list cut down to the classes Glass's processes use, generated from our own system with 4.4's `frameworks/base/tools/preload` | smaller zygote and boot image, faster boot | classes not preloaded load per process on first use, a small start-up cost; regenerate when the app set changes |
| Preloaded resources trimming | Overlay `preloaded_drawables` (in `arrays.xml`): drop drawables for the status bar, notification shade and phone UI that never show | a few MB less zygote memory | none known, as long as the list only removes |
| Heap sizing for 640x360 | Replace `phone-xhdpi-1024-dalvik-heap.mk` with values sized for the screen: start at `phone-hdpi-512` (5m/48m/128m, maxfree 2m) and compare with XE24's 5m/72m/192m | smaller per-app heaps, more processes fit | apps that load large bitmaps get `OutOfMemoryError`; `largeHeap` apps keep 128m. A 640x360 ARGB frame is 0.9 MB, so 48m is still 50 frames |
| Remove the Dalvik JIT setting | drop `dalvik.vm.jit.codecachesize` (does nothing under ART) | cleanliness only | none |
| Alarm batching | already in 4.4 for `targetSdkVersion >= 19`; our services and apps target 19 and use `setWindow`/inexact alarms | fewer wakeups | none for us; old apps keep exact alarms |
| Wakeup reduction | audit wakelocks with `dumpsys power`/`batterystats` on the device; set `wifi.supplicant_scan_interval` (already 60 s), turn off `NetworkLocationProvider` scanning when no app asks | less idle drain | none known |
| Sensor batching through glasshub | head-gesture and on-head detection use glasshub's own detection (activity threshold and timeout in its sysfs) instead of the application processor polling the IMU | the A9 sleeps while the wearer is still; probably a large idle-drain item on a head-worn device (unmeasured) | needs the R4 glasshub spec; until then use the IMU at the lowest rate that works |
| Log reduction | userdebug for development, `user` for daily use; `persist.logd.size` does not exist in 4.4 (logger is a kernel driver): shrink the `/dev/log/*` buffers, which are fixed in `drivers/staging/android/logger.c` (a source change in glass-kernel, not a config option); our own code logs below `I` only behind `Log.isLoggable` | less CPU and RAM spent on logging | harder debugging; keep userdebug builds |
| Cortex-A9 code generation | `TARGET_CPU_VARIANT := cortex-a9` (A9 bionic string routines), and a one-case patch to `armv7-a-neon.mk` so the variant emits `-mcpu=cortex-a9 -mfpu=neon` and `--no-fix-cortex-a8` | a few percent faster native code, mostly in string and memory copies | the build mixes A9-tuned and generic code; harmless. GCC 4.7/4.8 support `-mcpu=cortex-a9` |
| hwcomposer from source | roadmap R3: TI's OMAP4 hwcomposer (`hardware/ti/omap4`) over `dsscomp` | overlays compose without the GPU, so the GPU sleeps more | must match the kernel's `dsscomp` interface; R3 plan |
| SystemUI minimal | Glass has no status bar or navigation bar: `config_showNavigationBar=false`, no status bar window (overlay), keep SystemUI's power warnings (low battery, thermal) and volume UI, or move them into our Glass service | less RAM (SystemUI is one of the largest persistent processes) and fewer redraws | `config.disable_systemui=true` would also remove the low-battery warning and the wallpaper; do not use it unless those move elsewhere |
| Wi-Fi power | `wifi.supplicant_scan_interval=60` (set), `wifi_scan_always_enabled=0`, Wi-Fi off when the screen is off and nothing is syncing (`wifi_sleep_policy`), BCM4330 power-save mode (driver default PM2, keep) | less idle drain | slower reconnection |
| Bluetooth power | sniff mode for the phone link (bluedroid default), no discoverable mode except during pairing, `bluetooth.enable_timeout_ms` set | less idle drain | the OpenMyGlass link latency grows slightly in sniff mode; measure |

- [ ] **Step 1:** Apply the rows that are makefile or property changes (services, apps, heap, A9 build, SystemUI overlay, Wi-Fi and Bluetooth properties), each as its own commit, in the device tree's KitKat branch through its own pull requests.
- [ ] **Step 2:** Generate `preloaded-classes` once the system has its final app set (needs a device; until then use AOSP's list).
- [ ] **Step 3:** List the kernel needs (KSM, zRAM size, logger buffer sizes) as a glass-kernel issue. They are not done here.
- [ ] **Step 4:** Build. Expected: `system.img` size recorded, smaller than Task 2's; `build.prop` shows every property; `readelf -A` on `libc.so` shows `Tag_CPU_name: "cortex-a9"`.
- [ ] **Device checks (not run):**
  - boot;
  - no crash loop in system_server with the disabled services;
  - SystemUI shows the low-battery warning;
  - Wi-Fi and Bluetooth still reconnect after screen-off.

### Task 5: Backports from 5.x and 6.x

Ranked by gain for Glass against cost. Only the first group is planned.

The power items (ranks 1, 6 and 7 below) are replaced by the [power backports plan](2026-10-22-kitkat-power-backports.md): its rank 1 ports the 5.0/6.0 alarm fixes, and its rank 2 moves this rank 1 into the framework as a Glass device idle built from 6.0's Doze, because only the framework can hold back other apps' alarms and wake locks. The Wi-Fi parts of this rank 1 stay in Task 4. The rows below are kept as first written.

| Rank | Backport | Gain | Cost | Verdict |
|---|---|---|---|---|
| 1 | Doze-like idle as a small service of our own: when the screen is off and the wearer is off-head (glasshub), defer alarms with `AlarmManager` batching, turn off Wi-Fi scans, hold the CPU in suspend | large: Glass's idle drain comes from wakeups | small: our own service using public 4.4 APIs and the glasshub on-head signal, no framework surgery | **planned**, with R4 |
| 2 | `extra_free_kbytes` and LMK `minfree` tuning (4.4 already has the knobs) | medium: fewer jank-causing direct reclaims | small: config values | **planned** |
| 3 | `onTrimMemory` handling in our own services and apps | medium | small | **planned** (applies to our code only) |
| 4 | dex2oat filter defaults for system and user apps, a per-package override and a `space` default | medium: shorter installs and first boot | small: Task 3's installd patch | **planned** (Task 3) |
| 5 | Selected later ART bug fixes, cherry-picked one by one when a real app fails on 4.4 ART | case by case | medium: 4.4's ART diverges fast from 5.0's | **when needed**, each fix with a test app |
| 6 | JobScheduler (5.0) as a framework service | small: our services schedule with alarms already; third-party apps that need it fall back to their compat libraries (JobSchedulerCompat, Firebase JobDispatcher, WorkManager on AlarmManager) | high: new system service, binder API, permissions, framework hidden API | **not planned**: the compat libraries already cover apps |
| 7 | Doze and App Standby (6.0) in the framework | medium over rank 1 | high: `DeviceIdleController` depends on 6.0's `AlarmManager`, `PowerManager` and network policy changes | **not planned**: rank 1 gets most of the gain on a device whose idle state glasshub already knows |
| 8 | Lollipop ART (moving GC, AOT preopt at build time) | medium: less fragmentation, faster boot | very high: new runtime ABI, `core-libart` and framework changes; no one has done it publicly | **not planned** |
| 9 | Project Svelte from 5.x/6.x (memory trimming in system_server) | small: 4.4 already has the main Svelte work | high: many scattered framework changes | **not planned** |

- [ ] **Step 1:** ~~Write rank 1 as a section of the R4 services plan.~~ Replaced by the power backports plan's rank 2 (framework device idle). The R4 glasshub service only has to send its on-head state (`com.android.server.glass.action.WEARER_STATE`).
- [ ] **Step 2:** Rank 2: set `config_extraFreeKbytesAdjust` and `config_lowMemoryKillerMinFreeKbytesAdjust` in the device overlay. Start from AOSP defaults and change only after measurement.

### Task 6: Compatibility

- [ ] **Step 1: App test list.** Pick about 20 apps a Glass user plausibly installs: a few GDK samples (open-source), a music player, a podcast app, a navigation app, a notes app, a camera app, a terminal and so on, in versions that support API 19.
  - The GDK's `com.google.android.glass` library is Google's and is not shipped. GDK apps need a clean-room stub library. That belongs to R5 and is out of scope here.
- [ ] **Step 2: CheckJNI.** Turn it on for the test pass only with `setprop dalvik.vm.checkjni true` then `adb shell stop; adb shell start` so zygote reads it (not `ro.`, so it can be turned off again; `ro.kernel.android.checkjni` is only the fallback when it is unset).
- [ ] **Step 3: Fallbacks per failure:**
  - (a) the `interpret-only` filter for that app;
  - (b) a cherry-picked ART fix (Task 5, rank 5);
  - (c) document the app as unsupported.

  There is no fallback to Dalvik: that is the owner's decision. Dalvik could come back as an emergency build flavour by restoring `runtime_libdvm`, but it is not maintained.
- [ ] **Device checks (not run):** install and start each test app; record pass, crash or dex2oat failure, and the start time.

### Task 7: Measurement on hardware

Shared with Track B: see the roadmap's "Measurement plan". This track adds:
- first-boot time;
- `/data/dalvik-cache` size;
- APK install time with each filter.

## Decisions for the owner

1. Where the AOSP forks and the manifest live: a new `OpenMyGlass/manifest` repository plus forks named `android_<path>`, the LineageOS convention, or a `local_manifests/` folder in glass-rom.
2. The OMAP4 hardware base (Task 1, Step 1), after the comparison.
3. `ro.config.low_ram` on a 1 GB device: on or off, decided from Task 7's numbers.
4. No Dalvik fallback in releases (assumed in this plan).
5. The build machine (roadmap, "Build infrastructure").
