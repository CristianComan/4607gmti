from __future__ import annotations
from typing import Iterable
from .models.file import GmtiFile

def plot_detections(file: GmtiFile):
    """Minimal scatter of detections for sanity-checking."""
    import matplotlib.pyplot as plt
    lats, lons = [], []
    for dwell in file.dwells:
        for t in dwell.targets:
            lats.append(t.location.lat_deg)
            lons.append(t.location.lon_deg)
    plt.figure()
    plt.scatter(lons, lats, s=6)
    plt.xlabel("Longitude (deg)")
    plt.ylabel("Latitude (deg)")
    plt.title("4607 Detections (sanity plot)")
    plt.show()
