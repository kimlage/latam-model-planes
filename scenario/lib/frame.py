"""The local metric frame for the SCL scene. Single source of truth.

Origin  : threshold of RWY 17L at SCEL (start of the takeoff roll, south flow).
          lat -33.376099, lon -70.786697  [OurAirports / AIP Chile]
Axes    : x = East, y = North, z = Up, metres (WGS84 local ENU tangent frame).
Datum   : z = 0 at 474.0 m AMSL, the published SCEL aerodrome elevation
          (1555 ft). DEM orthometric heights are converted as z = h - 474.0.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from srtm import ENU

# --- origin -------------------------------------------------------------
LAT0 = -33.376099          # RWY 17L threshold latitude  (deg, WGS84)
LON0 = -70.786697          # RWY 17L threshold longitude (deg, WGS84)
DATUM_M = 474.0            # z = 0 plane, metres AMSL (SCEL elevation 1555 ft)

FT = 0.3048

# SCEL runway ends, from the AIP-Chile SCEL aerodrome chart.
RUNWAYS = {
    # Survey values from AIP-Chile SCEL ADC (see ../scl_aip_corrections.json).
    # They replaced OurAirports coordinates on 2026-08-18: those had 35L 79.7 m
    # too far south, gave the 35R PAVEMENT END instead of its landing threshold
    # (548.8 m out) and an ARP 762 m off, from before the second runway opened.
    "17L": dict(lat=-33.376081,  lon=-70.786708,  elev_ft=1550, hdg_true=177.416),
    "35R": dict(lat=-33.404889,  lon=-70.785158,  elev_ft=1550, hdg_true=357.416),
    "17R": dict(lat=-33.371950,  lon=-70.803717,  elev_ft=1551, hdg_true=177.424),
    "35L": dict(lat=-33.406181,  lon=-70.801881,  elev_ft=1551, hdg_true=357.424),
}
ARP = dict(lat=-33.394442, lon=-70.793803, elev_ft=1555)   # aerodrome ref point (AIP ADC)


def enu():
    """The scene's ENU frame. z=0 at DATUM_M metres AMSL."""
    return ENU(LAT0, LON0, DATUM_M)
