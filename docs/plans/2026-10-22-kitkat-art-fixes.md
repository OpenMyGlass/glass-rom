# Track A: fixes for KitKat's ART, and compiler settings

**Goal:** KitKat's ART was a preview: no shipped device ran it as the default runtime. Track A runs it as the only runtime, so it gets the ART fixes from later AOSP that apply to the 4.4 code. This document also covers the owner's request to get the most out of the compilers: the native toolchain (GCC 4.7) and ART's `dex2oat`.

**Status:** fixes cherry-picked and merged in [OpenMyGlass/android_art#1](https://github.com/OpenMyGlass/android_art/pull/1) (`glass-4.4` at `43dd266f`). The manifest pins them since [OpenMyGlass/manifest#5](https://github.com/OpenMyGlass/manifest/pull/5). The full CI build passed with every ART-only check ([run 39802639746](https://github.com/OpenMyGlass/manifest/actions/runs/39802639746), at `90ef778c`, which has the same tree). The fork PR is merged with a merge commit (never squash or rebase): the backports must stay separate commits with their upstream authors, and `check_backports.py` checks them one by one. The CI build is a compile and image check only. Nothing has run on a device.

**Parent plan:** [2026-10-21-android-lean-kitkat-art.md](2026-10-21-android-lean-kitkat-art.md), Task 5, rank 5.

## What Track A's ART is

- The manifest took `art` from `OpenMyGlass/android_art` branch `aosp-4.4`, revision `479fe13d`. That is AOSP `android-4.4.4_r2.0.1` (`d5e4ac0a`) plus one commit, "Finish fixing Zygote descriptor leakage problem". That one commit is the whole android-security `aosp-4.4` set for ART.
- AOSP's `kitkat-*` branches (`kitkat-mr2.2-release`, `kitkat-dev`, `kitkat-wear`, `kitkat-cts-dev`) have no ART commit after `android-4.4.4_r2.0.1`.
- So every further fix has to come from `master` of late 2013 and 2014, which became `lollipop-release`. That is 2,321 non-merge commits that 4.4.4 does not have, from August 2013 to October 2014.
- Most of them are for code that 4.4 does not have: the moving collectors, the RosAlloc and bump-pointer spaces, `Handle`/`StackHandleScope`, the Optimizing compiler, x86-64, ARM64, MIPS, relocation, the new assembler. Many "fixes" fix regressions from that new code. I checked each candidate against the 4.4 source and kept only the ones whose bug is in 4.4.
- `libcore` needs no change for any of them.

## Method

1. List `lollipop-release` commits not in `android-4.4.4_r2.0.1`. Filter by subject (fix, crash, race, leak, JNI, verifier, ARM, Thumb...), drop the architectures and subsystems 4.4 lacks, and try about 100 candidates on the pinned base.
2. For each one, read the 4.4 code: is the bug there? A clean `git cherry-pick` proves nothing. Git applied several commits "cleanly" by adding only the new half, for example `e508a209` (peek/poke intrinsics that 4.4 does not have) or `0d3bbff7`. Others "applied" but would not compile: `85db144f` calls `IsValidObjectAddress()`, and `2ef33c3d` calls `AlignUp()`, neither of which 4.4 has.
3. Cherry-pick with `-x`, keep the upstream author, and add an `OpenMyGlass:` paragraph that says what was adapted. The fork's CI (`tools/glass/check_backports.py`) checks this for every commit on `glass-4.4`.
4. Check that every symbol an adapted commit uses exists in 4.4, and that the code builds with ART's `-Wall -Werror -Wextra`. For example, `53dc70cc` needs a cast for `-Wsign-compare`.

## The fixes, ranked

Rank is gain for Glass against risk. "exact" means the same patch id as upstream. "Adapted" means the commit message says what changed.

| # | Upstream | What it fixes in 4.4 | Applies | Risk |
|---|---|---|---|---|
| 1 | [`1268b742`](https://android.googlesource.com/platform/art/+/1268b742c8cff7318dc0b5b283cbaeabfe0725ba) | JNI `IsAssignableFrom(c1, c2)` tested the reverse direction. Dalvik followed the spec, so native code written for Dalvik got wrong answers under ART | adapted; the gtest is ported and the 004-JniTest hunks are left out | low: Dalvik's behaviour |
| 2 | [`40bbb39b`](https://android.googlesource.com/platform/art/+/40bbb39b85c063cd6a9f4ab00ff70372370e08cf) | dex2oat aborted with "out of registers" on methods with a large frame and floating-point values, so the app failed to install ([AOSP issue 67349](https://code.google.com/p/android/issues/detail?id=67349)) | compiler change exact, test hunks left out | low |
| 3 | [`63e8a68c`](https://android.googlesource.com/platform/art/+/63e8a68c9a2cdbbe9bfd8d200610119dd359ee59) | A thread's exit woke only one `join()`er. With two joiners, the other hangs for ever | adapted (4.4's `ObjectLock`) | low |
| 4 | [`2ef33c3d`](https://android.googlesource.com/platform/art/+/2ef33c3dce17dabd9342ccf15cca5700487f2045) | `CardTable::ModifyCardsAtomic` handed the wrong card to the visitor for an unaligned scan end: heap corruption under the sticky and partial collectors | adapted: `RoundUp()` on `uintptr_t` instead of `AlignUp()` | low |
| 5 | [`1279d12e`](https://android.googlesource.com/platform/art/+/1279d12eb94b7664fc839d4ef7f30c7d6b20e603) | `byte_cas` (card marking) shifted by a byte count as if it were bits | exact | low |
| 6 | [`8db4a405`](https://android.googlesource.com/platform/art/+/8db4a405fe283d8769d5f38299d8692c009feb1a) | Miranda methods resolved from the wrong `DexCache` when a class in `classes.dex` implements an interface from `classes2.dex` (multidex apps) | adapted: `GetDeclaringClass()->GetDexCache()` | low |
| 7 | [`22cb09b3`](https://android.googlesource.com/platform/art/+/22cb09b35e8eb30c016065f0eec4b3b96666de43), [`2b5eaa2b`](https://android.googlesource.com/platform/art/+/2b5eaa2b49f7489bafdadc4b4463ae27e4261817) | dex2oat tried to compile classes whose superclass failed verification. They have no GC map, so dex2oat crashed. `2b5eaa2b` adds the `Runtime::IsCompiler()` guard that this needs in 4.4: the rejected-classes table exists only in dex2oat, so without the guard the device runtime would dereference NULL | `22cb09b3`: same change, only the context differs. `2b5eaa2b`: only its guard in `ClassLinker::VerifyClass()` | low |
| 8 | [`004644fe`](https://android.googlesource.com/platform/art/+/004644fe87046b965442b1ee1008b7206817d187) | JNI `GetMethodID` on an interface did not find a method declared in a super-interface (`NoSuchMethodError` where Dalvik succeeded) | `jni_internal.cc` only; 4.4 has `FindInterfaceMethod()` already | low |
| 9 | [`3a1444cc`](https://android.googlesource.com/platform/art/+/3a1444ccb92fb1b11d4943c3baa1f0a3abed4f10) | JNI `ExceptionDescribe()` with no pending exception aborted the process. Dalvik ignores it | adapted (4.4 uses `SirtRef`) | low |
| 10 | [`8249b425`](https://android.googlesource.com/platform/art/+/8249b425ba81d804c222c746e31bfcac9516e759) | Verifier `CHECK` failure on a quickened `invoke-virtual` on `null` | without the test hunks (4.4's test already uses a plain `null`) | low |
| 11 | [`ef809d09`](https://android.googlesource.com/platform/art/+/ef809d09cf0d28d999ac69969e4506d8afa4624d) | CheckJNI aborted on `NewDirectByteBuffer(addr, 0)` ([AOSP issue 63055](https://code.google.com/p/android/issues/detail?id=63055)) | exact | none: CheckJNI only |
| 12 | [`ade73185`](https://android.googlesource.com/platform/art/+/ade731854d18839823e57fb2d3d67238c5467d15) | Quick compiler read past the constant table for the high half of a wide constant | exact | low |
| 13 | [`906457c3`](https://android.googlesource.com/platform/art/+/906457c326d505f511fae42fc693cade1656c19e) | Uninitialised `live_stack_freeze_size_` in mark-sweep | exact | none |
| 14 | [`b917ea1a`](https://android.googlesource.com/platform/art/+/b917ea1a62aa0ab8eca3f689ef64b5be34e11abb), [`ba9ece9c`](https://android.googlesource.com/platform/art/+/ba9ece9c58de90b39c39b29dbdaee54b1654c066), [`a44d4f50`](https://android.googlesource.com/platform/art/+/a44d4f508fa1642294e79d3ebecd790afe75ea60) | Performance. `Float.floatToRawIntBits`, `String.isEmpty`, `String.indexOf(int)` and `String.indexOf(int, int)` were never inlined. 4.4's `GenIntrinsic()` compares against misspelt names (`float_to_raw_int_bits`, `is_empty`, `index_of`). Upstream measured `URI.equals` 1.55x faster. `a44d4f50` stops `GenInlinedIndexOf()` reading a third argument that `indexOf(int)` does not have | `b917ea1a` exact; `ba9ece9c` adapted (names fixed in `gen_invoke.cc`); `a44d4f50` without its x86 hunk | medium (see the note below) |
| 15 | [`53dc70cc`](https://android.googlesource.com/platform/art/+/53dc70cc824fa71c237015de2bebb2da6b462b5d) | Performance. On a hash collision, `InternTable::Lookup()` and `Remove()` scanned to the end of the table | adapted (4.4's lock and types; `int32_t` cast for `-Wsign-compare`) | low |
| 16 | [`e1467659`](https://android.googlesource.com/platform/art/+/e1467659568500cefd84abc4cdb399d8db7e214d) | Zygote `capset()` used the 32-bit v1 header, so capabilities above 31 were dropped. In 4.4 no caller asks for one yet: system_server's list ends at `CAP_SYS_TTY_CONFIG`. It matters as soon as one is added, for example `CAP_BLOCK_SUSPEND` (36), which 5.0's system_server gets | exact | low |

Two notes on the history. Rank 7's first commit (`22cb09b3`) would crash the device runtime without its guard, which comes later on the branch (`2b5eaa2b`, the second-last backport). A `git bisect` on the device must skip the commits between them. Rank 8 follows upstream exactly: `GetMethodID` on an interface now searches only the interface and its super-interfaces, so asking for a `java.lang.Object` method such as `toString` on an interface class throws `NoSuchMethodError`. Dalvik found it, and later ART behaves the same as this backport (checked up to 7.1).

Rank 14's risk: these intrinsics never ran in a shipped build. The ARM paths are small (`art_quick_indexof` clamps the start index; `isEmpty` is `negs`/`adcs`), and 5.0 shipped the same ARM code. `ba9ece9c` can be reverted alone if string code misbehaves.

These 16 fixes are 19 commits on `OpenMyGlass/android_art` `glass-4.4` (rank 7 is two commits, rank 14 three). `ba9ece9c` is adapted rather than cherry-picked: its upstream fix is in `dex_file_method_inliner.cc`, which 4.4 lacks.

### Considered and left out

- **Not a bug in 4.4** (the bug came with later code):
  - `41cdd43b` and `409fe94a`: the select pattern and the pseudo-op size. 4.4's `SetupResourceMasks()` returns early for pseudo-ops.
  - `0f5f6bbc`: the checkpoint loop. 4.4 clears the flag inside the CAS and runs the checkpoint after it.
  - `e508a209`: 4.4 has no `Memory.peek*`/`poke*` intrinsics.
  - `85db144f`: in 4.4, `IsHeapAddress(NULL)` is still true.
  - `cd937a9d`: 4.4's oat class layout has no bitmap.
  - `0d6adac2`: it reverts two master commits that 4.4 does not have.
  - `3e8b2e1f`: 4.4's `ReleasePrimitiveArray` is already right.
  - `9728f91a`, `a1ee14fc`, `5f51d4b8`: monitor and thread-list code that 4.4 does not have.
  - `99cb4eac`: 4.4 copies arrays in `java_lang_System.cc` with its own `MemmoveWords`.
  - `397297f9`: 4.4 has no `Math.abs(double)` intrinsic.
  - `a1983d4d`: it fixes the `RegStorage` pair code; 4.4 passes plain `low_reg`/`high_reg` integers.
  - `c17ebe86`: the bug is in x86's mul-long-by-1 special case. Its shared `gen_loadstore.cc` hunk (`UpdateLocWide` in `StoreValueWide`) only supports that x86 change, and ARM has no such case.
  - Many x86 fixes: `4554bfdc`, `34fa0d93`, `a1758d83`, `e78d4e1a`, `8ef84afb`, `91b6ffaf`, `51a80d72`, `653f2bf1`.
- **Moving-GC only.** 4.4's collectors never move objects: `07d447be`, `8770e5c7`, `1984152a`, `79b4f38d`, `c0a9ea40`, `55871bf5`.
- **Shutdown or tests only.** The runtime never shuts down on the device: `fd7e7f12`, `dfe78a6e`, `6afd409d`.
- **Real in 4.4, but larger than their gain:**
  - `37c16453`: `Thread.setName` hangs right after `start()`. Upstream makes the thread-suspend method non-static and changes the debugger and `VMStack` callers, all of which differ in 4.4, so it is more work.
  - `082833c8`: rewrites the register pool sanity checker, about 200 lines in `ralloc_util.cc`.
  - `59cde534`: works around the GCC volatile struct copy bug (GCC PR 47409). It came from Imagination's MIPS work. 4.4's ARM code has shipped with GCC 4.7 since 2013, so leave it until a device shows thread-state corruption.
  - The 2014 dex-file verifier hardening: `e09269ca`, `50d1bc19`, `78d639ef`, `277a7c7b`, `acc2bb69`, `5cac343e`, `d6cec905`. 4.4's verifier is older, and these do not apply. installd runs `dex2oat` with the app's own uid (`setgid`/`setuid` in `commands.c`, then the capabilities are dropped), so a malformed dex mostly attacks itself.
- **Security:** the android-security `aosp-4.4` ART set is one commit, the zygote descriptor fix, and it is in the base. I found no ART CVE fix for 4.4 beyond it.

### App patterns that later ART handled better

- In this set:
  - JNI that Dalvik accepted: ranks 1, 8, 9 and 11;
  - multidex: rank 6;
  - obfuscated or odd bytecode that crashed dex2oat or the verifier: ranks 2, 7 and 10;
  - `join()`: rank 3.
- 4.4.1 and 4.4.3 already have:
  - monitor-check verifier errors as warnings;
  - `NewLocalRef` on cleared weak globals;
  - `FindFieldID` with the class's own loader;
  - miranda methods;
  - mutual-recursion stack overflow.
- Still different from Dalvik, and not fixable by backports:
  - with CheckJNI off, Dalvik returned NULL for some bad JNI lookups, where 4.4 ART throws `NoSuchFieldError` or `NoSuchMethodError`;
  - Xposed never ran on 4.4 ART.

  The fallback stays the parent plan's: the `interpret-only` filter for the app, through `/data/system/glass-dex2oat-filters`.

## Lollipop's ART instead: the option

Taking the whole of 5.0's or 5.1's `art` is not feasible for this track:
- **libcore.** 5.0's runtime and `core-libart` change together: `java.lang.reflect.ArtMethod`/`ArtField`, `DexCache`, `Daemons`, `VMRuntime` (ISA-specific dalvik-cache, `is64Bit`), and `dalvik.system.DexFile` for multiple ISAs. That means taking 5.0's `libcore` with it, and the 4.4 framework calls 4.4's `libcore` APIs.
- **frameworks/base and native:**
  - installd and `PackageManagerService` use the ISA-specific `dalvik-cache/arm/` layout and pass ISA arguments;
  - `AndroidRuntime` passes `-Xcompiler-option` and the `dalvik.vm.dex2oat-*` properties;
  - zygote handles `--instruction-set`.
- **build and bionic:**
  - `dex_preopt_libart.mk` and boot-image rules in `build/core`;
  - `libsigchain`, and `libbacktrace` and `libunwind` versions;
  - 5.0's ART is built with GCC 4.8 or 4.9 and clang. 4.4's target GCCs are only 4.6 and 4.7.
- **Apps.** The moving collectors break JNI code that keeps raw object pointers. That is the most common 5.0 breakage, and 4.4's non-moving GC avoids it.

So it would be Track B's runtime on a KitKat framework: weeks of work, with no one to compare against. That is Track B's job (6.0.1), not Track A's. Keep backporting fixes one by one.

## Compiler settings: native code

The owner asked to make the compilers as fast as possible, with correctness first. I audited the 4.4 toolchain as it is configured now. `build` is `OpenMyGlass/android_build` `glass-4.4` at `2619fd59`. The device inherits `hardware/ti/omap4/BoardConfigCommon.mk`: `TARGET_ARCH_VARIANT := armv7-a-neon`, `TARGET_CPU_VARIANT := cortex-a9`, `TARGET_CPU_SMP := true`. The compiler is the prebuilt `arm-linux-androideabi-4.7`, the only target GCC that 4.4 has besides 4.6.

### Already on, and why each is safe

| Setting | Where | Why safe | Source |
|---|---|---|---|
| `-mcpu=cortex-a9` (also tunes for the A9: `-mtune` is implied) | `android_build` PR 1, `armv7-a-neon.mk` | Selects the A9's instruction set (ARMv7-A, no integer divide) and its scheduling. Nothing outside the A9's ISA | GCC manual; AOSP already did the same for `cortex-a15`, `-a8` and `-a7` in this file |
| `-Wl,--no-fix-cortex-a8` | same | The Cortex-A8 branch erratum does not exist on the A9 | binutils manual (`--fix-cortex-a8`: the A8 erratum for 32-bit Thumb-2 branches that span two 4 KB pages) |
| `-mfpu=neon -mfloat-abi=softfp` | `armv7-a-neon.mk` (stock) | OMAP4's A9 has NEON and VFPv3-D32. softfp keeps the ARM EABI that every Glass binary uses | AOSP 4.4 |
| `-ffunction-sections -fdata-sections` and `-Wl,--gc-sections` | `TARGET_linux-arm.mk` (stock) | The linker drops unreferenced sections. No semantic change | AOSP 4.4 |
| `-Wl,--icf=safe` | `TARGET_GLOBAL_LDFLAGS` (stock) | gold's "safe" mode folds only functions that cannot be told apart by address (on ARM, in practice mostly constructors and destructors) | AOSP 4.4; gold manual |
| `-O2 -fomit-frame-pointer -fstrict-aliasing` for ARM-mode modules; `-Os` for Thumb-2 modules (the default mode) | `TARGET_linux-arm.mk` (stock) | AOSP's own split | AOSP 4.4 to 6.0 unchanged |
| bionic `memcpy`, `memset`, `strcmp`, `strcpy`, `strcat`, `strlen`, and `__memcpy_chk`, `__memset_chk`, `__strcat_chk`, `__strcpy_chk`, for the Cortex-A9 | `bionic/libc/arch-arm/cortex-a9/` via `TARGET_CPU_VARIANT` | Hand-written A9 routines, chosen by the variant | AOSP 4.4. 5.1's versions differ only in macros, CFI and labels; 5.1 adds `stpcpy`, a new API, sharing `strcpy`'s code |
| ART at `-O3` | `art/build/Android.common.mk` (stock) | AOSP's choice for the runtime | AOSP 4.4 |
| libjpeg 6b (with NVIDIA's NEON code) ARM mode, `-O3 -fstrict-aliasing -fprefetch-loop-arrays`, NEON SIMD | `external/jpeg` (stock) | Library's own flags | AOSP 4.4 = 5.1 |
| zlib ARM mode, `-O3` | `external/zlib` (stock) | Library's own flags | AOSP 4.4 = 5.1 |
| Skia NEON paths (`__ARM_HAVE_NEON`, `*_neon.cpp`, `memset*_neon.S`) | `external/skia` (stock) | Selected by `ARCH_ARM_HAVE_NEON` | AOSP 4.4. 5.1 is still Thumb `-Os`; it adds `-O2` only for FDO builds |

### Evaluated and not applied

- **`-O2` for Thumb-2 modules globally, instead of `-Os`.** It changes no semantics. But AOSP kept `-Os` for Thumb from 4.4 through 6.0 (`TARGET_thumb_CFLAGS`), the A9 has a 32 KB instruction cache, and every process maps these libraries. Whether it is faster on Glass can only be measured on the device. An **owner decision**; if wanted, it is a one-line change in `android_build` plus a CI build to record the size delta.
- **`-O3` or ARM mode for more libraries.** AOSP's later releases did not do it for any library that 4.4 lacks it for: jpeg and zlib were already `-O3`/ARM in 4.4, and Skia stayed Thumb `-Os`. libpng's NEON filters came with libpng 1.6 in 5.x, and 4.4 has 1.2.46. So nothing qualifies under "only where AOSP later did the same".
- **Later bionic string routines.** No algorithmic difference from 4.4's Cortex-A9 set (see above).
- **LTO.** The 4.7 prebuilt has `lto1` and `liblto_plugin.so`, but:
  - 4.4's build has no LTO support (no plugin-aware `ar`, no LTO link rules);
  - GCC 4.7 cannot keep per-function ARM or Thumb mode across LTO: the `target("arm")`/`target("thumb")` attribute came in later GCC. A module's `LOCAL_ARM_MODE`, and inline assembly written for one mode, would not survive;
  - section GC and ICF already take most of the size gain.

  Not reliable, so not used.
- **GCC 4.8 or 4.9.** Not in the 4.4 manifest. Bringing in a newer prebuilt means a new, untested compiler for the whole system.
- **`-Wl,--hash-style=gnu`.** 4.4's bionic linker cannot read `DT_GNU_HASH` (support came in 6.0). Unsafe.
- **`-Wl,--as-needed`.** It drops `DT_NEEDED` entries that some 4.4 libraries rely on transitively. Unsafe without a full audit.
- **Never:** `-ffast-math`, `-Ofast`, `-fno-strict-overflow`, or any other global change to floating-point or aliasing semantics.

So the native toolchain already uses the strongest settings that are safe. This work changes no native flag, so there is no size delta to record. The CI build's `check-build.txt` artefact records the image sizes, and `build-numbers.txt` the build times and disk use. Nothing records per-library sizes yet: a later flag change needs that added to `tools/check-build.sh` first.

## Compiler settings: dex2oat

- **Instruction set.** 4.4's dex2oat has no `--instruction-set-features` option and no `DEX2OAT_TARGET_INSTRUCTION_SET_FEATURES` (they came with 5.0). Its ARM back end is Thumb-2 (`kThumb2`), and it never emits a divide instruction:
  - `div-int` and `rem-int` call `__aeabi_idivmod` (`pIdivmod`, `entrypoints_init_arm.cc`);
  - `div-long` and `rem-long` call `__aeabi_ldivmod`.

  I found no `sdiv`, `udiv` or VFPv4 (`vfma`) in `compiler/` or `runtime/arch/arm/`. `asm_support_arm.S` is `.arch armv7-a`. So nothing assumes a divider the A9 lacks.
- **Compiler filter per partition.** Already in the tree:
  - installd passes `--runtime-arg -compiler-filter:<f>`;
  - `persist.glass.d2o.sys=speed` for `/system` apps;
  - `persist.glass.d2o.usr=space` for user apps;
  - per-package overrides in `/data/system/glass-dex2oat-filters` (parent plan, Task 3; `android_frameworks_native` PR 1, device `system.prop`).

  4.4's filters are `interpret-only`, `space`, `balanced`, `speed` and `everything`. Apps with up to 900 method references (across all their dex files) are compiled with `speed` regardless, unless the filter is `interpret-only`.
- **Boot image.** Compiled once at first boot by `ImageSpace::GenerateImage()`: `-Xms64m -Xmx64m`, `--image-classes=preloaded-classes` from `framework.jar`, and no filter, so dex2oat's default `speed` (`ART_SMALL_MODE` is off, which would make it `interpret-only`). Every process maps it, so leave it at `speed`. `everything` would only add size. The parent plan's preloaded-classes trimming (Task 4) is the lever for its size.
- **Intrinsics.** Rank 14 above turns on the string and float intrinsics that 4.4 meant to have.
- **Not available in 4.4:**
  - build-time preopt for ART (parent plan, Task 3, Step 3);
  - a way to pass `--no-watch-dog` or `-j<n>` from a property or installd (dex2oat has both options, but installd passes neither; `-j` defaults to one thread per CPU, 2 on the OMAP4430);
  - `dalvik.vm.dex2oat-flags`;

## Tests

- **Fork CI** (`OpenMyGlass/android_art`, workflow `check`, required on `glass-4.4`):
  - unit tests of `tools/glass/check_backports.py`;
  - the check itself: every commit on top of `479fe13d` is a backport of an AOSP `lollipop-release` commit with the upstream author, the `-x` line, and an `OpenMyGlass:` note when its patch differs; anything else may touch only `.github/` and `tools/glass/`.
- **Full build** (`OpenMyGlass/manifest`, workflow `build`) with the ART-only checks of `tools/check-build.sh`.
- **ART's own tests** (gtests such as `jni_internal_test`, the `test/` run-tests) do not run in CI. They need ART built for the host (`WITH_HOST_DALVIK`, a host `core.art`, host `dex2oat`) on top of the full tree, or a device. That adds well over an hour to a build that already takes about 100 minutes on the free runner. Run them on a build machine: `make test-art-host`.

## Device checklist (not run)

All with `fastboot boot` only. Never write the `bootloader`, `xloader` or `fpga` partitions.

- [ ] **First boot (not run).** Time from `fastboot boot` to `sys.boot_completed=1`. Record:
  - the boot image compile: `logcat` `dex2oat` lines for `system@framework@boot.oat`, start to end;
  - the time of each system app's dex2oat (`installd` "Running /system/bin/dex2oat ... filter=speed" lines);
  - the size of `/data/dalvik-cache`.

  Target under 10 minutes (parent plan, Task 3).
- [ ] **Install times (not run):** one large app (over 20,000 methods) with `space`, `balanced` and `speed`.
- [ ] **Regression for rank 2 (not run):** an app with a very large method that uses floating point, for example a game engine. dex2oat must not abort with "out of registers".
- [ ] **CheckJNI pass (not run):** `setprop dalvik.vm.checkjni true; stop; start`. Then run the app list below and record any `JNI DETECTED ERROR`.
- [ ] **App compatibility smoke list (not run).** Install, start and use each for a minute, and record pass, crash, ANR or dex2oat failure. Pick versions that support API 19:
  - an app with native code that uses JNI reflection (a game on a native engine such as Unity or libGDX): ranks 1, 8 and 9;
  - a multidex app (any large app built with `multidex` for API 19): rank 6;
  - an app that joins one thread from two others, for example a download manager with a worker pool: rank 3;
  - a media player (ExoPlayer-based) and a podcast app: direct `ByteBuffer` (rank 11 under CheckJNI);
  - a browser built on the system WebView;
  - a terminal emulator (native PTY through JNI);
  - a navigation or map app (large, uses floating point heavily);
  - a notes app with full-text search (`String.indexOf` heavy: rank 14);
  - our own open Glass services and apps (roadmap R4, R5).
- [ ] **String intrinsics (not run):** our own test app that compares `String.indexOf`, `isEmpty` and `Float.floatToRawIntBits` results with an interpreted run (`interpret-only` override) over random inputs, including negative and too-large start indexes and supplementary characters.
- [ ] **GC soak (not run):** 30 minutes of an allocation-heavy app with `dalvik.vm.heapgrowthlimit=48m`, then `dumpsys meminfo`. No `heap corruption` or `CHECK` aborts in `logcat` (ranks 4 and 5).

## Decisions for the owner

1. Global Thumb-2 `-O2` instead of `-Os` (see "Evaluated and not applied"). It is not applied, because AOSP never did it. Measure on a device first if wanted.
2. Rank 14 (string and float intrinsics) is the only change that enables code no shipped device ran. It is in, as one commit that can be reverted alone. Keep it, or drop it until a device test exists.
3. The remaining candidates that are real in 4.4 (`37c16453`, `082833c8`, `59cde534`, the dex verifier hardening): take them now, or only when a device shows the bug (the parent plan's rule).
