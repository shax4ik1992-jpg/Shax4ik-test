"""Procedural sound design (no samples, no licenses): ambient drone + UI/transition effects.

Every cue is anchored to the same timeline as the visuals. The mix is normalized LOW
(TARGET_LUFS) so a voice-over recorded at ~-14 LUFS sits clearly on top.

  python3 sfx.py            -> output/sfx.wav
"""
import math
import os

import numpy as np
import pedalboard as pb
import pyloudnorm as pyln
from scipy.signal import butter, lfilter, sosfilt

import scenes as S
from timeline import CHAPTERS, DURATION, T, TE, chapter_bounds

SR = 48000
TARGET_LUFS = -26.0
PEAK_DB = -8.0
RNG = np.random.default_rng(1234)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def env_adsr(n, a, d, s_level, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    s = max(0, n - a - d - r)
    return np.concatenate([np.linspace(0, 1, a, endpoint=False), np.linspace(1, s_level, d, endpoint=False),
                           np.full(s, s_level), np.linspace(s_level, 0, r)])[:n]


def exp_decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def noise(n):
    return RNG.standard_normal(n)


def bandsweep(x, f0, f1, q=1.2, block=256):
    """Time-varying band-pass (block-wise biquad with carried state)."""
    out = np.zeros_like(x)
    zi = np.zeros(2)
    nb = (len(x) + block - 1) // block
    for i in range(nb):
        k = i / max(1, nb - 1)
        f = f0 * (f1 / f0) ** k
        w0 = 2 * math.pi * min(f, SR * 0.45) / SR
        alpha = math.sin(w0) / (2 * q)
        b = np.array([alpha, 0, -alpha])
        a = np.array([1 + alpha, -2 * math.cos(w0), 1 - alpha])
        seg = x[i * block:(i + 1) * block]
        y, zi = lfilter(b / a[0], a / a[0], seg, zi=zi)
        out[i * block:(i + 1) * block] = y
    return out


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def tone(freqs, dur, tau=None, harmonics=((1, 1.0),), sweep=None):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for f in np.atleast_1d(freqs):
        if sweep:
            fr = f * (sweep ** (tt / dur))
            ph = 2 * math.pi * np.cumsum(fr) / SR
        else:
            ph = 2 * math.pi * f * tt
        for h, g in harmonics:
            out += g * np.sin(ph * h)
    if tau:
        out *= exp_decay(n, tau)
    return out


# ---------------------------------------------------------------- one-shot sounds (mono)
def whoosh(dur=0.7, f0=250, f1=3200, peak=0.6):
    n = int(dur * SR)
    x = bandsweep(noise(n), f0, f1, q=0.9) * 2.2
    x += bandsweep(noise(n), f0 * 0.5, f1 * 0.4, q=0.6) * 1.2
    e = np.sin(np.linspace(0, math.pi, n)) ** 2.2
    e = e ** (1.0 / (0.6 + peak))
    return x * e * 0.5


def impact(gain=1.0, low=56):
    n = int(1.4 * SR)
    sub = tone(low * 2.2, 1.4, tau=0.32, sweep=0.38)
    click = highpass(noise(int(0.02 * SR)), 1800) * np.linspace(1, 0, int(0.02 * SR)) * 0.5
    body = lowpass(noise(n), 420) * exp_decay(n, 0.09) * 1.4
    x = sub * 0.9 + body
    x[:len(click)] += click
    return x * gain


def tick(f=2400, gain=0.35):
    return tone(f, 0.05, tau=0.008, harmonics=((1, 1), (2.01, 0.3))) * gain


def pop(f=880, gain=0.45):
    return tone(f, 0.22, tau=0.05, sweep=1.6, harmonics=((1, 1), (2, 0.25))) * gain


def chime(f=1320, gain=0.32):
    return tone([f, f * 1.5, f * 2.0], 1.6, tau=0.45, harmonics=((1, 1), (2.76, 0.18))) * gain / 2


def ignite(gain=0.6):
    n = int(0.75 * SR)
    x = bandsweep(noise(n), 160, 900, q=0.7) * 2.0
    x *= env_adsr(n, 0.04, 0.2, 0.4, 0.45)
    x += tone(70, 0.75, tau=0.15, sweep=0.6) * 0.6
    return x * gain


def drop_tone(dur=1.2, f0=620, f1=170, gain=0.28):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    fr = f0 * (f1 / f0) ** (tt / dur) * (1 + 0.02 * np.sin(2 * math.pi * 7 * tt))
    x = np.sin(2 * math.pi * np.cumsum(fr) / SR) + 0.3 * np.sin(4 * math.pi * np.cumsum(fr) / SR)
    return x * env_adsr(n, 0.05, 0.1, 0.8, 0.4) * gain


def rise_tone(dur=0.8, f0=180, f1=520, gain=0.22):
    return drop_tone(dur, f0, f1, gain)


def power_down(gain=0.18):
    return drop_tone(0.28, 520, 140, gain)


def buzz(gain=0.18):
    x = tone(110, 0.32, harmonics=((1, 1), (2, 0.5), (3, 0.35), (5, 0.2)))
    return lowpass(x, 1200) * env_adsr(len(x), 0.01, 0.05, 0.7, 0.15) * gain


def hiss(dur, gain=0.12):
    n = int(dur * SR)
    x = highpass(noise(n), 3500) * (0.8 + 0.2 * np.sin(np.arange(n) / SR * 2 * math.pi * 3.3))
    return x * env_adsr(n, 0.3, 0.1, 1.0, 0.5) * gain


def shimmer(dur=1.4, gain=0.2):
    n = int(dur * SR)
    x = np.zeros(n)
    for i in range(10):
        st = int(RNG.uniform(0, dur * 0.7) * SR)
        f = RNG.choice([1760, 2093, 2349, 2637, 3136])
        s = tone(f, 0.4, tau=0.12) * RNG.uniform(0.4, 1)
        x[st:st + len(s)] += s[:n - st]
    return x * gain


def rumble(dur, gain=0.3):
    n = int(dur * SR)
    x = lowpass(noise(n), 160, 4) * 3.0
    return x * env_adsr(n, 0.4, 0.2, 0.9, 0.6) * gain


def click_sfx(gain=0.6):
    n = int(0.06 * SR)
    return (highpass(noise(n), 2500) * exp_decay(n, 0.006) * 0.8 + tone(1800, 0.06, tau=0.01)) * gain


def strike(gain=0.4):
    return (whoosh(0.28, 900, 5000) * 1.2 + impact(0.35, 70)[:int(0.28 * SR)]) * gain


# ---------------------------------------------------------------- drone bed (stereo)
CHORDS = [  # per chapter: semitone offsets from A2 (110 Hz)
    (0, 3, 7), (-4, 0, 3), (-9, -5, -2), (-7, -3, 0), (0, 3, 7), (-4, 0, 3), (-2, 2, 5), (0, 3, 7)]


def drone(duration):
    n = int(duration * SR)
    tt = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)
    bounds = chapter_bounds()
    starts = [b[0] for b in bounds]
    for ci, chord in enumerate(CHORDS):
        s = max(0.0, starts[ci] - 0.6)
        e = starts[ci + 1] + 0.6 if ci + 1 < len(starts) else duration
        i0, i1 = int(s * SR), min(n, int(e * SR))
        seg_t = tt[i0:i1]
        m = len(seg_t)
        fade = np.minimum(1, np.minimum((seg_t - s) / 1.2, (e - seg_t) / 1.2)).clip(0, 1)
        for k, semi in enumerate(chord):
            f = 110 * 2 ** (semi / 12)
            for det, pan in ((-0.12, 0.2), (0.12, 0.8)):
                ph = 2 * math.pi * (f + det) * seg_t + k
                v = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
                v *= 0.7 + 0.3 * np.sin(2 * math.pi * (0.07 + 0.02 * k) * seg_t + ci)
                L[i0:i1] += v * fade * (1 - pan) * 0.16
                R[i0:i1] += v * fade * pan * 0.16
        root = 55 * 2 ** (chord[0] / 12)
        sub = np.sin(2 * math.pi * root * seg_t) * fade * 0.22
        L[i0:i1] += sub
        R[i0:i1] += sub
    air = lowpass(noise(n), 900, 2) * 0.05
    L, R = lowpass(L + air, 1400), lowpass(R + air[::-1], 1400)
    master = np.minimum(1, tt / 2.0) * np.minimum(1, (duration - tt) / 2.5).clip(0, 1)
    return np.stack([L * master, R * master])


