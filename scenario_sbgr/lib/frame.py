"""The local metric frame for the SBGR scene. Single source of truth.

Origin  : threshold of RWY 10L at SBGR (Sao Paulo/Guarulhos - Gov. Andre
          Franco Montoro, INTL), the published landing threshold of the
          NORTH runway - the runway the AIP's own intersection-departure
          notes mark as the take-off runway, and the end a departure in the
          dominant east flow lines up on.
          lat -23.4341667, lon -46.4825000   [AISWEB/ROTAER declared-distance
          table and the SBGR ADC, S 23 26 03 / W 046 28 57]
Axes    : x = East, y = North, z = Up, metres (WGS84 local ENU tangent frame).
Datum   : z = 0 at 750.0 m AMSL, the published SBGR aerodrome elevation
          (ROTAER '750 (2461)').

PRECISION WARNING, and it is the one divergence from the SDSC/SCL frames:
DECEA publishes the SBGR threshold coordinates to WHOLE SECONDS only
(+/- ~31 m N-S, ~28 m E-W). SDSC had centiseconds. The frame is exact about
an origin that is itself only known to ~30 m; sbgr_osm.json's runway
centrelines (traced from imagery) are the better RELATIVE geometry, and
sbgr_aip_survey.json records how the two reconcile. Every coordinate here
is the published string, converted, nothing else.

The runways are nearly LEVEL - the opposite of SDSC. Published THR
elevations: 10L 2445 ft, 28R 2441 ft (1.2 m fall over 3550 m, 0.03%);
10R 2451 ft, 28L 2446 ft (1.5 m over 3000 m, 0.05%). z = 0 is the aerodrome
elevation (750 m, the high point in the RWY 10R touchdown zone); the runway
surfaces sit 3-6 m below it. See ../sbgr_aip_survey.json.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from srtm import ENU

# --- origin -------------------------------------------------------------
LAT0 = -23.4341667         # RWY 10L threshold latitude  (deg, WGS84)
LON0 = -46.4825000         # RWY 10L threshold longitude (deg, WGS84)
DATUM_M = 750.0            # z = 0 plane, metres AMSL (SBGR elevation 2461 ft)

FT = 0.3048

# SBGR runway thresholds, from the AISWEB/ROTAER declared-distance table and
# the SBGR ADC (coordinates, whole seconds), and the SBGR IAC charts (THR
# elevations). See ../sbgr_aip_survey.json for every source string.
#   hdg_true is COMPUTED from the published thresholds in this frame
#   (073.41 deg north runway, 073.28 deg south runway; the 0.13 deg spread
#   between two nominally parallel runways is the whole-second coordinate
#   rounding, not geometry) and cross-checks the charts' 095 MAG final
#   course against VAR 22 W to ~0.3-0.4 deg.
RUNWAYS = {
    "10L": dict(lat=-23.4341667, lon=-46.4825000, elev_ft=2445,
                hdg_true=73.41, hdg_mag=95),
    "28R": dict(lat=-23.4250000, lon=-46.4491667, elev_ft=2441,
                hdg_true=253.41, hdg_mag=275),
    "10R": dict(lat=-23.4388889, lon=-46.4869444, elev_ft=2451,
                hdg_true=73.28, hdg_mag=95),
    "28L": dict(lat=-23.4311111, lon=-46.4588889, elev_ft=2446,
                hdg_true=253.28, hdg_mag=275),
}
ARP = dict(lat=-23.4355556, lon=-46.4730556, elev_ft=2461)  # 23 26 08S/046 28 23W

MAG_VAR_DEG_W = 22.0       # SBGR IAC charts, "VAR 22 W" box, AMDT 2605A1 2026
MAG_VAR_NOTE = ("chart value; the designators went 09/27 -> 10/28 in 2019 "
                "when the magnetic bearing crossed 095 deg")


def enu():
    """The scene's ENU frame. z=0 at DATUM_M metres AMSL."""
    return ENU(LAT0, LON0, DATUM_M)
