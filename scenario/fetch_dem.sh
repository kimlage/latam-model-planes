#!/usr/bin/env bash
# Re-download the elevation data for the SCL scene. The raw DEM tiles are NOT
# committed (~800 MB); this script reproduces them exactly.
#
#   Copernicus DEM GLO-30 -> dem_cop/   (primary)
#   SRTM v3 1 arcsec      -> dem/       (independent control)
#
# Then run:  python3 build_terrain.py && python3 horizon.py && python3 peaks.py
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dem dem_cop

echo "== Copernicus DEM GLO-30 (primary) =="
for la in 32 33 34 35; do for lo in 070 071 072; do
  n="Copernicus_DSM_COG_10_S${la}_00_W${lo}_00_DEM"
  [ -f "dem_cop/${n}.tif" ] || curl -sS --retry 3 -o "dem_cop/${n}.tif" \
    "https://copernicus-dem-30m.s3.amazonaws.com/${n}/${n}.tif" &
done; done; wait

echo "== SRTM v3 1 arcsec (control) =="
for t in S32W070 S32W071 S32W072 S33W070 S33W071 S33W072 \
         S34W070 S34W071 S34W072 S35W070 S35W071 S35W072; do
  [ -f "dem/${t}.hgt" ] && continue
  ( curl -sS --retry 3 -o "dem/${t}.hgt.gz" \
      "https://s3.amazonaws.com/elevation-tiles-prod/skadi/${t:0:3}/${t}.hgt.gz" \
    && gunzip -f "dem/${t}.hgt.gz" ) &
done; wait

echo "== normalise + despike (writes dem_cop_hgt/ and dem_srtm_clean/) =="
python3 prepare_dem.py
echo "done."
