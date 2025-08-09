from __future__ import annotations
from .bitcursor import Cursor

class SegmentType:
    MISSION = 1
    DWELL = 2
    HRR = 3
    JOB_DEF = 5
    FREE_TEXT = 6
    TEST_STATUS = 10
    PROC_HISTORY = 12
    PLATFORM_LOC = 13
    JOB_REQUEST = 101
    JOB_ACK = 102

def decode_segment_header(cur: Cursor) -> tuple[int, int]:
    """
    5-byte Segment Header: S1 (1 byte), S2 (4 bytes total size).
    Returns (seg_type, seg_size).
    """
    s1 = cur.u8()
    s2 = cur.u32()
    return s1, s2
