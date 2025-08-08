from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from .common import GeoPoint, Velocity, Classification

class TargetReport(BaseModel):
    id: int = Field(..., ge=0)
    location: GeoPoint
    velocity: Velocity | None = None
    snr_db: float | None = None
    classification: Classification | None = None
