import io
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import sparse  # noqa: E402

BLK = 4096


def chunk(kind, blocks, payload=b""):
    return struct.pack("<HHII", kind, 0, blocks, 12 + len(payload)) + payload


def image(chunks, total_blocks, blk=BLK):
    header = struct.pack("<IHHHHIIII", 0xED26FF3A, 1, 0, 28, 12, blk, total_blocks, len(chunks), 0)
    return header + b"".join(chunks)


def convert(data):
    out = io.BytesIO()
    sparse.unsparse(io.BytesIO(data), out)
    return out.getvalue()


class SparseTest(unittest.TestCase):
    def test_raw_fill_and_dont_care_chunks(self):
        data = image([
            chunk(0xCAC1, 1, b"A" * BLK),
            chunk(0xCAC2, 2, b"\x01\x02\x03\x04"),
            chunk(0xCAC3, 1),
            chunk(0xCAC1, 1, b"B" * BLK),
        ], total_blocks=5)
        raw = convert(data)
        self.assertEqual(len(raw), 5 * BLK)
        self.assertEqual(raw[:BLK], b"A" * BLK)
        self.assertEqual(raw[BLK:3 * BLK], b"\x01\x02\x03\x04" * (2 * BLK // 4))
        self.assertEqual(raw[3 * BLK:4 * BLK], b"\0" * BLK)
        self.assertEqual(raw[4 * BLK:], b"B" * BLK)

    def test_crc_chunk_is_skipped(self):
        data = image([chunk(0xCAC1, 1, b"A" * BLK), chunk(0xCAC4, 0, b"\0\0\0\0")], total_blocks=1)
        self.assertEqual(convert(data), b"A" * BLK)

    def test_trailing_dont_care_sets_full_length(self):
        data = image([chunk(0xCAC1, 1, b"A" * BLK), chunk(0xCAC3, 3)], total_blocks=4)
        self.assertEqual(len(convert(data)), 4 * BLK)

    def test_bad_magic_is_rejected(self):
        data = bytearray(image([chunk(0xCAC3, 1)], total_blocks=1))
        data[0] = 0
        with self.assertRaises(sparse.SparseError):
            convert(bytes(data))

    def test_truncated_raw_chunk_is_rejected(self):
        data = image([chunk(0xCAC1, 1, b"A" * BLK)], total_blocks=1)
        with self.assertRaises(sparse.SparseError):
            convert(data[:-10])

    def test_raw_size_mismatch_is_rejected(self):
        bad = struct.pack("<HHII", 0xCAC1, 0, 2, 12 + BLK) + b"A" * BLK
        with self.assertRaises(sparse.SparseError):
            convert(image([bad], total_blocks=2))

    def test_block_count_mismatch_is_rejected(self):
        with self.assertRaises(sparse.SparseError):
            convert(image([chunk(0xCAC3, 1)], total_blocks=2))

    def test_unknown_chunk_type_is_rejected(self):
        with self.assertRaises(sparse.SparseError):
            convert(image([chunk(0xCAC9, 1)], total_blocks=1))

    def test_is_sparse(self):
        self.assertTrue(sparse.is_sparse(image([chunk(0xCAC3, 1)], total_blocks=1)[:4]))
        self.assertFalse(sparse.is_sparse(b"\0\0\0\0"))


if __name__ == "__main__":
    unittest.main()
