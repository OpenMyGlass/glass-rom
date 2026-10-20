import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import render_packages  # noqa: E402

APPS = [
    {"package": "com.k", "label": "Keep", "version_name": "1", "path": "/system/app/K.apk",
     "size": 2048, "odex_size": 4096, "permissions": []},
    {"package": "com.r", "label": "Remove", "version_name": "2", "path": "/system/priv-app/R.apk",
     "size": 1024, "odex_size": 0, "permissions": ["android.permission.INTERNET"]},
]
ROWS = {"com.k": ("keep", "core"), "com.r": ("remove", "dead | backend")}


class RenderTest(unittest.TestCase):
    def test_table_orders_remove_first_and_counts_odex(self):
        rows = render_packages.table(APPS, ROWS)
        self.assertTrue(rows[0].startswith("| **remove** | `com.r`"))
        self.assertIn("| 2 KiB | 4 KiB |", rows[1])
        self.assertIn("| ✓ |", rows[0])

    def test_pipes_in_text_are_escaped(self):
        self.assertIn("dead \\| backend", render_packages.table(APPS, ROWS)[0])

    def test_summary_counts_decisions_and_sizes(self):
        self.assertEqual(render_packages.summary(APPS, ROWS),
                         "2 apps: 1 keep, 1 remove, 0 unknown. Removing every *remove* frees 1 KiB.")


if __name__ == "__main__":
    unittest.main()
