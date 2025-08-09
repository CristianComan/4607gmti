# tools/compact_probe.py
#!/usr/bin/env python3
from pathlib import Path
from gmti4607.binary.reader import _load_bytes
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs.packet_header import decode_packet_header
from gmti4607.binary.codecs.segment_header import decode_segment_header, SegmentType
from gmti4607.binary.codecs.dwell_mask import parse_dwell_header

def u24(b: bytes) -> int: return (b[0]<<16)|(b[1]<<8)|b[2]
def s24(v: int) -> int: return v - (1<<24) if (v & 0x800000) else v
def ba24_deg(v: int) -> float: return (v / (1<<24)) * 360.0

def main(path: Path, n=12):
    raw = _load_bytes(str(path))
    cur = Cursor(raw)
    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur); pkt_end = pkt_start + ph["packet_size"]
        while cur.tell()+5 <= pkt_end:
            st, sz = decode_segment_header(cur); payload = cur.take(sz-5)
            if SegmentType.DWELL != st: continue
            dcur = Cursor(payload)
            meta = parse_dwell_header(dcur)
            d5 = int(meta.get("D5_target_count", 0))
            if d5 <= 0 or not bool(meta.get("D32_1_targets_present", False)): continue

            # Fence target area
            start = dcur.tell(); rem = dcur.remaining(); total = rem
            if rem >= 3 and d5>0 and (rem-3) % d5 == 0: total = rem-3
            chunk = total // d5
            print(f"pkt={pkt_start} d5={d5} chunk={chunk} D10={'Y' if 'D10_lat_scale_sa32' in meta else 'n'} D11={'Y' if 'D11_lon_scale_ba32' in meta else 'n'}")
            tcur = Cursor(dcur.buf[dcur.pos:dcur.pos+total].tobytes())
            for i in range(min(d5, n)):
                rec = tcur.take(chunk)
                tid = int.from_bytes(rec[0:2], 'big')
                f1 = u24(rec[2:5]); f2 = u24(rec[5:8]); f3 = u24(rec[8:11]); f4 = u24(rec[11:14]); pad = rec[14]
                snr = ((f4>>16)&0xFF); snr = snr-256 if snr>=128 else snr
                print(
                    f"T[{i:02d}] id={tid:4d} "
                    f"f1=0x{f1:06x} s24={s24(f1):8d} ba24={ba24_deg(f1):8.3f}°  "
                    f"f2=0x{f2:06x} s24={s24(f2):8d} ba24={ba24_deg(f2):8.3f}°  "
                    f"f3=0x{f3:06x} s24={s24(f3):8d} ba24={ba24_deg(f3):8.3f}°  "
                    f"snr={snr:4d}"
                )
            return
    print("No dwell with targets found.")

if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1] if len(sys.argv)>1 else "tests/data/samples/binary/UV23/Day02 - GRCA1-mti.4607")
    main(p, n=16)
