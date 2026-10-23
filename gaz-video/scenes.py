"""All visuals, anchored to script lines via timeline.T(). draw_frame(t) -> RGBA ndarray."""
import math

import cv2
import numpy as np
import skia

import config as C
import gfx as G
from camera import Cam, Globe, MapView
from overlays import Vectors, route
from timeline import CHAPTERS, DURATION, T, TE, caption_chunks, chapter_at

# ------------------------------------------------------------------ places (lon, lat)
PATRON = (65.15, 38.95)        # Mirishkor district, Qashqadaryo (approximate)
MUYNAK_FIELD = (58.35, 43.95)  # Ustyurt, Mo'ynoq district (approximate)
TASHKENT = (69.24, 41.30)
UZ_CENTER = (64.3, 41.6)
CAC_ROUTE = [(48.57, 50.15), (51.2, 48.9), (53.32, 47.65), (55.20, 45.32), (57.2, 44.0), (58.84, 43.04),
             (60.36, 41.38), (62.2, 40.6), (63.45, 40.13)]  # Aleksandrov Gay -> Beyneu -> Kungrad -> Gazli

CITIES = [  # lon, lat, weight
    (69.24, 41.30, 3.2), (66.96, 39.65, 1.3), (71.67, 41.00, 1.1), (72.34, 40.78, 1.1), (71.78, 40.38, 0.9),
    (64.42, 39.77, 0.8), (65.79, 38.86, 0.8), (59.60, 42.46, 0.7), (67.84, 40.12, 0.5), (67.28, 37.22, 0.5),
    (60.63, 41.55, 0.7), (65.38, 40.10, 0.5), (68.78, 40.49, 0.4), (70.94, 40.53, 0.6), (69.58, 41.47, 0.4),
    (70.14, 41.02, 0.3), (71.72, 40.47, 0.4), (66.83, 39.06, 0.3), (67.90, 38.27, 0.3), (60.36, 41.38, 0.3),
    (69.60, 40.90, 0.35), (72.05, 40.95, 0.5), (71.25, 40.60, 0.4), (68.0, 39.9, 0.25), (66.25, 39.4, 0.3),
]

# schematic gas-field markers (locations are illustrative, not survey data)
_rng = np.random.default_rng(42)
FIELDS = ([(63.2 + _rng.uniform(0, 3.4), 38.4 + _rng.uniform(0, 1.9)) for _ in range(10)] +
          [(56.6 + _rng.uniform(0, 2.6), 42.6 + _rng.uniform(0, 1.9)) for _ in range(6)] +
          [(67.2 + _rng.uniform(0, 0.7), 37.5 + _rng.uniform(0, 0.8)) for _ in range(2)] +
          [(71.0 + _rng.uniform(0, 1.0), 40.6 + _rng.uniform(0, 0.4)) for _ in range(2)])
DEPLETED = set(_rng.permutation(len(FIELDS))[:17].tolist())  # 17 / 20 = 85 %

# ------------------------------------------------------------------ key times
T_G2M = T("a2", 0.2)            # globe -> map crossfade start
T_WIDE_IN = T("g1") - 0.45
T_WIDE_OUT = T("h1") - 0.35
XF = 0.5


class World:
    _inst = None

    @classmethod
    def get(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self):
        self.wide = MapView("wide")
        self.uz = MapView("uz", fallback=self.wide)
        self.globe = Globe()
        self.vuz = Vectors(self.uz, regions=("UZ-QA", "UZ-QR"), tol=0.008)
        self.vwide = Vectors(self.wide, tol=0.04)
        self.chunks = caption_chunks()
        yy, xx = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
        r = np.sqrt(((xx - C.W / 2) / (C.W * 0.78)) ** 2 + ((yy - C.H * 0.52) / (C.H * 0.62)) ** 2)
        vig = np.clip(1.0 - 0.62 * np.clip(r - 0.35, 0, 1) ** 1.4, 0, 1)
        top = np.clip(1 - yy / 420, 0, 1) ** 1.5 * 0.55
        vig *= (1 - top)
        self.vignette = vig[..., None].astype(np.float32)
        x = np.arange(256) / 255.0
        y = np.clip(0.5 + (x ** 1.08 - 0.5) * 1.14, 0, 1)
        self.lut = (y * 255).astype(np.uint8)
        self.bg_dark = np.empty((C.H, C.W, 3), np.float32)
        g = np.clip(1 - yy / C.H, 0, 1)[..., None]
        self.bg_dark[:] = np.array([9, 15, 23], np.float32) * (1 - g) + np.array([14, 26, 38], np.float32) * g
        self.rgba = np.zeros((C.H, C.W, 4), np.uint8)
        self.rgba[..., 3] = 255
        self.surface = skia.Surface(self.rgba)


# ------------------------------------------------------------------ cameras
UZ_KEYS = [
    (T_G2M, Cam(64.5, 40.6, 0.109, 0, 0, 0.5)),
    (T("a3"), Cam(63.9, 41.0, 0.135, 22, -4, 0.52)),
    (TE("a5"), Cam(63.6, 41.3, 0.15, 32, -7, 0.52)),
    (T("b1") + 1.3, Cam(65.25, 38.98, 0.62, 44, -8, 0.5)),
    (TE("b6"), Cam(65.12, 39.06, 0.72, 47, -15, 0.5)),
    (T("c1") + 1.3, Cam(62.2, 40.7, 0.17, 26, 0, 0.56)),
    (TE("c5"), Cam(62.5, 40.6, 0.185, 30, 5, 0.56)),
    (T("d1") + 1.2, Cam(58.5, 43.55, 0.55, 42, 10, 0.5)),
    (TE("d5"), Cam(58.7, 43.45, 0.6, 46, 16, 0.5)),
    (T("e1") + 1.2, Cam(69.4, 40.9, 0.33, 40, -12, 0.56)),
    (TE("e4"), Cam(69.8, 40.85, 0.37, 45, -18, 0.56)),
    (T("f1") + 1.0, Cam(69.30, 41.33, 1.25, 50, 18, 0.47)),
    (TE("f4") + 0.5, Cam(69.30, 41.35, 1.45, 53, 26, 0.47)),
    (T_WIDE_OUT, Cam(64.2, 41.1, 0.13, 20, 0, 0.5)),
    (DURATION, Cam(64.0, 41.1, 0.122, 27, -7, 0.5)),
]
WIDE_KEYS = [
    (T_WIDE_IN, Cam(60.5, 44.2, 0.85, 18, 0, 0.5)),
    (T("g2") + 0.4, Cam(56.6, 45.3, 1.05, 30, 0, 0.45)),
    (T_WIDE_OUT + XF, Cam(57.0, 45.1, 1.16, 35, 5, 0.45)),
]


