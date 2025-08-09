import math

def sa32_to_deg(v: int, full_scale_deg: float = 90.0) -> float:
    """
    Signed angle stored in 32-bit signed integer.
    For latitude, full_scale_deg should be 90 (→ ±90°).
    If you need a different signed angle, pass full_scale_deg accordingly.
    """
    return (v / (2**31)) * full_scale_deg

def ba32_to_deg(v: int) -> float:
    """Unsigned binary angle 0..360° over 32 bits."""
    return (v / (2**32)) * 360.0

def normalize_lon_deg(lon: float) -> float:
    """Wrap longitude to [-180, 180)."""
    lon = ((lon + 180.0) % 360.0) - 180.0
    # Handle the edge case where modulo returns -180 for 180
    return -180.0 if lon == 180.0 else lon

def ba16_to_deg(v: int) -> float:
    return (v / (2**16)) * 360.0

def cm_to_m(v: int) -> float:
    return v / 100.0

def cms_to_mps(v: int) -> float:
    return v / 100.0

def speed_from_components_cms(north_cms: int, east_cms: int) -> float:
    return ((north_cms**2 + east_cms**2) ** 0.5) / 100.0

def heading_from_components_deg(north_cms: int, east_cms: int) -> float:
    return (math.degrees(math.atan2(east_cms, north_cms)) + 360.0) % 360.0
