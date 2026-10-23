"""Skia drawing kit: fonts, colors, easing, HUD, labels, cards, big numbers, captions."""
import math
import os
from functools import lru_cache

import numpy as np
import skia

import config as C

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fonts")
FONT_FILES = {
    "inter": "Inter[opsz,wght].ttf",
    "unb": "Unbounded[wght].ttf",
    "mono": "JetBrainsMono[wght].ttf",
    "serif": "InstrumentSerif-Italic.ttf",
}

# palette (RGB)
WHITE = (255, 255, 255)
CYAN = (84, 212, 246)
CYAN_SOFT = (150, 226, 248)
GOLD = (244, 196, 108)
RED = (255, 96, 84)
GREEN = (96, 226, 150)
GRAY = (138, 150, 160)
INK = (8, 16, 24)
PANEL = (11, 20, 30)
MARK = {"*": CYAN, "^": GOLD, "~": RED}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t, s=1.6):
    t = clamp(t)
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def window(t, start, end, fade_in=0.3, fade_out=0.3):
    """0..1 visibility for an element living in [start, end]."""
    if t < start or t > end:
        return 0.0
    a = prog(t, start, fade_in) if fade_in > 0 else 1.0
    b = 1 - prog(t, end - fade_out, fade_out) if fade_out > 0 else 1.0
    return ease_out(min(a, b))


# ---------------------------------------------------------------- fonts
@lru_cache(maxsize=None)
def _typeface(kind, weight):
    tf = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, FONT_FILES[kind]))
    if kind == "serif":
        return tf
    tag = (ord("w") << 24) | (ord("g") << 16) | (ord("h") << 8) | ord("t")
    coords = skia.FontArguments.VariationPosition.Coordinates(
        [skia.FontArguments.VariationPosition.Coordinate(tag, float(weight))])
    args = skia.FontArguments()
    args.setVariationDesignPosition(skia.FontArguments.VariationPosition(coords))
    return tf.makeClone(args)


