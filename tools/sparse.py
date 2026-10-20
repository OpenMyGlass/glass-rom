#!/usr/bin/env python3
"""Convert an Android sparse image to a raw image.

Usage: sparse.py SPARSE_IMG RAW_IMG
"""
import shutil
import struct
import sys

MAGIC = 0xED26FF3A
FILE_HEADER = struct.Struct("<IHHHHIIII")
CHUNK_HEADER = struct.Struct("<HHII")
RAW, FILL, DONT_CARE, CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4


class SparseError(Exception):
    pass


def is_sparse(head: bytes) -> bool:
    return len(head) >= 4 and struct.unpack("<I", head[:4])[0] == MAGIC


def _read(f, n: int) -> bytes:
    data = f.read(n)
    if len(data) != n:
        raise SparseError("sparse image is truncated")
    return data


def unsparse(src, dst) -> None:
    """Read a sparse image from src and write the raw image to dst (both binary files)."""
    (magic, major, _minor, file_hdr, chunk_hdr, blk, total_blocks,
     total_chunks, _checksum) = FILE_HEADER.unpack(_read(src, FILE_HEADER.size))
    if magic != MAGIC or major != 1:
        raise SparseError("not an Android sparse image (v1)")
    if file_hdr < FILE_HEADER.size or chunk_hdr < CHUNK_HEADER.size or blk == 0 or blk % 4:
        raise SparseError("bad sparse header")
    _read(src, file_hdr - FILE_HEADER.size)

    written = 0
    for _ in range(total_chunks):
        kind, _reserved, blocks, total = CHUNK_HEADER.unpack(_read(src, CHUNK_HEADER.size))
        _read(src, chunk_hdr - CHUNK_HEADER.size)
        payload = total - chunk_hdr
        if kind == RAW:
            if payload != blocks * blk:
                raise SparseError("raw chunk size does not match its block count")
            remaining = payload
            while remaining:
                piece = _read(src, min(remaining, 1 << 20))
                dst.write(piece)
                remaining -= len(piece)
        elif kind == FILL:
            if payload != 4:
                raise SparseError("fill chunk must carry 4 bytes")
            block = _read(src, 4) * (blk // 4)
            for _ in range(blocks):
                dst.write(block)
        elif kind == DONT_CARE:
            if payload != 0:
                raise SparseError("don't-care chunk must be empty")
            dst.seek(blocks * blk, 1)
        elif kind == CRC32:
            _read(src, payload)
            continue
        else:
            raise SparseError(f"unknown chunk type {kind:#x}")
        written += blocks

    if written != total_blocks:
        raise SparseError(f"chunks cover {written} blocks, header says {total_blocks}")
    # A trailing don't-care chunk only moved the position: make the output full length.
    end = total_blocks * blk
    if dst.seek(0, 2) < end:
        dst.seek(end - 1)
        dst.write(b"\0")
    dst.truncate(end)


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], "rb") as src:
        if not is_sparse(src.read(4)):
            shutil.copyfile(argv[0], argv[1])
            print(f"{argv[0]} is not sparse; copied as is")
            return 0
        src.seek(0)
        with open(argv[1], "wb") as dst:
            unsparse(src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
