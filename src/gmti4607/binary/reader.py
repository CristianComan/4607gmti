from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple, Optional, Union

from .codecs.bitcursor import Cursor
from .codecs.packet_header import decode_packet_header
from .codecs.segment_header import decode_segment_header, SegmentType
from .codecs.dwell_codec import decode_dwell
from .codecs.dwell_mask import parse_dwell_header
from .codecs.bitcursor import Cursor as _Cursor  # for sub-slices in iterators

# Models
from gmti4607.models.file import GmtiFile  # type: ignore[import]
# If your model also exposes a header/security level type, you can import them as needed:
# from gmti4607.models.file import FileHeader, SecurityLevel  # type: ignore[import]
from gmti4607.models.dwell import Dwell

BytesLike = Union[str, Path, bytes, bytearray, memoryview]


class ParseError(ValueError):
    pass


# -----------------------------
# Helpers
# -----------------------------

def _load_bytes(inp: BytesLike) -> bytes:
    if isinstance(inp, (bytes, bytearray, memoryview)):
        return bytes(inp)
    p = Path(str(inp))
    return p.read_bytes()


def _seg_is_dwell(seg_type) -> bool:
    """Compare seg_type safely whether it's an int code or an Enum-like."""
    # SegmentType could be an Enum class or a constants holder
    try:
        return SegmentType.DWELL == seg_type  # type: ignore[comparison-overlap]
    except Exception:
        return getattr(SegmentType, "DWELL", None) == seg_type


# -----------------------------
# Full parse (heavy)
# -----------------------------

def parse_file(data: BytesLike) -> GmtiFile:
    """
    Full parse of a STANAG 4607 file. Decodes all DWELLs (and their targets),
    building a GmtiFile model.
    """
    raw = _load_bytes(data)
    cur = Cursor(raw)

    all_dwells = []

    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_size = ph["packet_size"]

        if pkt_size < 32:
            raise ParseError(f"Packet size {pkt_size} too small at {pkt_start}")
        pkt_end = pkt_start + pkt_size
        if pkt_end > len(cur.buf):
            raise ParseError(f"Packet overruns file: end {pkt_end} > size {len(cur.buf)}")

        while cur.tell() + 5 <= pkt_end:
            seg_start = cur.tell()
            seg_type, seg_size = decode_segment_header(cur)
            if seg_size < 5:
                raise ParseError(f"Bad segment size {seg_size} at {seg_start}")
            payload_len = seg_size - 5
            if cur.tell() + payload_len > pkt_end:
                raise ParseError(f"Segment overruns packet at {seg_start}")

            if _seg_is_dwell(seg_type):
                payload = cur.take(payload_len)
                try:
                    dcur = Cursor(payload)
                    dwell = decode_dwell(dcur)
                    # If any bytes remain unparsed in the dwell payload, ignore for now.
                    all_dwells.append(dwell)
                except Exception as e:
                    raise ParseError(f"DWELL decode failed at packet {pkt_start}: {e}") from e
            else:
                # Skip any non-dwell payload
                cur.skip(payload_len)

        cur.seek(pkt_end)

    # Build the file model (header population can be added if you parse a File Header segment)
    # This assumes your GmtiFile model has a compatible constructor.
    return GmtiFile(dwells=all_dwells)  # type: ignore[arg-type]


# -----------------------------
# Fast, low-memory summary
# -----------------------------