# ---------------------------------------------------------------- cue sheet
def cues():
    c = []
    add = lambda t, snd, pan=0.0, send=0.3: c.append((t, snd, pan, send))
    ticks = lambda t0, dur, n, f=2400, g=0.22: [add(t0 + dur * (1 - (1 - i / n) ** 2), tick(f, g), 0, 0.1)
                                               for i in range(n)]
    # camera moves -> whooshes, length matched to the move
    for keys in (S.UZ_KEYS, S.WIDE_KEYS):
        for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
            dist = abs(math.log(c1.zoom / c0.zoom)) + math.hypot(c1.lon - c0.lon, c1.lat - c0.lat) / 4
            if dist > 0.35 and t0 > 0.5:
                d = min(t1 - t0, 2.2)
                add(t0 - 0.05, whoosh(min(1.6, d * 0.8), 200, 2600, 0.8) * 0.8, RNG.uniform(-0.4, 0.4), 0.35)
    # chapter starts: soft sub hit
    for s, _ in chapter_bounds()[1:]:
        add(s + 0.25, impact(0.45, 44), 0, 0.2)
    # ch1
    add(0.15, impact(0.5, 40), 0, 0.3)
    add(0.55, whoosh(2.2, 120, 1800, 0.4) * 0.9, -0.2, 0.4)
    add(T("a1", 0.25), ignite(0.55), 0.1)
    add(T("a1", 0.3), pop(980, 0.4), 0.1)
    add(T("a2", 0.1), ignite(0.55), -0.2)
    add(T("a2", 0.15), pop(1170, 0.4), -0.2)
    add(S.T_G2M, whoosh(0.7, 400, 4000) * 0.7, 0.3)
    add(T("a3"), whoosh(0.5, 500, 3000) * 0.5, 0)
    add(T("a3", 0.3), drop_tone(1.3, 640, 160, 0.26), 0)
    for i in range(5):
        add(T("a3", 0.62) + i * 0.08, pop(520 + i * 40, 0.22), -0.6 + i * 0.3)
    add(T("a4"), impact(0.55, 52), 0, 0.4)
    add(T("a4", 0.4), shimmer(1.4, 0.16), 0, 0.6)
    add(T("a5"), tick(1800, 0.3), 0)
    # ch2
    add(T("b1", 0.3), chime(990, 0.18), 0, 0.6)
    add(T("b1", 0.55), pop(880, 0.38), -0.2)
    add(T("b1", 0.6), ignite(0.4), -0.2)
    add(T("b2", 0.3), impact(0.7), 0)
    ticks(T("b2", 0.3), 0.85, 10)
    add(T("b2", 0.35), pop(1320, 0.28), 0.4)
    add(T("b4", 0.2), pop(660, 0.3), 0)
    add(T("b5"), impact(0.7), 0)
    ticks(T("b5"), 0.75, 14)
    add(T("b6"), whoosh(0.45, 600, 3500) * 0.45, 0.2)
    for i in range(16):
        add(T("b6", 0.15) + i * 0.07, tick(1500 + i * 60, 0.24), -0.5 + i / 16, 0.15)
    add(T("b6", 0.75), impact(0.55, 60), 0)
    add(T("b6", 0.78), chime(1568, 0.24), 0, 0.6)
    # ch3
    for i in range(len(S.FIELDS)):
        add(T("c1", 0.3) + i * 0.045, pop(700 + 25 * i, 0.12), RNG.uniform(-0.6, 0.6), 0.2)
    add(T("c2", 0.3), impact(0.8, 48), 0)
    ticks(T("c2", 0.3), 0.85, 12)
    for k in range(len(S.DEPLETED)):
        add(T("c2", 0.35) + k * 0.07, power_down(0.12), RNG.uniform(-0.6, 0.6), 0.2)
    add(T("c3"), whoosh(0.45, 600, 3500) * 0.45, -0.2)
    add(T("c3", 0.25), rise_tone(0.6, 220, 520, 0.2), -0.3)
    for i in range(3):
        add(T("c3", 0.7) + i * 0.18, rise_tone(0.4, 200, 380 - i * 30, 0.13), -0.1 + 0.15 * i)
    add(T("c4", 0.3), drop_tone(0.7, 320, 150, 0.22), 0.4)
    add(T("c5"), impact(0.45, 60), 0)
    add(T("c5", 0.05), chime(1175, 0.2), 0, 0.6)
    # ch4
    add(T("d1", 0.3), ignite(0.45), 0.2)
    add(T("d1", 0.35), pop(940, 0.34), 0.2)
    add(T("d1", 0.55), whoosh(0.45, 600, 3500) * 0.4, 0)
    add(T("d1", 0.6), tick(2000, 0.3), -0.2)
    add(T("d2", 0.2), tick(2200, 0.3), -0.2)
    add(T("d3", 0.35), impact(0.75, 46), 0)
    ticks(T("d3", 0.35), 0.8, 10)
    add(T("d3", 0.4), rise_tone(0.7, 260, 520, 0.18), -0.3)
    add(T("d4", 0.15), drop_tone(1.1, 300, 120, 0.26), 0.3)
    add(T("d5", 0.3), impact(0.6, 58), 0)
    add(T("d5", 0.32), chime(1046, 0.24), 0, 0.6)
    # ch5
    add(T("e1", 0.25), impact(0.6), 0)
    ticks(T("e1", 0.25), 1.2, 16, 2600, 0.16)
    add(T("e1", 0.1), shimmer(3.6, 0.14), 0, 0.7)
    add(T("e2", 0.3), pop(1240, 0.32), -0.3)
    add(T("e3"), whoosh(0.45, 600, 3500) * 0.4, 0.2)
    for k, fr in enumerate((0.0, 0.17, 0.36, 0.62)):
        add(T("e3", fr), pop(780 + 120 * k, 0.32), -0.6 + 0.4 * k)
    add(T("e3", 0.78), rumble(1.2, 0.28), 0)
    add(T("e3", 0.8), ignite(0.5), 0)
    add(T("e4"), whoosh(0.45, 600, 3500) * 0.4, -0.2)
    for i in range(5):
        tt = T("e4", 0.1) + i * 0.32
        add(tt, chime(1318 + 110 * i, 0.16) if i < 3 else buzz(0.16), -0.3 + 0.15 * i, 0.4 if i < 3 else 0.1)
    # ch6
    add(T("f1", 0.1), shimmer(1.6, 0.12), 0, 0.6)
    add(T("f1", 0.1), rise_tone(1.6, 150, 300, 0.12), 0)
    add(T("f1", 0.6), hiss(TE("f4") - T("f1", 0.6) + 0.6, 0.045), 0.2, 0.3)
    for j in range(7):
        add(T("f1", 0.6) + j * 0.22, pop(420 + 30 * j, 0.14), RNG.uniform(-0.6, 0.6), 0.2)
    add(T("f2", 0.45), impact(0.75, 48), 0)
    ticks(T("f2", 0.45), 0.85, 10)
    add(T("f3"), impact(0.65), 0)
    ticks(T("f3"), 0.75, 14)
    add(T("f4"), whoosh(0.45, 600, 3500) * 0.4, 0.2)
    add(T("f4", 0.2), rise_tone(1.2, 200, 420, 0.18), 0)
    # ch7
    add(S.T_WIDE_IN, whoosh(1.1, 150, 2200, 0.5) * 0.9, -0.3, 0.4)
    add(T("g1", 0.45), strike(0.45), 0.2)
    add(T("g1", 0.6), impact(0.6, 52), 0)
    add(T("g2", 0.05), rumble(2.6, 0.32), -0.2)
    add(T("g2", 0.05), rise_tone(2.4, 160, 260, 0.1), -0.2)
    add(T("g2", 0.6), pop(860, 0.32), -0.3)
    add(T("g2", 0.9), pop(1020, 0.32), 0.3)
    add(T("g3"), impact(0.6), 0)
    ticks(T("g3"), 0.85, 10)
    add(T("g4", 0.3), impact(0.7, 50), 0)
    ticks(T("g4", 0.3), 0.85, 14)
    add(T("g4", 0.35), chime(1568, 0.2), 0.3, 0.6)
    add(T("g5", 0.1), buzz(0.18), 0)
    add(T("g5", 0.12), pop(700, 0.3), 0)
    # ch8
    add(S.T_WIDE_OUT, whoosh(1.0, 2000, 200, 0.5) * 0.8, 0.3, 0.4)
    add(T("h1", 0.2), impact(0.45, 56), 0)
    add(T("h2", 0.15), impact(0.55, 46), 0)
    add(T("h2", 0.15), shimmer(1.2, 0.14), 0, 0.6)
    add(T("h3", 0.3), pop(700, 0.3), -0.3)
    add(T("h3", 0.45), strike(0.4), -0.3)
    add(T("h3", 0.65), impact(0.6, 50), 0.2)
    ticks(T("h3", 0.65), 0.9, 12, 2000)
    add(T("h4") - 0.1, rise_tone(0.8, 200, 400, 0.1), 0)
    add(T("h4", 0.4), impact(0.6, 44), 0)
    add(T("h4", 0.4), shimmer(1.6, 0.16), 0, 0.7)
    add(T("h5"), whoosh(0.6, 500, 3500) * 0.5, 0)
    add(T("h5") + 0.3, pop(990, 0.35), 0)
    add(T("h5") + 1.2, whoosh(0.9, 1200, 3000, 0.2) * 0.25, 0.4)
    add(T("h5") + 2.3, click_sfx(0.6), 0.2)
    add(T("h5") + 2.34, chime(1760, 0.26), 0.2, 0.6)
    return c


