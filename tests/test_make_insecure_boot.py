import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import bootimg  # noqa: E402
import make_insecure_boot  # noqa: E402
import ramdisk  # noqa: E402

from test_bootimg import synthetic  # noqa: E402
from test_ramdisk import sample  # noqa: E402


def stock():
    return bootimg.pack(synthetic(ramdisk=ramdisk.write(sample())))


def props(image: bytes) -> str:
    entries = ramdisk.read(bootimg.parse(image).ramdisk)
    return next(e for e in entries if e.name == "default.prop").data.decode()


class MakeInsecureBootTest(unittest.TestCase):
    def test_sets_root_adb_props(self):
        p = props(make_insecure_boot.make(stock()))
        for line in ("ro.secure=0", "ro.adb.secure=0", "ro.debuggable=1"):
            self.assertIn(line + "\n", p)

    def test_keeps_stock_kernel_and_header_by_default(self):
        before, after = bootimg.parse(stock()), bootimg.parse(make_insecure_boot.make(stock()))
        self.assertEqual(after.kernel, before.kernel)
        self.assertEqual(after.cmdline, before.cmdline)
        self.assertEqual(after.kernel_addr, before.kernel_addr)
        self.assertEqual(after.page_size, before.page_size)

    def test_replaces_kernel_when_given(self):
        after = bootimg.parse(make_insecure_boot.make(stock(), kernel=b"NEWKERNEL"))
        self.assertEqual(after.kernel, b"NEWKERNEL")


if __name__ == "__main__":
    unittest.main()
