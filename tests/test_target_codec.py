# tests/test_target_codec.py
from gmti4607.binary.codecs.bitcursor import Cursor
from gmti4607.binary.codecs.target_codec import decode_target

def test_target_decoding_smoke():
    buf = bytearray()
    # if you have a mask, put one that enables fields you encode below:
    # buf += (0b00011111).to_bytes(2, "big")

    # build bytes in the exact order your codec expects
    # lat s32, lon u32, alt s32, vn s16, ve s16, snr u8 (example)
    buf += (-2000).to_bytes(4, "big", signed=True)
    buf += (1_000_000_000).to_bytes(4, "big", signed=False)
    buf += (2500).to_bytes(4, "big", signed=True)
    buf += (300).to_bytes(2, "big", signed=True)
    buf += (400).to_bytes(2, "big", signed=True)
    buf += (36).to_bytes(1, "big", signed=False)

    t = decode_target(Cursor(bytes(buf)), idx=42)
    assert t.id == 42
    assert t.location.alt_m == 25.0
    assert 0 <= t.velocity.heading_deg < 360
    assert t.snr_db in (18.0, 36.0)  # depends if your scale is 0.5 dB or 1 dB
