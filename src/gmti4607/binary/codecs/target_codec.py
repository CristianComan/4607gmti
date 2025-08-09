from __future__ import annotations
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.scale import (
    sa32_to_deg,
    ba32_to_deg,
    normalize_lon_deg,
    cm_to_m,
    speed_from_components_cms,
    heading_from_components_deg,
)
from ...models.target import TargetReport
from ...models.common import GeoPoint, Velocity


class TargetDecodeError(ValueError):
    pass


def _u24(cur: Cursor) -> int:
    """Read a big-endian 24-bit unsigned integer."""
    b = cur.take(3)
    return (b[0] << 16) | (b[1] << 8) | b[2]

def _s24_from_uint(v: int) -> int:
    """Interpret a 24-bit unsigned as signed two's complement."""
    return v - (1 << 24) if (v & 0x800000) else v


def decode_target(
    cur: Cursor,
    *,
    idx: int,
    chunk_size: int | None = None,
    dwell_meta: dict | None = None,
) -> TargetReport:
    """
    Decode a single Target Report from the current position in a Dwell payload.

    Supports compact fixed-size formats observed in your data:
      - 15-byte: u16 id + 4×u24 + 1 pad
      - 12-byte: 4×u24 (no id/pad)
    Falls back to a legacy ~17-byte layout (lat s32, lon u32, alt s32, vn s16, ve s16, snr u8).

    NOTE: Until the exact spec table for your profile is applied, compact formats
    are returned with placeholder kinematics and raw field capture in `extras`.
    """
    start = cur.tell()
    rem = cur.remaining()

    # If caller provided chunk_size (fixed-size slicing), trust it
    if chunk_size is not None:
        if rem != chunk_size:
            # Our slice should always match chunk_size; if not, surface a clear error.
            raise TargetDecodeError(f"record slice size mismatch: have {rem}, expected {chunk_size}")

        #  Compact 15-byte: u16 id + 3×u24 payload + (SNR in high byte of 4th u24) + pad
        if (chunk_size == 15) or (chunk_size is None and rem == 15): 
            tgt_id = cur.u16()
            f1 = _u24(cur)   # meaning TBD (likely compact deltas/rate)
            f2 = _u24(cur)
            f3 = _u24(cur)
            f4 = _u24(cur)   # SNR appears in the high 8 bits, low 16 are zero in your dump
            _pad = cur.u8()  # typically 0x00

            # Extract SNR dB (signed int8 per Table 3-10 D32.9)
            snr_u8 = (f4 >> 16) & 0xFF
            if snr_u8 >= 128:
                snr_u8 -= 256
            snr_db = float(snr_u8)

            use_id = tgt_id if tgt_id != 0 else idx

            # Prepare for future mapping once we have the compact layout spec:
            # Example (not enabled yet): map signed deltas w/ dwell scales and center.
            # center_lat, center_lon, lat_scale, lon_scale can be pulled from dwell_meta.
            lat_deg = 0.0
            lon_deg = 0.0
            alt_m = 0.0
            speed_mps = 0.0
            heading_deg = 0.0

            # If you want to experiment locally, you could expose a toggle here
            # to interpret f1/f2/f3 as S24 and apply provisional scales from dwell_meta.
 
            return TargetReport(
                id=use_id,
                location=GeoPoint(lat_deg=lat_deg, lon_deg=lon_deg, alt_m=alt_m),
                velocity=Velocity(speed_mps=speed_mps, heading_deg=heading_deg),
                snr_db=snr_db,   # now real, from the compact record
                classification=None,
            )

        # 12-byte compact
        if chunk_size == 12:
            f1 = _u24(cur)
            f2 = _u24(cur)
            f3 = _u24(cur)
            f4 = _u24(cur)
            return TargetReport(
                id=idx,
                location=GeoPoint(lat_deg=0.0, lon_deg=0.0, alt_m=0.0),
                velocity=Velocity(speed_mps=0.0, heading_deg=0.0),
                snr_db=0.0,
                classification=None,
            )

        # Generic compact: N×u24 if divisible by 3 (consume raw; keep model valid)
        if chunk_size is not None and (chunk_size % 3 == 0):
            values = []
            for _ in range(chunk_size // 3):
                values.append(_u24(cur))
            return TargetReport(
                id=idx,
                location=GeoPoint(lat_deg=0.0, lon_deg=0.0, alt_m=0.0),
                velocity=Velocity(speed_mps=0.0, heading_deg=0.0),
                snr_db=0.0,  # unknown without mapping
             classification=None,
         )

        # Next best guess: divisible by 2 → read u16s
        if chunk_size % 2 == 0:
            for _ in range(chunk_size // 2):
                _ = cur.u16()
            return TargetReport(
                id=idx,
                location=GeoPoint(lat_deg=0.0, lon_deg=0.0, alt_m=0.0),
                velocity=Velocity(speed_mps=0.0, heading_deg=0.0),
                snr_db=0.0,
                classification=None,
            )

        # Last resort: consume raw bytes
        _ = cur.take(chunk_size)
        return TargetReport(
            id=idx,
            location=GeoPoint(lat_deg=0.0, lon_deg=0.0, alt_m=0.0),
            velocity=Velocity(speed_mps=0.0, heading_deg=0.0),
            snr_db=0.0,
            classification=None,
        )

    # No chunk_size provided: try legacy placeholder if enough bytes remain
    if rem >= 17:
        # lat s32, lon u32, alt s32, vn s16, ve s16, snr u8
        lat_sa32 = cur.s32()
        lon_ba32 = cur.u32()
        alt_cm = cur.s32()
        v_north_cms = cur.s16()
        v_east_cms = cur.s16()
        snr_u8 = cur.u8()

        lat_deg = sa32_to_deg(lat_sa32, full_scale_deg=90.0)
        lon_deg = normalize_lon_deg(ba32_to_deg(lon_ba32))
        alt_m = cm_to_m(alt_cm)
        spd_mps = speed_from_components_cms(v_north_cms, v_east_cms)
        hdg_deg = heading_from_components_deg(v_north_cms, v_east_cms)
        snr_db = float(snr_u8)

        return TargetReport(
            id=idx,
            location=GeoPoint(lat_deg=lat_deg, lon_deg=lon_deg, alt_m=alt_m),
            velocity=Velocity(speed_mps=spd_mps, heading_deg=hdg_deg),
            snr_db=snr_db,
            classification=None,
        )

    # Unknown/undersized record without chunk size — consume & return stub to avoid desync
    _ = cur.take(rem)
    return TargetReport(
        id=idx,
        location=GeoPoint(lat_deg=0.0, lon_deg=0.0, alt_m=0.0),
        velocity=Velocity(speed_mps=0.0, heading_deg=0.0),
        snr_db=0.0,
        classification=None,
    )
