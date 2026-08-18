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

# SCEL runway ends, from OurAirports (public domain), derived from AIP Chile.
RUNWAYS = {
    "17L": dict(lat=-33.376099,      lon=-70.786697,      elev_ft=1550, hdg_true=178.0),
    "35R": dict(lat=-33.409901,      lon=-70.785202,      elev_ft=1555, hdg_true=358.0),
    "17R": dict(lat=-33.371898651,   lon=-70.803703308,   elev_ft=1551, hdg_true=177.0),
    "35L": dict(lat=-33.406898499,   lon=-70.801902771,   elev_ft=1550, hdg_true=357.0),
}
ARP = dict(lat=-33.393001556, lon=-70.785797119, elev_ft=1555)   # aerodrome ref point


def enu():
    """The scene's ENU frame. z=0 at DATUM_M metres AMSL."""
    return ENU(LAT0, LON0, DATUM_M)
