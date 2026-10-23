"""Vector map overlays (borders, regions, routes) projected through the map camera."""
import numpy as np
import skia
from shapely.geometry import box

import geo
import gfx


class Vectors:
    def __init__(self, view, focus="UZB", regions=(), tol=0.01):
        self.view = view
        bb = box(*view.bbox).buffer(2)
        cs = geo.countries("10m")
        self.focus = []
        self.borders = []
        for code, g in cs.items():
            if not g.intersects(bb):
                continue
            g = g.intersection(bb).simplify(tol)
            rings = [self._w(r) for r in geo.lines_of(g)]
            if code == focus:
                self.focus = rings
            else:
                self.borders += rings
        self.regions = {}
        a1 = geo.admin1("UZB")
        for iso in regions:
            self.regions[iso] = [self._w(r) for r in geo.lines_of(a1[iso].simplify(tol))]
        self.rivers = []
        for name, rank, g in geo.rivers(view.bbox):
            if name and " ".join(name.split()) in ("Amu Darya", "Syr Darya", "Zarafshon", "Naryn", "Panj"):
                self.rivers += [self._w(r) for r in geo.lines_of(g.simplify(tol))]

    def _w(self, ring):
        x, y = self.view.world(ring[:, 0], ring[:, 1])
        return np.stack([x, y], 1)

    @staticmethod
    def path(H, ring, closed=True):
        p = H @ np.stack([ring[:, 0], ring[:, 1], np.ones(len(ring))])
        w = p[2]
        ok = w > 1e-3
        xs, ys = p[0] / np.where(ok, w, 1), p[1] / np.where(ok, w, 1)
        pth = skia.Path()
        pen = False
        for X, Y, o in zip(xs.tolist(), ys.tolist(), ok.tolist()):
            if not o or abs(X) > 2e4 or abs(Y) > 2e4:
                pen = False
                continue
            if pen:
                pth.lineTo(X, Y)
            else:
                pth.moveTo(X, Y)
                pen = True
        if closed and ok.all():
            pth.close()
        return pth

    def draw_borders(self, c, H, a=1.0, focus_a=1.0, glow=True):
        if a > 0:
            p = gfx.paint((235, 225, 205), 0.22 * a, stroke=1.3)
            for r in self.borders:
                c.drawPath(self.path(H, r), p)
        if focus_a > 0:
            for r in self.focus:
                pth = self.path(H, r)
                if glow:
                    c.drawPath(pth, gfx.paint(gfx.GOLD, 0.45 * focus_a, stroke=6, blur=6))
                c.drawPath(pth, gfx.paint((255, 226, 168), 0.85 * focus_a, stroke=2.0))

    def draw_region(self, c, H, iso, a=1.0, rgb=gfx.GOLD, fill=0.14):
        if a <= 0:
            return
        for r in self.regions[iso]:
            pth = self.path(H, r)
            c.drawPath(pth, gfx.paint(rgb, fill * a))
            c.drawPath(pth, gfx.paint(rgb, 0.5 * a, stroke=7, blur=7))
            c.drawPath(pth, gfx.paint(rgb, 0.95 * a, stroke=2.2))

    def draw_rivers(self, c, H, a=1.0):
        if a <= 0:
            return
        for r in self.rivers:
            pth = self.path(H, r, closed=False)
            c.drawPath(pth, gfx.paint(gfx.CYAN, 0.25 * a, stroke=5, blur=4))
            c.drawPath(pth, gfx.paint(gfx.CYAN, 0.55 * a, stroke=1.6))


def route(c, xs, ys, progress, t, a=1.0, rgb=gfx.CYAN, width=5.0, flow=True):
    """Animated glowing route along screen-space polyline, drawn up to `progress` (0..1)."""
    if a <= 0 or progress <= 0:
        return
    pts = np.stack([xs, ys], 1)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    L = seg.sum()
    target = L * progress
    pth = skia.Path()
    pth.moveTo(*pts[0])
    acc = 0.0
    head = pts[0]
    for i, s in enumerate(seg):
        if acc + s >= target:
            k = (target - acc) / max(s, 1e-6)
            head = pts[i] + (pts[i + 1] - pts[i]) * k
            pth.lineTo(*head)
            break
        pth.lineTo(*pts[i + 1])
        acc += s
        head = pts[i + 1]
    c.drawPath(pth, gfx.paint(rgb, 0.35 * a, stroke=width * 3.2, blur=10))
    c.drawPath(pth, gfx.paint((16, 40, 56), 0.9 * a, stroke=width + 3))
    c.drawPath(pth, gfx.paint(rgb, 0.95 * a, stroke=width))
    if flow:
        p = gfx.paint((235, 252, 255), 0.9 * a, stroke=width * 0.55)
        p.setPathEffect(skia.DashPathEffect.Make([14.0, 26.0], -(t * 90.0) % 40.0))
        c.drawPath(pth, p)
    c.drawCircle(float(head[0]), float(head[1]), width * 2.6, gfx.paint(rgb, 0.6 * a, blur=8))
    c.drawCircle(float(head[0]), float(head[1]), width * 1.1, gfx.paint(gfx.WHITE, a))
