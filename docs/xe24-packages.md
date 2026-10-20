# XE24 system apps

Inventory of `/system/app` and `/system/priv-app` in Google's XE24 factory image (`glass_1-img-5585826`, SHA-256 `76a9d382…2363`). It was produced offline:

```sh
tools/fetch-factory.sh factory/
tools/sparse.py factory/system.img factory/system.raw
tools/inventory.py factory/system.raw factory/inventory.json
tools/check_debloat.py factory/inventory.json debloat/xe24-packages.tsv
tools/render_packages.py factory/inventory.json debloat/xe24-packages.tsv docs/xe24-packages.md
```

The decisions come from [`debloat/xe24-packages.tsv`](../debloat/xe24-packages.tsv), which is the source of truth. They are a **draft**:
- every *remove* is first disabled on a device (`pm disable`, reversible) and checked before anything is deleted;
- every *unknown* needs that check before it gets a decision.

Notes:
- The image is odexed: each APK has its `.odex` next to it, and removing an app means deleting both files.
- The Glass apps report version `XE22.0`, while the system is XE24 (`4.4.4-5585826`).
- The Glass-specific framework libraries, `/system/framework/glass-core.jar` and `glass-services.jar` (permission file `glass-core.xml`), stay.
- *Net* means the app requests `android.permission.INTERNET`.

45 apps: 33 keep, 2 remove, 10 unknown. Removing every *remove* frees 3104 KiB.

