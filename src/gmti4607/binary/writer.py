from __future__ import annotations
from ..models.file import GmtiFile

def write_file(file: GmtiFile) -> bytes:
    """Placeholder writer that emits a tiny header marker.
    Replace with complete writer based on the spec.
    """
    marker = b"4607GMTI\x00"
    return marker
