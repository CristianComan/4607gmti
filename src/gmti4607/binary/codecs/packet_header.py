from __future__ import annotations
from .bitcursor import Cursor
from gmti4607.models.file_header import FileHeader
from gmti4607.models.common import SecurityLevel, TimeRef

def _read_ascii(cur: Cursor, n: int) -> str:
    raw = cur.take(n)
    return raw.decode("ascii", errors="ignore").rstrip("\x00").rstrip()

def _read_bcs_padded(cur: Cursor, n: int) -> str:
    # BCS padding is 0x20 (space) per spec notes; treat as ASCII superset
    raw = cur.take(n)
    return raw.decode("ascii", errors="ignore").rstrip(" ")

def decode_packet_header(cur: Cursor) -> dict:
    """
    Parse the 32-byte Packet Header (Table 3-1).
    Returns a dict with raw fields; FileHeader will be built in reader.
    """
    start = cur.tell()
    p1 = _read_ascii(cur, 2)                      # Version ID (alnum “mn”)
    p2 = cur.u32()                                 # Packet Size
    p3 = _read_ascii(cur, 2)                       # Nationality digraph
    p4 = cur.u8()                                  # Security classification (enum)
    p5 = _read_ascii(cur, 2)                       # Classification System
    p6 = cur.u16()                                 # Code (flags)
    p7 = cur.u8()                                  # Exercise Indicator (enum)
    p8 = _read_bcs_padded(cur, 10)                 # Platform ID (padded)
    p9 = cur.u32()                                 # Mission ID
    p10 = cur.u32()                                # Job ID

    # Sanity: header must be 32 bytes
    if cur.tell() - start != 32:
        raise ValueError("Packet Header not 32 bytes")

    return {
        "version_id": p1, "packet_size": p2, "nationality": p3, "sec_enum": p4,
        "class_system": p5, "sec_code": p6, "exercise": p7,
        "platform_id": p8, "mission_id": p9, "job_id": p10,
    }

def encode_packet_header(hdr: FileHeader, *, packet_size: int) -> bytes:
    # Compose Version ID “mn”, e.g., “41” for Edition A (4) Version 1
    # You can refine once you bind edition/version explicitly.
    version_id = (hdr.schema_version or "41")[:2].ljust(2)

    out = bytearray()
    out += version_id.encode("ascii")
    out += packet_size.to_bytes(4, "big", signed=False)
    out += (hdr.platform_id or "XN")[:2].ljust(2).encode("ascii")     # Nationality digraph placeholder
    out += int(hdr.security).to_bytes(1, "big")
    out += (hdr.mission_id or "NS").ljust(2)[:2].encode("ascii")      # Classification System placeholder
    out += (0).to_bytes(2, "big")                                     # Code (flags) placeholder
    out += (0).to_bytes(1, "big")                                     # Exercise Indicator placeholder
    out += (hdr.platform_id or "").ljust(10)[:10].encode("ascii")
    out += (0).to_bytes(4, "big")                                     # Mission ID numeric placeholder
    out += (0).to_bytes(4, "big")                                     # Job ID numeric placeholder
    assert len(out) == 32
    return bytes(out)
