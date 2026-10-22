# Track A: power-saving backports from Android 5.x-7.x into 4.4 — Plan

**Goal:** Give the KitKat build (Track A) the power-saving behaviour of later Android releases where it pays off on Glass, by porting the AOSP code where that is practical. The owner's request: "for power saving etc., try to inherit them from the other Android versions".

**Where:** `frameworks/base` from a new branch `glass-4.4` of OpenMyGlass/android_frameworks_base. That repository is our unmodified mirror of android-security's `aosp-4.4` (the manifest pins it at `1056ab76`), so `glass-4.4` starts from that commit and the mirror branches stay as they are. The manifest then pins `glass-4.4` in a pull request of its own.

**Base plan:** this replaces Task 5 ("Backports from 5.x and 6.x") of [the Track A plan](2026-10-21-android-lean-kitkat-art.md) for the power items. Its rank 1, a Doze-like idle as a service of our own, moves into the framework (item 2 below), because the framework is the only place that can hold back other apps' alarms and wake locks.

**Rules that bind every item:**
- Safety rule 6: nothing touches charging, the battery driver, thermal limits, voltages or CPU frequencies. The idle controller only reads the plug state from `ACTION_BATTERY_CHANGED`.
- Apps that target API 19 or lower must keep working. No public API is added or changed, so `api/current.txt` stays the same; new methods are internal to `system_server`.
- Upstream authorship is kept. A commit taken from AOSP keeps its `From:` and ends with "(cherry picked from commit <sha>)", or "(adapted from commit <sha>)" when the 4.4 code needed changes. New code says which upstream commits it follows.
- Nothing is tested on a device. Every item ends with a build check and device checks marked **not run**.

AOSP commits below are on `platform/frameworks/base`; the android-security branches `aosp-5.1` and `aosp-6.0` carry them with the same SHA. Paths are in 5.0+ layout (`services/core/java/...`); in 4.4 the same files are under `services/java/...`.

## Candidates, ranked

