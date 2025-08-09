#!/usr/bin/env python3
"""
Grab DWELL segments from a STANAG 4607 file and print basic info.
Also peeks D5 (target count) from the DWELL payload and shows a hex preview
of the target area. Saves the DWELL payload to tools/first_dwell.bin.

Usage:
  python tools/grab_first_dwell.py --input path/to/file.4607
  python tools/grab_first_dwell.py --input path/to/file.4607 --sample-with-targets 5
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gmti4607.binary.reader import _load_bytes
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs import segment_header
from gmti4607.binary.codecs.packet_header import decode_packet_header
from gmti4607.binary.codecs.segment_header import decode_segment_header

# Default input points to your test file
INPUT_FILE = Path(__file__).parent.parent / "tests/data/samples/binary/UV23/Day02 - GRCA1-mti.4607"
# Default output in tools/
OUTPUT_FILE = Path(__file__).parent / "first_dwell.bin"
HEX_PREVIEW_BYTES = 64


def _seg_type_str(code: int) -> str:
    """Resolve a human-readable name for segment type code."""
    st = getattr(segment_header, "SegmentType", None)
    if st is None:
        return f"UNKNOWN({code})"

    # If it's an enum (has __members__), try mapping
    if hasattr(st, "__members__"):
        for name, member in st.__members__.items():  # type: ignore[attr-defined]
            if getattr(member, "value", None) == code:
                return name
        return f"UNKNOWN({code})"

    # Else, scan attributes of a constants-holder class
    try:
        for attr in dir(st):
            if attr.startswith("_"):
                continue
            if getattr(st, attr) == code:
                return attr
    except Exception:
        pass
    return f"UNKNOWN({code})"


def _hex_preview(b: bytes, n: int = 64) -> str:
    return b[:n].hex()


def _peek_d5_target_count(dwell_payload: bytes) -> tuple[int | None, int, int]:
    """
    VERY LIGHT peek into the DWELL payload to read D5 (Target Count).

    Assumes the beginning of the payload is:
      D1 existence mask (8 bytes)
      D2 revisit (u16)
      D3 dwell (u16)
      D4 last dwell flag (u8)
      D5 target count (u16)

    Returns: (d5_count or None, offset_of_targets_guess, remaining_after_header)
    """
    cur = Cursor(dwell_payload)
    try:
        # D1
        cur.skip(8)
        # D2, D3
        cur.skip(2 + 2)
        # D4
        cur.skip(1)
        # D5
        d5 = cur.u16()
        # We don't advance further — just report where we are
        off = cur.tell()
        rem = cur.remaining()
        return d5, off, rem
    except Exception:
        # Can't parse — return None but still provide offsets
        return None, cur.tell(), cur.remaining()


def main():
    ap = argparse.ArgumentParser(description="Extract and inspect DWELL segments from a STANAG 4607 file.")
    ap.add_argument("--input", "-i", type=Path, required=False, help="Path to .4607 file")
    ap.add_argument("--out", "-o", type=Path, default=OUTPUT_FILE, help="Where to save DWELL payload")
    ap.add_argument("--hex", type=int, default=64, help="Hex preview bytes (default: 64)")
    ap.add_argument("--sample-with-targets", type=int, help="Only output the first N dwells that contain targets")
    args = ap.parse_args()

    raw = _load_bytes(str(INPUT_FILE))
    cur = Cursor(raw)

    pkt_index = 0
    found = False
    dwells_with_targets = 0
    max_dwells_with_targets = args.sample_with_targets

    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_size = ph["packet_size"]
        pkt_end = pkt_start + pkt_size

        print(f"[pkt {pkt_index}] start={pkt_start} size={pkt_size} end={pkt_end}")

        # Walk segments within this packet
        while cur.tell() + 5 <= pkt_end:
            seg_start = cur.tell()
            seg_type_code, seg_size = decode_segment_header(cur)
            if seg_size < 5:
                print(f"  !! bad segment size {seg_size} at {seg_start}, skipping")
                break
            payload = cur.take(seg_size - 5)

            seg_name = _seg_type_str(seg_type_code)
            print(f"  seg @ {seg_start} type={seg_name}({seg_type_code}) size={seg_size}")

            # Compare with whatever constant you have for DWELL
            is_dwell = False
            ST = getattr(segment_header, "SegmentType", None)
            if ST is not None:
                # try to compare to DWELL constant if present
                try:
                    is_dwell = (getattr(ST, "DWELL", None) == seg_type_code)
                except Exception:
                    is_dwell = False

            if is_dwell:
                # Peek D5 (target count) if possible
                d5, off, rem = _peek_d5_target_count(payload)
                has_targets = d5 is not None and d5 > 0
                
                # If --sample-with-targets is specified, only process dwells with targets
                if max_dwells_with_targets is not None:
                    if not has_targets:
                        print(f"  seg @ {seg_start} type={seg_name}({seg_type_code}) size={seg_size} - skipping (no targets)")
                        continue
                    else:
                        dwells_with_targets += 1
                        print(f"---> Found DWELL with targets #{dwells_with_targets} in packet {pkt_index}")
                else:
                    print(f"---> Found first DWELL in packet {pkt_index}")
                
                print(f"     Payload length: {len(payload)} bytes")
                print(f"     First {args.hex} bytes: { _hex_preview(payload, args.hex) }")

                if d5 is not None:
                    print(f"     D5 (target count): {d5}")
                    print(f"     After D5 offset={off} (bytes from DWELL start), remaining={rem}")
                    # Show next bytes (likely the start of D6 or subsequent fields before targets)
                    preview_after_d5 = payload[off : off + args.hex]
                    print(f"     Next {args.hex} bytes after D5: {preview_after_d5.hex()}")
                else:
                    print("     (Could not read D5 with the lightweight peek — layout may differ)")

                # Save DWELL payload
                if max_dwells_with_targets is not None:
                    # Create unique filename for each dwell when sampling
                    dwell_filename = args.out.parent / f"dwell_{dwells_with_targets:03d}.bin"
                    dwell_filename.write_bytes(payload)
                    print(f"     Saved DWELL payload to {dwell_filename}")
                else:
                    # Save to the default output file for single dwell mode
                    args.out.write_bytes(payload)
                    print(f"     Saved DWELL payload to {args.out}")
                found = True
                
                # If we're sampling with targets and we've reached the limit, stop
                if max_dwells_with_targets is not None and dwells_with_targets >= max_dwells_with_targets:
                    print(f"     Reached limit of {max_dwells_with_targets} dwells with targets")
                    return
                
                # If not sampling with targets, stop after first dwell
                if max_dwells_with_targets is None:
                    break

        # Move to next packet
        cur.seek(pkt_end)
        # Only break if we're not sampling with targets and we found a dwell
        if found and max_dwells_with_targets is None:
            break
        pkt_index += 1

    if not found:
        print("No DWELL segments found.")
    elif max_dwells_with_targets is not None:
        print(f"Found {dwells_with_targets} dwells with targets (requested: {max_dwells_with_targets})")


if __name__ == "__main__":
    main()
