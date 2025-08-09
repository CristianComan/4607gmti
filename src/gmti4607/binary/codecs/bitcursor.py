from __future__ import annotations
import struct

class Cursor:
    __slots__ = ("buf", "pos", "_bitbuf", "_bitcnt")

    def __init__(self, data: bytes | bytearray | memoryview):
        self.buf = memoryview(data)
        self.pos = 0
        self._bitbuf = 0
        self._bitcnt = 0

    def remaining(self) -> int: return len(self.buf) - self.pos
    def tell(self) -> int: return self.pos

    def seek(self, pos: int) -> None:
        if not (0 <= pos <= len(self.buf)): raise ValueError("seek out of bounds")
        self.pos, self._bitbuf, self._bitcnt = pos, 0, 0

    def skip(self, n: int) -> None: self.seek(self.pos + n)

    def take(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.buf): raise ValueError(f"underrun: need {n} at {self.pos}")
        out = self.buf[self.pos:end].tobytes()
        self.pos = end
        return out

    # byte-aligned big-endian reads
    def _unpack(self, fmt: str, n: int):
        return struct.unpack(fmt, self.take(n))[0]
    def u8(self) -> int:  return self._unpack(">B", 1)
    def s8(self) -> int:  return self._unpack(">b", 1)
    def u16(self) -> int: return self._unpack(">H", 2)
    def s16(self) -> int: return self._unpack(">h", 2)
    def u32(self) -> int: return self._unpack(">I", 4)
    def s32(self) -> int: return self._unpack(">i", 4)
    def u64(self) -> int: return self._unpack(">Q", 8)
    def s64(self) -> int: return self._unpack(">q", 8)
    def f32(self) -> float: return self._unpack(">f", 4)
    def f64(self) -> float: return self._unpack(">d", 8)

    # bits (MSB-first)
    def bits(self, n: int) -> int:
        if not (0 < n <= 32): raise ValueError("bits 1..32")
        while self._bitcnt < n:
            if self.remaining() <= 0: raise ValueError("bit underrun")
            self._bitbuf = (self._bitbuf << 8) | self.u8()
            self._bitcnt += 8
        shift = self._bitcnt - n
        val = (self._bitbuf >> shift) & ((1 << n) - 1)
        self._bitbuf &= (1 << shift) - 1
        self._bitcnt = shift
        return val

    def byte_align(self): self._bitbuf = 0; self._bitcnt = 0

    def peek(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.buf): raise ValueError("peek underrun")
        return self.buf[self.pos:end].tobytes()
