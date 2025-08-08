from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List
from .file_header import FileHeader
from .dwell import Dwell

class GmtiFile(BaseModel):
    header: FileHeader
    dwells: List[Dwell] = Field(default_factory=list)

    # Convenience constructors (stubs to be implemented in binary/xml layers)
    @classmethod
    def from_binary(cls, data: bytes | str) -> "GmtiFile":
        from ..binary.reader import parse_file
        return parse_file(data)

    def to_binary(self) -> bytes:
        from ..binary.writer import write_file
        return write_file(self)

    @classmethod
    def from_xml(cls, xml: str | bytes | str) -> "GmtiFile":
        from ..xmlio.read import read_xml_file
        return read_xml_file(xml)

    def to_xml(self, *, validate: bool = False, pretty: bool = True) -> str:
        from ..xmlio.write import write_xml_file
        return write_xml_file(self, validate=validate, pretty=pretty)
