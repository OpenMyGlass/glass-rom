# XE24 system apps

Inventory of `/system/app` and `/system/priv-app` in Google's XE24 factory image (`glass_1-img-5585826`, SHA-256 `76a9d382…2363`). It was produced offline with:

```sh
tools/fetch-factory.sh factory/
tools/sparse.py factory/system.img factory/system.raw
tools/inventory.py factory/system.raw factory/inventory.json
tools/check_debloat.py factory/inventory.json debloat/xe24-packages.tsv
```

The decisions come from [`debloat/xe24-packages.tsv`](../debloat/xe24-packages.tsv), which is the source of truth. They are a **draft**:
- every *remove* is first disabled on a device (`pm disable`, reversible) and checked before anything is deleted;
- *unknown* packages need that check before a decision.

Notes:
- The Glass apps report version `XE22.0`, while the system is XE24 (`4.4.4-5585826`). XE23/XE24 changed the platform and services, not the Glass apps' version names.
- Glass-specific framework libraries: `/system/framework/glass-core.jar` and `glass-services.jar` (permission file `glass-core.xml`). They stay: the GDK runtime is built on them.
- *Net* means the app requests `android.permission.INTERNET`.

| Decision | Package | Label | Version | Path | Size | Net | Reason |
|---|---|---|---|---|---:|:-:|---|
| **remove** | `com.google.android.backuptransport` | Google Backup Transport | 4.4.4-5585826 | `/system/priv-app/GoogleBackupTransport.apk` | 105 KiB |  | Google cloud backup; backend shut down |
| **remove** | `com.google.android.gsf.login` | Google Account Manager | 4.4.4-5585826 | `/system/priv-app/GoogleLoginService.apk` | 1677 KiB | ✓ | Google account sign-in, removed by XE24 |
| **remove** | `com.google.glass.logging` |  | XE22.0 | `/system/priv-app/GlassLogging.apk` | 3191 KiB | ✓ | usage logging and crash upload to Google; backend gone |
| **remove** | `com.google.glass.sync` | Glass Sync | XE22.0 | `/system/priv-app/GlassSync.apk` | 3455 KiB | ✓ | timeline/cloud sync with Google servers; backend gone |
| **remove** | `com.google.glass.update` | Glass Update | XE22.0 | `/system/priv-app/GlassUpdate.apk` | 2734 KiB | ✓ | OTA updater; no updates exist after XE24, and an update would undo the debloat |
| **unknown** | `com.android.providers.calendar` | Calendar Storage | 4.4.4-5585826 | `/system/priv-app/CalendarProvider.apk` | 156 KiB | ✓ | content provider other apps may query; nothing syncs into it after XE24 |
| **unknown** | `com.google.android.gms` | Google Play services | 6.1.11 (1474901-334) | `/system/priv-app/GmsCore.apk` | 12476 KiB | ✓ | Google Play services 6.1, backend gone; check that Glass Home, Voice and Camera still start without it |
| **unknown** | `com.google.android.gsf` | Google Services Framework | 4.4.4-5585826 | `/system/priv-app/GoogleServicesFramework.apk` | 1089 KiB | ✓ | Google Services Framework, backend gone; same check as gms |
| **unknown** | `com.google.glass.companion` | Glass Wear | XE22.0 | `/system/priv-app/MyGlassWear.apk` | 3994 KiB | ✓ | 'Glass Wear': the Glass side of the MyGlass companion link (time zone, Wi-Fi setup) that OpenMyGlass talks to; probably keep |
| **unknown** | `com.google.glass.litesetup` | Lite setup | XE22.0 | `/system/priv-app/GlassLiteSetup.apk` | 1251 KiB | ✓ | first-run setup; check whether pairing or Wi-Fi setup depends on it |
| **unknown** | `com.google.glass.remoteime` | RemoteIme | 000000 | `/system/priv-app/GlassRemoteIme.apk` | 2168 KiB |  | remote keyboard input from the companion app; check whether anything still uses it |
| **keep** | `board_id.com.ti` | TI Board ID App | 1.0 | `/system/app/Board_id.apk` | 56 KiB |  | TI board identification (hardware support) |
| **keep** | `com.android.backupconfirm` |  | 4.4.4-5585826 | `/system/priv-app/BackupRestoreConfirmation.apk` | 15 KiB |  | AOSP: confirms adb backup/restore |
| **keep** | `com.android.bluetooth` | Bluetooth Share | 4.4.4-5585826 | `/system/app/Bluetooth.apk` | 388 KiB | ✓ | AOSP Bluetooth stack: the OpenMyGlass bridge runs over it |
| **keep** | `com.android.certinstaller` | Certificate Installer | 4.4.4-5585826 | `/system/app/CertInstaller.apk` | 27 KiB |  | AOSP: Wi-Fi/VPN certificates |
| **keep** | `com.android.defcontainer` | Package Access Helper | 4.4.4-5585826 | `/system/priv-app/DefaultContainerService.apk` | 13 KiB |  | AOSP: needed to install APKs |
| **keep** | `com.android.inputdevices` | Input Devices | 4.4.4-5585826 | `/system/priv-app/InputDevices.apk` | 55 KiB |  | AOSP: keyboard layouts |
| **keep** | `com.android.keychain` | Key Chain | 4.4.4-5585826 | `/system/app/KeyChain.apk` | 21 KiB |  | AOSP: credential storage |
| **keep** | `com.android.keyguard` |  | 4.4.4-5585826 | `/system/priv-app/Keyguard.apk` | 615 KiB |  | AOSP lock screen, used by Glass head-wake/lock |
| **keep** | `com.android.location.fused` | Fused Location | 4.4.4-5585826 | `/system/priv-app/FusedLocation.apk` | 9 KiB |  | AOSP location provider |
| **keep** | `com.android.packageinstaller` | Package installer | 4.4.4-5585826 | `/system/app/PackageInstaller.apk` | 88 KiB |  | AOSP: needed to sideload the OpenMyGlass Glass app |
| **keep** | `com.android.providers.contacts` | Contacts Storage | 4.4.4-5585826 | `/system/priv-app/ContactsProvider.apk` | 298 KiB |  | content provider used by Phone and notifications |
| **keep** | `com.android.providers.downloads` | Download Manager | 4.4.4-5585826 | `/system/priv-app/DownloadProvider.apk` | 219 KiB | ✓ | AOSP Download Manager, used by framework services |
| **keep** | `com.android.providers.media` | Media Storage | 4.4.4-5585826 | `/system/priv-app/MediaProvider.apk` | 101 KiB |  | indexes photos/videos (camera, media sync) |
| **keep** | `com.android.providers.settings` | Settings Storage | 4.4.4-5585826 | `/system/priv-app/SettingsProvider.apk` | 116 KiB |  | AOSP settings storage: removing it breaks boot |
| **keep** | `com.android.providers.telephony` | Phone/Messaging Storage | 4.4.4-5585826 | `/system/app/TelephonyProvider.apk` | 80 KiB |  | AOSP: SMS/MMS storage used by the phone/messaging features |
| **keep** | `com.android.providers.userdictionary` | User Dictionary | 4.4.4-5585826 | `/system/app/UserDictionaryProvider.apk` | 11 KiB |  | AOSP: small, used by input methods |
| **keep** | `com.android.sharedstoragebackup` |  | 4.4.4-5585826 | `/system/priv-app/SharedStorageBackup.apk` | 6 KiB |  | AOSP: part of adb backup |
| **keep** | `com.android.shell` | Shell | 4.4.4-5585826 | `/system/priv-app/Shell.apk` | 16 KiB |  | AOSP: adb shell and bugreports |
| **keep** | `com.android.systemui` | System UI | 4.4.4-5585826 | `/system/priv-app/SystemUI.apk` | 787 KiB |  | AOSP system UI: removing it breaks boot |
| **keep** | `com.android.vpndialogs` | VpnDialogs | 4.4.4-5585826 | `/system/priv-app/VpnDialogs.apk` | 12 KiB |  | AOSP: VPN confirmation dialogs, tiny |
| **keep** | `com.google.android.glass.systemui` | Glass System UI | 4.4.4-5585826 | `/system/priv-app/GlassSystemUI.apk` | 61 KiB |  | Glass system UI |
| **keep** | `com.google.android.tts` | Google Text-to-speech Engine | 3.0.11.5585826 | `/system/app/GoogleTTS.apk` | 1529 KiB | ✓ | offline text-to-speech, used for spoken navigation and readouts |
| **keep** | `com.google.glass.bluetooth` | Glass Bluetooth | XE22.0 | `/system/priv-app/GlassBluetooth.apk` | 2253 KiB | ✓ | Glass Bluetooth pairing UI |
| **keep** | `com.google.glass.camera` | Camera | XE22.0 | `/system/priv-app/GlassCamera.apk` | 3506 KiB | ✓ | camera: photos and videos for media sync |
| **keep** | `com.google.glass.frameworkstubs` | Framework Stubs | 4.4.4-5585826 | `/system/app/FrameworkStubs.apk` | 20 KiB |  | Glass framework stubs, needed by the GDK runtime |
| **keep** | `com.google.glass.gesture` |  | XE22.0 | `/system/priv-app/GlassGesture.apk` | 3010 KiB | ✓ | touchpad and head gestures |
| **keep** | `com.google.glass.home` | Glass Home | XE22.0 | `/system/priv-app/GlassHome.apk` | 3600 KiB | ✓ | launcher and timeline; hosts the GDK LiveCards the OpenMyGlass app uses |
| **keep** | `com.google.glass.lockrecovery` | Lock Screen Recovery | XE22.0 | `/system/priv-app/GlassLockRecovery.apk` | 8438 KiB | ✓ | recovery when the screen lock pattern is forgotten |
| **keep** | `com.google.glass.phone` | Phone | XE22.0 | `/system/priv-app/GlassPhone.apk` | 2864 KiB | ✓ | calls through the paired phone (Bluetooth HFP) |
| **keep** | `com.google.glass.settings` | Glass Settings Provider | 4.4.4-5585826 | `/system/priv-app/GlassSettingsProvider.apk` | 8 KiB |  | Glass settings storage |
| **keep** | `com.google.glass.settings.ui` | Glass Settings | XE22.0 | `/system/priv-app/GlassSettings.apk` | 8001 KiB | ✓ | Glass settings screens |
| **keep** | `com.google.glass.sound` | Glass Sound | XE22.0 | `/system/priv-app/GlassSound.apk` | 1694 KiB | ✓ | system sounds |
| **keep** | `com.google.glass.videoplayer` | Glass Video Player | XE22.0 | `/system/priv-app/GlassVideoPlayer.apk` | 3365 KiB | ✓ | plays recorded videos |
| **keep** | `com.google.glass.voice` | Glass Voice | XE22.0 | `/system/priv-app/GlassVoice.apk` | 10769 KiB | ✓ | 'ok glass' hotword and voice menus |