@lru_cache(maxsize=None)
def font(kind, size, weight=400):
    f = skia.Font(_typeface(kind, weight), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def color(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


def paint(rgb=WHITE, a=1.0, stroke=None, blur=0.0, aa=True):
    p = skia.Paint(AntiAlias=aa)
    p.setColor4f(color(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def text_w(f, s, spacing=0.0):
    return f.measureText(s) + spacing * max(0, len(s) - 1)


def draw_text(c, s, x, y, f, rgb=WHITE, a=1.0, align="left", spacing=0.0, blur=0.0, p=None):
    if a <= 0.003 or not s:
        return 0
    w = text_w(f, s, spacing)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    pp = p or paint(rgb, a, blur=blur)
    if spacing == 0:
        c.drawString(s, x, y, f, pp)
    else:
        for ch in s:
            c.drawString(ch, x, y, f, pp)
            x += f.measureText(ch) + spacing
    return w


def glow_text(c, s, x, y, f, rgb, a=1.0, align="left", spacing=0.0, glow=10, glow_a=0.55):
    draw_text(c, s, x, y, f, rgb, a * glow_a, align, spacing, blur=glow)
    return draw_text(c, s, x, y, f, rgb, a, align, spacing)


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


def panel(c, x, y, w, h, a=1.0, r=22, border=(120, 200, 230), fill=PANEL, fill_a=0.80):
    """Dark glass card with a soft shadow and hairline border."""
    if a <= 0:
        return
    c.drawRRect(rrect(x, y + 14, w, h, r), paint(INK, 0.55 * a, blur=26))
    c.drawRRect(rrect(x, y, w, h, r), paint(fill, fill_a * a))
    top = skia.Paint(AntiAlias=True)
    top.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(x, y), skia.Point(x, y + h)],
        [skia.Color4f(1, 1, 1, 0.07 * a).toColor(), skia.Color4f(1, 1, 1, 0.0).toColor()]))
    c.drawRRect(rrect(x, y, w, h, r), top)
    c.drawRRect(rrect(x + 0.5, y + 0.5, w - 1, h - 1, r), paint(border, 0.28 * a, stroke=1.5))


# ---------------------------------------------------------------- HUD
def hud(c, t, chapter_idx, chapter_prog, chapters, a=1.0):
    if a <= 0:
        return
    y = 168
    f = font("mono", 19, 700)
    label = f"{C.SERIES} · #{C.EPISODE}"
    w = text_w(f, label, 1.6) + 54
    c.drawRRect(rrect(62, y - 28, w, 40, 20), paint(PANEL, 0.72 * a))
    c.drawRRect(rrect(62, y - 28, w, 40, 20), paint(CYAN, 0.30 * a, stroke=1.4))
    pulse = 0.65 + 0.35 * math.sin(t * 4.0)
    c.drawCircle(84, y - 8, 9, paint(CYAN, 0.5 * a * pulse, blur=6))
    c.drawCircle(84, y - 8, 5.5, paint(CYAN, a))
    draw_text(c, label, 100, y - 1, f, WHITE, 0.92 * a, spacing=1.6)
    num, name = chapters[chapter_idx]
    right = f"{chapter_idx + 1:02d}/{len(chapters):02d}  ·  {name}"
    draw_text(c, right, 1018, y - 1, f, WHITE, 0.82 * a, align="right", spacing=1.6)
    n = len(chapters)
    x0, x1, gap = 62, 1018, 9
    sw = (x1 - x0 - gap * (n - 1)) / n
    for i in range(n):
        sx = x0 + i * (sw + gap)
        c.drawRRect(rrect(sx, y + 24, sw, 4, 2), paint(WHITE, 0.16 * a))
        fill = 1.0 if i < chapter_idx else chapter_prog if i == chapter_idx else 0.0
        if fill > 0:
            c.drawRRect(rrect(sx, y + 24, sw * fill, 4, 2), paint(CYAN, (0.55 if i < chapter_idx else 1.0) * a))
            if i == chapter_idx:
                c.drawRRect(rrect(sx, y + 22, sw * fill, 8, 4), paint(CYAN, 0.35 * a, blur=5))


# ---------------------------------------------------------------- map labels
def pin_label(c, t, x, y, text, start, end=1e9, sub=None, side="right", dy=-70, accent=CYAN, icon="dot",
              lead=True, scale=1.0):
    """Mono-caps pill tag anchored to a map point (x, y) with a leader line and pulse."""
    v = window(t, start, end, 0.35, 0.35)
    if v <= 0:
        return
    k = ease_out_back(prog(t, start, 0.45))
    # anchor marker
    ring = (t - start) % 1.6 / 1.6
    c.drawCircle(x, y, (10 + 34 * ring) * scale, paint(accent, 0.55 * v * (1 - ring), stroke=2))
    c.drawCircle(x, y, 9 * scale, paint(accent, 0.6 * v, blur=7))
    c.drawCircle(x, y, 5.5 * scale, paint(WHITE, v))
    f = font("mono", 21 * scale, 700)
    fs = font("mono", 16 * scale, 500)
    tw = text_w(f, text, 1.8)
    sw = text_w(fs, sub, 1.4) if sub else 0
    w = max(tw, sw) + 62 * scale
    h = (74 if sub else 46) * scale
    lx = x + (24 if side == "right" else -24 - w) * scale
    ly = y + dy * scale - h / 2
    if side == "center":
        lx = x - w / 2
    if lead:
        ex = lx if side == "right" else lx + w if side == "left" else x
        ey = ly + h / 2 if side != "center" else ly + h
        lp = paint(accent, 0.55 * v, stroke=1.6)
        c.drawLine(x, y, lerp(x, ex, k), lerp(y, ey, k), lp)
    c.save()
    cx, cy = lx + w / 2, ly + h / 2
    c.translate(cx, cy)
    c.scale(0.85 + 0.15 * k, 0.85 + 0.15 * k)
    c.translate(-cx, -cy)
    c.drawRRect(rrect(lx, ly + 8, w, h, h / 2 if not sub else 14), paint(INK, 0.5 * v, blur=14))
    c.drawRRect(rrect(lx, ly, w, h, h / 2 if not sub else 14), paint(PANEL, 0.85 * v))
    c.drawRRect(rrect(lx, ly, w, h, h / 2 if not sub else 14), paint(accent, 0.35 * v, stroke=1.4))
    ix, iy = lx + 24 * scale, ly + (h / 2 if not sub else 26 * scale)
    if icon == "dot":
        c.drawCircle(ix, iy, 5 * scale, paint(accent, v))
    elif icon == "check":
        c.drawCircle(ix, iy, 9 * scale, paint(GREEN, v, stroke=2))
        pth = skia.Path()
        pth.moveTo(ix - 4 * scale, iy)
        pth.lineTo(ix - 1 * scale, iy + 3.5 * scale)
        pth.lineTo(ix + 4.5 * scale, iy - 3.5 * scale)
        c.drawPath(pth, paint(GREEN, v, stroke=2))
    elif icon == "flame":
        flame(c, ix, iy + 6 * scale, 15 * scale, t, v)
    elif icon == "x":
        c.drawCircle(ix, iy, 9 * scale, paint(RED, v, stroke=2))
        c.drawLine(ix - 4 * scale, iy - 4 * scale, ix + 4 * scale, iy + 4 * scale, paint(RED, v, stroke=2))
        c.drawLine(ix + 4 * scale, iy - 4 * scale, ix - 4 * scale, iy + 4 * scale, paint(RED, v, stroke=2))
    draw_text(c, text, lx + 42 * scale, iy + 7.5 * scale, f, WHITE, v, spacing=1.8)
    if sub:
        draw_text(c, sub, lx + 42 * scale, iy + 34 * scale, fs, CYAN_SOFT, 0.8 * v, spacing=1.4)
    c.restore()


def flame(c, x, y, size, t, a=1.0, hue=CYAN):
    """Stylized blue gas flame; (x, y) is the base center."""
    if a <= 0:
        return
    fl = 1.0 + 0.06 * math.sin(t * 17.0) + 0.04 * math.sin(t * 29.0 + 1.3)
    h = size * 1.9 * fl
    w = size * 0.95

    def tongue(scale, col, alpha, blur=0.0):
        p = skia.Path()
        hh, ww = h * scale, w * scale
        p.moveTo(x, y - hh)
        p.cubicTo(x + ww * 0.35, y - hh * 0.62, x + ww, y - hh * 0.42, x + ww * 0.82, y - hh * 0.12)
        p.cubicTo(x + ww * 0.62, y + hh * 0.08, x - ww * 0.62, y + hh * 0.08, x - ww * 0.82, y - hh * 0.12)
        p.cubicTo(x - ww, y - hh * 0.42, x - ww * 0.35, y - hh * 0.62, x, y - hh)
        p.close()
        c.drawPath(p, paint(col, alpha * a, blur=blur))

    tongue(1.15, hue, 0.45, blur=size * 0.5)
    tongue(1.0, (40, 140, 255), 0.95)
    tongue(0.68, CYAN, 1.0)
    tongue(0.36, (230, 250, 255), 1.0)


# ---------------------------------------------------------------- numbers
def fmt_num(v, decimals=0, sep=" "):
    s = f"{v:,.{decimals}f}".replace(",", " " if sep == "thin" else sep)
    return s.replace(".", ",")


def big_number(c, t, x, y, value, start, end=1e9, unit="", label="", decimals=0, size=150, count=0.9,
               prefix="", align="left", grad=(WHITE, CYAN_SOFT), unit_rgb=CYAN, from_value=0.0, a=1.0):
    v = window(t, start, end, 0.25, 0.35) * a
    if v <= 0:
        return 0
    k = ease_out(prog(t, start, count))
    val = lerp(from_value, value, k)
    s = prefix + fmt_num(val, decimals)
    f = font("unb", size, 700)
    fu = font("unb", size * 0.38, 600)
    w = text_w(f, s)
    wu = text_w(fu, unit) + size * 0.08 if unit else 0
    tot = w + wu
    if align == "center":
        x -= tot / 2
    elif align == "right":
        x -= tot
    blur = 14 * (1 - ease_out(prog(t, start, 0.35)))
    rise = 26 * (1 - ease_out(prog(t, start, 0.45)))
    yy = y + rise
    draw_text(c, s, x, yy, f, grad[1], 0.35 * v, blur=22)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(0, yy - size * 0.78), skia.Point(0, yy + size * 0.05)],
        [color(grad[0], v).toColor(), color(grad[1], v).toColor()]))
    if blur > 0.3:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawString(s, x, yy, f, p)
    if unit:
        draw_text(c, unit, x + w + size * 0.08, yy, fu, unit_rgb, v)
    if label:
        draw_text(c, label, x + 4, yy + size * 0.36, font("mono", 22, 600), CYAN_SOFT, 0.78 * v, spacing=2.2)
    return tot


