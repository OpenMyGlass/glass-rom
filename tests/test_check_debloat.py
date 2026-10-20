import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_debloat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

TSV = """\
# package\tdecision\treason
com.a\tkeep\tcore
com.b\tremove\tdead cloud service
com.c\tunknown\tcheck on device
"""


class CheckDebloatTest(unittest.TestCase):
    def test_parse_skips_comments_and_reads_decisions(self):
        rows = check_debloat.parse(TSV)
        self.assertEqual(rows, {"com.a": ("keep", "core"), "com.b": ("remove", "dead cloud service"),
                                "com.c": ("unknown", "check on device")})

    def test_bad_decision_is_rejected(self):
        with self.assertRaises(check_debloat.DebloatError):
            check_debloat.parse("com.a\tmaybe\twhy\n")

    def test_missing_reason_is_rejected(self):
        with self.assertRaises(check_debloat.DebloatError):
            check_debloat.parse("com.a\tremove\t\n")

    def test_duplicate_package_is_rejected(self):
        with self.assertRaises(check_debloat.DebloatError):
            check_debloat.parse("com.a\tkeep\tx\ncom.a\tremove\ty\n")

    def test_compare_reports_unlisted_and_stale(self):
        rows = check_debloat.parse(TSV)
        unlisted, stale = check_debloat.compare(rows, ["com.a", "com.b", "com.new"])
        self.assertEqual(unlisted, ["com.new"])
        self.assertEqual(stale, ["com.c"])

    def test_shipped_list_is_valid(self):
        rows = check_debloat.parse((ROOT / "debloat" / "xe24-packages.tsv").read_text())
        self.assertIn("com.google.glass.home", rows)
        self.assertEqual(rows["com.google.glass.home"][0], "keep")
        self.assertEqual(rows["com.google.android.glass.systemui"][0], "keep")


if __name__ == "__main__":
    unittest.main()