def cam_at(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if t <= t1:
            # moves take at most 2.2 s, then the camera drifts slowly until the next key
            move = min(t1 - t0, 2.2)
            k = (t - t0) / move
            if k <= 1:
                return c0.mix(c1, G.ease_in_out(k) * 0.9)
            drift = (t - t0 - move) / max(0.01, t1 - t0 - move)
            return c0.mix(c1, 0.9 + 0.1 * drift)
    return keys[-1][1]


# ------------------------------------------------------------------ background
def globe_params(t):
    k = G.ease_in_out(G.prog(t, 0.0, T_G2M + XF))
    k2 = G.ease_in_out(G.prog(t, 0.0, T_G2M + XF)) ** 2.2
    lon = G.lerp(28.0, 64.5, k)
    lat = G.lerp(24.0, 40.6, k)
    R = math.exp(G.lerp(math.log(470), math.log(3000), k2))
    cy = G.lerp(980, 960, k)
    return lon, lat, R, 540.0, cy


def dim_at(t):
    d = 0.0
    d = max(d, 0.42 * G.window(t, T("a3"), TE("a3") + 0.2, 0.4, 0.5))
    d = max(d, 0.28 * G.window(t, T("a4"), TE("a5"), 0.4, 0.6))
    d = max(d, 0.32 * G.window(t, T("b6"), TE("b6") + 0.4, 0.4, 0.5))
    d = max(d, 0.38 * G.window(t, T("c3"), TE("c5") + 0.3, 0.4, 0.5))
    d = max(d, 0.34 * G.window(t, T("d2"), TE("d5") + 0.3, 0.4, 0.5))
    d = max(d, 0.34 * G.window(t, T("e3"), TE("e4") + 0.3, 0.4, 0.5))
    d = max(d, 0.34 * G.window(t, T("f4"), TE("f4") + 0.4, 0.4, 0.5))
    d = max(d, 0.50 * G.window(t, T("h1"), DURATION + 1, 0.6, 0.01))
    return d


def background(w, t):
    """Returns (float frame, ctx dict) where ctx holds the active map + homography."""
    ctx = {"globe": None, "uz": None, "wide": None}
    layers = []
    if t < T_G2M + XF:
        lon, lat, R, cx, cy = globe_params(t)
        img = w.globe.render(lon, lat, R, cx, cy, w.bg_dark)
        a = 1.0 - G.prog(t, T_G2M, XF)
        layers.append((img, a))
        ctx["globe"] = (lon, lat, R, cx, cy, a)
    in_wide = T_WIDE_IN <= t < T_WIDE_OUT + XF
    if t >= T_G2M and (t < T_WIDE_IN + XF or t >= T_WIDE_OUT):
        cam = cam_at(UZ_KEYS, t)
        img = w.uz.render(cam)
        if t < T_WIDE_IN + XF and t >= T_WIDE_IN:
            a = 1.0 - G.prog(t, T_WIDE_IN, XF)
        elif t >= T_WIDE_OUT:
            a = G.prog(t, T_WIDE_OUT, XF)
        else:
            a = G.prog(t, T_G2M, XF) if t < T_G2M + XF else 1.0
        layers.append((img, a))
        ctx["uz"] = (cam, w.uz.homography(cam), a)
    if in_wide:
        cam = cam_at(WIDE_KEYS, t)
        img = w.wide.render(cam)
        a = G.prog(t, T_WIDE_IN, XF) if t < T_WIDE_IN + XF else 1.0 - G.prog(t, T_WIDE_OUT, XF)
        layers.append((img, a))
        ctx["wide"] = (cam, w.wide.homography(cam), a)
    # composite: first layer is the base, later layers fade over it
    out = layers[0][0]
    for img, a in layers[1:]:
        out = out * (1 - a) + img * a if a < 1 else img
    d = dim_at(t)
    if d > 0:
        out = out * (1 - d) + w.bg_dark * d * 0.6
    return out, ctx


# ------------------------------------------------------------------ small drawing helpers
def P(view, H, lon, lat):
    x, y, ok = view.project(None, [lon], [lat], H=H)
    return float(x[0]), float(y[0]), bool(ok[0])


def card_title(c, x, y, s, a, rgb=G.CYAN_SOFT):
    G.draw_text(c, s, x, y, G.font("mono", 21, 700), rgb, 0.85 * a, spacing=2.0)


def footnote(c, s, a, y=1392):
    G.draw_text(c, s, 540, y, G.font("mono", 17, 500), (170, 180, 190), 0.55 * a, align="center", spacing=1.2)


def icon(c, kind, x, y, s, a, rgb=G.CYAN):
    p = G.paint(rgb, a, stroke=3.2 * s / 40)
    pf = G.paint(rgb, 0.18 * a)
    if kind == "house":
        pth = skia.Path()
        pth.moveTo(x - s, y)
        pth.lineTo(x, y - s * 0.9)
        pth.lineTo(x + s, y)
        pth.moveTo(x - s * 0.72, y - s * 0.2)
        pth.lineTo(x - s * 0.72, y + s * 0.8)
        pth.lineTo(x + s * 0.72, y + s * 0.8)
        pth.lineTo(x + s * 0.72, y - s * 0.2)
        c.drawPath(pth, p)
        c.drawRect(skia.Rect.MakeXYWH(x - s * 0.2, y + s * 0.25, s * 0.4, s * 0.55), p)
    elif kind == "factory":
        pth = skia.Path()
        pth.moveTo(x - s, y + s * 0.8)
        pth.lineTo(x - s, y - s * 0.1)
        pth.lineTo(x - s * 0.4, y + s * 0.25)
        pth.lineTo(x - s * 0.4, y - s * 0.1)
        pth.lineTo(x + s * 0.2, y + s * 0.25)
        pth.lineTo(x + s * 0.2, y - s * 0.9)
        pth.lineTo(x + s * 0.6, y - s * 0.9)
        pth.lineTo(x + s * 0.6, y + s * 0.8)
        pth.close()
        c.drawPath(pth, pf)
        c.drawPath(pth, p)
        pth2 = skia.Path()
        pth2.moveTo(x - s, y + s * 0.8)
        pth2.lineTo(x + s, y + s * 0.8)
        c.drawPath(pth2, p)
    elif kind == "car":
        c.drawRRect(G.rrect(x - s, y - s * 0.1, 2 * s, s * 0.6, s * 0.18), p)
        pth = skia.Path()
        pth.moveTo(x - s * 0.62, y - s * 0.1)
        pth.lineTo(x - s * 0.35, y - s * 0.55)
        pth.lineTo(x + s * 0.35, y - s * 0.55)
        pth.lineTo(x + s * 0.62, y - s * 0.1)
        c.drawPath(pth, p)
        c.drawCircle(x - s * 0.55, y + s * 0.55, s * 0.22, p)
        c.drawCircle(x + s * 0.55, y + s * 0.55, s * 0.22, p)
        G.draw_text(c, "CNG", x, y + s * 0.32, G.font("mono", s * 0.32, 800), rgb, a, align="center")
    elif kind == "plant":
        for dx in (-0.45, 0.45):
            pth = skia.Path()
            bx = x + dx * s
            pth.moveTo(bx - s * 0.42, y + s * 0.8)
            pth.cubicTo(bx - s * 0.22, y + s * 0.1, bx - s * 0.22, y - s * 0.3, bx - s * 0.3, y - s * 0.7)
            pth.lineTo(bx + s * 0.3, y - s * 0.7)
            pth.cubicTo(bx + s * 0.22, y - s * 0.3, bx + s * 0.22, y + s * 0.1, bx + s * 0.42, y + s * 0.8)
            pth.close()
            c.drawPath(pth, pf)
            c.drawPath(pth, p)
        pth = skia.Path()
        pth.moveTo(x + s * 0.2, y - s * 0.95)
        pth.lineTo(x - s * 0.05, y - s * 0.55)
        pth.lineTo(x + s * 0.12, y - s * 0.55)
        pth.lineTo(x - s * 0.12, y - s * 0.1)
        c.drawPath(pth, G.paint(G.GOLD, a, stroke=3 * s / 40))


def gauge(c, cx, cy, r, value, a, label="", sub=""):
    """Half-ring pressure gauge, value 0..1."""
    rect = skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r)
    c.drawArc(rect, 180, 180, False, G.paint(G.WHITE, 0.12 * a, stroke=18))
    col = G.RED if value < 0.35 else G.GOLD if value < 0.6 else G.CYAN
    c.drawArc(rect, 180, 180 * value, False, G.paint(col, 0.45 * a, stroke=26, blur=10))
    c.drawArc(rect, 180, 180 * value, False, G.paint(col, a, stroke=18))
    for i in range(11):
        ang = math.radians(180 + i * 18)
        x0, y0 = cx + (r - 34) * math.cos(ang), cy + (r - 34) * math.sin(ang)
        x1, y1 = cx + (r - 48) * math.cos(ang), cy + (r - 48) * math.sin(ang)
        c.drawLine(x0, y0, x1, y1, G.paint(G.WHITE, 0.4 * a, stroke=2))
    ang = math.radians(180 + 180 * value)
    c.drawLine(cx, cy, cx + (r - 60) * math.cos(ang), cy + (r - 60) * math.sin(ang), G.paint(G.WHITE, a, stroke=5))
    c.drawCircle(cx, cy, 12, G.paint(G.WHITE, a))
    if label:
        G.draw_text(c, label, cx, cy + 62, G.font("mono", 24, 700), G.WHITE, 0.9 * a, align="center", spacing=2)
    if sub:
        G.draw_text(c, sub, cx, cy + 96, G.font("mono", 19, 600), col, 0.9 * a, align="center", spacing=1.6)


