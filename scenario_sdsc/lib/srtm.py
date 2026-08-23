"""SRTM 1-arcsec (.hgt) mosaic reader + WGS84 local-ENU frame for the SCL scene.

DEM source : SRTM v3 1-arcsec via AWS "elevation-tiles-prod" skadi endpoint.
Vertical   : metres above the EGM96 geoid (SRTM native).
Horizontal : WGS84 geographic, 1 arcsec (~30 m).
"""
import os, glob
import numpy as np

TILE_N = 3601
VOID = -32768

# --- WGS84 -------------------------------------------------------------
A = 6378137.0
F = 1.0 / 298.257223563
E2 = F * (2 - F)
B = A * (1 - F)


class Mosaic:
    """Lazy memory-mapped mosaic of 1-arcsec .hgt tiles."""

    def __init__(self, demdir):
        self.demdir = demdir
        self._tiles = {}
        self.available = set()
        for p in glob.glob(os.path.join(demdir, "*.hgt")):
            name = os.path.basename(p)[:7]
            self.available.add(self._name_to_sw(name))

    @staticmethod
    def _name_to_sw(name):
        lat = int(name[1:3]) * (-1 if name[0].upper() == "S" else 1)
        lon = int(name[4:7]) * (-1 if name[3].upper() == "W" else 1)
        return (lat, lon)

    @staticmethod
    def _sw_to_name(lat, lon):
        return "%s%02d%s%03d" % ("S" if lat < 0 else "N", abs(lat),
                                 "W" if lon < 0 else "E", abs(lon))

    def _tile(self, sw):
        t = self._tiles.get(sw)
        if t is None:
            path = os.path.join(self.demdir, self._sw_to_name(*sw) + ".hgt")
            if not os.path.exists(path):
                return None
            t = np.memmap(path, dtype=">i2", mode="r").reshape(TILE_N, TILE_N)
            self._tiles[sw] = t
        return t

    def sample(self, lat, lon):
        """Nearest-neighbour elevation (m). NaN where no tile / void."""
        lat = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        out = np.full(lat.shape, np.nan, dtype=np.float32)
        tlat = np.floor(lat).astype(np.int32)
        tlon = np.floor(lon).astype(np.int32)
        for sw in np.unique(np.stack([tlat, tlon], axis=-1).reshape(-1, 2), axis=0):
            sw = (int(sw[0]), int(sw[1]))
            t = self._tile(sw)
            if t is None:
                continue
            m = (tlat == sw[0]) & (tlon == sw[1])
            # row 0 = north edge (lat = sw_lat + 1); col 0 = west edge (lon = sw_lon)
            r = np.rint((sw[0] + 1 - lat[m]) * 3600.0).astype(np.int32)
            c = np.rint((lon[m] - sw[1]) * 3600.0).astype(np.int32)
            np.clip(r, 0, TILE_N - 1, out=r)
            np.clip(c, 0, TILE_N - 1, out=c)
            v = t[r, c].astype(np.float32)
            v[v == VOID] = np.nan
            out[m] = v
        return out

    def sample_bilinear(self, lat, lon):
        """Bilinear elevation (m). NaN where any corner is void/missing."""
        lat = np.atleast_1d(np.asarray(lat, dtype=np.float64))
        lon = np.atleast_1d(np.asarray(lon, dtype=np.float64))
        out = np.full(lat.shape, np.nan, dtype=np.float64)
        # global 1-arcsec pixel coordinates
        gy = (60.0 - lat) * 3600.0     # rows increase southward from lat=+60
        gx = (lon + 180.0) * 3600.0
        y0 = np.floor(gy); x0 = np.floor(gx)
        fy = gy - y0; fx = gx - x0
        acc = np.zeros(lat.shape); wsum = np.zeros(lat.shape)
        bad = np.zeros(lat.shape, dtype=bool)
        for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1)):
            la = 60.0 - (y0 + dy) / 3600.0
            lo = (x0 + dx) / 3600.0 - 180.0
            v = self.sample(la, lo).astype(np.float64)
            w = (fy if dy else 1 - fy) * (fx if dx else 1 - fx)
            bad |= np.isnan(v) & (w > 0)
            acc += np.nan_to_num(v) * w
            wsum += w
        out = acc / np.where(wsum == 0, np.nan, wsum)
        out[bad] = np.nan
        return out


# --- local ENU frame ---------------------------------------------------
def geodetic_to_ecef(lat_deg, lon_deg, h):
    lat = np.radians(lat_deg); lon = np.radians(lon_deg)
    s = np.sin(lat)
    N = A / np.sqrt(1 - E2 * s * s)
    x = (N + h) * np.cos(lat) * np.cos(lon)
    y = (N + h) * np.cos(lat) * np.sin(lon)
    z = (N * (1 - E2) + h) * s
    return x, y, z


def ecef_to_geodetic(x, y, z):
    """Bowring's method."""
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    ep2 = (A * A - B * B) / (B * B)
    th = np.arctan2(A * z, B * p)
    lat = np.arctan2(z + ep2 * B * np.sin(th) ** 3,
                     p - E2 * A * np.cos(th) ** 3)
    s = np.sin(lat)
    N = A / np.sqrt(1 - E2 * s * s)
    h = p / np.cos(lat) - N
    return np.degrees(lat), np.degrees(lon), h


class ENU:
    """East-North-Up tangent frame at (lat0, lon0, h0). Metres."""

    def __init__(self, lat0, lon0, h0):
        self.lat0, self.lon0, self.h0 = lat0, lon0, h0
        self.x0, self.y0, self.z0 = geodetic_to_ecef(lat0, lon0, h0)
        la, lo = np.radians(lat0), np.radians(lon0)
        sla, cla, slo, clo = np.sin(la), np.cos(la), np.sin(lo), np.cos(lo)
        # rows: E, N, U expressed in ECEF
        self.R = np.array([[-slo,            clo,           0.0],
                           [-sla * clo, -sla * slo,         cla],
                           [ cla * clo,  cla * slo,         sla]])

    def from_geodetic(self, lat, lon, h):
        x, y, z = geodetic_to_ecef(lat, lon, h)
        d = np.stack([np.asarray(x) - self.x0,
                      np.asarray(y) - self.y0,
                      np.asarray(z) - self.z0], axis=0)
        enu = self.R @ d.reshape(3, -1)
        return [c.reshape(np.asarray(x).shape) for c in enu]

    def to_geodetic(self, e, n, u):
        enu = np.stack([np.asarray(e, dtype=float),
                        np.asarray(n, dtype=float),
                        np.asarray(u, dtype=float)], axis=0)
        shp = enu.shape[1:]
        d = self.R.T @ enu.reshape(3, -1)
        return ecef_to_geodetic(d[0].reshape(shp) + self.x0,
                                d[1].reshape(shp) + self.y0,
                                d[2].reshape(shp) + self.z0)
