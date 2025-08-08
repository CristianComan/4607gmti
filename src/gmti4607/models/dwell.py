from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from .target import TargetReport

class Dwell(BaseModel):
    dwell_time_s: float = Field(..., ge=0)
    beam_id: int = Field(..., ge=0)
    prf_hz: float | None = None
    targets: List[TargetReport] = Field(default_factory=list)
