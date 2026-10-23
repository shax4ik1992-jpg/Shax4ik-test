"""Geography helpers: Web Mercator math, Natural Earth loading, polygon rasterizing."""
import json
import math
import os
from functools import lru_cache

import cv2
import numpy as np
from shapely.geometry import shape, box, MultiPolygon, Polygon, LineString, MultiLineString
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
os.makedirs(CACHE, exist_ok=True)


def merc_px(lon, lat, z):
    """Global Web Mercator pixel coordinates at zoom z (256px tiles). Vectorized."""
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.clip(np.asarray(lat, dtype=np.float64), -85.05, 85.05)
    n = 256.0 * 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def merc_lonlat(x, y, z):
    n = 256.0 * 2 ** z
    lon = np.asarray(x) / n * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * np.asarray(y) / n))))
    return lon, lat


def meters_per_px(lat, z):
    return 40075016.686 * math.cos(math.radians(lat)) / (256 * 2 ** z)


@lru_cache(maxsize=None)
def load_layer(name):
    with open(os.path.join(DATA, "ne", name + ".geojson"), encoding="utf-8") as f:
        return json.load(f)["features"]


def countries(res="10m"):
    out = {}
    for f in load_layer(f"ne_{res}_admin_0_countries"):
        p = f["properties"]
        code = p.get("ADM0_A3") or p.get("adm0_a3")
        out[code] = shape(f["geometry"])
    return out


def admin1(country="UZB"):
    out = {}
    for f in load_layer("ne_10m_admin_1_states_provinces"):
        p = f["properties"]
        if p.get("adm0_a3") == country:
            out[p["iso_3166_2"]] = shape(f["geometry"])
    return out


def lakes(res="10m", bbox=None):
    geoms = []
    for f in load_layer(f"ne_{res}_lakes"):
        g = shape(f["geometry"])
        if bbox is None or g.intersects(box(*bbox)):
            geoms.append(g)
    return geoms


def rivers(bbox):
    out = []
    b = box(*bbox)
    for f in load_layer("ne_10m_rivers_lake_centerlines"):
        g = shape(f["geometry"])
        if g.intersects(b):
            out.append((f["properties"].get("name"), f["properties"].get("scalerank", 9), g))
    return out


def polygons_of(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        res = []
        for gg in g.geoms:
            res += polygons_of(gg)
        return res
    return []


def lines_of(g):
    if isinstance(g, LineString):
        return [np.asarray(g.coords)]
    if isinstance(g, MultiLineString):
        return [np.asarray(l.coords) for l in g.geoms]
    if isinstance(g, (Polygon, MultiPolygon)):
        res = []
        for p in polygons_of(g):
            res.append(np.asarray(p.exterior.coords))
            res += [np.asarray(i.coords) for i in p.interiors]
        return res
    if hasattr(g, "geoms"):
        res = []
        for gg in g.geoms:
            res += lines_of(gg)
        return res
    return []


def rasterize(geoms, shape_hw, to_px, value=255):
    """Fill polygons (lon/lat) into a uint8 mask. to_px maps (lon,lat) arrays -> (x,y) arrays."""
    m = np.zeros(shape_hw, np.uint8)
    S = 16  # 4-bit subpixel shift
    for g in geoms:
        for p in polygons_of(g):
            ext = np.asarray(p.exterior.coords)
            x, y = to_px(ext[:, 0], ext[:, 1])
            cv2.fillPoly(m, [np.round(np.stack([x, y], 1) * S).astype(np.int32)], value, cv2.LINE_AA, shift=4)
            for hole in p.interiors:
                h = np.asarray(hole.coords)
                x, y = to_px(h[:, 0], h[:, 1])
                cv2.fillPoly(m, [np.round(np.stack([x, y], 1) * S).astype(np.int32)], 0, cv2.LINE_AA, shift=4)
    return m
