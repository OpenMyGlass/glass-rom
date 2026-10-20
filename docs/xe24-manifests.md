# XE24 app dependencies (from manifests)

How the *unknown* entries of the phase 2 debloat list were narrowed down, without a device. Each APK's manifest was dumped with `aapt2 dump xmltree --file AndroidManifest.xml` and summarized with `tools/manifest_deps.py`. Only declarations were read: providers, services, permissions and libraries. No code was decompiled, and nothing from the image is committed.

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
| `com.google.glass.sync` | Owns the **timeline provider** `com.google.glass.sync.timeline`. Glass Home and 12 other Glass apps request its `TIMELINE_PROVIDER` permission. | keep (was remove) |
| `com.google.android.gsf` | Its Gservices settings are read (`READ_GSERVICES`) by Glass Home, Voice, Settings, Video player, Glass Wear and TTS. | keep |
| `com.google.glass.companion` ("Glass Wear") | Binds `com.google.android.gms.wearable.BIND_LISTENER`. It hosts the notification bridge and connection setup of the companion link. | keep |
| `com.google.android.gms` | Hosts the Wearable data layer that Glass Wear listens to (`WearableService`, `BluetoothServerService`), plus network location. | keep |
| `com.google.glass.logging` | No provider. 14 Glass apps request its signature permission `USER_EVENT_SERVICE` and bind its service. | unknown: disable first, then watch for crashes |
| `com.google.android.gsf.login` | Google account authenticator. Only GSF requests its permissions. | unknown |
| `com.google.glass.litesetup` | First-run wizard (`DEVICE_INITIALIZATION_WIZARD`), needed again after a factory reset. | unknown |
| `com.google.glass.lockrecovery` | A GDK app (`uses-library com.google.android.glass`). Nothing depends on it. | unknown |
| `com.google.glass.remoteime` | Input method fed by the companion app (`COMPANION_APP_CONNECTIVITY_CHANGE`). | unknown |
| `com.android.providers.calendar` | Only Shell requests `READ_CALENDAR`/`WRITE_CALENDAR`. | remove (was unknown) |
| `com.google.glass.update` | Glass Home and GSF only hold `TRIGGER_OTA`, which lets them start an update. | remove |

Implication for OpenMyGlass: the stock companion link goes through Play services' Wearable layer, so Play services and GSF stay even though Google's backends are gone. Shrinking them is out of scope.

Manifests show declarations only. A run-time dependency through code, such as a `bindService` or a content query on an undeclared authority, is not visible here. That is why every *remove* is still disabled on a device first (phase 3).