| Decision | Package | Label | Version | Path | APK | Odex | Net | Reason |
|---|---|---|---|---|---:|---:|:-:|---|
| **remove** | `com.google.android.backuptransport` | Google Backup Transport | 4.4.4-5585826 | `/system/priv-app/GoogleBackupTransport.apk` | 105 KiB | 265 KiB |  | Google cloud backup; backend shut down |
| **remove** | `com.google.glass.update` | Glass Update | XE22.0 | `/system/priv-app/GlassUpdate.apk` | 2734 KiB | 0 KiB | ✓ | OTA updater; no updates exist after XE24 (check that first-run setup does not wait on it) |
| **unknown** | `com.android.providers.calendar` | Calendar Storage | 4.4.4-5585826 | `/system/priv-app/CalendarProvider.apk` | 156 KiB | 388 KiB | ✓ | content provider other apps may query; nothing syncs into it after XE24 |
| **unknown** | `com.google.android.gms` | Google Play services | 6.1.11 (1474901-334) | `/system/priv-app/GmsCore.apk` | 12476 KiB | 0 KiB | ✓ | Google Play services 6.1, backend gone; check that Glass Home, Voice and Camera still start without it |
| **unknown** | `com.google.android.gsf` | Google Services Framework | 4.4.4-5585826 | `/system/priv-app/GoogleServicesFramework.apk` | 1089 KiB | 1717 KiB | ✓ | Google Services Framework, backend gone; same check as gms |
| **unknown** | `com.google.android.gsf.login` | Google Account Manager | 4.4.4-5585826 | `/system/priv-app/GoogleLoginService.apk` | 1677 KiB | 809 KiB | ✓ | Google account sign-in; XE24 no longer needs an account, but GSF and Play services authenticate through it: decide together with gsf and gms |
| **unknown** | `com.google.glass.companion` | Glass Wear | XE22.0 | `/system/priv-app/MyGlassWear.apk` | 3994 KiB | 0 KiB | ✓ | 'Glass Wear': the Glass side of the MyGlass companion link (time zone, Wi-Fi setup) that OpenMyGlass talks to; probably keep |
| **unknown** | `com.google.glass.litesetup` | Lite setup | XE22.0 | `/system/priv-app/GlassLiteSetup.apk` | 1251 KiB | 0 KiB | ✓ | first-run setup; check whether pairing or Wi-Fi setup depends on it |
| **unknown** | `com.google.glass.lockrecovery` | Lock Screen Recovery | XE22.0 | `/system/priv-app/GlassLockRecovery.apk` | 8438 KiB | 0 KiB | ✓ | screen-lock recovery; uses the network and probably needs a dead Google backend |
| **unknown** | `com.google.glass.logging` |  | XE22.0 | `/system/priv-app/GlassLogging.apk` | 3191 KiB | 0 KiB | ✓ | usage logging and crash upload to Google (backend gone); other Glass apps may write to its provider and crash without it: check its manifest and disable first |
| **unknown** | `com.google.glass.remoteime` | RemoteIme | 000000 | `/system/priv-app/GlassRemoteIme.apk` | 2168 KiB | 0 KiB |  | remote keyboard input from the companion app; check whether anything still uses it |
| **unknown** | `com.google.glass.sync` | Glass Sync | XE22.0 | `/system/priv-app/GlassSync.apk` | 3455 KiB | 0 KiB | ✓ | timeline/cloud sync with Google (backend gone); it may own the account, sync adapter or provider Glass Home uses: check before removing |
| **keep** | `board_id.com.ti` | TI Board ID App | 1.0 | `/system/app/Board_id.apk` | 56 KiB | 12 KiB |  | TI board identification (hardware support) |
| **keep** | `com.android.backupconfirm` |  | 4.4.4-5585826 | `/system/priv-app/BackupRestoreConfirmation.apk` | 15 KiB | 9 KiB |  | AOSP: confirms adb backup/restore |
| **keep** | `com.android.bluetooth` | Bluetooth Share | 4.4.4-5585826 | `/system/app/Bluetooth.apk` | 388 KiB | 808 KiB | ✓ | AOSP Bluetooth stack: the OpenMyGlass bridge runs over it |
| **keep** | `com.android.certinstaller` | Certificate Installer | 4.4.4-5585826 | `/system/app/CertInstaller.apk` | 27 KiB | 33 KiB |  | AOSP: Wi-Fi/VPN certificates |
| **keep** | `com.android.defcontainer` | Package Access Helper | 4.4.4-5585826 | `/system/priv-app/DefaultContainerService.apk` | 13 KiB | 20 KiB |  | AOSP: needed to install APKs |
| **keep** | `com.android.inputdevices` | Input Devices | 4.4.4-5585826 | `/system/priv-app/InputDevices.apk` | 55 KiB | 1 KiB |  | AOSP: keyboard layouts |
| **keep** | `com.android.keychain` | Key Chain | 4.4.4-5585826 | `/system/app/KeyChain.apk` | 21 KiB | 29 KiB |  | AOSP: credential storage |
| **keep** | `com.android.keyguard` |  | 4.4.4-5585826 | `/system/priv-app/Keyguard.apk` | 615 KiB | 364 KiB |  | AOSP lock screen (keyguard); likely used by the Glass screen lock |
| **keep** | `com.android.location.fused` | Fused Location | 4.4.4-5585826 | `/system/priv-app/FusedLocation.apk` | 9 KiB | 12 KiB |  | AOSP location provider |
| **keep** | `com.android.packageinstaller` | Package installer | 4.4.4-5585826 | `/system/app/PackageInstaller.apk` | 88 KiB | 153 KiB |  | AOSP: needed to sideload the OpenMyGlass Glass app |
| **keep** | `com.android.providers.contacts` | Contacts Storage | 4.4.4-5585826 | `/system/priv-app/ContactsProvider.apk` | 298 KiB | 779 KiB |  | content provider used by Phone and notifications |
| **keep** | `com.android.providers.downloads` | Download Manager | 4.4.4-5585826 | `/system/priv-app/DownloadProvider.apk` | 219 KiB | 326 KiB | ✓ | AOSP Download Manager, used by framework services |
| **keep** | `com.android.providers.media` | Media Storage | 4.4.4-5585826 | `/system/priv-app/MediaProvider.apk` | 101 KiB | 174 KiB |  | indexes photos/videos (camera, media sync) |
| **keep** | `com.android.providers.settings` | Settings Storage | 4.4.4-5585826 | `/system/priv-app/SettingsProvider.apk` | 116 KiB | 84 KiB |  | AOSP settings storage: removing it breaks boot |
| **keep** | `com.android.providers.telephony` | Phone/Messaging Storage | 4.4.4-5585826 | `/system/app/TelephonyProvider.apk` | 80 KiB | 100 KiB |  | AOSP: SMS/MMS storage used by the phone/messaging features |
| **keep** | `com.android.providers.userdictionary` | User Dictionary | 4.4.4-5585826 | `/system/app/UserDictionaryProvider.apk` | 11 KiB | 17 KiB |  | AOSP: small, used by input methods |
| **keep** | `com.android.sharedstoragebackup` |  | 4.4.4-5585826 | `/system/priv-app/SharedStorageBackup.apk` | 6 KiB | 9 KiB |  | AOSP: part of adb backup |
| **keep** | `com.android.shell` | Shell | 4.4.4-5585826 | `/system/priv-app/Shell.apk` | 16 KiB | 18 KiB |  | AOSP: adb shell and bugreports |
| **keep** | `com.android.systemui` | System UI | 4.4.4-5585826 | `/system/priv-app/SystemUI.apk` | 787 KiB | 453 KiB |  | AOSP system UI: removing it breaks boot |
| **keep** | `com.android.vpndialogs` | VpnDialogs | 4.4.4-5585826 | `/system/priv-app/VpnDialogs.apk` | 12 KiB | 9 KiB |  | AOSP: VPN confirmation dialogs, tiny |
| **keep** | `com.google.android.glass.systemui` | Glass System UI | 4.4.4-5585826 | `/system/priv-app/GlassSystemUI.apk` | 61 KiB | 107 KiB |  | Glass system UI |
| **keep** | `com.google.android.tts` | Google Text-to-speech Engine | 3.0.11.5585826 | `/system/app/GoogleTTS.apk` | 1529 KiB | 3052 KiB | ✓ | offline text-to-speech engine, available to apps that read text aloud |
| **keep** | `com.google.glass.bluetooth` | Glass Bluetooth | XE22.0 | `/system/priv-app/GlassBluetooth.apk` | 2253 KiB | 0 KiB | ✓ | Glass Bluetooth pairing UI |
| **keep** | `com.google.glass.camera` | Camera | XE22.0 | `/system/priv-app/GlassCamera.apk` | 3506 KiB | 0 KiB | ✓ | camera: photos and videos for media sync |
| **keep** | `com.google.glass.frameworkstubs` | Framework Stubs | 4.4.4-5585826 | `/system/app/FrameworkStubs.apk` | 20 KiB | 37 KiB |  | Glass framework stubs; likely part of the GDK runtime |
| **keep** | `com.google.glass.gesture` |  | XE22.0 | `/system/priv-app/GlassGesture.apk` | 3010 KiB | 0 KiB | ✓ | touchpad and head gestures |
| **keep** | `com.google.glass.home` | Glass Home | XE22.0 | `/system/priv-app/GlassHome.apk` | 3600 KiB | 0 KiB | ✓ | launcher and timeline; hosts the GDK LiveCards the OpenMyGlass app uses |
| **keep** | `com.google.glass.phone` | Phone | XE22.0 | `/system/priv-app/GlassPhone.apk` | 2864 KiB | 0 KiB | ✓ | calls through the paired phone (Bluetooth HFP) |
| **keep** | `com.google.glass.settings` | Glass Settings Provider | 4.4.4-5585826 | `/system/priv-app/GlassSettingsProvider.apk` | 8 KiB | 10 KiB |  | Glass settings storage |
| **keep** | `com.google.glass.settings.ui` | Glass Settings | XE22.0 | `/system/priv-app/GlassSettings.apk` | 8001 KiB | 0 KiB | ✓ | Glass settings screens |
| **keep** | `com.google.glass.sound` | Glass Sound | XE22.0 | `/system/priv-app/GlassSound.apk` | 1694 KiB | 0 KiB | ✓ | system sounds |
| **keep** | `com.google.glass.videoplayer` | Glass Video Player | XE22.0 | `/system/priv-app/GlassVideoPlayer.apk` | 3365 KiB | 0 KiB | ✓ | plays recorded videos |
| **keep** | `com.google.glass.voice` | Glass Voice | XE22.0 | `/system/priv-app/GlassVoice.apk` | 10769 KiB | 0 KiB | ✓ | 'ok glass' hotword and voice menus |
