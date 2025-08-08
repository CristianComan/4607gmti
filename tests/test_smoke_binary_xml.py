from gmti4607.models.file import GmtiFile

def test_stub_roundtrips():
    f = GmtiFile.from_binary(b"\x00\x01")
    xml = f.to_xml()
    g = GmtiFile.from_xml(xml)
    data = g.to_binary()
    assert isinstance(xml, str)
    assert isinstance(data, (bytes, bytearray))
