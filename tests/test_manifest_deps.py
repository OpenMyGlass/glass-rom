import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import manifest_deps  # noqa: E402

PROVIDER_APP = """\
N: android=http://schemas.android.com/apk/res/android (line=2)
  E: manifest (line=2)
    A: http://schemas.android.com/apk/res/android:sharedUserId(0x0101000b)="android.uid.system" (Raw: "android.uid.system")
    A: package="com.example.store" (Raw: "com.example.store")
      E: permission (line=5)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.store.permission.READ" (Raw: "com.example.store.permission.READ")
      E: application (line=7)
        E: provider (line=8)
          A: http://schemas.android.com/apk/res/android:name(0x01010003)=".StoreProvider" (Raw: ".StoreProvider")
          A: http://schemas.android.com/apk/res/android:authorities(0x01010018)="com.example.store" (Raw: "com.example.store")
        E: service (line=10)
          A: http://schemas.android.com/apk/res/android:name(0x01010003)=".Sync" (Raw: ".Sync")
          E: intent-filter (line=11)
            E: action (line=12)
              A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.SYNC" (Raw: "com.example.SYNC")
"""

CLIENT_APP = """\
N: android=http://schemas.android.com/apk/res/android (line=2)
  E: manifest (line=2)
    A: package="com.example.client" (Raw: "com.example.client")
      E: uses-permission (line=4)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.store.permission.READ" (Raw: "com.example.store.permission.READ")
      E: application (line=6)
        E: uses-library (line=7)
          A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.google.android.glass" (Raw: "com.google.android.glass")
"""


class ManifestDepsTest(unittest.TestCase):
    def test_parse_collects_declarations(self):
        m = manifest_deps.parse(PROVIDER_APP)
        self.assertEqual(m["package"], "com.example.store")
        self.assertEqual(m["shared_user"], "android.uid.system")
        self.assertEqual(m["permissions"], ["com.example.store.permission.READ"])
        self.assertEqual(m["providers"], ["com.example.store"])
        self.assertEqual(m["services"], [".Sync"])
        self.assertEqual(m["actions"], ["com.example.SYNC"])

    def test_parse_collects_uses(self):
        m = manifest_deps.parse(CLIENT_APP)
        self.assertEqual(m["uses_permissions"], ["com.example.store.permission.READ"])
        self.assertEqual(m["libraries"], ["com.google.android.glass"])

    def test_dependents_are_apps_using_its_permissions(self):
        apps = [manifest_deps.parse(PROVIDER_APP), manifest_deps.parse(CLIENT_APP)]
        self.assertEqual(manifest_deps.dependents(apps, "com.example.store"), ["com.example.client"])
        self.assertEqual(manifest_deps.dependents(apps, "com.example.client"), [])

    def test_text_without_manifest_is_an_error(self):
        with self.assertRaises(ValueError):
            manifest_deps.parse("W: no manifest\n")


if __name__ == "__main__":
    unittest.main()
