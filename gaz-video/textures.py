"""Bake shaded-relief color textures (sand-gold land, cyan water) from the DEM mosaics.

Outputs to data/cache/: tex_uz.png, tex_wide.png, tex_globe.png (+ .json metadata).
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from shapely.ops import unary_union

import geo

# elevation (m) -> base RGB, linear interpolated
RAMP = [
    (-100, (92, 66, 38)),
    (0, (150, 108, 62)),
    (150, (176, 128, 74)),
    (400, (186, 140, 84)),
    (900, (168, 122, 72)),
    (1800, (140, 100, 62)),
    (3200, (148, 114, 84)),
    (5000, (176, 154, 128)),
]
SHADOW = np.array([22, 17, 16], np.float32)
WATER_DEEP = np.array([9, 38, 60], np.float32)
WATER_MID = np.array([16, 92, 128], np.float32)
WATER_EDGE = np.array([70, 206, 240], np.float32)
OCEAN_GLOBE = np.array([10, 28, 44], np.float32)


def ramp(elev):
    xs = np.array([r[0] for r in RAMP], np.float32)
    out = np.empty(elev.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(elev, xs, np.array([r[1][c] for r in RAMP], np.float32))
    return out


def hillshade(dem, res_m, ve, az=315.0, alt=38.0):
    d = cv2.GaussianBlur(dem, (0, 0), 0.8) * ve
    gy, gx = np.gradient(d, res_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azr, altr = math.radians(360.0 - az + 90.0), math.radians(alt)
    hs = np.sin(altr) * np.cos(slope) + np.cos(altr) * np.sin(slope) * np.cos(azr - aspect)
    return np.clip(hs, 0, 1)


def dune_noise(shape_hw, seed=7):
    """Fractal noise used as fake dune relief on flat lowlands (meters)."""
    rng = np.random.default_rng(seed)
    H, W = shape_hw
    acc = np.zeros(shape_hw, np.float32)
    for octave, amp in ((64, 1.0), (24, 0.55), (9, 0.3), (4, 0.15)):
        small = rng.standard_normal((H // octave + 2, W // octave + 2)).astype(np.float32)
        acc += amp * cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
    return acc


def shade_land(dem, res_m, ve, dunes=0.0):
    if dunes:
        low = np.clip(1.0 - dem / 600.0, 0, 1)
        dem = dem + dunes * low * dune_noise(dem.shape)
    h1 = hillshade(dem, res_m, ve, 315, 36)
    h2 = hillshade(dem, res_m, ve, 255, 50)
    hs = 0.72 * h1 + 0.28 * h2
    flat = math.sin(math.radians(36)) * 0.72 + math.sin(math.radians(50)) * 0.28
    hs = hs / flat  # 1.0 == flat ground
    # local relief: ridges brighter, valleys darker (cheap ambient occlusion)
    big = cv2.GaussianBlur(dem, (0, 0), 18)
    relief = np.clip((dem - big) / 400.0, -1, 1)
    base = ramp(dem)
    k = np.clip(hs, 0, 1.6)[..., None]
    col = base * (0.30 + 0.78 * k)
    hi = np.clip(k - 1.0, 0, 1) ** 1.5
    col += hi * np.array([70, 52, 26], np.float32)
    lo = np.clip(1.0 - k, 0, 1) ** 1.3
    col = col * (1 - 0.55 * lo) + SHADOW * 0.55 * lo
    col *= (1.0 + 0.18 * relief)[..., None]
    return col


def water_color(water_mask, dem, edge_px):
    dist = cv2.distanceTransform((water_mask > 127).astype(np.uint8), cv2.DIST_L2, 5)
    t1 = np.clip(dist / edge_px, 0, 1)[..., None]
    t2 = np.clip((dist - edge_px) / (edge_px * 5), 0, 1)[..., None]
    col = WATER_EDGE * (1 - t1) + WATER_MID * t1
    col = col * (1 - t2) + WATER_DEEP * t2
    # faint bathymetry where the DEM has it
    depth = np.clip(-dem / 600.0, 0, 1)[..., None]
    col = col * (1 - 0.35 * depth)
    return col


def bake_mercator(name, ve, edge_px, dim_outside=None, dunes=0.0):
    npz = np.load(os.path.join(geo.DATA, f"dem_{name}.npz"))
    dem, z, px0, py0 = npz["dem"], int(npz["z"]), float(npz["px0"]), float(npz["py0"])
    H, W = dem.shape
    lon0, lat1 = geo.merc_lonlat(px0, py0, z)
    lon1, lat0 = geo.merc_lonlat(px0 + W, py0 + H, z)
    bbox = (float(lon0), float(lat0), float(lon1), float(lat1))
    to_px = lambda lo, la: tuple(a - b for a, b in zip(geo.merc_px(lo, la, z), (px0, py0)))
    lat_c = (bbox[1] + bbox[3]) / 2
    res_m = geo.meters_per_px(lat_c, z)
    print(f"[{name}] {W}x{H} z{z} bbox={tuple(round(v, 2) for v in bbox)} res={res_m:.0f}m")

    cs = geo.countries("10m")
    from shapely.geometry import box
    b = box(*bbox).buffer(1)
    land_geoms = [g for g in cs.values() if g.intersects(b)]
    land = geo.rasterize(land_geoms, (H, W), to_px)
    lk = geo.rasterize(geo.lakes("10m", bbox), (H, W), to_px)
    water = np.maximum(255 - land, lk)
    water = cv2.GaussianBlur(water, (0, 0), 0.6)

    col_land = shade_land(dem, res_m, ve, dunes)
    col_water = water_color(water, dem, edge_px)
    a = (water.astype(np.float32) / 255.0)[..., None]
    # glow of water onto the shore
    glow = cv2.GaussianBlur(water.astype(np.float32) / 255.0, (0, 0), edge_px * 0.9)[..., None]
    col_land = col_land + np.clip(glow - a, 0, 1) * np.array([30, 90, 110], np.float32) * 0.8
    col = col_land * (1 - a) + col_water * a

    if dim_outside:
        m = geo.rasterize([cs[dim_outside]], (H, W), to_px).astype(np.float32) / 255.0
        m = cv2.GaussianBlur(m, (0, 0), 6)[..., None]
        col = col * (0.80 + 0.20 * m)

    img = np.clip(col, 0, 255).astype(np.uint8)
    out = os.path.join(geo.CACHE, f"tex_{name}.png")
    cv2.imwrite(out, img[:, :, ::-1])
    with open(out.replace(".png", ".json"), "w") as f:
        json.dump({"z": z, "px0": px0, "py0": py0, "w": W, "h": H, "bbox": bbox}, f)


def bake_globe():
    npz = np.load(os.path.join(geo.DATA, "dem_globe.npz"))
    dem, z = npz["dem"], int(npz["z"])
    W, H = 4096, 2048
    lon = (np.arange(W) + 0.5) / W * 360 - 180
    lat = 90 - (np.arange(H) + 0.5) / H * 180
    LON, LAT = np.meshgrid(lon, lat)
    mx, my = geo.merc_px(LON, LAT, z)
    eq_dem = cv2.remap(dem, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    eq_dem[np.abs(LAT) > 84.5] = 2500  # polar caps
    to_px = lambda lo, la: ((np.asarray(lo) + 180) / 360 * W, (90 - np.asarray(la)) / 180 * H)
    land = geo.rasterize([f for f in [__import__("shapely.geometry", fromlist=["shape"]).shape(ft["geometry"])
                                      for ft in geo.load_layer("ne_50m_land")]], (H, W), to_px)
    res_m = 40075016.0 / W
    col_land = shade_land(np.maximum(eq_dem, 0), res_m * 0.5, 14.0)
    depth = np.clip(-eq_dem / 5000.0, 0, 1)[..., None]
    col_ocean = OCEAN_GLOBE * (1.15 - 0.45 * depth)
    a = (cv2.GaussianBlur(land, (0, 0), 0.7).astype(np.float32) / 255.0)[..., None]
    glow = cv2.GaussianBlur(land.astype(np.float32) / 255.0, (0, 0), 5)[..., None]
    col_ocean = col_ocean + np.clip(glow, 0, 1) * np.array([10, 40, 55], np.float32)
    col = col_land * a + col_ocean * (1 - a)
    img = np.clip(col, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(geo.CACHE, "tex_globe.png"), img[:, :, ::-1])
    print("[globe] done")


if __name__ == "__main__":
    which = sys.argv[1:] or ["uz", "wide", "globe"]
    if "uz" in which:
        bake_mercator("uz", ve=3.6, edge_px=18, dim_outside="UZB", dunes=5.0)
    if "wide" in which:
        bake_mercator("wide", ve=6.0, edge_px=6)
    if "globe" in which:
        bake_globe()
