#!/usr/bin/env python3
"""Draw the SDSC horizon so a human can check it against a photograph.

Two panels. The top one is plotted on the SAME vertical scale Santiago uses
(0-5.6 deg), because the single most important fact about this field is what
that panel looks like: empty. The bottom one zooms to the real band so the
shape can be read at all.
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
ax.set_title("SDSC / Sao Carlos horizon from the RWY 02 threshold "
             "(Copernicus GLO-30, refraction k=0.13)\n"
             "plotted on the SAME scale as the Santiago silhouette: the Andes "
             "fill 3.2-4.9 deg of that panel, here there is nothing above 1.4 deg",
             fontsize=11)
ax.grid(alpha=.25, lw=.5)
ax.axhspan(3.2, 4.9, color="#c98a2e", alpha=.13, lw=0)
ax.text(180, 4.05, "where the Andes sit in the SCL profile", ha="center",
        fontsize=9, color="#7a5c1e")

ax = axes[1]
ax.fill_between(az, -2, ang, color="#3b4a5a", lw=0)
ax.plot(az, ang, color="#18202a", lw=1.0, label="terrain horizon (>1.5 km)")
ax.plot(az5, nf5, color="#d84a2f", lw=1.0, ls="--",
        label="near field (60 m - 1.5 km): hangars, tree lines, masts")
ax.axhline(0, color="#888", lw=.6, ls="--")
ax.set_xlim(0, 360); ax.set_ylim(-0.6, 1.7)
ax.set_xticks(np.arange(0, 361, 15))
ax.set_xlabel("azimuth (deg true)   -   0 N, 90 E, 180 S, 270 W")
ax.set_ylabel("horizon elevation (deg)")
ax.grid(alpha=.25, lw=.5)
ax.legend(loc="upper left", fontsize=9)
ax.axvspan(150, 210, color="#6f9e6f", alpha=.13, lw=0)
ax.text(180, 1.55, "S - the land rises toward Sao Carlos city (~856 m, 12 km)",
        ha="center", fontsize=8.5, color="#3f5f3f")
ax.axvspan(340, 360, color="#7f9ec9", alpha=.13, lw=0)
ax.axvspan(0, 30, color="#7f9ec9", alpha=.13, lw=0)
ax.text(10, 1.55, "N - the ground falls away, 806 m -> 580 m at 23 km", ha="center", fontsize=8.5,
        color="#3d5a7a")

plt.tight_layout()
plt.savefig(os.path.join(OUT, "horizon_silhouette.png"), dpi=125,
            facecolor="white")
print("wrote", os.path.join(OUT, "horizon_silhouette.png"))
