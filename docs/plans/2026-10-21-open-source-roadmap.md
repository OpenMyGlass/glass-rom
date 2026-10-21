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
| R2 | Kernel: GPU module from source, then low-risk tuning | glass-kernel | `pvrsrvkm_sgx540_120.ko` built from OMAP4-AOSP `pvr-source` (MIT/GPL-2.0) once its DDK version matches XE24's user-space libraries. With the binary module gone, the config cleanups that change struct layouts become possible. Then, from `reports/Ottimizzazioni kernel OMAP4.md`, only items rated no or low risk: interactive backports (`io_is_busy`, per-frequency `above_hispeed_delay`), the xrr02 input-boost handler, linux-3.4.y stable up to 3.4.113, and a check of the XE-C 2 GB memory map. No overclock, undervolt or raised thermal limit. |
| R3 | Open HALs | android_device_glass_glass-1 | power HAL (interactive values, boostpulse, screen-off cap), lights, audio (finish `android-6.0.1_r31-audio`), sensors over IIO, camera from TI's OMAP4 HAL on top of the Ducati blob. Each removes one entry from `proprietary-files.txt`. |
| R4 | Glass system services, clean-room | new repo | touchpad gestures, head gestures, on-head and wink detection (needs the glasshub protocol), screen wake. Spec written from observations, code written only from the spec. |
| R5 | Glass apps, clean-room | new repo | card timeline launcher at 640×360, settings, setup, camera, voice with an open hotword; dictation goes through OpenMyGlass to the phone. |

## Reverse engineering the binaries

Any binary on the "stays binary" list, and any HAL, daemon or library that a phase replaces, may be reverse engineered to learn its interfaces, for interoperability:
- **Tools:** the REA MCP server (`rea-agents`, with JADX and Ghidra as providers), plus whatever the target needs: Ghidra for ARM/Thumb `.so` files and Cortex-M3 firmware, a TI C6000 disassembler for the Tesla DSP. Install them when a phase needs them.
- **Workspace:** `_re/` in OpenMyGlass, which is not versioned. Decompiled code, disassembly and extracted files never leave it.
- **Clean room:** what reverse engineering finds goes into a spec under `docs/specs/`: interfaces, ioctls, sysfs paths, message formats, timings, and where each fact was observed. The open replacement is written from the spec only, by an implementer (person or agent) who has not read the decompiled code.
- **Order:** the targets of the next phase come first:
  1. R3: `audio.primary.glass_1.so` and `libglassalsa.so`, `sensors.glass_1.so` (InvenSense MPL), `gps.omap4.so`;
  2. Glass daemons: `sysproxyd`, `shm_service`, `bqflash`, `raft`, `bootconfig`;
  3. R4: `libglassgaze.so` and the glasshub protocol, `libglass_services_jni.so`, `libglassinputdevice.so`;
  4. the camera libraries.

  PowerVR user space and chip firmware (Ducati, Tesla, BCM4330, glasshub) come last. Reversing them documents the interfaces, but they stay binary unless a replacement turns out to be realistic.

## Open decision

The device tree's default branch targets Android 6.0.1 with blobs built for KitKat; the 5.1.1 branch is the only one reported to have booted (2016, XE22 blobs). Which Android version to build is decided before R3, when the first HAL needs a target API.