def headline(c, t, x, y, text, start, end=1e9, size=74, rgb=WHITE, align="left", kind="inter", weight=800,
             a=1.0, accent=None):
    """Large title text with fade/rise. Words wrapped in *..* get the accent color."""
    v = window(t, start, end, 0.3, 0.35) * a
    if v <= 0:
        return
    f = font(kind, size, weight)
    rise = 18 * (1 - ease_out(prog(t, start, 0.4)))
    parts = parse_marks(text)
    total = sum(text_w(f, w + " ") for w, _ in parts) - text_w(f, " ")
    xx = x - total / 2 if align == "center" else x - total if align == "right" else x
    for word, mark in parts:
        col = MARK.get(mark, rgb) if mark else rgb
        if mark and accent:
            col = accent
        draw_text(c, word, xx, y + rise, f, col, v)
        xx += text_w(f, word + " ")


# ---------------------------------------------------------------- captions
def parse_marks(text):
    """'Yangi *gaz koni* topildi' -> [(word, mark|None)]; marks: *cyan* ^gold^ ~red~."""
    out, mark = [], None
    for raw in text.split():
        w = raw
        start_mark = None
        if w[0] in MARK and mark is None:
            start_mark = w[0]
            w = w[1:]
            mark = start_mark
        cur = mark
        if w and w[-1] in MARK and mark is not None and w[-1] == mark:
            w = w[:-1]
            mark = None
        elif len(w) > 1 and w[-2] in MARK and mark is not None and w[-2] == mark and not w[-1].isalnum():
            w = w[:-2] + w[-1]
            mark = None
        out.append((w, cur))
    return out


