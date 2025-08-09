from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Tuple
from .bitcursor import Cursor

# Bit numbering: 63 is the MSB of the 64-bit mask (byte 7, bit 7);
# 0 is the LSB (byte 0, bit 0). Figure 3-1 in the spec.

def _bit_set(mask: int, bit_index_from_msb: int) -> bool:
    return bool((mask >> bit_index_from_msb) & 1)


@dataclass(frozen=True)
class DwellField:
    name: str
    bit: int  # 63..0 (MSB-first)
    read: Callable[[Cursor], object]


# Basic big-endian readers
def u8(c: Cursor)  -> int: return c.u8()
def s8(c: Cursor)  -> int: return int.from_bytes(c.take(1), "big", signed=True)
def u16(c: Cursor) -> int: return c.u16()
def s16(c: Cursor) -> int: return int.from_bytes(c.take(2), "big", signed=True)
def u32(c: Cursor) -> int: return c.u32()
def s32(c: Cursor) -> int: return c.s32()

# ---- Dwell Existence Mask plan (Figure 3-1 + Table 3-9) ----
# Byte 7 (bits 63..56): D2..D9
# Byte 6 (bits 55..48): D10..D17
# Byte 5 (bits 47..40): D18..D25
# Byte 4 (bits 39..32): D26..D32.2 (presence flags at 33/32)

DWELL_FIELD_PLAN: Tuple[DwellField, ...] = (
    # D2..D9 (mandatory)
    DwellField("D2_revisit_index", 63, u16),   # I16
    DwellField("D3_dwell_index",   62, u16),   # I16
    DwellField("D4_last_flag",     61, u8),    # FL8
    DwellField("D5_target_count",  60, u16),   # I16
    DwellField("D6_time_ms",       59, u32),   # I32 (ms)
    DwellField("D7_lat_sa32",      58, s32),   # SA32
    DwellField("D8_lon_ba32",      57, u32),   # BA32
    DwellField("D9_alt_cm",        56, s32),   # S32 (cm)

    # D10..D17 (conditional/optional depending on profile)
    DwellField("D10_lat_scale_sa32",   55, s32),  # SA32
    DwellField("D11_lon_scale_ba32",   54, u32),  # BA32
    DwellField("D12_pos_unc_at_cm",    53, u32),  # I32
    DwellField("D13_pos_unc_ct_cm",    52, u32),  # I32
    DwellField("D14_pos_unc_alt_cm",   51, u16),  # I16
    DwellField("D15_sensor_track_ba16",50, u16),  # BA16
    DwellField("D16_sensor_speed_mmps",49, u32),  # I32
    DwellField("D17_sensor_vv_dmps",   48, s8),   # S8

    # D18..D25
    DwellField("D18_track_unc_deg",    47, u8),   # I8
    DwellField("D19_speed_unc_mmps",   46, u16),  # I16
    DwellField("D20_vv_unc_cmps",      45, u16),  # I16
    DwellField("D21_plat_head_ba16",   44, u16),  # BA16
    DwellField("D22_plat_pitch_sa16",  43, s16),  # SA16
    DwellField("D23_plat_roll_sa16",   42, s16),  # SA16
    DwellField("D24_center_lat_sa32",  41, s32),  # SA32
    DwellField("D25_center_lon_ba32",  40, u32),  # BA32

    # D26..D32.2
    DwellField("D26_range_half_km_b16",39, u16),  # B16 (range in 1/2 km or 1/256 km per profile—scale later)
    DwellField("D27_angle_half_ba16",  38, u16),  # BA16
    DwellField("D28_sensor_head_ba16", 37, u16),  # BA16
    DwellField("D29_sensor_pitch_sa16",36, s16),  # SA16
    DwellField("D30_sensor_roll_sa16", 35, s16),  # SA16
    DwellField("D31_mdv_dmps",         34, u8),   # I8
    # D32.1 (bit 33) / D32.2 (bit 32) are presence flags; no bytes to read here.
)

def parse_dwell_header(cur: Cursor) -> Dict[str, object]:
    """
    Read D1 (8-byte existence mask), then conditionally read each field
    in on-wire order according to DWELL_FIELD_PLAN.
    Leaves the cursor positioned at the start of the target list / next block.
    """
    start = cur.tell()
    d1_mask = int.from_bytes(cur.take(8), "big")

    out: Dict[str, object] = {"D1_mask": d1_mask, "_start": start}

    for fld in DWELL_FIELD_PLAN:
        if _bit_set(d1_mask, fld.bit):
            out[fld.name] = fld.read(cur)

    # Expose D32.1 / D32.2 presence flags as booleans (no payload bytes)
    out["D32_1_targets_present"] = _bit_set(d1_mask, 33)
    out["D32_2_hrr_present"]     = _bit_set(d1_mask, 32)

    out["_after_header_off"] = cur.tell() - start
    out["_remaining"] = cur.remaining()
    return out
