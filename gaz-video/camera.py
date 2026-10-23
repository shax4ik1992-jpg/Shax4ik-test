"""Perspective map camera over a Web-Mercator texture, plus an orthographic globe."""
import json
import math
import os
from dataclasses import dataclass

import cv2
import numpy as np

import config as C
import geo

FOG = np.array([12, 20, 30], np.float32)


@dataclass
class Cam:
    lon: float
    lat: float
    zoom: float      # screen px per texture px at the look-at point
    tilt: float = 0  # degrees from straight down
    bearing: float = 0
    cy: float = 0.5  # look-at point vertical screen position (0..1)

    def mix(self, o, t):
        L = lambda a, b: a + (b - a) * t
        z = math.exp(L(math.log(self.zoom), math.log(o.zoom)))
        return Cam(L(self.lon, o.lon), L(self.lat, o.lat), z, L(self.tilt, o.tilt), L(self.bearing, o.bearing),
                   L(self.cy, o.cy))


class MapView:
    def __init__(self, name, levels=5, fallback=None):
        self.fallback = fallback  # coarser MapView drawn where this texture has no data
        meta = json.load(open(os.path.join(geo.CACHE, f"tex_{name}.json")))
        self.z, self.px0, self.py0 = meta["z"], meta["px0"], meta["py0"]
        self.bbox = meta["bbox"]
        img = cv2.imread(os.path.join(geo.CACHE, f"tex_{name}.png"), cv2.IMREAD_COLOR)[:, :, ::-1]
        self.pyr = [np.ascontiguousarray(img)]
        for _ in range(levels - 1):
            self.pyr.append(cv2.pyrDown(self.pyr[-1]))
        self.W, self.H = C.W, C.H
        self.f = (C.H / 2) / math.tan(math.radians(34 / 2))
        ys = np.linspace(0, 1, C.H, dtype=np.float32)
        self._fog_ramp = np.clip(1 - ys / 0.55, 0, 1) ** 1.6
        # feathered coverage mask (small; stretched over the texture when warped)
        m = np.zeros((256, 256), np.float32)
        m[6:-6, 6:-6] = 1.0
        self._mask = cv2.GaussianBlur(m, (0, 0), 3.0)
        self._mask_scale = np.diag([img.shape[1] / 256.0, img.shape[0] / 256.0, 1.0])

    def world(self, lon, lat):
        x, y = geo.merc_px(lon, lat, self.z)
        return x - self.px0, y - self.py0

    def homography(self, cam):
        """3x3 matrix mapping texture px (level 0) -> screen px."""
        tx, ty = self.world(cam.lon, cam.lat)
        th, br = math.radians(cam.tilt), math.radians(cam.bearing)
        D = self.f / cam.zoom
        ca, sa = math.cos(br), math.sin(br)
        rot = lambda v: np.array([v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca, v[2]])
        xc = rot((1.0, 0.0, 0.0))
        yc = rot((0.0, math.cos(th), -math.sin(th)))
        zc = rot((0.0, -math.sin(th), -math.cos(th)))
        Cpos = np.array([tx, ty, 0.0]) - D * zc
        R = np.stack([xc, yc, zc])
        t = -R @ Cpos
        K = np.array([[self.f, 0, self.W / 2], [0, self.f, self.H * cam.cy], [0, 0, 1]])
        M = np.stack([R[:, 0], R[:, 1], t], 1)
        return K @ M

    def project(self, cam, lon, lat, H=None):
        """lon/lat arrays -> screen x, y arrays and a 'in front of camera' mask."""
        H = self.homography(cam) if H is None else H
        x, y = self.world(np.asarray(lon, float), np.asarray(lat, float))
        p = H @ np.stack([np.ravel(x), np.ravel(y), np.ones(np.size(x))])
        w = p[2]
        ok = w > 1e-6
        w = np.where(ok, w, 1e-6)
        return p[0] / w, p[1] / w, ok

    def _warp(self, H):
        """Warp texture with homography H (texture px -> screen) using trilinear-ish mip blending."""
        Hi = np.linalg.inv(H)

        def tex_at(u, v):
            q = Hi @ np.array([u, v, 1.0])
            return q[:2] / q[2]

        a, b = tex_at(540, 760), tex_at(541, 760)
        texel = max(1e-6, float(np.hypot(*(b - a))))
        lvl = max(0.0, min(len(self.pyr) - 1.001, math.log2(max(1.0, texel)) - 0.25))
        l0 = int(lvl)
        fr = lvl - l0
        out = None
        for li, wgt in ((l0, 1 - fr), (l0 + 1, fr)):
            if wgt < 0.02 or li >= len(self.pyr):
                continue
            S = np.diag([2.0 ** li, 2.0 ** li, 1.0])
            img = cv2.warpPerspective(self.pyr[li], H @ S, (self.W, self.H), flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=(14, 22, 30))
            out = img.astype(np.float32) * wgt if out is None else out + img.astype(np.float32) * wgt
        return out

    def _coverage(self, H):
        return cv2.warpPerspective(self._mask, H @ self._mask_scale, (self.W, self.H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def _fallback_h(self, H):
        fb = self.fallback
        s = 2.0 ** (self.z - fb.z)
        A = np.array([[s, 0, s * fb.px0 - self.px0], [0, s, s * fb.py0 - self.py0], [0, 0, 1.0]])
        return H @ A

    def render(self, cam):
        H = self.homography(cam)
        out = self._warp(H)
        if self.fallback is not None:
            cov = self._coverage(H)
            if cov.min() < 0.999:
                fb = self.fallback._warp(self._fallback_h(H))
                m = cov[..., None]
                out = fb * (1 - m) + out * m
        # distance fog toward the top when tilted
        k = min(1.0, cam.tilt / 48.0) * 0.85
        if k > 0:
            f = (self._fog_ramp * k)[:, None, None]
            out = out * (1 - f) + FOG * f
        return out


class Globe:
    def __init__(self):
        img = cv2.imread(os.path.join(geo.CACHE, "tex_globe.png"), cv2.IMREAD_COLOR)[:, :, ::-1]
        self.pyr = [img]
        for _ in range(3):
            self.pyr.append(cv2.pyrDown(self.pyr[-1]))
        yy, xx = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
        self.xx, self.yy = xx, yy

    @staticmethod
    def forward(lon, lat, lon0, lat0):
        lon, lat = np.radians(lon), np.radians(lat)
        l0, p0 = math.radians(lon0), math.radians(lat0)
        X, Y, Z = np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)
        X1 = X * math.cos(l0) - Z * math.sin(l0)
        Z1 = X * math.sin(l0) + Z * math.cos(l0)
        Y2 = Y * math.cos(p0) - Z1 * math.sin(p0)
        Z2 = Y * math.sin(p0) + Z1 * math.cos(p0)
        return X1, Y2, Z2

    def project(self, lon, lat, lon0, lat0, R, cx, cy):
        X, Y, Z = self.forward(lon, lat, lon0, lat0)
        return cx + R * X, cy - R * Y, Z > 0.02

    def render(self, lon0, lat0, R, cx, cy, bg):
        """bg: float32 HxWx3 background. Returns float32 frame (only the disk's bbox is computed)."""
        x0, x1 = int(max(0, math.floor(cx - R - 2))), int(min(C.W, math.ceil(cx + R + 2)))
        y0, y1 = int(max(0, math.floor(cy - R - 2))), int(min(C.H, math.ceil(cy + R + 2)))
        out = bg.copy()
        if x1 <= x0 or y1 <= y0:
            return out
        u = (self.xx[y0:y1, x0:x1] - cx) / R
        v = (self.yy[y0:y1, x0:x1] - cy) / R
        r2 = u * u + v * v
        z = np.sqrt(np.clip(1 - r2, 0, 1))
        l0, p0 = math.radians(lon0), math.radians(lat0)
        Y1 = -v * math.cos(p0) + z * math.sin(p0)
        Z1 = v * math.sin(p0) + z * math.cos(p0)
        X = u * math.cos(l0) + Z1 * math.sin(l0)
        Zw = -u * math.sin(l0) + Z1 * math.cos(l0)
        texel = (self.pyr[0].shape[1] / (2 * math.pi)) / R
        li = int(max(0, min(len(self.pyr) - 1, math.floor(math.log2(max(1.0, texel))))))
        tex = self.pyr[li]
        th, tw = tex.shape[:2]
        mx = (np.arctan2(X, Zw) * (tw / (2 * math.pi)) + tw / 2).astype(np.float32)
        my = ((math.pi / 2 - np.arcsin(np.clip(Y1, -1, 1))) * (th / math.pi)).astype(np.float32)
        col = cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        light = np.clip(0.35 * (-u) + 0.45 * (-v) + 0.82 * z, 0, 1)
        shade = (0.38 + 0.72 * light) * (0.55 + 0.45 * np.sqrt(z))
        m = np.clip((1 - np.sqrt(np.clip(r2, 0, 1))) * R / 1.5, 0, 1) * (r2 < 1)
        m = m[..., None].astype(np.float32)
        sub = out[y0:y1, x0:x1]
        out[y0:y1, x0:x1] = sub * (1 - m) + col * (shade[..., None] * m)
        return out
