import gzip
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import ramdisk  # noqa: E402


def sample():
    return [
        ramdisk.Entry(name="dev", mode=0o040755, data=b""),
        ramdisk.Entry(name="default.prop", mode=0o100644,
                      data=b"#\n# ADDITIONAL_DEFAULT_PROPERTIES\n#\nro.secure=1\nro.allow.mock.location=0\nro.debuggable=0\npersist.sys.usb.config=mtp\n"),
        ramdisk.Entry(name="init", mode=0o100750, data=b"\x7fELF" + b"\0" * 100),
        ramdisk.Entry(name="sbin/adbd", mode=0o100750, data=b"adbd"),
    ]


class RamdiskTest(unittest.TestCase):
    def test_write_then_read_round_trips_entries(self):
        entries = ramdisk.read(ramdisk.write(sample()))
        self.assertEqual(entries[-1].name, "TRAILER!!!")
        entries = entries[:-1]
        self.assertEqual([(e.name, e.mode, e.data) for e in entries],
                         [(e.name, e.mode, e.data) for e in sample()])

    def test_read_then_write_is_byte_identical(self):
        data = ramdisk.write(sample())
        self.assertEqual(ramdisk.write(ramdisk.read(data)), data)

    def test_trailer_fields_are_kept_on_rewrite(self):
        entries = sample() + [ramdisk.Entry(name="TRAILER!!!", mode=0o644, data=b"", ino=0x49407)]
        raw = gzip.decompress(ramdisk.write(ramdisk.read(ramdisk.write(entries))))
        self.assertIn(b"070701" + b"%08x" % 0x49407 + b"%08x" % 0o644, raw)

    def test_output_is_gzip_of_newc_cpio_with_trailer(self):
        raw = gzip.decompress(ramdisk.write(sample()))
        self.assertTrue(raw.startswith(b"070701"))
        self.assertIn(b"TRAILER!!!\0", raw)

    def test_set_props_replaces_existing_and_appends_missing(self):
        out = ramdisk.set_props(sample(), {"ro.secure": "0", "ro.debuggable": "1", "ro.adb.secure": "0"})
        prop = next(e for e in out if e.name == "default.prop").data.decode()
        self.assertIn("\nro.secure=0\n", prop)
        self.assertIn("\nro.debuggable=1\n", prop)
        self.assertTrue(prop.endswith("ro.adb.secure=0\n"))
        self.assertNotIn("ro.secure=1", prop)
        self.assertIn("persist.sys.usb.config=mtp\n", prop)

    def test_set_props_leaves_other_entries_untouched(self):
        before = sample()
        after = ramdisk.set_props(before, {"ro.secure": "0"})
        for a, b in zip(before, after):
            if a.name != "default.prop":
                self.assertEqual(a, b)

    def test_set_props_requires_default_prop(self):
        with self.assertRaises(ramdisk.RamdiskError):
            ramdisk.set_props([e for e in sample() if e.name != "default.prop"], {"ro.secure": "0"})

    def test_garbage_is_rejected(self):
        with self.assertRaises(ramdisk.RamdiskError):
            ramdisk.read(gzip.compress(b"not a cpio archive"))


if __name__ == "__main__":
    unittest.main()
