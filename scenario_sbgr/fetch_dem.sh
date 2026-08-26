#!/usr/bin/env bash
# Re-download the elevation data for the SBGR scene. The raw DEM tiles are NOT
# committed (~700 MB); this script reproduces them exactly.
#
#   Copernicus DEM GLO-30 -> dem_cop/   (primary)
#   SRTM v3 1 arcsec      -> dem/       (independent control)
#
# Then run:  python3 prepare_dem.py && python3 build_terrain.py && python3 horizon.py
#
# Nine tiles of each, S23-S25 x W046-W048: ~120 km around Guarulhos, which
# reaches the Serra da Cantareira, the Serra do Mar, the Mantiqueira foothills
# and the Atlantic - unlike Sao Carlos, this horizon has real terrain in it,
# and unlike Sao Carlos two of the SRTM tiles are mostly ocean.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dem dem_cop

echo "== Copernicus DEM GLO-30 (primary) =="
for la in 23 24 25; do for lo in 046 047 048; do
  n="Copernicus_DSM_COG_10_S${la}_00_W${lo}_00_DEM"
  [ -f "dem_cop/${n}.tif" ] || curl -sS --retry 3 -o "dem_cop/${n}.tif" \
    "https://copernicus-dem-30m.s3.amazonaws.com/${n}/${n}.tif" &
done; done; wait

echo "== SRTM v3 1 arcsec (control) =="
for t in S23W046 S23W047 S23W048 S24W046 S24W047 S24W048 \
         S25W046 S25W047 S25W048; do
  [ -f "dem/${t}.hgt" ] && continue
  ( curl -sS --retry 3 -o "dem/${t}.hgt.gz" \
      "https://s3.amazonaws.com/elevation-tiles-prod/skadi/${t:0:3}/${t}.hgt.gz" \
    && gunzip -f "dem/${t}.hgt.gz" ) &
done; wait

echo "== normalise + despike (writes dem_cop_hgt/ and dem_srtm_clean/) =="
python3 prepare_dem.py
echo "done."
