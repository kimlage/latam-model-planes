#!/usr/bin/env bash
# Re-download the elevation data for the SDSC scene. The raw DEM tiles are NOT
# committed (~770 MB); this script reproduces them exactly.
#
#   Copernicus DEM GLO-30 -> dem_cop/   (primary)
#   SRTM v3 1 arcsec      -> dem/       (independent control)
#
# Then run:  python3 prepare_dem.py && python3 build_terrain.py && python3 horizon.py
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dem dem_cop

echo "== Copernicus DEM GLO-30 (primary) =="
for la in 21 22 23; do for lo in 047 048 049 050; do
  n="Copernicus_DSM_COG_10_S${la}_00_W${lo}_00_DEM"
  [ -f "dem_cop/${n}.tif" ] || curl -sS --retry 3 -o "dem_cop/${n}.tif" \
    "https://copernicus-dem-30m.s3.amazonaws.com/${n}/${n}.tif" &
done; done; wait

echo "== SRTM v3 1 arcsec (control) =="
for t in S21W047 S21W048 S21W049 S21W050 S22W047 S22W048 S22W049 S22W050 \
         S23W047 S23W048 S23W049 S23W050; do
  [ -f "dem/${t}.hgt" ] && continue
  ( curl -sS --retry 3 -o "dem/${t}.hgt.gz" \
      "https://s3.amazonaws.com/elevation-tiles-prod/skadi/${t:0:3}/${t}.hgt.gz" \
    && gunzip -f "dem/${t}.hgt.gz" ) &
done; wait

echo "== normalise + despike (writes dem_cop_hgt/ and dem_srtm_clean/) =="
python3 prepare_dem.py
echo "done."
