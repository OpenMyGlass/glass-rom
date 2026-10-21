# Open graphics user space for the SGX540: effort estimate

**Question:** what would it cost to replace the PowerVR SGX540 user-space libraries of XE24 (the OMAP4430 GPU stack listed in [`xe24-blobs.md`](xe24-blobs.md)) with open code, and what can be used instead?

**Short answer:** about 26 to 54 person-months for open GLES 1/2 on top of the stock init program and GPU firmware, and 40 to 80 or more for a fully open stack. That is several person-years of expert work, it needs a Glass on the desk for nearly all of it, and no open SGX driver exists to start from. The open stack is **not planned**. What is planned instead is cheap: measure software rendering on the device once one is available, and keep the UI light enough for it.

All numbers are rough. They are for one experienced GPU driver developer with a working device, a serial or network log, and the stock libraries available for clean-room observation. They come from the public history of comparable drivers (below), adjusted for what is and is not public for SGX. This page uses only public information and open source code.

## What exists today

### The stock stack

From [`xe24-blobs.md`](xe24-blobs.md), all built from Imagination's DDK `1.9@2166536`:

| File | Size (bytes) | Role |
|---|---|---|
| `libsrv_um_SGX540_120.so` | 160856 | Services client: device memory, mapping, sync objects, command submission through the kernel bridge |
| `libsrv_init_SGX540_120.so`, `pvrsrvinit` | 111596, 9328 | One-shot GPU initialisation at boot; supplies the GPU microkernel ("EDM program") and register scripts |
| `libusc_SGX540_120.so` | 861320 | USSE shader compiler back end ("Universal Shader Compiler") |
| `libglslcompiler_SGX540_120.so` | 259164 | GLSL ES 1.00 front end |
| `libGLESv1_CM_POWERVR_SGX540_120.so` | 414924 | OpenGL ES 1.1 |
| `libGLESv2_POWERVR_SGX540_120.so` | 357584 | OpenGL ES 2.0 |
| `libEGL_POWERVR_SGX540_120.so`, `libIMGegl_SGX540_120.so` | 9152, 62660 | EGL 1.4 |
| `libpvrANDROID_WSEGL_SGX540_120.so` | 9352 | Window system glue for Android |
| `gralloc.omap4430.so` | 26676 | Android buffer allocator |
| `libpvr2d_SGX540_120.so` | 21480 | 2D blits |

The GL libraries and the compiler alone are about 1.9 MB of ARM code. That is a rough hint of size, not a measure of work.

### The open kernel driver

glass-kernel builds `pvrsrvkm` from the same DDK (`scripts/fetch-pvr.sh`, dual MIT/GPL-2.0, 164 C files, about 111,000 lines). It is the most useful public input. What it exposes:
- **The user-space ABI.** `services4/include/pvr_bridge.h` (about 140 bridge call definitions) and `sgx_bridge.h` (about 40 SGX calls) define every ioctl on `/dev/pvrsrvkm`, with their argument structures. The kernel side of each call shows what it does. The Android build is the non-DRM one (`SUPPORT_DRI_DRM` is off for `omap4430_android`).
- **Memory management.** Heaps, device virtual memory and the SGX MMU (`mmu.c`), buffer export and mapping, the display class interface (`kerneldisplay.h`) and sync objects.
- **Part of the firmware interface.** `sgx_mkif_km.h` and `sgxinfo.h` define the kernel CCB (circular command buffer), the host control block, the command types (`SGXMKIF_CMD_TA`, `_TRANSFER`, `_2D`, `_POWER`, ...) and the kernel-visible part of the TA command (`SGXMKIF_CMDTA_SHARED`: sync values and status updates). The comment says this is only "part of the TA command structure proper"; the rest is not in the kernel source.
- **Initialisation.** `SGX_BRIDGE_INIT_INFO` lists what user-space init hands over: memory for the CCB, host control, TA/3D control, the host kick addresses of the microkernel and register-write scripts (`sgxscript.h`). The kernel runs those scripts and starts the microkernel, but **the microkernel itself is not in the kernel source**: user space loads it.
- **Registers.** `hwdefs/sgx540defs.h` has 515 register defines, mostly the bus interface, MMU, clock gating, events and the USE code base. It does not describe the tile accelerator, ISP, TSP or PDS state words, and nothing of the shader instruction set.

