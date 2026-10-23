"""Download all open data the renderer needs into data/.

Sources (all public, no keys):
  - Elevation: AWS Terrain Tiles, Terrarium PNG (github.com/tilezen/joerd)
  - Borders/lakes/rivers: Natural Earth (github.com/nvkelso/natural-earth-vector)
  - Fonts: Google Fonts (github.com/google/fonts), OFL licensed
"""
import math
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{}"

NE_LAYERS = [
    "ne_10m_admin_0_countries", "ne_10m_admin_1_states_provinces", "ne_10m_lakes",
    "ne_10m_rivers_lake_centerlines", "ne_50m_land", "ne_50m_admin_0_countries", "ne_50m_lakes",
]
FONTS = {
    "Inter[opsz,wght].ttf": "inter/Inter%5Bopsz,wght%5D.ttf",
    "Unbounded[wght].ttf": "unbounded/Unbounded%5Bwght%5D.ttf",
    "JetBrainsMono[wght].ttf": "jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    "InstrumentSerif-Italic.ttf": "instrumentserif/InstrumentSerif-Italic.ttf",
}

# name: (zoom, lon0, lat0, lon1, lat1)
DEM_REGIONS = {
    "uz": (9, 54.0, 36.3, 74.0, 46.8),
    "wide": (6, 35.0, 30.0, 95.0, 62.0),
    "globe": (4, -180.0, -85.0, 180.0, 85.0),
}


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    lr = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lr)) / math.pi) / 2.0 * n
    return x, y


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                blob = r.read()
            with open(path + ".part", "wb") as f:
                f.write(blob)
            os.replace(path + ".part", path)
            return path
        except Exception as e:  # network hiccup: retry with backoff
            if attempt == 3:
                raise RuntimeError(f"{url}: {e}")
            import time
            time.sleep(2 ** (attempt + 1))


def build_dem(name, z, lon0, lat0, lon1, lat1):
    """Mosaic Terrarium tiles into a float32 elevation grid (Web Mercator pixels)."""
    out = os.path.join(DATA, f"dem_{name}.npz")
    if os.path.exists(out):
        return
    x0, y0 = lonlat_to_tile(lon0, lat1, z)
    x1, y1 = lonlat_to_tile(lon1, lat0, z)
    tx0, ty0 = int(math.floor(x0)), int(math.floor(y0))
    tx1, ty1 = int(math.ceil(x1)) - 1, int(math.ceil(y1)) - 1
    tx1 = min(tx1, 2 ** z - 1)
    ty1 = min(ty1, 2 ** z - 1)
    jobs = [(x, y) for y in range(ty0, ty1 + 1) for x in range(tx0, tx1 + 1)]
    print(f"[dem:{name}] z{z} {len(jobs)} tiles")
    tdir = os.path.join(DATA, "tiles", str(z))

    def one(xy):
        x, y = xy
        return fetch(TILE_URL.format(z=z, x=x, y=y), os.path.join(tdir, f"{x}_{y}.png"))

    with ThreadPoolExecutor(24) as ex:
        list(ex.map(one, jobs))
    W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    dem = np.zeros((H, W), np.float32)
    for x, y in jobs:
        img = cv2.imread(os.path.join(tdir, f"{x}_{y}.png"), cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32)
        e = img[:, :, 0] * 256.0 + img[:, :, 1] + img[:, :, 2] / 256.0 - 32768.0
        dem[(y - ty0) * 256:(y - ty0 + 1) * 256, (x - tx0) * 256:(x - tx0 + 1) * 256] = e
    # origin = global mercator pixel of the mosaic's top-left corner at this zoom
    np.savez_compressed(out, dem=dem, z=z, px0=tx0 * 256, py0=ty0 * 256)
    print(f"[dem:{name}] {W}x{H} saved")


def main():
    for layer in NE_LAYERS:
        fetch(NE_URL.format(layer), os.path.join(DATA, "ne", layer + ".geojson"))
    for local, remote in FONTS.items():
        fetch(FONT_URL.format(remote), os.path.join(DATA, "fonts", local))
    only = sys.argv[1:] or list(DEM_REGIONS)
    for name in only:
        build_dem(name, *DEM_REGIONS[name])


if __name__ == "__main__":
    main()
