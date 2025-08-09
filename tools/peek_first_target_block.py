#!/usr/bin/env python3
from pathlib import Path
from gmti4607.binary.reader import _load_bytes
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs.packet_header import decode_packet_header
from gmti4607.binary.codecs.segment_header import decode_segment_header
from gmti4607.binary.codecs import segment_header as sh
from gmti4607.binary.codecs.dwell_mask import parse_dwell_header

def hexs(b, n=64): return b[:n].hex()

p = Path("tests/data/samples/binary/UV23/Day02 - GRCA1-mti.4607")  # adjust if needed
data = _load_bytes(str(p))
cur = Cursor(data)

while cur.remaining() >= 32:
    pkt_start = cur.tell()
    ph = decode_packet_header(cur)
    pkt_end = pkt_start + ph["packet_size"]
    while cur.tell() + 5 <= pkt_end:
        st, sz = decode_segment_header(cur)
        payload = cur.take(sz - 5)
        if getattr(sh.SegmentType, "DWELL", None) == st:
            dcur = Cursor(payload)
            meta = parse_dwell_header(dcur)
            d5 = int(meta.get("D5_target_count", 0))
            if d5 > 0:
                start = dcur.tell()
                rem = dcur.remaining()
                print(f"DWELL with targets found. d5={d5}, target_area_bytes={rem}, chunk_guess={rem/d5:.3f}")
                print("first 64 bytes of target area:", hexs(dcur.peek(min(64, rem)), 64))
                # Save the entire target area
                out = Path("tools/first_target_block.bin")
                out.write_bytes(dcur.peek(rem))
                print("saved:", out)
                raise SystemExit(0)
    cur.seek(pkt_end)

print("No dwell with targets found.")