def badge(c, x, y, s, a, rgb=G.RED, size=44, align="left"):
    if a <= 0:
        return
    f = G.font("unb", size, 700)
    w = G.text_w(f, s) + size * 0.9
    h = size * 1.55
    if align == "center":
        x -= w / 2
    k = G.ease_out_back(min(1, a * 1.4))
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.scale(k, k)
    c.translate(-(x + w / 2), -(y + h / 2))
    c.drawRRect(G.rrect(x, y, w, h, h / 2), G.paint(rgb, 0.35 * a, blur=14))
    c.drawRRect(G.rrect(x, y, w, h, h / 2), G.paint(rgb, 0.22 * a))
    c.drawRRect(G.rrect(x, y, w, h, h / 2), G.paint(rgb, 0.9 * a, stroke=2.2))
    G.draw_text(c, s, x + w / 2, y + h * 0.68, f, rgb, a, align="center")
    c.restore()


def puff(c, x, y, t, t0, a, n=6, seed=0, rgb=(200, 225, 235)):
    """Rising, expanding gas puffs (deterministic)."""
    rng = np.random.default_rng(seed)
    for i in range(n):
        ph = ((t - t0) * 0.55 + i / n) % 1.0
        dx = rng.uniform(-26, 26) + 22 * ph * rng.uniform(-1, 1)
        r = 8 + 40 * ph
        c.drawCircle(x + dx, y - 90 * ph, r, G.paint(rgb, 0.32 * a * (1 - ph) ** 1.3, blur=r * 0.55))


# ------------------------------------------------------------------ chapter overlays
def ch1(c, t, w, ctx):
    g = ctx["globe"]
    if g:
        lon0, lat0, R, cx, cy, ga = g
        x, y, ok = w.globe.project(PATRON[0], PATRON[1], lon0, lat0, R, cx, cy)
        if ok:
            G.pin_label(c, t, float(x), float(y), "YANGI KON", T("a1", 0.25), T_G2M + XF, icon="flame",
                        sub="QASHQADARYO · 2026", dy=-90)
        # atmosphere
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeRadial(
            skia.Point(cx, cy), R * 1.12,
            [skia.Color4f(0.3, 0.8, 1, 0).toColor(), skia.Color4f(0.3, 0.8, 1, 0).toColor(),
             skia.Color4f(0.33, 0.83, 0.97, 0.34 * ga).toColor(), skia.Color4f(0.3, 0.8, 1, 0).toColor()],
            [0.0, 0.86, 0.9, 1.0]))
        c.drawCircle(cx, cy, R * 1.12, p)
    m = ctx["uz"]
    if m and t < T("b1") + 2:
        cam, H, ma = m
        v = w.uz
        a_end = 1 - G.prog(t, T("b1"), 0.6)
        w.vuz.draw_borders(c, H, 0.9 * ma * a_end, ma * a_end)
        x, y, _ = P(v, H, *UZ_CENTER)
        la = G.window(t, T_G2M + 0.2, T("a3") + 0.4, 0.5, 0.5) * ma
        if la > 0:
            G.glow_text(c, "O‘ZBEKISTON", x, y, G.font("unb", 44, 600), G.GOLD, la, align="center",
                        spacing=14, glow=14)
        x, y, _ = P(v, H, *PATRON)
        G.pin_label(c, t, x, y, "YANGI KON", T("a1", 0.25), T("a3") + 0.3, icon="flame",
                    sub="QASHQADARYO · 2026", dy=-90)
        x, y, _ = P(v, H, *MUYNAK_FIELD)
        G.pin_label(c, t, x, y, "YANA BITTASI", T("a2", 0.1), T("a3") + 0.3, icon="flame",
                    sub="USTYURT · MO‘YNOQ", dy=-90)
    # a3: winter pressure + queue
    a = G.window(t, T("a3"), TE("a3") + 0.25, 0.35, 0.4)
    if a > 0:
        G.panel(c, 90, 470, 900, 700, a)
        card_title(c, 130, 530, "QISH · ISTE'MOLCHIDA", a)
        k = G.ease_in_out(G.prog(t, T("a3", 0.3), 1.2))
        gauge(c, 540, 830, 230, G.lerp(0.82, 0.18, k), a, "GAZ BOSIMI", "PASAYADI" if k > 0.5 else "")
        qa = G.ease_out(G.prog(t, T("a3", 0.62), 0.6)) * a
        for i in range(5):
            xi = 230 + i * 155 + 80 * (1 - G.ease_out(G.prog(t, T("a3", 0.62) + i * 0.08, 0.5)))
            icon(c, "car", xi, 1040, 42, qa * (1 - i * 0.12), G.GOLD if i == 0 else G.CYAN_SOFT)
        G.draw_text(c, "ZAPRAVKADA NAVBAT", 540, 1130, G.font("mono", 21, 700), G.GOLD, qa, align="center",
                    spacing=2)
    # a4-a5: the question
    v1 = G.window(t, T("a4"), TE("a5") + 0.1, 0.35, 0.4)
    if v1 > 0:
        G.headline(c, t, 540, 560, "Topilyapti-yu,", T("a4"), TE("a5") + 0.1, size=88, align="center")
        f = G.font("serif", 128)
        rise = 22 * (1 - G.ease_out(G.prog(t, T("a4", 0.4), 0.5)))
        va = G.window(t, T("a4", 0.4), TE("a5") + 0.1, 0.35, 0.4)
        G.glow_text(c, "nega yetmayapti?", 540, 700 + rise, f, G.CYAN, va, align="center", glow=18, glow_a=0.5)
        vb = G.window(t, T("a5"), TE("a5") + 0.1, 0.35, 0.4)
        G.draw_text(c, "8 TA RAQAM  ·  8 BOB", 540, 800, G.font("mono", 24, 700), G.CYAN_SOFT, 0.8 * vb,
                    align="center", spacing=3)


