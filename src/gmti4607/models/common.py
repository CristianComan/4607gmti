from __future__ import annotations
from enum import Enum, IntEnum
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class Classification(str, Enum):
    UNKNOWN = "unknown"
    FRIEND = "friend"
    NEUTRAL = "neutral"
    SUSPECT = "suspect"
    HOSTILE = "hostile"

class GeoPoint(BaseModel):
    lat_deg: float = Field(..., ge=-90, le=90)
    lon_deg: float = Field(..., ge=-180, le=180)
    alt_m: float | None = None

class Velocity(BaseModel):
    speed_mps: float = Field(..., ge=0)
    heading_deg: float = Field(..., ge=0, lt=360)

class TimeRef(str, Enum):
    UTC = "utc"
    MISSION = "mission"

class SecurityLevel(IntEnum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3