def summarize_file(
    data: BytesLike,
    max_dwells: Optional[int] = None,
    max_targets: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Streaming summary: returns (dwells_count, targets_count).
    Parses packet/segment headers and DWELL header (D1..D5) only; skips target bodies.
    Supports early stop via max_* limits.
    """
    raw = _load_bytes(data)
    cur = Cursor(raw)
    dwells = 0
    targets = 0

    def _hit_limit() -> bool:
        if max_dwells is not None and dwells >= max_dwells:
            return True
        if max_targets is not None and targets >= max_targets:
            return True
        return False

    while cur.remaining() >= 32 and not _hit_limit():
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_size = ph["packet_size"]
        if pkt_size < 32:
            raise ParseError(f"Packet size {pkt_size} too small at {pkt_start}")
        pkt_end = pkt_start + pkt_size
        if pkt_end > len(cur.buf):
            raise ParseError(f"Packet overruns file: end {pkt_end} > size {len(cur.buf)}")

        while cur.tell() + 5 <= pkt_end and not _hit_limit():
            seg_start = cur.tell()
            seg_type, seg_size = decode_segment_header(cur)
            if seg_size < 5:
                raise ParseError(f"Bad segment size {seg_size} at {seg_start}")
            payload_len = seg_size - 5
            if cur.tell() + payload_len > pkt_end:
                raise ParseError(f"Segment overruns packet at {seg_start}")

            if _seg_is_dwell(seg_type):
                # Peek the payload for header-only parse (don’t advance the main cursor)
                dcur = Cursor(cur.peek(payload_len))
                meta = parse_dwell_header(dcur)
                d5 = int(meta.get("D5_target_count", 0))
                dwells += 1
                targets += d5

            # Skip the payload
            cur.skip(payload_len)

        cur.seek(pkt_end)

    return dwells, targets


# -----------------------------
# Streaming iterators
# -----------------------------

def iter_dwells(
    data: BytesLike,
    *,
    decode_targets: bool = False,
    max_dwells: Optional[int] = None,
    max_targets_total: Optional[int] = None,
    max_targets_per_dwell: Optional[int] = None,
) -> Iterator:
    """
    Stream DWELLs from a 4607 file.
      - decode_targets=False: yield header-only Dwell objects (targets=[]).
      - decode_targets=True: decode target blocks, capped by provided limits.
    """
    raw = _load_bytes(data)
    cur = Cursor(raw)

    dwells_emitted = 0
    targets_emitted_total = 0

    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_size = ph["packet_size"]
        if pkt_size < 32:
            raise ParseError(f"Packet size {pkt_size} too small at offset {pkt_start}")
        pkt_end = pkt_start + pkt_size
        if pkt_end > len(cur.buf):
            raise ParseError(f"Packet overruns file: end {pkt_end} > size {len(cur.buf)} (start {pkt_start})")

        while cur.tell() + 5 <= pkt_end:
            seg_start = cur.tell()
            seg_type, seg_size = decode_segment_header(cur)
            if seg_size < 5:
                raise ParseError(f"Bad segment size {seg_size} at {seg_start}")

            payload = cur.take(seg_size - 5)

            if not _seg_is_dwell(seg_type):
                continue

            # Header-only parse to position at the target block
            dcur = _Cursor(payload)
            meta = parse_dwell_header(dcur)
            d5 = int(meta.get("D5_target_count", 0))
            targets_present = bool(meta.get("D32_1_targets_present", False))
            d6_time_ms = int(meta.get("D6_time_ms", 0))
            d3_dwell = int(meta.get("D3_dwell_index", 0))

            # Minimal Dwell; you can enrich from meta if your model supports more fields
            dwell = Dwell(
                dwell_time_s=d6_time_ms / 1000.0,
                beam_id=d3_dwell,
                prf_hz=None,
                targets=[],
            )

            if not decode_targets or d5 == 0 or not targets_present:
                dwells_emitted += 1
                yield dwell
                if max_dwells is not None and dwells_emitted >= max_dwells:
                    return
                continue

            # Fence target area (similar to dwell_codec)
            targets_start = dcur.tell()
            rem = dcur.remaining()
            target_bytes_total = rem
            if rem >= 3 and d5 > 0:
                minus3 = rem - 3
                if minus3 % d5 == 0:
                    target_bytes_total = minus3

            chunk = (target_bytes_total // d5) if d5 else 0
            fixed = (d5 > 0 and target_bytes_total % d5 == 0 and 1 <= chunk <= 256)

            end_of_targets = targets_start + target_bytes_total
            tcur = _Cursor(dcur.buf[dcur.pos:dcur.pos + target_bytes_total].tobytes())
            # (We don’t need to advance dcur beyond target area in streaming mode)

            # Compute per-dwell/global caps
            to_take = d5
            if max_targets_per_dwell is not None:
                to_take = min(to_take, max_targets_per_dwell)
            if max_targets_total is not None:
                remaining_global = max_targets_total - targets_emitted_total
                if remaining_global <= 0:
                    dwells_emitted += 1
                    yield dwell
                    if max_dwells is not None and dwells_emitted >= max_dwells:
                        return
                    continue
                to_take = min(to_take, remaining_global)

            if fixed:
                for i in range(to_take):
                    if tcur.remaining() < chunk:
                        break
                    one = _Cursor(tcur.take(chunk))
                    tgt = decode_dwell_target(one, i, chunk)  # shim to share decode with dwell_codec
                    dwell.targets.append(tgt)
                    targets_emitted_total += 1
            else:
                # Variable-size: decode until cap or exhaustion
                i = 0
                while i < to_take and tcur.remaining() > 0:
                    start_before = tcur.tell()
                    tgt = decode_dwell_target(tcur, i, None)
                    if tcur.tell() == start_before:  # safety
                        break
                    dwell.targets.append(tgt)
                    targets_emitted_total += 1
                    i += 1

            dwells_emitted += 1
            yield dwell
            if (max_dwells is not None and dwells_emitted >= max_dwells) or (
                max_targets_total is not None and targets_emitted_total >= max_targets_total
            ):
                return

        cur.seek(pkt_end)


def iter_targets(
    data: BytesLike,
    *,
    max_dwells: Optional[int] = None,
    max_targets_total: Optional[int] = None,
) -> Iterator[tuple[int, object]]:
    """
    Stream TargetReport objects as (dwell_index, target).
    Decodes targets directly from each DWELL’s target area (no Dwell accumulation).
    """
    raw = _load_bytes(data)
    cur = Cursor(raw)

    dwells_seen = 0
    targets_emitted = 0

    while cur.remaining() >= 32:
        pkt_start = cur.tell()
        ph = decode_packet_header(cur)
        pkt_size = ph["packet_size"]
        if pkt_size < 32:
            raise ParseError(f"Packet size {pkt_size} too small at offset {pkt_start}")
        pkt_end = pkt_start + pkt_size
        if pkt_end > len(cur.buf):
            raise ParseError(f"Packet overruns file: end {pkt_end} > size {len(cur.buf)} (start {pkt_start})")

        while cur.tell() + 5 <= pkt_end:
            seg_start = cur.tell()
            seg_type, seg_size = decode_segment_header(cur)
            if seg_size < 5:
                raise ParseError(f"Bad segment size {seg_size} at {seg_start}")

            payload = cur.take(seg_size - 5)

            if not _seg_is_dwell(seg_type):
                continue

            dcur = _Cursor(payload)
            meta = parse_dwell_header(dcur)
            d5 = int(meta.get("D5_target_count", 0))
            targets_present = bool(meta.get("D32_1_targets_present", False))
            d3_dwell = int(meta.get("D3_dwell_index", 0))

            if d5 == 0 or not targets_present:
                dwells_seen += 1
                if max_dwells is not None and dwells_seen >= max_dwells:
                    return
                continue

            # Fence target area
            targets_start = dcur.tell()
            rem = dcur.remaining()
            target_bytes_total = rem
            if rem >= 3 and d5 > 0:
                minus3 = rem - 3
                if minus3 % d5 == 0:
                    target_bytes_total = minus3

            chunk = (target_bytes_total // d5) if d5 else 0
            fixed = (d5 > 0 and target_bytes_total % d5 == 0 and 1 <= chunk <= 256)

            end_of_targets = targets_start + target_bytes_total
            tcur = _Cursor(dcur.buf[dcur.pos:dcur.pos + target_bytes_total].tobytes())

            if fixed:
                for i in range(d5):
                    if max_targets_total is not None and targets_emitted >= max_targets_total:
                        return
                    if tcur.remaining() < chunk:
                        break
                    one = _Cursor(tcur.take(chunk))
                    tgt = decode_dwell_target(one, i, chunk)
                    yield d3_dwell, tgt
                    targets_emitted += 1
            else:
                i = 0
                while i < d5 and tcur.remaining() > 0:
                    if max_targets_total is not None and targets_emitted >= max_targets_total:
                        return
                    start_before = tcur.tell()
                    tgt = decode_dwell_target(tcur, i, None)
                    if tcur.tell() == start_before:
                        break
                    yield d3_dwell, tgt
                    targets_emitted += 1
                    i += 1

            dwells_seen += 1
            if max_dwells is not None and dwells_seen >= max_dwells:
                return

        cur.seek(pkt_end)


# -----------------------------
# Internal shim to share target decode
# -----------------------------

def decode_dwell_target(cur: _Cursor, idx: int, chunk_size: Optional[int]):
    """
    Small shim so iterators can reuse the same target decoder used by dwell_codec.
    """
    from .codecs.target_codec import decode_target
    return decode_target(cur, idx=idx, chunk_size=chunk_size)
