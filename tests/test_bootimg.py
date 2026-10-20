import hashlib
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import bootimg  # noqa: E402


def synthetic(kernel=b"K" * 5000, ramdisk=b"R" * 3000, second=b"", page=2048):
    return bootimg.BootImage(
        kernel=kernel, ramdisk=ramdisk, second=second,
        kernel_addr=0x80008000, ramdisk_addr=0x81000000, second_addr=0x80f00000,
        tags_addr=0x80000100, page_size=page,
        name=b"test", cmdline=b"console=ttyO2,115200n8",
    )


class BootImageTest(unittest.TestCase):
    def test_pack_then_parse_round_trips_every_field(self):
        img = synthetic(second=b"S" * 10)
        parsed = bootimg.parse(bootimg.pack(img))
        self.assertEqual(parsed.kernel, img.kernel)
        self.assertEqual(parsed.ramdisk, img.ramdisk)
        self.assertEqual(parsed.second, img.second)
        self.assertEqual(parsed.kernel_addr, 0x80008000)
        self.assertEqual(parsed.ramdisk_addr, 0x81000000)
        self.assertEqual(parsed.tags_addr, 0x80000100)
        self.assertEqual(parsed.page_size, 2048)
        self.assertEqual(parsed.name, b"test")
        self.assertEqual(parsed.cmdline, b"console=ttyO2,115200n8")

    def test_parse_then_pack_is_byte_identical(self):
        data = bootimg.pack(synthetic())
        self.assertEqual(bootimg.pack(bootimg.parse(data)), data)

    def test_sections_are_page_aligned(self):
        data = bootimg.pack(synthetic(kernel=b"K" * 2049, ramdisk=b"R" * 1))
        self.assertEqual(len(data), 2048 * (1 + 2 + 1))
        self.assertEqual(data[2048:2048 + 2049], b"K" * 2049)
        self.assertEqual(data[2048 * 3:2048 * 3 + 1], b"R")

    def test_id_is_sha1_of_sections_and_sizes(self):
        img = synthetic(second=b"S" * 7)
        data = bootimg.pack(img)
        expected = hashlib.sha1(
            img.kernel + struct.pack("<I", len(img.kernel))
            + img.ramdisk + struct.pack("<I", len(img.ramdisk))
            + img.second + struct.pack("<I", len(img.second))
        ).digest()
        self.assertEqual(data[576:576 + 20], expected)

    def test_changed_ramdisk_gets_a_new_id(self):
        a = bootimg.pack(synthetic(ramdisk=b"A" * 10))
        b = bootimg.pack(synthetic(ramdisk=b"B" * 10))
        self.assertNotEqual(a[576:608], b[576:608])

    def test_bad_magic_is_rejected(self):
        data = bytearray(bootimg.pack(synthetic()))
        data[0:8] = b"NOTANDRO"
        with self.assertRaises(bootimg.BootImageError):
            bootimg.parse(bytes(data))

    def test_truncated_image_is_rejected(self):
        data = bootimg.pack(synthetic())
        with self.assertRaises(bootimg.BootImageError):
            bootimg.parse(data[:-2048])

    def test_trailing_data_is_preserved(self):
        data = bootimg.pack(synthetic()) + b"\x00SIGNATURE"
        self.assertEqual(bootimg.pack(bootimg.parse(data)), data)


if __name__ == "__main__":
    unittest.main()