Benefit is for Glass: a small battery (`battery.capacity` 580 mAh in the device tree's `power_profile.xml`), no Google Play services (so no push messages), mostly worn or lying on a desk, and few third-party apps. Size counts the lines that land in 4.4.

| Rank | Candidate | Benefit on Glass | Port risk and size | Verdict |
|---|---|---|---|---|
| 1 | 5.0/6.0 alarm fixes: delay non-wakeup alarms while the screen is off, a 60 s minimum repeat interval and a 5 s minimum futurity, the batch sort fix | medium: fewer and shorter awake periods; a spammy alarm can no longer hold the CPU up | low, about 200 lines in `AlarmManagerService.java` only | **planned** (implemented first) |
| 2 | Glass device idle: a small Doze for when Glass is off the head, built from 6.0's `DeviceIdleController`, its alarm deferral and its wake-lock disabling | high for idle drain caused by apps; zero for the system's own work | medium, about 800 lines: a new controller plus small hooks in `AlarmManagerService` and `PowerManagerService` | **planned** (second), off unless the device overlay turns it on |
| 3 | Device config already in 4.4: LMK `minfree` and `extra_free_kbytes` adjustments, Wi-Fi framework scan interval | small to medium | config values in the device tree | device tree (Track A plan, Tasks 4 and 5); not a backport |
| 4 | 5.0 battery saver (low power mode) | small: its largest effect is the `POWER_HINT_LOW_POWER` CPU hint, which rule 6 rules out; apps can only query it from API 21 | medium-high: `PowerManagerService`, `BatteryService`, SystemUI, settings | **not planned** |
| 5 | 6.0 Doze in full (`DeviceIdleController`) | small over rank 2 | high: needs 6.0's netd firewall chains, `BroadcastOptions` temporary whitelists, the `LocalServices` and `SystemService` framework of 5.0 | **not planned**; rank 2 takes its alarm and wake-lock parts |
| 6 | 6.0 App Standby | small: few apps, and rank 2's whitelist covers the same ground | high: built on 5.0's `UsageStatsService` and on JobScheduler | **not planned** |
| 7 | 5.0 JobScheduler | none for apps that target API 19 or lower: `android.app.job` is API 21, and the compat libraries (JobSchedulerCompat, Firebase JobDispatcher, WorkManager) check `SDK_INT` and fall back to `AlarmManager` on 4.4 | high: new system service, binder API, permissions | **not planned** |
| 8 | `setAndAllowWhileIdle` and `setExactAndAllowWhileIdle` (6.0) | none as API: apps on 4.4 cannot call them | API 23 | **not planned** as API; rank 2 gives the same exemption to system alarms and whitelisted apps |
| 9 | 7.0 background check (no manifest `CONNECTIVITY_ACTION`, background service limits) | none: 7.0 applies it only to apps that target API 24+, and applying it to older apps would break them | medium | **not planned** |
| 10 | 5.x/6.x process-state and LMK changes in ActivityManager | small: 4.4 already has process states, procstats, `ro.config.low_ram` and the LMK adjustments | high: many scattered "Project Svelte" changes | **not planned** |
| 11 | Network deferral while idle (6.0's `FIREWALL_CHAIN_DOZABLE`) | small: no push service, and Wi-Fi traffic is rare when nothing runs | high to do blind: 4.4's netd firewall has only a global whitelist mode, which also blocks DHCP and DNS unless every system uid is allowed | **later**, after device measurements |

### Rank 1: alarm fixes from 5.0 and 6.0

| AOSP commit | Author | What | In 4.4 |
|---|---|---|---|
| `d4e6d467cd61d6bec1ae25744a415a96f0a0f760` "Delay the dispatching of non-wakeup alarms." | Dianne Hackborn | With the screen off, non-wakeup alarms that come due while the CPU is awake for another reason wait: up to 2 min in the first 5 min of screen-off, 15 min up to 30 min, then an hour. Screen-on or the next wakeup alarm delivers them. | adapted: the alarm-stats change to `PendingIntent` tags (5.0 API) and the package-manager command are left out |
| `864d42eb96a9127b7d2f10ad11e709c24b4b4304` "Properly recognize repeating wakeup alarms" | Christopher Tate | Fix to the above: repeating wakeup alarms count as wakeups | adapted (line moves only) |
| `649acab38956759213309835de39b14d43c1417e` "Fix bugs regarding delay the dispatching of non-wakeup alarms" | minho.choo (LGE) | Fix to the above: a reversed comparison | adapted (path) |
| `498c6cbd78f42d4f6d2568ead6c2697fcfaa326e` "Prevent some alarm pathologies" | Christopher Tate | Repeat intervals below 60 s become 60 s, trigger times less than 5 s ahead become 5 s | adapted (path, 4.4 `set()` signature) |
| `1acd32a60b9ec67878302f6d629c5d5e7e2ee813` "Fix bug regarding the comparator sorts Alarms into increasing time order." | jinho.park (LGE) | The in-batch sort used `when`, which mixes RTC and elapsed time; it now uses `whenElapsed` | adapted (path) |

Left out on purpose:
- `81f9882b5aad` "Tune delivery and batching of alarms" and its partial rollback `0dab4dc03d1d`: a batching policy change (exact alarms stop coalescing), not a power saving.
- `c83d3e4b72f8` "Always re-establish kernel alarms": reverted upstream by `753e9e0f2d0c`.
- `c352722e8af0` "Ignore small time changes": fixes spurious time-change flags of the 5.0 timerfd backend; 4.4 uses `/dev/alarm`, which does not produce them.
- `1590f1ee7b7b` "Fix alarm delivery-order sorting": delivery order only.

Compatibility: the 60 s and 5 s floors are what 5.0 and later impose on every app, whatever its target. An app that repeats faster than once a minute through `AlarmManager` gets one alarm a minute; `Handler` and `Timer` are unaffected. Non-wakeup alarms were never guaranteed to run while the screen is off (`AlarmManager.RTC` and `ELAPSED_REALTIME` documentation).

### Rank 2: Glass device idle

A simpler, Glass-specific version of 6.0's Doze. It defers alarms and disables partial wake locks of apps that are not exempt while Glass is idle, and lets them run in maintenance windows.

**Upstream code it follows:**
- `PowerManagerService`: the "disabled" wake lock flag and the uid whitelist from `8d66b3fbf5d8036e25d64a8472bcd2b6b7892a1a` "Implement device idle in power manager." (Dianne Hackborn), with 6.0.1's exemption for apps in the foreground or running a foreground service.
- `AlarmManagerService`: the "pending while idle" list from `4870e9d5eba59fb257a87f97f1adf0b734cf48d3` "More work on device idle mode and other power stuff." and `1e38382b542f5cef9957a89692b02c55a3dd351c` "Fixes to idle alarm scheduling" (Dianne Hackborn), and 6.0's rule that alarms set by the system for itself (uid below 10000, no work source) are not deferred (`a750a63d639f`, `3d1933c45fe9`).
- The controller: the states and timeouts of `DeviceIdleController` (`8ad2af7e5b28f71e7bdfc1bb097937c6c1d22b18` "First stab at device idle mode.", `88e98dfa59e68a860d8c3b462ec03bc0b06d6b5c` "More work on device idle mode.") and the significant-motion exit.

**What differs from 6.0, and why:**
- **Entry.** Screen off and not plugged in (as 6.0), plus "not worn" when a wear signal exists. 6.0 waits for a stationary device (significant motion, then AnyMotion); Glass has a better signal, on-head detection, which the R4 glasshub service will provide. Until then:
  - a broadcast `com.android.server.glass.action.WEARER_STATE` (extra `worn`, sender needs `DEVICE_POWER`) lets that service report it;
  - the significant-motion sensor is used if the sensor HAL lists one (`TYPE_SIGNIFICANT_MOTION`, API 18); motion leaves idle;
  - with no wear report, the inactive timeout is the long one (30 min, as 6.0); after a "not worn" report it is short (5 min).
- **Who is exempt.** System uids (below 10000), packages in `config_glassIdleWhitelist`, and apps that have a process in the foreground, visible or with a foreground service. 6.0 also lets whitelisted apps keep the network but still defers their alarms; on Glass the whitelist exempts alarms too, since the companion app's link to the phone is the main reason to whitelist anything.
- **Not ported:** network blocking (rank 11), sync and job deferral (no JobScheduler; SyncManager has little to do without Google accounts), the `DEVICE_IDLE_MODE_CHANGED` broadcast and `PowerManager.isDeviceIdleMode()` (API 23), the temporary whitelist for high-priority messages (no push service), AnyMotion.
- **Schedule:** idle for 60 min, doubling up to 6 h, with a 5 min maintenance window in between (6.0's defaults). Leaving idle (screen on, plug in, worn, motion) ends deferral at once and delivers what was held.
- **Switches:** `config_glassIdleEnabled` (default `false`; the device tree's overlay turns it on), `persist.glass.idle=0` turns it off at run time, and `dumpsys glassidle` shows the state and has `enable`, `disable`, `force-idle`, `step` and `unforce` for testing.

### Files

| Repository | Branch | Files |
|---|---|---|
| OpenMyGlass/android_frameworks_base | `glass-4.4` (from `aosp-4.4` at `1056ab76`) | `services/java/com/android/server/AlarmManagerService.java`, `services/java/com/android/server/power/PowerManagerService.java`, new `services/java/com/android/server/GlassIdleController.java` and `GlassIdlePolicy.java`, `services/java/com/android/server/SystemServer.java`, `core/res/res/values/config.xml` and `symbols.xml`, a host test and its CI workflow |
| OpenMyGlass/manifest | `main` | `default.xml`: pin `glass-4.4` |
| OpenMyGlass/android_device_glass_glass-1 | `android-4.4.4` | overlay: `config_glassIdleEnabled=true`, `config_glassIdleWhitelist` |

## Device checks (not run)

Nothing here has run on a Glass. With a device:

- [ ] Boot; `dumpsys alarm` shows the "pending non-wakeup" section and `dumpsys glassidle` its state; no `system_server` crash in `logcat`.
- [ ] Rank 1: with the screen off, `dumpsys alarm` lists delayed non-wakeup alarms and their count; screen on delivers them; the clock is right after screen-on.
- [ ] Rank 1: a test app with `setRepeating(..., 1000, ...)` logs "Suspiciously short interval" and fires once a minute.
- [ ] Rank 2: off the head, unplugged, screen off: `dumpsys glassidle` reaches `IDLE` after the inactive timeout; `dumpsys power` shows app wake locks as `DISABLED`; `dumpsys alarm` lists app alarms as pending while idle.
- [ ] Rank 2: a maintenance window delivers the held alarms; screen-on, plugging in and putting Glass on each leave idle at once.
- [ ] Rank 2: music with a foreground service keeps playing through idle; the OpenMyGlass companion link stays up when whitelisted.
- [ ] Idle drain over 8 h off the head, with and without `persist.glass.idle=0`, and the wakeup count from `dumpsys batterystats` (roadmap "Measurement plan").

## Decisions for the owner

1. Rank 1's 60 s repeat floor and 5 s futurity floor apply to every app, as on 5.0 and later. Keep them (assumed), or limit them to apps that target API 19+.
2. Rank 2 is off in the framework and on through the device overlay. Its whitelist starts empty except for system uids; the OpenMyGlass companion package goes in when its package name is fixed.
3. Network blocking while idle (rank 11): only after an idle-drain measurement shows Wi-Fi wakeups matter.
