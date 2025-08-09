from __future__ import annotations
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.models.dwell import Dwell
from gmti4607.binary.codecs.target_codec import decode_target
from gmti4607.binary.codecs.dwell_mask import parse_dwell_header
from gmti4607.binary.scale import sa32_to_deg, ba32_to_deg, normalize_lon_deg  # reserved for future geo mapping

# Legacy placeholder guess; we no longer rely on it to detect fixed-size.
MIN_TARGET_BYTES = 4 + 4 + 4 + 2 + 2 + 1

def _hexpeek(cur: Cursor, n: int = 32) -> str:
    return cur.peek(min(n, cur.remaining())).hex()

def decode_dwell(cur: Cursor) -> Dwell:
    """
    Spec-compliant DWELL decode:
      1) Read D1 (existence mask) and conditionally consume D2..D31 in on-wire order.
      2) Land exactly at the start of the Target Report list.
      3) Decode targets, fencing off any small trailer bytes at the end of the dwell payload.
    """
    # 1) Mask-driven header — positions cursor at start of target area
    meta = parse_dwell_header(cur)

    d5_count        = int(meta.get("D5_target_count", 0))
    d6_time_ms      = int(meta.get("D6_time_ms", 0))
    d3_dwell_index  = int(meta.get("D3_dwell_index", 0))
    targets_present = bool(meta.get("D32_1_targets_present", False))
    _hrr_present    = bool(meta.get("D32_2_hrr_present", False))

    dwell = Dwell(
        dwell_time_s=d6_time_ms / 1000.0,
        beam_id=d3_dwell_index,   # adjust if your model expects a different field for beam/azimuth
        prf_hz=None,
        targets=[],
    )

    # Sanity: if there are targets, the presence flag should be set
    if d5_count > 0 and not targets_present:
        raise ValueError(
            f"Inconsistent DWELL header: D5={d5_count} but D32.1(targets_present)=False"
        )

    # 2) Targets — fence the target area to avoid chewing into any trailer/pad/CRC bytes
    targets_start = cur.tell()
    rem = cur.remaining()

    target_bytes_total = rem
    # Heuristic: a small (often 3B) trailer may follow the targets. If removing it yields
    # an even division by d5_count, treat it as trailer.
    if d5_count > 0 and rem >= 3:
        minus3 = rem - 3
        if minus3 % d5_count == 0:
            target_bytes_total = minus3

    # Trust even division: if bytes divide evenly by d5, treat as fixed-size targets.
    chunk = (target_bytes_total // d5_count) if d5_count else 0
    fixed_size = (d5_count > 0 and target_bytes_total % d5_count == 0 and 1 <= chunk <= 256)

    # Create a sub-cursor limited to the target area and advance the main cursor past it
    end_of_targets = targets_start + target_bytes_total
    tcur = Cursor(cur.buf[cur.pos:cur.pos + target_bytes_total].tobytes())
    cur.seek(end_of_targets)

    if d5_count == 0:
        return dwell

    if fixed_size:
        # Uncomment to debug:
        # print(f"[dw] targets={d5_count}, target_bytes={target_bytes_total}, chunk={chunk}, "
        #       f"trailer={rem - target_bytes_total}, peek={_hexpeek(tcur, 16)}")
        for i in range(d5_count):
            if tcur.remaining() < chunk:
                raise ValueError(f"target[{i}] underrun in fixed-size mode: need {chunk}, left {tcur.remaining()}")

            one = Cursor(tcur.take(chunk))  # exactly this record
            # Pass dwell meta (center, scales) so target mapping can use them when we add it
            tgt = decode_target(
                one,
                idx=i,
                chunk_size=chunk,
                dwell_meta=meta,
            )

            if one.remaining() != 0:
                raise ValueError(f"target[{i}] left {one.remaining()} unparsed bytes (chunk={chunk})")
            dwell.targets.append(tgt)
    else:
        # Variable-size targets (e.g., per-target mask/TLV). decode_target() must handle its own structure.
        for i in range(d5_count):
            if tcur.remaining() < MIN_TARGET_BYTES:
                peek = _hexpeek(tcur, 24)
                raise ValueError(
                    f"target[{i}] underrun: left {tcur.remaining()} in target area; peek={peek}"
                )
            
            dwell.targets.append(
                decode_target(tcur, idx=i, chunk_size=None, dwell_meta=meta)
            )

    return dwell
