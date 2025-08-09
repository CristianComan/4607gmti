import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs.segment_header import decode_segment_header

def test_segment_header_layout():
    # S1=2 (DWELL), S2=5+10=15
    data = bytes([2]) + (15).to_bytes(4, "big") + b"\xAA"*10
    cur = Cursor(data)
    s1, s2 = decode_segment_header(cur)
    assert s1 == 2 and s2 == 15
    assert cur.remaining() == 10