def ch2(c, t, w, ctx):
    m = ctx["uz"]
    if not m or not (T("b1") - 0.5 < t < TE("b6") + 1.5):
        return
    cam, H, ma = m
    v = w.uz
    a_all = G.window(t, T("b1") - 0.3, TE("b6") + 0.8, 0.5, 0.6) * ma
    w.vuz.draw_borders(c, H, 0.8 * a_all, 0.9 * a_all)
    w.vuz.draw_region(c, H, "UZ-QA", G.window(t, T("b1", 0.3), TE("b6") + 0.8, 0.6, 0.6) * ma)
    w.vuz.draw_rivers(c, H, 0.7 * a_all)
    x, y, _ = P(v, H, *PATRON)
    G.pin_label(c, t, x, y, "PATRON KONI", T("b1", 0.55), TE("b6") + 0.8, icon="flame",
                sub="MIRISHKOR · QASHQADARYO", dy=-120, side="left")
    G.pin_label(c, t, x, y, "3,3 KM CHUQURLIKDA", T("b2", 0.3), T("b5"), dy=-120, side="right",
                accent=G.GOLD, lead=True)
    G.big_number(c, t, 62, 360, 2.5, T("b2", 0.3), T("b4") + 0.3, unit="mlrd m³", decimals=1,
                 label="ZAXIRA · DASTLABKI BAHO")
    qa = G.window(t, T("b4", 0.2), T("b5"), 0.3, 0.2)
    if qa > 0:
        G.glow_text(c, "bir kunda — ?", 62, 350, G.font("serif", 120), G.CYAN, qa, glow=16)
    G.big_number(c, t, 62, 360, 154, T("b5"), TE("b6") + 0.6, unit="mln m³", label="KUNLIK ISTE'MOL · QISH",
                 count=0.8, from_value=0)
    # b6: calendar month with 16 lit days
    a = G.window(t, T("b6"), TE("b6") + 0.6, 0.35, 0.45)
    if a > 0:
        x0, y0 = 110, 500
        G.panel(c, x0 - 20, y0 - 30, 900, 640, a)
        card_title(c, x0 + 20, y0 + 20, "2 500 ÷ 154 ≈ 16 KUN", a, G.GOLD)
        cs, gap = 104, 12
        for i in range(31):
            r, col = divmod(i, 7)
            xx = x0 + 30 + col * (cs + gap) + 8
            yy = y0 + 60 + r * (cs * 0.78 + gap)
            on = G.prog(t, T("b6", 0.15) + i * 0.07, 0.15) if i < 16 else 0
            c.drawRRect(G.rrect(xx, yy, cs, cs * 0.78, 12), G.paint(G.WHITE, 0.07 * a))
            if on > 0:
                c.drawRRect(G.rrect(xx, yy, cs, cs * 0.78, 12), G.paint(G.CYAN, 0.35 * a * on, blur=8))
                c.drawRRect(G.rrect(xx, yy, cs, cs * 0.78, 12), G.paint((30, 120, 160), 0.95 * a * on))
            G.draw_text(c, str(i + 1), xx + cs / 2, yy + cs * 0.5, G.font("mono", 26, 700),
                        G.WHITE if i < 16 else GRAYC, (0.95 if i < 16 else 0.35) * a, align="center")
        ka = G.window(t, T("b6", 0.75), TE("b6") + 0.6, 0.3, 0.45)
        G.big_number(c, t, 980, 1110, 16, T("b6", 0.75), TE("b6") + 0.6, unit="kun", align="right", size=120,
                     grad=(G.WHITE, G.GOLD), unit_rgb=G.GOLD, a=a)
    footnote(c, "Manba: Energetika vazirligi, 2025–2026", G.window(t, T("b2"), TE("b6"), 0.4, 0.4))


GRAYC = (150, 158, 166)
PROD = [(2019, 60.7), (2022, 51.7), (2023, 46.7), (2024, 44.6), (2025, 42.3)]


def ch3(c, t, w, ctx):
    m = ctx["uz"]
    if not m or not (T("c1") - 0.5 < t < TE("c5") + 1.2):
        return
    cam, H, ma = m
    v = w.uz
    a_all = G.window(t, T("c1") - 0.3, TE("c5") + 0.6, 0.5, 0.5) * ma
    w.vuz.draw_borders(c, H, 0.8 * a_all, 0.9 * a_all)
    for i, (lo, la) in enumerate(FIELDS):
        x, y, ok = P(v, H, lo, la)
        if not ok:
            continue
        ap = G.ease_out_back(G.prog(t, T("c1", 0.3) + i * 0.045, 0.4)) * a_all
        if ap <= 0:
            continue
        dead = G.prog(t, T("c2", 0.35) + (sorted(DEPLETED).index(i) * 0.07 if i in DEPLETED else 0), 0.35) \
            if i in DEPLETED else 0.0
        if dead < 1:
            c.drawCircle(x, y, 26, G.paint(G.CYAN, 0.25 * (1 - dead) * min(1.0, ap), blur=12))
            G.flame(c, x, y + 14, 19 * min(1.0, ap), t + i, (1 - dead) * min(1.0, ap))
        if dead > 0:
            c.drawCircle(x, y, 12, G.paint((96, 96, 96), 0.9 * dead * a_all))
            c.drawCircle(x, y, 12, G.paint((210, 210, 210), 0.6 * dead * a_all, stroke=2))
            c.drawLine(x - 5, y - 5, x + 5, y + 5, G.paint((230, 230, 230), 0.8 * dead * a_all, stroke=2))
            c.drawLine(x + 5, y - 5, x - 5, y + 5, G.paint((230, 230, 230), 0.8 * dead * a_all, stroke=2))
    G.big_number(c, t, 62, 360, 85, T("c2", 0.3), TE("c2") + 0.4, unit="%", label="KONLAR QURIB BORMOQDA",
                 grad=(G.WHITE, G.RED), unit_rgb=G.RED)
    footnote(c, "Manba: Energetika vaziri, 11.12.2025  ·  kon belgilari sxematik",
             G.window(t, T("c1", 0.5), TE("c2") + 0.4, 0.4, 0.4))
    # production bars
    a = G.window(t, T("c3"), TE("c5") + 0.5, 0.35, 0.45)
    if a > 0:
        x0, y0, wd, ht = 90, 470, 900, 700
        G.panel(c, x0, y0, wd, ht, a)
        card_title(c, x0 + 40, y0 + 56, "GAZ QAZIB OLISH · MLRD M³ / YIL", a)
        base = y0 + ht - 90
        scale = 420 / 62.0
        bw = 120
        for i, (yr, val) in enumerate(PROD):
            st = T("c3", 0.25) if i == 0 else T("c3", 0.7) + (i - 1) * 0.18 if i < 4 else T("c4", 0.3)
            k = G.ease_out(G.prog(t, st, 0.6))
            if k <= 0:
                continue
            bx = x0 + 70 + i * 162
            h = val * scale * k
            col = G.CYAN if i == 0 else G.RED if i == 4 else (110, 150, 170)
            c.drawRRect(G.rrect(bx, base - h, bw, h, 10), G.paint(col, 0.3 * a, blur=12))
            c.drawRRect(G.rrect(bx, base - h, bw, h, 10), G.paint(col, 0.92 * a))
            G.draw_text(c, G.fmt_num(val * k, 1), bx + bw / 2, base - h - 18, G.font("unb", 32, 700), G.WHITE,
                        a * k, align="center")
            G.draw_text(c, str(yr), bx + bw / 2, base + 46, G.font("mono", 24, 700), G.CYAN_SOFT, 0.85 * a,
                        align="center")
        # gap bracket
        ka = G.ease_out(G.prog(t, T("c5"), 0.5)) * a
        if ka > 0:
            y60 = base - 60.7 * scale
            y42 = base - 42.3 * scale
            bx = x0 + 70 + 4 * 162 + bw + 22
            pdash = G.paint(G.GOLD, 0.8 * ka, stroke=2)
            pdash.setPathEffect(skia.DashPathEffect.Make([10.0, 8.0], 0.0))
            c.drawLine(x0 + 70, y60, bx, y60, pdash)
            c.drawLine(bx, y60, bx, y42, G.paint(G.GOLD, ka, stroke=3))
            c.drawLine(bx - 10, y60, bx + 10, y60, G.paint(G.GOLD, ka, stroke=3))
            c.drawLine(bx - 10, y42, bx + 10, y42, G.paint(G.GOLD, ka, stroke=3))
            badge(c, x0 + 520, y0 + 96, "−30%", ka, G.GOLD, size=40)
    footnote(c, "Manba: Milliy statistika qo‘mitasi", G.window(t, T("c3"), TE("c5"), 0.4, 0.4))


