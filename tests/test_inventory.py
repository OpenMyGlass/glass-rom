import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import inventory  # noqa: E402

LS = """\
     12   40755 (2)      0      0    4096 22-May-2019 19:49 .
      2   40755 (2)      0      0    4096  1-Jan-1970 01:00 ..
     13  100644 (1)      0      0   397593 22-May-2019 19:49 Bluetooth.apk
     14  100644 (1)      0      0   828112 22-May-2019 19:49 Bluetooth.odex
     20   40755 (2)      0      0    4096 22-May-2019 19:49 SomeDir.apk
     21  100644 (1)      0      0     1234 22-May-2019 19:49 My App.apk

"""

BADGING = """\
package: name='com.example.glass' versionCode='42' versionName='1.2 beta' platformBuildVersionName=''
sdkVersion:'19'
targetSdkVersion:'19'
uses-permission: name='android.permission.INTERNET'
uses-permission: name='android.permission.BLUETOOTH'
application-label:'Example'
application-label-it:'Esempio'
launchable-activity: name='com.example.glass.Main'  label='' icon=''
"""


class InventoryParserTest(unittest.TestCase):
    def test_ls_lists_regular_apk_files_with_sizes(self):
        self.assertEqual(inventory.parse_ls(LS), [("Bluetooth.apk", 397593), ("My App.apk", 1234)])

    def test_ls_of_missing_dir_is_empty(self):
        self.assertEqual(inventory.parse_ls("/nope: File not found by ext2_lookup\n"), [])

    def test_badging_fields(self):
        info = inventory.parse_badging(BADGING)
        self.assertEqual(info["package"], "com.example.glass")
        self.assertEqual(info["version_code"], "42")
        self.assertEqual(info["version_name"], "1.2 beta")
        self.assertEqual(info["label"], "Example")
        self.assertTrue(info["launchable"])
        self.assertEqual(info["permissions"], ["android.permission.INTERNET", "android.permission.BLUETOOTH"])

    def test_badging_without_label_or_activity(self):
        info = inventory.parse_badging("package: name='a.b' versionCode='1' versionName=''\n")
        self.assertEqual(info["package"], "a.b")
        self.assertEqual(info["label"], "")
        self.assertFalse(info["launchable"])
        self.assertEqual(info["permissions"], [])

    def test_badging_without_package_line_is_an_error(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.parse_badging("ERROR: dump failed\n")


if __name__ == "__main__":
    unittest.main()
