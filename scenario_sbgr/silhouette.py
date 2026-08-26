#!/usr/bin/env python3
"""Draw the SBGR horizon so a human can check it against a photograph.

Two panels, same convention as the SCL and SDSC silhouettes. The top one is on
the SCL scale (0-5.6 deg) so the three projects compare directly: Santiago's
Andes fill 3.2-4.9 deg of it, Sao Carlos leaves it empty, and Guarulhos puts a
2.3-2.8 deg wall across the NORTH - the Cabucu spur of the Serra da
Cantareira, 4-5 km out - with the Cantareira main crest and the Pico do
Jaragua sector at 1.2-2.2 deg across the west. The bottom panel zooms in and
marks the sectors.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "terrain")

prof = np.load(os.path.join(OUT, "_fine_profile.npy"))
az, ang, dist, hgt = prof[0], prof[1], prof[2], prof[3]
j5 = json.load(open(os.path.join(OUT, "horizon_5deg.json")))
az5 = np.array([r["azimuth_deg"] for r in j5["profile"]])
nf5 = np.array([r["near_field_elev_deg"] for r in j5["profile"]])

fig, axes = plt.subplots(2, 1, figsize=(17, 9.5))

ax = axes[0]
ax.fill_between(az, -2, ang, color="#33404d", lw=0)
ax.plot(az, ang, color="#1d262f", lw=0.8)
ax.axhline(0, color="#888", lw=.6, ls="--")
ax.set_xlim(0, 360); ax.set_ylim(-2.0, 5.6)
ax.set_xticks(np.arange(0, 361, 30))
ax.set_ylabel("horizon elevation (deg)")
ax.set_title("SBGR / Guarulhos horizon from the RWY 10L threshold "
             "(Copernicus GLO-30, refraction k=0.13)\n"
             "on the SCL scale: the Andes fill 3.2-4.9 deg of this panel, "
             "Sao Carlos leaves it empty, Guarulhos has a real ring",
             fontsize=11)
ax.grid(alpha=.25, lw=.5)
ax.axhspan(3.2, 4.9, color="#c98a2e", alpha=.13, lw=0)
ax.text(180, 4.05, "where the Andes sit in the SCL profile", ha="center",
        fontsize=9, color="#7a5c1e")

ax = axes[1]
ax.fill_between(az, -2, ang, color="#3b4a5a", lw=0)
ax.plot(az, ang, color="#18202a", lw=1.0,
        label="terrain horizon (scan starts 1.5 km; 5 km in the 050-120 sector)")
ax.plot(az5, nf5, color="#d84a2f", lw=1.0, ls="--",
        label="near field (60 m - scan start): the airport itself, then the city")
ax.axhline(0, color="#888", lw=.6, ls="--")
ax.set_xlim(0, 360); ax.set_ylim(-0.6, 3.2)
ax.set_xticks(np.arange(0, 361, 15))
ax.set_xlabel("azimuth (deg true)   -   0 N, 90 E, 180 S, 270 W")
ax.set_ylabel("horizon elevation (deg)")
ax.grid(alpha=.25, lw=.5)
ax.legend(loc="upper center", fontsize=9)
ax.axvspan(325, 360, color="#7f9ec9", alpha=.13, lw=0)
ax.axvspan(0, 20, color="#7f9ec9", alpha=.13, lw=0)
ax.text(350, 2.95, "N: Cabucu spur of the Cantareira, 4-5 km", ha="center",
        fontsize=8.5, color="#3d5a7a")
ax.axvspan(265, 320, color="#9e8fc9", alpha=.13, lw=0)
ax.text(292, 2.6, "W-NW: Cantareira crest 13-14 km,\nJaragua sector",
        ha="center", fontsize=8.5, color="#5a4a7a")
ax.axvspan(50, 120, color="#6f9e6f", alpha=.13, lw=0)
ax.text(85, 2.6, "ESE: the departure direction -\nthe LOWEST sector "
        "(0.34-0.57 deg)", ha="center", fontsize=8.5, color="#3f5f3f")
ax.axvspan(130, 185, color="#c9a97f", alpha=.13, lw=0)
ax.text(157, 2.95, "S-SSE: near ridge at 1.6-1.8 km", ha="center",
        fontsize=8.5, color="#7a5c3d")

plt.tight_layout()
plt.savefig(os.path.join(OUT, "horizon_silhouette.png"), dpi=125,
            facecolor="white")
print("wrote", os.path.join(OUT, "horizon_silhouette.png"))