def ch4(c, t, w, ctx):
    m = ctx["uz"]
    if not m or not (T("d1") - 0.5 < t < TE("d5") + 1.2):
        return
    cam, H, ma = m
    v = w.uz
    a_all = G.window(t, T("d1") - 0.3, TE("d5") + 0.6, 0.5, 0.5) * ma
    w.vuz.draw_borders(c, H, 0.8 * a_all, 0.9 * a_all)
    w.vuz.draw_region(c, H, "UZ-QR", 0.55 * a_all, rgb=G.CYAN, fill=0.06)
    x, y, _ = P(v, H, *MUYNAK_FIELD)
    G.pin_label(c, t, x, y, "MO‘YNOQ KONI", T("d1", 0.3), TE("d5") + 0.6, icon="flame", sub="USTYURT · 2 QUDUQ",
                dy=-130, side="right")
    G.big_number(c, t, 62, 360, 15, T("d3", 0.35), TE("d5") + 0.6, unit="%", prefix="−",
                 label="QAZIB OLISH · 2026 I CHORAK", grad=(G.WHITE, G.RED), unit_rgb=G.RED)
    a = G.window(t, T("d1", 0.55), TE("d5") + 0.5, 0.35, 0.45)
    if a > 0:
        x0, y0, wd = 90, 470, 900
        G.panel(c, x0, y0, wd, 690, a)
        card_title(c, x0 + 40, y0 + 56, "YANGI QUDUQLAR · MLN M³ / KUN", a)
        rows = [("Mo‘ynoq (Ustyurt)", 3.0, T("d1", 0.6)), ("Patron (Qashqadaryo)", 0.5, T("d2", 0.2))]
        for i, (name, val, st) in enumerate(rows):
            k = G.ease_out(G.prog(t, st, 0.5)) * a
            yy = y0 + 120 + i * 78
            G.flame(c, x0 + 58, yy + 14, 14, t + i, k)
            G.draw_text(c, name, x0 + 92, yy + 12, G.font("inter", 34, 700), G.WHITE, k)
            G.draw_text(c, "+" + G.fmt_num(val, 1), x0 + wd - 44, yy + 12, G.font("unb", 36, 700), G.CYAN, k,
                        align="right")
        # balance bars
        kb = G.window(t, T("d3", 0.1), TE("d5") + 0.5, 0.35, 0.45)
        if kb > 0:
            card_title(c, x0 + 40, y0 + 350, "KUNLIK FARQ · 2026 I CHORAK vs 2025", kb)
            scale = 780 / 19.0
            k1 = G.ease_out(G.prog(t, T("d3", 0.4), 0.7))
            k2 = G.ease_out(G.prog(t, T("d4", 0.15), 1.0))
            by = y0 + 400
            c.drawRRect(G.rrect(x0 + 40, by, 3.5 * scale * k1, 70, 12), G.paint(G.CYAN, 0.92 * kb))
            G.draw_text(c, "+3,5  QO‘SHILDI", x0 + 60 + 3.5 * scale * k1, by + 48, G.font("mono", 26, 800),
                        G.CYAN, kb * k1)
            c.drawRRect(G.rrect(x0 + 40, by + 100, 19 * scale * k2, 70, 12), G.paint(G.RED, 0.35 * kb, blur=10))
            c.drawRRect(G.rrect(x0 + 40, by + 100, 19 * scale * k2, 70, 12), G.paint(G.RED, 0.92 * kb))
            G.draw_text(c, "−19  KAMAYDI", x0 + 62, by + 148, G.font("mono", 26, 800), G.WHITE, kb * k2)
            badge(c, x0 + wd - 230, y0 + 300, "×5", G.ease_out(G.prog(t, T("d5", 0.3), 0.4)) * kb, G.GOLD, 46)
    footnote(c, "Manba: Energetika vazirligi; Milliy statistika qo‘mitasi", G.window(t, T("d1"), TE("d5"), 0.4, 0.4))


