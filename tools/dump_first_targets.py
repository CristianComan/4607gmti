#!/usr/bin/env python3
from pathlib import Path
from gmti4607.binary.reader import _load_bytes
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs.packet_header import decode_packet_header
from gmti4607.binary.codecs.segment_header import decode_segment_header
from gmti4607.binary.codecs import segment_header as sh
from gmti4607.binary.codecs.dwell_mask import parse_dwell_header

def u24(b: bytes) -> int:
    return (b[0] << 16) | (b[1] << 8) | b[2]

def main(path: Path, max_targets: int = 10):
    raw = _load_bytes(str(path))
    cur = Cursor(raw)

    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_end = pkt_start + ph["packet_size"]

        while cur.tell() + 5 <= pkt_end:
            st, sz = decode_segment_header(cur)
            payload = cur.take(sz - 5)
            if getattr(sh.SegmentType, "DWELL", None) != st:
                continue

            dcur = Cursor(payload)
            meta = parse_dwell_header(dcur)
            d5 = int(meta.get("D5_target_count", 0))
            if d5 <= 0 or not bool(meta.get("D32_1_targets_present", False)):
                continue

            # Fence target area
            start = dcur.tell()
            rem = dcur.remaining()
            total = rem
            if rem >= 3 and d5 > 0 and (rem - 3) % d5 == 0:
                total = rem - 3
            chunk = total // d5 if d5 else 0

            print(f"Dwell @pkt {pkt_start}: D5={d5}, target_bytes={total}, chunk={chunk}")
            print(f"Mask bits present: D10={ 'Y' if 'D10_lat_scale_sa32' in meta else 'n' }, "
                  f"D11={ 'Y' if 'D11_lon_scale_ba32' in meta else 'n' }")
            if 'D10_lat_scale_sa32' in meta:
                print(f"  D10_lat_scale_sa32: {meta['D10_lat_scale_sa32']}")
            if 'D11_lon_scale_ba32' in meta:
                print(f"  D11_lon_scale_ba32: {meta['D11_lon_scale_ba32']}")

            tcur = Cursor(dcur.buf[dcur.pos:dcur.pos + total].tobytes())

            for i in range(min(d5, max_targets)):
                rec = tcur.take(chunk)
                # Heuristics for common compact layouts
                if chunk == 15:
                    tid = int.from_bytes(rec[0:2], 'big')
                    f1 = u24(rec[2:5]); f2 = u24(rec[5:8]); f3 = u24(rec[8:11]); f4 = u24(rec[11:14]); pad = rec[14]
                    print(f"  T[{i:02d}] id={tid:5d}  u24s=({f1},{f2},{f3},{f4}) pad=0x{pad:02x}")
                elif chunk == 12:
                    f1 = u24(rec[0:3]); f2 = u24(rec[3:6]); f3 = u24(rec[6:9]); f4 = u24(rec[9:12])
                    print(f"  T[{i:02d}] u24s=({f1},{f2},{f3},{f4})")
                elif chunk % 3 == 0:
                    vals = [u24(rec[j:j+3]) for j in range(0, chunk, 3)]
                    print(f"  T[{i:02d}] u24x{len(vals)}={vals}")
                elif chunk % 2 == 0:
                    vals = [int.from_bytes(rec[j:j+2], 'big') for j in range(0, chunk, 2)]
                    print(f"  T[{i:02d}] u16x{len(vals)}={vals}")
                else:
                    print(f"  T[{i:02d}] raw={rec.hex()}")

            return  # only the first dwell-with-targets
    print("No dwell with targets found.")

if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/data/samples/binary/UV23/Day02 - GRCA1-mti.4607")
    main(p)
