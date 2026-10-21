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


class AddFileTest(unittest.TestCase):
    def test_adds_parents_then_file_before_trailer(self):
        entries = ramdisk.read(ramdisk.write(sample()))
        out = ramdisk.add_file(entries, "lib/modules/m.ko", b"KO")
        names = [e.name for e in out]
        self.assertEqual(names[-4:], ["lib", "lib/modules", "lib/modules/m.ko", "TRAILER!!!"])
        self.assertEqual(out[-3].mode, 0o040755)
        self.assertEqual(out[-2].mode, 0o100644)
        self.assertEqual(out[-2].data, b"KO")

    def test_reuses_existing_dirs_and_replaces_existing_file(self):
        entries = sample() + [ramdisk.Entry(name="sbin", mode=0o040750, data=b""),
                              ramdisk.Entry(name="sbin/x", mode=0o100755, data=b"old")]
        out = ramdisk.add_file(entries, "sbin/x", b"new")
        names = [e.name for e in out]
        self.assertEqual(names.count("sbin/x"), 1)
        self.assertEqual(names.count("sbin"), 1)
        self.assertEqual(out[-1].data, b"new")

    def test_round_trips_through_cpio(self):
        out = ramdisk.read(ramdisk.write(ramdisk.add_file(sample(), "lib/modules/m.ko", b"KO")))
        self.assertIn(("lib/modules/m.ko", b"KO"), [(e.name, e.data) for e in out])

    def test_rejects_bad_paths(self):
        for bad in ("/abs", "", "a/../b"):
            with self.assertRaises(ramdisk.RamdiskError):
                ramdisk.add_file(sample(), bad, b"")


class ReplaceLineTest(unittest.TestCase):
    RC = b"on fs\n    mount_all /fstab\n    insmod /a.ko\n\non boot\n"

    def entries(self, data=RC):
        return sample() + [ramdisk.Entry(name="init.x.rc", mode=0o100750, data=data)]

    def test_replaces_the_line_and_keeps_indent_and_the_rest(self):
        out = ramdisk.replace_line(self.entries(), "init.x.rc", "insmod /a.ko", "insmod /b.ko")
        rc = next(e for e in out if e.name == "init.x.rc")
        self.assertEqual(rc.data, self.RC.replace(b"/a.ko", b"/b.ko"))
        self.assertEqual(rc.mode, 0o100750)

    def test_fails_when_the_line_is_missing_or_repeated(self):
        for data in (b"on fs\n", self.RC + b"  insmod /a.ko\n"):
            with self.assertRaises(ramdisk.RamdiskError):
                ramdisk.replace_line(self.entries(data), "init.x.rc", "insmod /a.ko", "x")

    def test_fails_when_the_file_is_missing(self):
        with self.assertRaises(ramdisk.RamdiskError):
            ramdisk.replace_line(sample(), "init.x.rc", "a", "b")


if __name__ == "__main__":
    unittest.main()