def ch5(c, t, w, ctx):
    m = ctx["uz"]
    if not m or not (T("e1") - 0.5 < t < TE("e4") + 1.2):
        return
    cam, H, ma = m
    v = w.uz
    a_all = G.window(t, T("e1") - 0.3, TE("e4") + 0.6, 0.5, 0.5) * ma
    w.vuz.draw_borders(c, H, 0.8 * a_all, 0.9 * a_all)
    rng = np.random.default_rng(5)
    n = 0
    for lo, la, wt in CITIES:
        for j in range(int(6 + wt * 14)):
            dx, dy = rng.normal(0, 0.06 + 0.05 * wt, 2)
            st = T("e1", 0.1) + rng.uniform(0, 1.6) + (rng.uniform(0, 2.2) if j > 6 + wt * 9 else 0)
            k = G.prog(t, st, 0.3) * a_all
            if k <= 0:
                continue
            x, y, ok = P(v, H, lo + dx, la + dy * 0.75)
            if not ok:
                continue
            r = 2.2 + rng.uniform(0, 2.6)
            tw = 0.75 + 0.25 * math.sin(t * 3 + n)
            c.drawCircle(x, y, r * 3.2, G.paint(G.GOLD, 0.28 * k * tw, blur=r * 2))
            c.drawCircle(x, y, r, G.paint((255, 236, 190), 0.95 * k * tw))
            n += 1
    G.big_number(c, t, 62, 360, 38.4, T("e1", 0.25), TE("e2") + 0.6, unit="mln", decimals=1,
                 label="AHOLI · 2026", count=1.2, from_value=30)
    badge(c, 62, 430, "+685 ming / yil", G.window(t, T("e2", 0.3), TE("e2") + 0.6, 0.3, 0.4), G.GOLD, 30)
    # who uses the gas
    a = G.window(t, T("e3"), TE("e3") + 0.25, 0.35, 0.35)
    if a > 0:
        x0, y0 = 90, 520
        G.panel(c, x0, y0, 900, 620, a)
        card_title(c, x0 + 40, y0 + 56, "GAZ KIMGA KETADI", a)
        kinds = [("house", "UYLAR", 0.0), ("factory", "ZAVODLAR", 0.17), ("car", "METAN AVTO", 0.36),
                 ("plant", "ELEKTR ST.", 0.62)]
        fx, fy = 540, y0 + 500
        for i, (kd, lab, fr) in enumerate(kinds):
            k = G.ease_out_back(G.prog(t, T("e3", fr), 0.45)) * a
            ix = x0 + 135 + i * 210
            iy = y0 + 210
            if k <= 0:
                continue
            c.drawCircle(ix, iy, 78, G.paint(G.CYAN, 0.08 * k))
            c.drawCircle(ix, iy, 78, G.paint(G.CYAN, 0.35 * k, stroke=1.5))
            icon(c, kd, ix, iy, 38 * min(1.2, k), min(1.0, k))
            G.draw_text(c, lab, ix, iy + 122, G.font("mono", 21, 700), G.WHITE, 0.9 * min(1, k), align="center",
                        spacing=1.5)
            kl = G.ease_in_out(G.prog(t, T("e3", 0.78), 0.6))
            if kl > 0:
                route(c, np.array([ix, ix, fx]), np.array([iy + 150, fy - 60, fy - 20]), kl, t, a, G.CYAN, 3,
                      flow=True)
        kf = G.ease_out_back(G.prog(t, T("e3", 0.8), 0.5)) * a
        G.flame(c, fx, fy + 18, 30 * min(1.2, kf), t, min(1, kf))
    a = G.window(t, T("e4"), TE("e4") + 0.6, 0.35, 0.45)
    if a > 0:
        x0, y0 = 90, 500
        G.panel(c, x0, y0, 900, 650, a)
        card_title(c, x0 + 40, y0 + 56, "QISHDA GAZ NAVBATI · DEKABR 2025", a)
        rows = [("Aholi", True, "birinchi"), ("Ijtimoiy obyektlar", True, ""), ("Elektr stansiyalari", True, ""),
                ("Mavsumiy iste'molchilar", False, "uziladi"), ("Metan zapravkalar", False, "cheklov")]
        for i, (name, ok, note) in enumerate(rows):
            k = G.ease_out(G.prog(t, T("e4", 0.1) + i * 0.32, 0.4)) * a
            yy = y0 + 130 + i * 98
            col = G.GREEN if ok else G.RED
            G.draw_text(c, f"{i + 1}", x0 + 56, yy + 12, G.font("unb", 32, 700), col, k)
            G.draw_text(c, name, x0 + 110, yy + 12, G.font("inter", 36, 700), G.WHITE if ok else GRAYC, k)
            G.draw_text(c, ("✓ " if ok else "✕ ") + note.upper(), x0 + 860, yy + 12, G.font("mono", 22, 800), col,
                        k, align="right", spacing=1.5)
            c.drawLine(x0 + 40, yy + 46, x0 + 860, yy + 46, G.paint(G.WHITE, 0.08 * k, stroke=1))
    footnote(c, "Manba: Milliy statistika qo‘mitasi; Energetika vazirligi", G.window(t, T("e1"), TE("e4"), 0.4, 0.4))


def _network(w):
    """Schematic gas distribution tree around Tashkent in lon/lat."""
    if hasattr(w, "_net"):
        return w._net
    rng = np.random.default_rng(11)
    segs, nodes = [], []

    def grow(lo, la, ang, length, depth):
        if depth == 0:
            return
        lo2 = lo + math.cos(ang) * length
        la2 = la + math.sin(ang) * length * 0.75
        segs.append(((lo, la), (lo2, la2), depth))
        nodes.append((lo2, la2, depth))
        for d in (-0.75, 0.0, 0.8):
            if rng.uniform() < (0.85 if d == 0 else 0.6):
                grow(lo2, la2, ang + d + rng.normal(0, 0.18), length * rng.uniform(0.55, 0.75), depth - 1)

    grow(68.85, 41.20, 0.2, 0.30, 5)
    w._net = (segs, nodes, rng.permutation(len(nodes))[:7].tolist())
    return w._net


def ch6(c, t, w, ctx):
    m = ctx["uz"]
    if not m or not (T("f1") - 0.5 < t < TE("f4") + 1.4):
        return
    cam, H, ma = m
    v = w.uz
    a_all = G.window(t, T("f1") - 0.3, TE("f4") + 0.8, 0.5, 0.5) * ma
    w.vuz.draw_borders(c, H, 0.5 * a_all, 0.6 * a_all, glow=False)
    segs, nodes, leaks = _network(w)
    grow = G.ease_in_out(G.prog(t, T("f1", 0.1), 1.6))
    for (a0, a1, depth) in segs:
        x0, y0, ok0 = P(v, H, *a0)
        x1, y1, ok1 = P(v, H, *a1)
        if not (ok0 and ok1):
            continue
        k = G.clamp(grow * 6 - (5 - depth))
        if k <= 0:
            continue
        xe, ye = G.lerp(x0, x1, k), G.lerp(y0, y1, k)
        wdt = 2.0 + depth * 1.5
        c.drawLine(x0, y0, xe, ye, G.paint(G.CYAN, 0.45 * a_all, stroke=wdt * 3.4, blur=8))
        c.drawLine(x0, y0, xe, ye, G.paint((14, 40, 56), 0.8 * a_all, stroke=wdt + 2.5))
        c.drawLine(x0, y0, xe, ye, G.paint((190, 238, 255), 0.95 * a_all, stroke=wdt))
    la = G.window(t, T("f1", 0.6), TE("f4") + 0.8, 0.4, 0.5)
    for j, ni in enumerate(leaks):
        lo, la_, d = nodes[ni]
        x, y, ok = P(v, H, lo, la_)
        if not ok:
            continue
        k = G.prog(t, T("f1", 0.6) + j * 0.22, 0.3) * la * a_all
        if k <= 0:
            continue
        ring = (t * 1.3 + j * 0.37) % 1
        c.drawCircle(x, y, 10 + 30 * ring, G.paint(G.RED, 0.7 * k * (1 - ring), stroke=2.5))
        c.drawCircle(x, y, 7, G.paint(G.RED, k))
        puff(c, x, y - 6, t, j, k, n=5, seed=j)
    pa = G.window(t, T("f1", 0.4), TE("f4") + 0.8, 0.3, 0.4) * ma
    x, y, _ = P(v, H, *TASHKENT)
    G.pin_label(c, t, x, y, "TARMOQ · SXEMATIK", T("f1", 0.5), T("f2"), dy=-150, side="center", lead=True)
    G.big_number(c, t, 62, 360, 7.6, T("f2", 0.45), T("f3") + 0.2, unit="%", decimals=1,
                 label="TARMOQDA YO‘QOLGAN · 2026 I YARIM YIL", grad=(G.WHITE, G.RED), unit_rgb=G.RED)
    G.big_number(c, t, 62, 360, 797, T("f3"), TE("f4") + 0.7, unit="mln m³", label="6 OYDA YO‘QOLGAN GAZ",
                 count=0.8)
    a = G.window(t, T("f4"), TE("f4") + 0.7, 0.35, 0.45)
    if a > 0:
        x0, y0 = 90, 520
        G.panel(c, x0, y0, 900, 600, a)
        card_title(c, x0 + 40, y0 + 56, "PATRON KONI ZAXIRASI = 2 500 MLN M³", a)
        cx, cy, r = x0 + 260, y0 + 330, 190
        rect = skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r)
        c.drawArc(rect, 0, 360, False, G.paint((40, 120, 160), 0.9 * a, stroke=46))
        k = G.ease_in_out(G.prog(t, T("f4", 0.2), 1.2))
        sweep = 360 * 797 / 2500 * k
        c.drawArc(rect, -90, sweep, False, G.paint(G.RED, 0.45 * a, stroke=60, blur=12))
        c.drawArc(rect, -90, sweep, False, G.paint(G.RED, a, stroke=46))
        G.draw_text(c, "≈1/3", cx, cy + 22, G.font("unb", 64, 700), G.WHITE, a * k, align="center")
        G.draw_text(c, "797", x0 + 520, y0 + 300, G.font("unb", 74, 700), G.RED, a)
        G.draw_text(c, "MLN M³ YO‘QOLDI", x0 + 522, y0 + 345, G.font("mono", 22, 700), G.WHITE, 0.85 * a, spacing=1.6)
        G.draw_text(c, "atigi 6 oyda", x0 + 520, y0 + 430, G.font("serif", 64), G.GOLD, a)
    footnote(c, "Manba: Prezident yig‘ilishi, iyul 2026  ·  tarmoq sxematik", G.window(t, T("f2"), TE("f4"), 0.4, 0.4))