[openpvrsgx](https://github.com/openpvrsgx-devgroup/linux_openpvrsgx) (Letux) carries the same kernel driver forward for mainline kernels. Its own description says it is "NOT about reverse engineering or user-space components (firmware and libs), just the kernel device drivers". It is DDK `1.9@2188537`, which does not match XE24's libraries (see the roadmap).

### Public documentation from Imagination

- The *PowerVR Series5 Architecture Guide for Developers* describes the tile-based deferred renderer at a level useful to application developers ([Imagination forum](https://forums.imgtec.com/t/sgx-architecture-guide-for-developers-document/1114)).
- The instruction set is not public: "Documentation for the Series5 and Series5XT instruction set are available under NDA" (Imagination, 2015, [forum](https://forums.imgtec.com/t/instruction-set-for-powervr-gpus/2326)).
- Imagination's open drivers are for Rogue and later only: the Vulkan driver in Mesa 22.1 ([Phoronix](https://www.phoronix.com/news/Mesa-22.1-PowerVR-PVR-Vulkan), [merge request](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/15243)) and the `drm/imagination` kernel driver ([LKML](https://lkml.rescloud.iu.edu/2311.2/07309.html)). Coverage at the time said Imagination did not appear to support pre-Rogue IP with them ([Phoronix](https://www.phoronix.com/news/Open-Source-PowerVR-Vulkan)). Rogue is a different architecture (new ISA, firmware processor, command formats), so the code does not carry over to SGX; only Mesa's shared infrastructure does.
- No SGX user-space code or ISA document has been published as far as public sources show.

### Open SGX user-space efforts

- **[SGX535-reMESA](https://github.com/gabrieelgama/SGX535-reMESA)** (MIT), a Mesa/Gallium driver for the SGX535 in Intel GMA 500. Started 16 September 2026. Its README reports a first GPU triangle on 6 October and a `glDrawArrays` through Gallium on 21 October 2026, and a partial USSE encoder and decoder; it says repeated submissions, synchronisation and presentation are not yet verified. It targets desktop GL 2.1 on x86. Its stated sources include disassembly and Ghidra analysis of the original compiler, which matters for provenance (see Decisions).
- The Replicant project's graphics research page lists an SGX reverse-engineering attempt with no progress after 2013 (page currently behind a bot wall; summary from its [search snippet](https://redmine.replicant.us/projects/replicant/wiki/GraphicsResearch)).
- Letux and Maemo Leste use the closed user space on top of an open kernel driver. A 2019 Letux thread notes that a mainline kernel driver is blocked because "there is no open source userspace library for SGX" ([letux-kernel](https://lists.goldelico.com/pipermail/letux-kernel/2019-February/003202.html)).
- Mesa has no SGX driver. The [freedesktop PowerVR page](https://dri.freedesktop.org/wiki/PowerVR/) has nothing on SGX.

SGX535 and SGX540 are both Series5: same USSE family, same microkernel model, same DDK. The SGX540 has 4 USSE pipes (`sgxfeaturedefs.h`), and its register header differs a lot from the SGX535's (`diff` of `sgx535defs.h` and `sgx540defs.h` gives 532 changed lines; the files have 739 and 605 lines), so register-level work is per chip. If reMESA matures, much of its ISA and state knowledge would apply to Glass.

## Comparable drivers built without vendor code

| Driver | GPU | Start | First triangle with own code | Usable GLES2 upstream | People | Firmware |
|---|---|---|---|---|---|---|
| Freedreno | Adreno 2xx/3xx | 2012 ([Phoronix](https://www.phoronix.com/review/qualcomm_freedreno/2)) | 2012 | Mesa 9.2, 2013 ([Phoronix](https://www.phoronix.com/news/MTMyNTE)) | 1 (Rob Clark, spare time at first) | vendor microcode |
| Lima | Mali-400 | 2011/2012 ([Phoronix](https://www.phoronix.com/review/arm_mali_reverse/3)) | early 2012 (FOSDEM demo, [Phoronix](https://www.phoronix.com/news/MTA0OTQ)) | Mesa 19.1 and Linux 5.2, 2019, "not ready for daily usage" at merge ([MR 465](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/465), [Phoronix](https://www.phoronix.com/news/Mesa-19.1-Picks-Up-Lima)) | 1 at first, restarted by Qiang Yu and others | none |
| Etnaviv | Vivante GC | 2012 ([XDC 2015](https://wiki.freedesktop.org/xorg/Events/XDC2015/Program/Stach_etnaviv.pdf)) | 2013 ([Phoronix](https://www.phoronix.com/news/MTI3MjU)) | kernel 4.5, 2016; Mesa 17.0, 2017 ([LPC](https://lpc.events/event/9/contributions/618/attachments/729/1334/etnaviv_status_update.pdf)) | 1, then 3 to 4 | none |
| Panfrost | Mali Midgard | 2017/2018 | 2018 (ES 2.0 prototype, [XDC 2018](https://webcf.waybackmachine.org/web/20210615031847/https:/xdc2018.x.org/slides/Panfrost-XDC_2018.pdf)) | Mesa 19.1, 2019 ([Phoronix](https://www.phoronix.com/news/Panfrost-Initial-Mesa-19.1)) | 2 to 3, then Collabora | none |
| Asahi | Apple AGX | January 2021 | January 2021, on macOS's kernel driver ([part II](https://alyssarosenzweig.ca/blog/asahi-gpu-part-2.html)); compiler April 2021 ([part III](https://alyssarosenzweig.ca/blog/asahi-gpu-part-3.html)) | alpha GL 2.1/ES 2.0 December 2022 ([Asahi](https://asahilinux.org/2022/12/gpu-drivers-now-in-asahi-linux/)); conformant ES 3.1 August 2023 ([Asahi](https://asahilinux.org/2023/08/first-conformant-m1-gpu-driver/)) | about 4 | vendor (Apple) |

What these show:
- **First triangle** takes weeks to a year. **Usable GLES2** takes 1.5 to 5 years of calendar time, mostly by one to four very experienced people. Measured in work, that is roughly 2 to 8 person-years.
- The fastest projects (Freedreno, Asahi, Panfrost from 2018) had the vendor's firmware or no firmware at all, a device on the desk, and authors who had written GPU drivers before. Asahi and Panfrost also had today's Mesa (Gallium, NIR, shared GLSL front end), which removes much of the API work Lima and Etnaviv did in 2012.
- **None of them wrote GPU firmware.** The vendors' firmware stayed binary (Adreno, Apple) or the GPU had none (Mali, Vivante). SGX is the hard case here: its microkernel runs on the shader cores and is part of the user-space init library.

## Estimate per component

Person-months (PM) for one experienced developer with a device. Each range includes the clean-room work of rule 2: an RE agent observes the stock stack (ioctl arguments, memory contents, register writes) and writes specs, and a separate implementer writes code from the specs. That process adds roughly a quarter to a third over working directly.

| # | Component | Replaces | PM | Depends on | Recommendation |
|---|---|---|---|---|---|
| 1 | Memory allocator and services client | `libsrv_um`, `gralloc.omap4430.so`, parts of `libpvr2d` | 3 to 6 | kernel module (done) | later |
| 2 | Services init, without firmware | `pvrsrvinit`, `libsrv_init` (except the microkernel) | 2 to 4 | 1, 6 | later; keep the stock init until then |
| 3 | EGL and Android window glue | `libEGL`, `libIMGegl`, `libpvrANDROID_WSEGL` | 3 to 6 | 1, 4 | later |
| 4 | GLES 1.1 and 2.0 driver (Mesa Gallium) | `libGLESv1_CM`, `libGLESv2` | 10 to 20 | 1, 5, a working init | later |
| 5 | Shader compiler, including ISA reverse engineering | `libusc`, `libglslcompiler` | 8 to 18 | device for tests | later |
| 6 | GPU firmware (microkernel) | the EDM program inside `libsrv_init` | 12 to 24, possibly more | 5 (ISA), 2 | not planned |
| | **Open GLES on stock init and firmware** (1, 3, 4, 5) | | **26 to 54** | | |
| | **Fully open** (all six) | | **40 to 80+** | | |

### 1. Memory allocator and services client: 3 to 6 PM

- **Work:** open `/dev/pvrsrvkm`, connect, enumerate devices and heaps, allocate and map device memory, export buffers, sync objects, submit to a CCB, wait for completion. On Android also a gralloc HAL that allocates through this path and posts to the display class or `dsscomp`.
- **Evidence:** every ioctl and argument structure is in the public kernel headers, and the kernel code shows the semantics. This is the best-documented layer. What is not public is the exact sequence and flags the stock client uses, which a short trace of the stock stack (in the clean room) shows. Imagination's Rogue Vulkan driver was published able to run on either the new DRM driver or the services kernel driver of its own DDK ([Phoronix](https://www.phoronix.com/news/Open-Source-PowerVR-Vulkan)), so Mesa has carried a services-style winsys before; the Rogue ABI is different from SGX's.
- **Range:** 3 PM if only Linux user space is needed, 6 PM with gralloc and Android display integration.

### 2. Services init, without firmware: 2 to 4 PM

- **Work:** build `SGX_BRIDGE_INIT_INFO`: allocate the kernel CCB, host control, TA/3D control and the other blocks, write the register scripts, pass the microkernel and its kick addresses, then call the init bridge.
- **Evidence:** the structures are in `sgxinfo.h`, `sgx_mkif_km.h` and `sgxscript.h`, and `sgxinit.c` shows how the kernel consumes them. Not public: the register values in the scripts (clock gating, bus configuration, hardware bug workarounds, the `FIX_HW_BRN_*` blocks) and the initial contents the microkernel expects. These are observable at the ioctl boundary.
- **Note:** this component cannot exist without a microkernel. Until component 6 exists, the stock `pvrsrvinit` stays: it runs once at boot and only talks to the kernel. Open GL libraries can then run on top of the GPU it initialised, as Asahi's first work ran on Apple's firmware.

### 3. EGL and Android window glue: 3 to 6 PM

- **Work:** EGL 1.4 displays, configs, contexts and window surfaces; `ANativeWindow` buffer handling, fences and swap through gralloc on Android, or KMS/fbdev on plain Linux.
- **Evidence:** Mesa's EGL can be used, but its Android platform expects DRM render nodes and DRI image buffers, and the XE24 kernel is the non-DRM Android build. So either a custom Mesa EGL platform over the services client, or the DDK's `SUPPORT_DRI_DRM` build of the kernel module (present in the source, not tested on Glass). Mesa dropped its `Android.mk` build in 2021 ([MR 9728](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/9728)); building current Mesa for Android 6.0 means a Meson cross-build with the NDK, or an older Mesa.

### 4. GLES 1.1 and 2.0 driver: 10 to 20 PM

- **Work:** a Gallium driver. Mesa supplies the GL state tracker, so GLES 1.1 and 2.0 come from one driver. The driver must produce the SGX command stream: tile accelerator control streams, ISP/TSP state words, PDS programs for vertex fetch and iterators, texture and sampler state, pixel back end for render targets, and the full TA and 3D command layouts for the microkernel. It must also manage the parameter buffer, including partial renders when it overflows, which is specific to tile-based deferred renderers.
- **Evidence:** none of these formats are public (only the "shared" fragment of the TA command is in the kernel). Comparable Gallium drivers took 1 to 4 years of calendar time to usable GLES2 (table above). The low end assumes reMESA or a similar project publishes SGX state formats that hold for SGX540. The high end assumes our own observation of the stock driver for every state word.

### 5. Shader compiler: 8 to 18 PM

- **Work:** learn the USSE instruction encoding (the ISA is under NDA), then a NIR back end: instruction selection, register allocation across the USSE register banks, and the small PDS programs that feed the shaders. Mesa's GLSL front end and NIR replace `libglslcompiler` entirely.
- **Evidence:** Midgard's ISA was decoded by one person before Panfrost started, and its compiler took most of 2018 ([XDC 2018](https://webcf.waybackmachine.org/web/20210615031847/https:/xdc2018.x.org/slides/Panfrost-XDC_2018.pdf)); Asahi had a first compiler about three months in ([part III](https://alyssarosenzweig.ca/blog/asahi-gpu-part-3.html)); Lima's vertex compiler took years. reMESA reports a partial USSE encoder after about a month. The stock compiler is the largest single library (861 KB).

### 6. GPU firmware: 12 to 24 PM or more

- **Work:** write a microkernel that runs on the USSE: take kicks from the host and from the CCB, schedule TA and 3D work, manage the parameter buffer memory (the DPM), handle out-of-memory and partial renders, context switches, power events, cache flushes and status updates in the format the kernel driver expects.
- **Evidence:** the kernel source fixes the host-side interface (`sgx_mkif_km.h`, `sgx_ukernel_status_codes.h`, `SGX_BRIDGE_INIT_INFO`) but not the microkernel's internals. None of the drivers in the table wrote GPU firmware. The nearest precedent is nouveau's own context-switch firmware for NVIDIA's falcon controllers (the `.fuc` sources under `drivers/gpu/drm/nouveau/nvkm/engine/gr/fuc/` in Linux), and falcon is a small general-purpose controller, not a shader core like USSE. It needs component 5's ISA knowledge first. A bug here hangs the GPU with little to observe.
- **Recommendation:** not planned. The microkernel joins the other chip firmware on the roadmap's "stays binary" list, delivered through the stock `pvrsrvinit`.

## Fallbacks without the GPU

At 640x360 the panel has 230,400 pixels; 30 frames per second is about 7 million pixels per second, 60 is about 14 million. On a 1 GHz dual Cortex-A9 that is 70 to 140 CPU cycles per pixel per frame across both cores, before the rest of the system. No public benchmark of these renderers on a Cortex-A9 was found, so the notes below are expectations to measure, not results.

- **Plain 2D drawing plus display overlays (route 2, and Android with software HWUI).** A card UI is mostly blits, text and a few gradients. Drawn with a CPU 2D library (Skia, pixman, cairo) into a buffer and shown on an OMAP4 display pipeline through `dsscomp` or KMS, it avoids 3D entirely. This is the most likely to hold 30 or 60 fps.
- **Mesa llvmpipe (plain Linux).** Builds and runs on ARMv7 with LLVM. A Mesa bug report shows glmark2 at a score of 13 on a quad Cortex-A7 ([bug 93570](https://bugs.freedesktop.org/show_bug.cgi?id=93570)), at a larger default resolution. Expect simple full-screen GL scenes at 640x360 to run at tens of fps, with two of the A9's cores busy. That is fine for a UI and bad for battery and heat on the temple. softpipe is much slower and only useful for tests.
- **SwiftShader (Android).** Google's software GLES and Vulkan (Apache-2.0). Since April 2019 it needs Android 6.0 or later ([commit](https://swiftshader.googlesource.com/SwiftShader/+/d632e6d54e5a368f87af41066a6b7cb40191e1f7%5E%21)), so it fits the device tree's 6.0.1 branch but not a KitKat build. Its ARMv7 JIT is LLVM or Subzero. Performance on this CPU is unknown.
- **libagl (Android).** AOSP 6.0.1 still contains `libagl` ([source](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-6.0.1_r31/opengl/libagl/)), a software OpenGL ES 1.x renderer enough for SurfaceFlinger, not for GLES2 apps.

## Recommendation

- **Do now:** nothing on the GPU stack itself. Keep the stock user space on route 1, as the roadmap says, and keep R4/R5's thin graphics layer able to run on a CPU 2D renderer.
- **Do once a Glass is available:** measure the fallbacks on the device: frame rate, CPU load, battery drain and temperature for the card UI with CPU 2D plus overlays, llvmpipe and SwiftShader. This takes days, not months, and decides whether route 2 is usable without a GPU.
- **Later:** components 1 to 5, only if all of these hold: a device, a contributor with GPU driver experience, and a public SGX effort (reMESA or another) that has published USSE and state formats. Order: 1, then 5 and 4 together, then 3; 2 only with 6.
- **Not planned:** component 6, the GPU microkernel.

## Decisions for the owner

- **Provenance of other projects' work.** SGX535-reMESA (MIT) lists disassembly and Ghidra analysis of Imagination's compiler among its sources. Rule 1 is about Google files and rule 2 sets our own clean room; neither says whether code from an outside project with that method may be merged. Reading its public documentation as facts is in line with "public information"; importing its code needs a decision.
- **Whether route 2 needs a GPU at all.** If the device measurements show the UI is smooth in software and battery drain is acceptable, this estimate can stay a reference page.
