from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from .common import SecurityLevel, TimeRef

class FileHeader(BaseModel):
    version: str = "STANAG-4607"
    schema_version: str = "UNKNOWN"
    security: SecurityLevel = SecurityLevel.UNCLASSIFIED
    time_ref: TimeRef = TimeRef.UTC
    platform_id: str | None = None
    mission_id: str | None = None
    # Add more fields as you map the spec