def ch7(c, t, w, ctx):
    m = ctx["wide"]
    if not m:
        return
    cam, H, ma = m
    v = w.wide
    w.vwide.draw_borders(c, H, 0.9 * ma, ma)
    for name, lo, la, sz in (("ROSSIYA", 50.5, 52.3, 34), ("QOZOG‘ISTON", 61.5, 47.6, 32),
                             ("O‘ZBEKISTON", 61.6, 42.2, 28), ("TURKMANISTON", 57.8, 39.6, 20)):
        x, y, ok = P(v, H, lo, la)
        # labels near the top-left stay hidden while big numbers/text occupy that corner
        la_ = ma * (G.window(t, T("g2") - 0.3, T("g3"), 0.4, 0.3) if name == "ROSSIYA"
                    else G.window(t, T("g1", 0.8), 1e9, 0.5, 0.3))
        if ok and la_ > 0:
            G.glow_text(c, name, x, y, G.font("unb", sz, 600), G.GOLD if name == "O‘ZBEKISTON" else (235, 220, 190),
                        0.85 * la_, align="center", spacing=sz * 0.3, glow=10, glow_a=0.4)
    k = G.ease_in_out(G.prog(t, T("g2", 0.05), 2.4))
    pts = [P(v, H, lo, la) for lo, la in CAC_ROUTE]
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    route(c, xs, ys, k, t, ma * G.window(t, T("g2") - 0.2, 1e9, 0.3, 0.3), G.CYAN, 6)
    bx, by, _ = P(v, H, 55.20, 45.32)
    G.pin_label(c, t, bx, by, "O‘RTA OSIYO — MARKAZ", T("g2", 0.6), T_WIDE_OUT, sub="QUVURI · TESKARI OQIM",
                dy=-110, side="left")
    sx, sy, _ = P(v, H, *CAC_ROUTE[-1])
    G.pin_label(c, t, sx, sy, "O‘ZBEKISTONGA", T("g2", 0.9), T_WIDE_OUT, dy=90, side="left", accent=G.GOLD)
    # export -> import
    a = G.window(t, T("g1", 0.1), TE("g1") + 0.3, 0.3, 0.35)
    if a > 0:
        f = G.font("unb", 92, 700)
        G.draw_text(c, "EKSPORT", 62, 350, f, (200, 205, 210), a)
        ks = G.ease_out(G.prog(t, T("g1", 0.45), 0.4))
        c.drawLine(56, 318, 56 + (G.text_w(f, "EKSPORT") + 12) * ks, 318, G.paint(G.RED, a, stroke=9))
        ki = G.window(t, T("g1", 0.6), TE("g1") + 0.3, 0.3, 0.35)
        G.glow_text(c, "→ IMPORT", 62, 470, f, G.CYAN, ki, glow=14)
    G.big_number(c, t, 62, 360, 6.5, T("g3"), T("g4") + 0.1, unit="mlrd m³", decimals=1, label="ROSSIYADAN · 2025")
    ba = G.window(t, T("g3", 0.3), T("g4") + 0.1, 0.3, 0.3)
    if ba > 0:
        for i, (yr, val) in enumerate(((2024, 5.64), (2025, 6.48))):
            yy = 450 + i * 60
            ww = val / 6.48 * 380 * G.ease_out(G.prog(t, T("g3", 0.3) + i * 0.2, 0.6))
            G.draw_text(c, str(yr), 62, yy + 30, G.font("mono", 24, 700), G.CYAN_SOFT, ba)
            c.drawRRect(G.rrect(150, yy + 6, ww, 32, 8), G.paint(G.CYAN if i else (110, 150, 170), 0.9 * ba))
            G.draw_text(c, G.fmt_num(val, 2), 162 + ww, yy + 32, G.font("unb", 26, 700), G.WHITE, ba)
    G.big_number(c, t, 62, 360, 360, T("g4", 0.3), T_WIDE_OUT + 0.3, unit="mln", prefix="$",
                 label="IMPORTGA · 2026 I CHORAK", grad=(G.WHITE, G.GOLD), unit_rgb=G.GOLD)
    badge(c, 62, 430, "×2,2", G.window(t, T("g5", 0.1), T_WIDE_OUT + 0.3, 0.3, 0.35), G.RED, 36)
    footnote(c, "Manba: Gazprom yillik hisoboti; Milliy statistika qo‘mitasi  ·  yo‘nalish sxematik",
             G.window(t, T("g2"), T_WIDE_OUT, 0.4, 0.4))


def ch8(c, t, w, ctx):
    m = ctx["uz"]
    if m and t > T_WIDE_OUT:
        cam, H, ma = m
        w.vuz.draw_borders(c, H, 0.5 * ma, 0.7 * ma)
    a = G.window(t, T("h1"), TE("h2") + 0.3, 0.35, 0.4)
    if a > 0:
        G.headline(c, t, 540, 600, "Topilyapti — ha.", T("h1", 0.2), TE("h2") + 0.3, size=92, align="center")
        va = G.window(t, T("h2", 0.15), TE("h2") + 0.3, 0.35, 0.4)
        rise = 22 * (1 - G.ease_out(G.prog(t, T("h2", 0.15), 0.5)))
        G.glow_text(c, "Qoplayaptimi — yo‘q.", 540, 740 + rise, G.font("serif", 112), G.CYAN, va, align="center",
                    glow=18)
    a = G.window(t, T("h3"), TE("h3") + 0.3, 0.35, 0.4)
    if a > 0:
        card_title(c, 540 - G.text_w(G.font("mono", 21, 700), "2030-YIL REJASI · MLRD M³ / YIL", 2.0) / 2, 500,
                   "2030-YIL REJASI · MLRD M³ / YIL", a)
        f = G.font("unb", 150, 700)
        k1 = G.ease_out(G.prog(t, T("h3", 0.3), 0.5))
        G.draw_text(c, "62", 330, 720, f, (190, 196, 202), a * k1, align="center")
        ks = G.ease_out(G.prog(t, T("h3", 0.45), 0.35))
        c.drawLine(230, 668, 230 + 200 * ks, 668, G.paint(G.RED, a, stroke=10))
        k2 = G.ease_out(G.prog(t, T("h3", 0.65), 0.5))
        G.draw_text(c, "→", 520, 700, G.font("unb", 90, 700), G.WHITE, a * k2, align="center")
        G.big_number(c, t, 780, 720, 48.5, T("h3", 0.65), TE("h3") + 0.3, decimals=1, align="center", size=150,
                     from_value=62)
        footnote(c, "Manba: hukumat strategiyasi, fevral 2026", a, y=820)
    a = G.window(t, T("h4"), TE("h4") + 0.3, 0.35, 0.4)
    if a > 0:
        G.headline(c, t, 540, 520, "Qancha topamiz emas —", T("h4"), TE("h4") + 0.3, size=60, align="center",
                   rgb=(220, 225, 230))
        va = G.window(t, T("h4", 0.4), TE("h4") + 0.3, 0.35, 0.4)
        rise = 22 * (1 - G.ease_out(G.prog(t, T("h4", 0.4), 0.5)))
        G.glow_text(c, "qanchasini", 540, 680 + rise, G.font("serif", 130), G.CYAN, va, align="center", glow=18)
        G.glow_text(c, "isrof qilmaymiz?", 540, 810 + rise, G.font("serif", 130), G.CYAN, va, align="center", glow=18)
    end_card(c, t)


