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

GUARDED_APP = """\
N: android=http://schemas.android.com/apk/res/android (line=2)
  E: manifest (line=2)
    A: http://schemas.android.com/apk/res/android:sharedUserId(0x0101000b)="android.uid.system" (Raw: "android.uid.system")
    A: package="com.example.installer" (Raw: "com.example.installer")
      E: permission-tree (line=3)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.AUTH" (Raw: "com.example.AUTH")
      E: permission (line=4)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.TRIGGER" (Raw: "com.example.TRIGGER")
      E: application (line=6)
        E: provider (line=7)
          A: http://schemas.android.com/apk/res/android:authorities(0x01010018)="com.example.a;com.example.b" (Raw: "com.example.a;com.example.b")
          A: http://schemas.android.com/apk/res/android:readPermission(0x01010007)="android.permission.READ_THINGS" (Raw: "android.permission.READ_THINGS")
          A: http://schemas.android.com/apk/res/android:exported(0x01010010)=true
        E: receiver (line=9)
          A: http://schemas.android.com/apk/res/android:permission(0x01010006)="com.example.TRIGGER" (Raw: "com.example.TRIGGER")
"""

TRIGGER_APP = """\
N: android=http://schemas.android.com/apk/res/android (line=2)
  E: manifest (line=2)
    A: http://schemas.android.com/apk/res/android:sharedUserId(0x0101000b)="android.uid.system" (Raw: "android.uid.system")
    A: package="com.example.updater" (Raw: "com.example.updater")
      E: uses-permission (line=3)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.TRIGGER" (Raw: "com.example.TRIGGER")
      E: uses-permission (line=4)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.example.AUTH.mail" (Raw: "com.example.AUTH.mail")
      E: uses-permission (line=5)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="android.permission.READ_THINGS" (Raw: "android.permission.READ_THINGS")
"""


class GuardedDepsTest(unittest.TestCase):
    def setUp(self):
        self.apps = [manifest_deps.parse(t) for t in (PROVIDER_APP, CLIENT_APP, GUARDED_APP, TRIGGER_APP)]

    def test_multiple_authorities_and_guards_are_parsed(self):
        m = manifest_deps.parse(GUARDED_APP)
        self.assertEqual(m["providers"], ["com.example.a", "com.example.b"])
        self.assertEqual(sorted(m["guards"]), ["android.permission.READ_THINGS", "com.example.TRIGGER"])
        self.assertEqual(m["permission_trees"], ["com.example.AUTH"])

    @staticmethod
    def only(request):
        """TRIGGER_APP reduced to a single uses-permission."""
        lines = TRIGGER_APP.splitlines()
        keep, i = lines[:4], 4
        while i < len(lines):
            if request in lines[i + 1]:
                keep += lines[i:i + 2]
            i += 2
        return manifest_deps.parse("\n".join(keep) + "\n")

    def test_permission_tree_requests_count_as_dependents(self):
        apps = [manifest_deps.parse(GUARDED_APP), self.only("com.example.AUTH.mail")]
        self.assertEqual(manifest_deps.dependents(apps, "com.example.installer"), ["com.example.updater"])

    def test_holders_of_framework_guard_permissions_count_as_dependents(self):
        apps = [manifest_deps.parse(GUARDED_APP), self.only("android.permission.READ_THINGS")]
        self.assertEqual(manifest_deps.dependents(apps, "com.example.installer"), ["com.example.updater"])

    def test_depends_on_lists_packages_declaring_what_it_requests(self):
        self.assertEqual(manifest_deps.depends_on(self.apps, "com.example.updater"), ["com.example.installer"])
        self.assertEqual(manifest_deps.depends_on(self.apps, "com.example.client"), ["com.example.store"])

    def test_shared_user_peers(self):
        self.assertEqual(manifest_deps.shared_user_peers(self.apps, "com.example.installer"),
                         ["com.example.store", "com.example.updater"])
        self.assertEqual(manifest_deps.shared_user_peers(self.apps, "com.example.client"), [])


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
