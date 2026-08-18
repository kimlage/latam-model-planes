#!/usr/bin/env python3
"""Draw the SCL skyline so a human can check it against a photograph."""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "terrain")

prof = np.load(os.path.join(OUT, "_fine_profile.npy"))
az, ang, dist, hgt = prof[0], prof[1], prof[2], prof[3]
pk = json.load(open(os.path.join(OUT, "peaks.json")))

fig, axes = plt.subplots(2, 1, figsize=(17, 9.5))

# --- full 360 -----------------------------------------------------------
ax = axes[0]
ax.fill_between(az, 0, ang, color="#33404d", lw=0)
ax.plot(az, ang, color="#1d262f", lw=0.8)
ax.set_xlim(0, 360); ax.set_ylim(0, 5.6)
ax.set_xticks(np.arange(0, 361, 30))
ax.set_xlabel("azimuth (deg true)   —   0 N, 90 E, 180 S, 270 W")
ax.set_ylabel("horizon elevation (deg)")
ax.set_title("SCL / SCEL horizon from the RWY 17L threshold  (Copernicus GLO-30, "
             "refraction k=0.13)", fontsize=11)
ax.grid(alpha=.25, lw=.5)
for lbl, a0, a1, c in [("N", 0, 0, None), ("E — the Andes", 45, 125, "#c98a2e"),
                       ("W — Cordillera de la Costa", 240, 320, "#6f9e6f")]:
    if a1 > a0:
        ax.axvspan(a0, a1, color=c, alpha=.13, lw=0)
        ax.text((a0 + a1) / 2, 5.25, lbl, ha="center", fontsize=9, color="#444")

# --- east sector, labelled ---------------------------------------------
ax = axes[1]
m = (az >= 40) & (az <= 130)
ax.fill_between(az[m], 0, ang[m], color="#3b4a5a", lw=0)
ax.plot(az[m], ang[m], color="#18202a", lw=1.0)
ax.set_xlim(40, 130); ax.set_ylim(0, 7.0)
ax.set_xticks(np.arange(40, 131, 5))
ax.set_xlabel("azimuth (deg true) — eastern sector, the recognisable Andes wall")
ax.set_ylabel("horizon elevation (deg)")
ax.grid(alpha=.25, lw=.5)

named = [n for n in pk["skyline_peaks"]
         if 40 <= n["azimuth_deg"] <= 130 and n["confidence"] == "confirmed"]
named.sort(key=lambda n: -n["dem_height_m"])
used = []
for n in named:
    a = n["azimuth_deg"]
    if any(abs(a - u) < 4.5 for u in used):
        continue
    used.append(a)
    y = n["elev_deg"]
    lvl = len(used) % 3
    ax.plot([a], [y], "o", ms=3.5, color="#d84a2f", zorder=5)
    ax.annotate("%s\n%.0f m · %.0f km" % (n["name"], n["dem_height_m"], n["dist_km"]),
                xy=(a, y), xytext=(a, y + 0.45 + 0.46 * lvl),
                ha="center", fontsize=7.6, color="#22303d", zorder=6,
                bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=.72),
                arrowprops=dict(arrowstyle="-", lw=.6, color="#8a97a3"))

plt.tight_layout()
plt.savefig(os.path.join(OUT, "horizon_silhouette.png"), dpi=125,
            facecolor="white")
print("wrote", os.path.join(OUT, "horizon_silhouette.png"))
