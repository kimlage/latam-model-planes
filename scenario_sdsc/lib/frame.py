"""The local metric frame for the SDSC scene. Single source of truth.

Origin  : threshold of RWY 02 at SDSC (Sao Carlos / Mario Pereira Lopes),
          the published landing threshold, which is also where a RWY 02
          take-off roll lines up.
          lat -21.8818417, lon -47.9039639   [AISWEB/ROTAER declared-distance
          table, S 21 52 54.63 / W 047 54 14.27]
Axes    : x = East, y = North, z = Up, metres (WGS84 local ENU tangent frame).
Datum   : z = 0 at 807.0 m AMSL, the published SDSC aerodrome elevation
          (2648 ft). DEM orthometric heights are converted as z = h - 807.0.

Note that the runway at SDSC is NOT level: the published threshold elevations
are 2640 ft at THR 02 and 2607 ft at THR 20, so the field falls ~10 m over the
1620 m between them. z = 0 is the aerodrome elevation, not the runway surface;
the runway surface is z = -2.3 m at THR 02 and z = -12.4 m at THR 20.
See ../sdsc_aip_survey.json.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from srtm import ENU

# --- origin -------------------------------------------------------------
LAT0 = -21.8818417         # RWY 02 threshold latitude  (deg, WGS84)
LON0 = -47.9039639         # RWY 02 threshold longitude (deg, WGS84)
DATUM_M = 807.0            # z = 0 plane, metres AMSL (SDSC elevation 2648 ft)

FT = 0.3048

# SDSC runway thresholds, from the AISWEB/ROTAER declared-distance table
# (coordinates and displacements) and the SDSC IAC charts (THR elevations,
# magnetic final course). See ../sdsc_aip_survey.json for every source.
RUNWAYS = {
    "02": dict(lat=-21.8818417, lon=-47.9039639, elev_ft=2640,
               hdg_true=1.02, hdg_mag=23),
    "20": dict(lat=-21.8672139, lon=-47.9036833, elev_ft=2607,
               hdg_true=181.02, hdg_mag=203),
}
# Physical pavement ends (OSM runway centreline way 35448784 endpoints).
PAVEMENT_ENDS = {
    "south_02": dict(lat=-21.8822625, lon=-47.9039903),
    "north_20": dict(lat=-21.8668158, lon=-47.9037595),
}
ARP = dict(lat=-21.876389, lon=-47.903333, elev_ft=2648)   # 21 52 35S/047 54 12W

MAG_VAR_DEG_W = 22.0       # IAC RNP Y RWY 20 / RNP Z RWY 02, "VAR 22 W", 2025
MAG_VAR_ANNUAL_CHANGE = "04' W per year"


def enu():
    """The scene's ENU frame. z=0 at DATUM_M metres AMSL."""
    return ENU(LAT0, LON0, DATUM_M)