def caption_shadow(c):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(
        skia.Point(540, 1282), 520,
        [skia.Color4f(0, 0, 0, 0.62).toColor(), skia.Color4f(0, 0, 0, 0.0).toColor()]))
    c.save()
    c.scale(1.0, 0.24)
    c.translate(0, 1282 / 0.24 - 1282)
    c.drawCircle(540, 1282, 520, p)
    c.restore()


def caption(c, t, chunk, a=1.0):
    """chunk = dict(words=[(word, mark, t_on)], start, end). Spoken words light up."""
    if a <= 0:
        return
    f = font("inter", 62, 800)
    words = chunk["words"]
    space = text_w(f, " ")
    widths = [text_w(f, w) for w, _, _ in words]
    total = sum(widths) + space * (len(words) - 1)
    x = 540 - total / 2
    k = ease_out(prog(t, chunk["start"], 0.18))
    y = 1302 + 14 * (1 - k)
    a *= k
    for (w, mark, ton), ww in zip(words, widths):
        on = prog(t, ton, 0.12)
        base = MARK.get(mark, WHITE) if mark else WHITE
        if on < 1:
            draw_text(c, w, x, y, f, (120, 128, 136), 0.75 * a * (1 - on))
        if on > 0:
            if mark:
                draw_text(c, w, x, y, f, base, 0.45 * a * on, blur=12)
            draw_text(c, w, x, y, f, base, a * on)
        x += ww + space
