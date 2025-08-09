#!/usr/bin/env python3
from pathlib import Path
from gmti4607.binary.reader import _load_bytes
from gmti4607.binary.codecs.bitcursor import Cursor

p = Path("tools/first_dwell.bin")  # from your earlier extractor
data = _load_bytes(str(p))
cur = Cursor(data)
mask = int.from_bytes(cur.take(8), "big")

print(f"D1 mask: 0x{mask:016x}")
print("Bits set (from MSB=63 down to 0):")
bits = [i for i in range(63, -1, -1) if (mask >> i) & 1]
print(bits)