def build():
    n = int((DURATION + 0.5) * SR)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))
    for t, snd, pan, send in cues():
        i0 = int(max(0, t) * SR)
        if i0 >= n:
            continue
        m = min(len(snd), n - i0)
        gl, gr = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        for ch, g in ((0, gl), (1, gr)):
            dry[ch, i0:i0 + m] += snd[:m] * g * math.sqrt(2) * (1 - send * 0.5)
            wet[ch, i0:i0 + m] += snd[:m] * g * math.sqrt(2) * send
    verb = pb.Pedalboard([pb.Reverb(room_size=0.82, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])
    wet = verb(wet.astype(np.float32), SR)
    bed = drone(n / SR)
    mix = dry + wet * 0.9 + bed * 0.22
    chain = pb.Pedalboard([pb.HighpassFilter(28), pb.Compressor(threshold_db=-18, ratio=2.5, attack_ms=8,
                                                                 release_ms=180), pb.Limiter(threshold_db=-3)])
    mix = chain(mix.astype(np.float32), SR)
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix.T)
    mix = mix * 10 ** ((TARGET_LUFS - lufs) / 20)
    peak = np.abs(mix).max()
    if 20 * math.log10(peak) > PEAK_DB:
        mix *= 10 ** (PEAK_DB / 20) / peak
    print(f"sfx: {lufs:.1f} LUFS -> {meter.integrated_loudness(mix.T):.1f} LUFS, "
          f"peak {20 * math.log10(np.abs(mix).max()):.1f} dBFS")
    os.makedirs(OUT, exist_ok=True)
    import wave
    pcm = (np.clip(mix.T, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, "sfx.wav"), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


if __name__ == "__main__":
    build()
