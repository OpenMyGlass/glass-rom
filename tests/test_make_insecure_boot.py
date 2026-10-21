import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import bootimg  # noqa: E402
import make_insecure_boot  # noqa: E402
import ramdisk  # noqa: E402

from test_bootimg import synthetic  # noqa: E402
from test_ramdisk import sample  # noqa: E402


RC = (b"on fs\n    mount_all /fstab.omap4430\n\n    # Load Required Kernel Modules\n"
      b"    insmod /system/lib/modules/pvrsrvkm_sgx540_120.ko\n\non boot\n")
# Synthetic, not a real module: an ELF header, a vermagic and the DDK build string.
OUR_KO = b"\x7fELF\x01\x01" + b"\0" * 12 + b"\x28\x00" + b"\0" * 44 + b"vermagic=3.4.94-g989d925 SMP\0SGX_DDK 1.9@2166536\0"


def stock(rc=RC):
    entries = sample() + [ramdisk.Entry(name="init.omap4430.rc", mode=0o100750, data=rc)]
    return bootimg.pack(synthetic(ramdisk=ramdisk.write(entries)))


def files(image: bytes) -> dict:
    return {e.name: e for e in ramdisk.read(bootimg.parse(image).ramdisk)}


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

    def test_main_creates_the_output_directory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            stock_path = Path(d) / "boot.img"
            stock_path.write_bytes(stock())
            out = Path(d) / "out" / "nested" / "boot-insecure.img"
            make_insecure_boot.main([str(stock_path), str(out)])
            self.assertTrue(out.exists())


class PvrModuleTest(unittest.TestCase):
    def test_puts_our_module_in_the_ramdisk_and_loads_it_from_there(self):
        f = files(make_insecure_boot.make(stock(), kernel=b"K", pvr_module=OUR_KO))
        self.assertEqual(f["lib/modules/pvrsrvkm_sgx540_120.ko"].data, OUR_KO)
        self.assertEqual(f["lib/modules/pvrsrvkm_sgx540_120.ko"].mode, 0o100644)
        self.assertEqual(f["lib/modules"].mode, 0o040755)
        rc = f["init.omap4430.rc"].data
        self.assertIn(b"\n    insmod /lib/modules/pvrsrvkm_sgx540_120.ko\n", rc)
        self.assertNotIn(b"/system/lib/modules/pvrsrvkm", rc)
        self.assertEqual(rc, RC.replace(b"/system/lib/modules/", b"/lib/modules/"))

    def test_without_a_module_the_ramdisk_keeps_the_stock_insmod(self):
        f = files(make_insecure_boot.make(stock()))
        self.assertEqual(f["init.omap4430.rc"].data, RC)
        self.assertNotIn("lib/modules/pvrsrvkm_sgx540_120.ko", f)

    def test_refuses_modules_that_are_not_ours(self):
        import hashlib
        stock_ko = OUR_KO + b" stock"
        cases = {
            b"not elf": "not an ELF",
            OUR_KO[:20] + b" no modinfo 1.9@2166536": "no vermagic",
            OUR_KO[:20] + b" vermagic=x 1.9@2291151": "not DDK 1.9@2166536",
            OUR_KO[:18] + b"\x03\x00 vermagic=x 1.9@2166536": "not a 32-bit little-endian ARM",
        }
        for ko, msg in cases.items():
            with self.assertRaisesRegex(make_insecure_boot.PvrModuleError, msg):
                make_insecure_boot.make(stock(), pvr_module=ko)
        old = make_insecure_boot.STOCK_PVR_SHA256
        make_insecure_boot.STOCK_PVR_SHA256 = hashlib.sha256(stock_ko).hexdigest()
        try:
            with self.assertRaisesRegex(make_insecure_boot.PvrModuleError, "stock XE24 module"):
                make_insecure_boot.make(stock(), pvr_module=stock_ko)
        finally:
            make_insecure_boot.STOCK_PVR_SHA256 = old

    def test_fails_when_the_stock_insmod_line_is_not_there(self):
        with self.assertRaises(ramdisk.RamdiskError):
            make_insecure_boot.make(stock(rc=b"on fs\n"), pvr_module=OUR_KO)

    def test_fails_when_another_rc_still_loads_the_stock_module(self):
        img = bootimg.parse(stock())
        entries = ramdisk.read(img.ramdisk)
        entries.insert(0, ramdisk.Entry(name="init.extra.rc", mode=0o100750,
                                        data=b"insmod /system/lib/modules/pvrsrvkm_sgx540_120.ko\n"))
        from dataclasses import replace
        image = bootimg.pack(replace(img, ramdisk=ramdisk.write(entries)))
        with self.assertRaisesRegex(make_insecure_boot.PvrModuleError, "init.extra.rc"):
            make_insecure_boot.make(image, pvr_module=OUR_KO)


class MainPvrTest(unittest.TestCase):
    def run_main(self, *extra, ko=OUR_KO):
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d)
        (Path(d) / "boot.img").write_bytes(stock())
        (Path(d) / "zImage").write_bytes(b"K")
        (Path(d) / "m.ko").write_bytes(ko)
        args = [str(Path(d) / "boot.img"), str(Path(d) / "out.img")]
        args += [a.replace("@", d + "/") for a in extra]
        make_insecure_boot.main(args)
        return Path(d) / "out.img"

    def test_kernel_without_module_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main("--kernel", "@zImage")
        self.assertEqual(cm.exception.code, 2)

    def test_kernel_with_keep_stock_pvr_is_allowed(self):
        out = self.run_main("--kernel", "@zImage", "--keep-stock-pvr")
        self.assertEqual(files(out.read_bytes())["init.omap4430.rc"].data, RC)

    def test_kernel_with_module(self):
        out = self.run_main("--kernel", "@zImage", "--pvr-module", "@m.ko")
        self.assertIn("lib/modules/pvrsrvkm_sgx540_120.ko", files(out.read_bytes()))

    def test_bad_module_exits_1_and_removes_an_old_output(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, d)
        (d / "boot.img").write_bytes(stock())
        (d / "m.ko").write_bytes(b"junk")
        (d / "out.img").write_bytes(b"old image")
        with self.assertRaises(SystemExit) as cm:
            make_insecure_boot.main([str(d / "boot.img"), str(d / "out.img"),
                                     "--pvr-module", str(d / "m.ko")])
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse((d / "out.img").exists())

    def test_both_options_are_refused(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main("--pvr-module", "@m.ko", "--keep-stock-pvr")
        self.assertEqual(cm.exception.code, 2)

    def test_output_over_the_stock_image_is_refused(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, d)
        (d / "boot.img").write_bytes(stock())
        with self.assertRaises(SystemExit) as cm:
            make_insecure_boot.main([str(d / "boot.img"), str(d / "boot.img")])
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual((d / "boot.img").read_bytes(), stock())

    def test_module_without_kernel_keeps_the_stock_kernel(self):
        out = self.run_main("--pvr-module", "@m.ko")
        img = bootimg.parse(out.read_bytes())
        self.assertEqual(img.kernel, bootimg.parse(stock()).kernel)
        self.assertIn("lib/modules/pvrsrvkm_sgx540_120.ko", files(out.read_bytes()))


if __name__ == "__main__":
    unittest.main()
