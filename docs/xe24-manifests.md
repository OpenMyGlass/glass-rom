# XE24 app dependencies (from manifests)

How the *unknown* entries of the phase 2 debloat list were narrowed down, without a device. Each APK's manifest was dumped with `aapt2 dump xmltree --file AndroidManifest.xml` and summarized with `tools/manifest_deps.py`. It reports, for each package: shared-user peers; permissions that guard its components; the apps it depends on (they declare a permission it requests, directly or through a permission tree); and the apps that depend on it (they request one of its permissions or guards). Only declarations were read: providers, services, permissions and libraries. No code was decompiled, and nothing from the image is committed.

```sh
# after tools/sparse.py (see docs/xe24-packages.md)
mkdir -p factory/manifests
for d in app priv-app; do
  for f in $(debugfs -R "ls /$d" factory/system.raw | tr -s ' ' '\n' | grep '\.apk$'); do
    debugfs -R "dump /$d/$f factory/t.apk" factory/system.raw
    aapt2 dump xmltree --file AndroidManifest.xml factory/t.apk > "factory/manifests/${f%.apk}.txt"
  done
done
tools/manifest_deps.py factory/manifests com.google.glass.sync com.google.glass.logging
```

## Findings

| Package | Finding | Decision |
|---|---|---|
| `com.google.glass.sync` | Owns the **timeline provider** `com.google.glass.sync.timeline`. Glass Home and 12 other Glass apps request its `TIMELINE_PROVIDER` permission. | keep (was unknown; phase 2 first had it as remove) |
| `com.google.android.gsf` | Its Gservices settings are read (`READ_GSERVICES`) by Glass Home, Voice, Settings, Video player, Glass Wear, Glass Sync and TTS, among others. | keep |
| `com.google.glass.companion` ("Glass Wear") | Its listener service filters `com.google.android.gms.wearable.BIND_LISTENER`, so Play services' Wearable layer binds to it. It also hosts the notification bridge and connection setup of the companion link. | keep |
| `com.google.android.gms` | Hosts the Wearable data layer (`WearableService`, `BluetoothServerService`) that binds Glass Wear's listener, plus network location. | keep |
| `com.google.glass.logging` | No provider. 14 Glass apps hold its signature permission `USER_EVENT_SERVICE`, which guards its service. Whether they bind it is decided in code, which this check cannot see. | unknown: disable first, then watch for crashes |
| `com.google.android.gsf.login` | Google account authenticator. Only GSF requests its permissions. | unknown |
| `com.google.glass.litesetup` | First-run wizard (`DEVICE_INITIALIZATION_WIZARD`), needed again after a factory reset. | unknown |
| `com.google.glass.lockrecovery` | A GDK app (`uses-library com.google.android.glass`). Nothing depends on it. | unknown |
| `com.google.glass.remoteime` | Input method fed by the companion app (`COMPANION_APP_CONNECTIVITY_CHANGE`). | unknown |
| `com.android.providers.calendar` | Its provider is guarded by `READ_CALENDAR`/`WRITE_CALENDAR`, which only Shell requests. No other manifest names the `com.android.calendar` authority. | remove (was unknown) |
| `com.google.android.backuptransport` | Shares `com.google.uid.shared` with GSF, Play services and Google login. Its services are guarded by `android.permission.BACKUP`, and no other manifest references it. | remove: check the `backup_transport` setting on a device |
| `com.google.glass.update` | GSF declares `TRIGGER_OTA` and hosts the receiver that installs updates (`INSTALL_UPDATE`); Glass Update and Glass Home only send to it. Nothing depends on Glass Update. | remove |

Implication for OpenMyGlass: the stock companion link goes through Play services' Wearable layer, so Play services and GSF stay even though Google's backends are gone. Shrinking them is out of scope.

Manifests show declarations only. A run-time dependency through code, such as a `bindService` or a content query on an undeclared authority, is not visible here. That is why every *remove* is still disabled on a device first (phase 3).