def end_card(c, t):
    st = T("h5")
    a = G.window(t, st, DURATION + 1, 0.45, 0.01)
    if a <= 0:
        return
    G.headline(c, t, 540, 470, "Bunday *hisob-kitoblarni*", st, DURATION + 1, size=66, align="center",
               accent=G.GOLD)
    G.headline(c, t, 540, 550, "o‘tkazib yubormang", st + 0.15, DURATION + 1, size=66, align="center")
    k = G.ease_out_back(G.prog(t, st + 0.3, 0.6))
    x0, y0, wd, ht = 190, 640, 700, 470
    c.save()
    c.translate(540, y0 + ht / 2)
    c.scale(0.9 + 0.1 * k, 0.9 + 0.1 * k)
    c.translate(-540, -(y0 + ht / 2))
    G.panel(c, x0, y0, wd, ht, a, r=30, border=(150, 120, 255), fill=(22, 20, 44), fill_a=0.88)
    cx, cy = 540, y0 + 20
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeSweep(cx, cy, [skia.Color4f(0.33, 0.83, 0.96, a).toColor(),
                                                       skia.Color4f(0.62, 0.45, 1.0, a).toColor(),
                                                       skia.Color4f(0.96, 0.77, 0.42, a).toColor(),
                                                       skia.Color4f(0.33, 0.83, 0.96, a).toColor()]))
    c.drawCircle(cx, cy, 96, p)
    c.drawCircle(cx, cy, 88, G.paint((14, 22, 34), a))
    G.flame(c, cx, cy + 46, 44, t, a)
    title = C.CHANNEL_NAME or "Raqamlar gapiradi"
    G.draw_text(c, title, 540, y0 + 186, G.font("inter", 44, 800), G.WHITE, a, align="center")
    if C.HANDLE:
        G.draw_text(c, C.HANDLE, 540, y0 + 232, G.font("mono", 24, 600), G.CYAN_SOFT, 0.85 * a, align="center")
    G.draw_text(c, "Iqtisod va energetika — raqamlarda", 540, y0 + 276, G.font("inter", 26, 500), (190, 196, 210),
                0.8 * a, align="center")
    click = st + 2.3
    done = t >= click
    bw, bh = 460, 92
    bx, by = 540 - bw / 2 - 40, y0 + 320
    press = 1 - 0.06 * math.exp(-((t - click) * 9) ** 2) if t > click - 0.3 else 1
    c.save()
    c.translate(bx + bw / 2, by + bh / 2)
    c.scale(press, press)
    c.translate(-(bx + bw / 2), -(by + bh / 2))
    if not done:
        c.drawRRect(G.rrect(bx, by, bw, bh, 22), G.paint((40, 130, 255), 0.45 * a, blur=16))
        c.drawRRect(G.rrect(bx, by, bw, bh, 22), G.paint((40, 130, 255), a))
        G.draw_text(c, "Obuna bo‘lish", bx + bw / 2, by + 60, G.font("inter", 38, 800), G.WHITE, a, align="center")
    else:
        c.drawRRect(G.rrect(bx, by, bw, bh, 22), G.paint((60, 66, 96), a))
        G.draw_text(c, "Obunasiz ✓", bx + bw / 2, by + 60, G.font("inter", 38, 800), (220, 225, 240), a,
                    align="center")
    c.restore()
    belx = bx + bw + 30
    c.drawRRect(G.rrect(belx, by, 92, bh, 22), G.paint((60, 66, 96) if done else (45, 50, 80), a))
    bell = skia.Path()
    bcx, bcy = belx + 46, by + 44
    bell.moveTo(bcx - 18, bcy + 12)
    bell.cubicTo(bcx - 14, bcy + 4, bcx - 16, bcy - 20, bcx, bcy - 20)
    bell.cubicTo(bcx + 16, bcy - 20, bcx + 14, bcy + 4, bcx + 18, bcy + 12)
    bell.close()
    c.drawPath(bell, G.paint(G.CYAN if done else G.WHITE, a))
    c.drawCircle(bcx, bcy + 18, 5, G.paint(G.CYAN if done else G.WHITE, a))
    c.restore()
    # cursor
    ka = G.ease_in_out(G.prog(t, st + 1.2, 1.0))
    mx = G.lerp(900, bx + bw * 0.62, ka)
    my = G.lerp(1500, by + bh * 0.62, ka)
    ca = G.window(t, st + 1.0, click + 1.2, 0.3, 0.4) * a
    if ca > 0:
        cur = skia.Path()
        cur.moveTo(mx, my)
        cur.lineTo(mx, my + 46)
        cur.lineTo(mx + 12, my + 35)
        cur.lineTo(mx + 22, my + 56)
        cur.lineTo(mx + 30, my + 52)
        cur.lineTo(mx + 20, my + 32)
        cur.lineTo(mx + 36, my + 32)
        cur.close()
        c.drawPath(cur, G.paint(G.INK, 0.5 * ca, blur=6))
        c.drawPath(cur, G.paint(G.WHITE, ca))
        c.drawPath(cur, G.paint(G.INK, ca, stroke=2))
        if t > click:
            rr = (t - click) * 160
            c.drawCircle(mx, my, rr, G.paint(G.WHITE, max(0, 0.6 - (t - click) * 1.2) * ca, stroke=3))


# ------------------------------------------------------------------ frame
def draw_frame(t, captions=True, w=None):
    """Render frame at time t. Returns (rgba_clean, rgba_captioned) views into reusable buffers."""
    w = w or World.get()
    bg, ctx = background(w, t)
    bg = bg * w.vignette
    rgb = cv2.LUT(np.clip(bg, 0, 255).astype(np.uint8), w.lut)
    w.rgba[..., :3] = rgb
    c = w.surface.getCanvas()
    ch1(c, t, w, ctx)
    ch2(c, t, w, ctx)
    ch3(c, t, w, ctx)
    ch4(c, t, w, ctx)
    ch5(c, t, w, ctx)
    ch6(c, t, w, ctx)
    ch7(c, t, w, ctx)
    ch8(c, t, w, ctx)
    idx, pr = chapter_at(t)
    G.hud(c, t, idx, pr, CHAPTERS, G.window(t, 0.25, DURATION + 1, 0.6, 0.01))
    clean = w.rgba.copy()
    if captions:
        cur = None
        for ch in w.chunks:
            if ch["start"] <= t < ch["end"]:
                cur = ch
        G.caption_shadow(c)
        if cur:
            G.caption(c, t, cur)
        if C.HANDLE:
            G.draw_text(c, C.HANDLE, 540, 1376, G.font("mono", 22, 500), (200, 210, 220), 0.5, align="center",
                        spacing=1.2)
    return clean, w.rgba
