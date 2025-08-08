from __future__ import annotations
from io import BytesIO
from typing import BinaryIO
from struct import unpack_from
from ..models.file import GmtiFile
from ..models.file_header import FileHeader
from ..models.dwell import Dwell
from ..models.target import TargetReport
from ..models.common import GeoPoint, Velocity

class Cursor:
    def __init__(self, data: bytes):
        self.buf = memoryview(data)
        self.pos = 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.buf):
            raise ValueError(f"Buffer underrun at pos={self.pos}, need {n} bytes")
        out = self.buf[self.pos:self.pos+n]
        self.pos += n
        return out.tobytes()

    def u8(self) -> int: return int.from_bytes(self.take(1), "big")
    def u16(self) -> int: return int.from_bytes(self.take(2), "big")
    def u32(self) -> int: return int.from_bytes(self.take(4), "big")
    def f32(self) -> float:
        import struct
        return struct.unpack(">f", self.take(4))[0]

def parse_file(data: bytes | str) -> GmtiFile:
    """Very small placeholder parser.
    Replace with real 4607 parsing using the spec mapping.
    """
    if isinstance(data, str):
        with open(data, "rb") as f:
            raw = f.read()
    else:
        raw = data
    cur = Cursor(raw)
    # Placeholder: create a minimal structure
    header = FileHeader(schema_version="DRAFT")
    # No actual parsing yet; return empty dwells
    return GmtiFile(header=header, dwells=[])
