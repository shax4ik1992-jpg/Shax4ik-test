"""Voice-over script = single source of truth for timing.

Every visual and sound cue is anchored to a line id (T("b2") -> start time of line b2),
so re-timing to a real recording only means filling `VOICE_TIMES` (line id -> start sec).
Markup inside text: *cyan*  ^gold^  ~red~
"""
import json
import os

import config as C

CHAPTERS = [
    ("01", "SAVOL"),
    ("02", "YANGI KON"),
    ("03", "ESKI KONLAR"),
    ("04", "BALANS"),
    ("05", "ISTE'MOL"),
    ("06", "QUVURLAR"),
    ("07", "IMPORT"),
    ("08", "XULOSA"),
]

# (id, chapter index, text)
SCRIPT = [
    ("a1", 0, "Yangi *gaz koni* topildi."),
    ("a2", 0, "Yana bittasi."),
    ("a3", 0, "Lekin qish kelsa — uyda gaz ~bosimi tushadi,~ zapravkada ~navbat.~"),
    ("a4", 0, "Gaz topilyapti-yu, ^nega yetmayapti?^"),
    ("a5", 0, "Keling, *raqamlar* bilan tekshiramiz."),

    ("b1", 1, "Sentabrda Qashqadaryoda ^«Patron»^ degan yangi kon topildi."),
    ("b2", 1, "Zaxirasi — taxminan *2,5 milliard* kub metr."),
    ("b3", 1, "Ko‘p tuyuladi."),
    ("b4", 1, "Lekin qishda mamlakat bir kunda qancha gaz sarflaydi?"),
    ("b5", 1, "Taxminan *154 million* kub."),
    ("b6", 1, "Demak, bu kon butun O‘zbekistonga atigi ^16 kunga^ yetadi."),

    ("c1", 2, "Gap shundaki, eski konlar ~tugayapti.~"),
    ("c2", 2, "Energetika vaziri aytishicha, konlarning ~85 foizi~ qurib bormoqda."),
    ("c3", 2, "2019-yilda *60 milliard* kubdan ko‘p gaz qazib olingan."),
    ("c4", 2, "2025-yilda esa — atigi ~42 milliard.~"),
    ("c5", 2, "Olti yilda deyarli ^uchdan biri^ yo‘qoldi."),

    ("d1", 3, "Yangi konlar ham bor: ^Mo‘ynoqdagi^ ikki quduq kuniga *3 million* kub beryapti."),
    ("d2", 3, "^Patron^ qudug‘i — yana *yarim million.*"),
    ("d3", 3, "Ammo 2026-yil birinchi chorakda qazib olish ~15 foizga~ tushdi."),
    ("d4", 3, "Bu kuniga taxminan ~19 million~ kub kam degani."),
    ("d5", 3, "Ya’ni topganimizdan ^besh barobar^ ko‘p yo‘qotyapmiz."),

    ("e1", 4, "Bu orada aholi *38 milliondan* oshdi"),
    ("e2", 4, "va har yili yana ^685 ming^ kishiga ko‘payyapti."),
    ("e3", 4, "Uylar, zavodlar, metan mashinalar, elektr stansiyalar — hammasi *shu gazda.*"),
    ("e4", 4, "Qishda gaz avval ^aholiga^ va ^elektr stansiyalariga^ beriladi."),

    ("f1", 5, "Yana bir teshik — ~quvurlar.~"),
    ("f2", 5, "2026-yilning birinchi yarmida tarmoqlarda ~7,6 foiz~ gaz yo‘qolgan."),
    ("f3", 5, "Bu *797 million* kub —"),
    ("f4", 5, "Patron konining ^uchdan biri^ — olti oyda."),

    ("g1", 6, "Natijada, gaz sotgan O‘zbekiston endi gaz ~sotib olyapti.~"),
    ("g2", 6, "2023-yildan beri — ^Rossiyadan,^ ^Qozog‘iston^ orqali."),
    ("g3", 6, "2025-yilda *6,5 milliard* kub olindi."),
    ("g4", 6, "2026-yil birinchi chorakda importga *360 million dollar* ketdi —"),
    ("g5", 6, "o‘tgan yilgidan ~2,2 barobar~ ko‘p."),

    ("h1", 7, "Demak, gaz topilmayapti emas."),
    ("h2", 7, "Topilgani — ~tugayotganini~ qoplamayapti."),
    ("h3", 7, "Hukumat ham 2030-yil rejasini *62* dan *48,5* milliard kubga tushirdi."),
    ("h4", 7, "Endi savol: qancha topamiz emas — ^qanchasini isrof qilmaymiz?^"),
    ("h5", 7, "Bunday hisob-kitoblarni o‘tkazib yubormang — *obuna bo‘ling.*"),
]

# Fill after recording: {"a1": 0.42, "a2": 2.10, ...} or place voice_times.json next to this file.
VOICE_TIMES = {}
_vt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_times.json")
if os.path.exists(_vt):
    with open(_vt, encoding="utf-8") as _f:
        VOICE_TIMES.update(json.load(_f))


def _plain(text):
    for m in "*^~":
        text = text.replace(m, "")
    return text


def _speak_dur(text):
    s = _plain(text)
    pauses = s.count(",") * 0.12 + s.count("—") * 0.18 + s.count(":") * 0.15
    return max(0.9, len(s) / C.CHARS_PER_SEC + pauses)


def build():
    lines, t, prev_ch = [], C.LEAD_IN, 0
    for lid, ch, text in SCRIPT:
        if ch != prev_ch:
            t += C.GAP_CHAPTER - C.GAP_LINE
            prev_ch = ch
        start = VOICE_TIMES.get(lid, t)
        dur = _speak_dur(text)
        lines.append({"id": lid, "ch": ch, "text": text, "start": start, "dur": dur})
        t = start + dur + C.GAP_LINE
    # if real times are given, durations run up to the next line's start
    for i in range(len(lines) - 1):
        if lines[i]["id"] in VOICE_TIMES and lines[i + 1]["id"] in VOICE_TIMES:
            lines[i]["dur"] = max(0.6, lines[i + 1]["start"] - lines[i]["start"] - 0.1)
    return lines


LINES = build()
BY_ID = {l["id"]: l for l in LINES}
END_CARD = 3.6
DURATION = LINES[-1]["start"] + LINES[-1]["dur"] + END_CARD


def T(lid, frac=0.0):
    """Start time of a line, optionally offset by a fraction of its duration."""
    l = BY_ID[lid]
    return l["start"] + frac * l["dur"]


def TE(lid):
    l = BY_ID[lid]
    return l["start"] + l["dur"]


def chapter_bounds():
    out = []
    for i in range(len(CHAPTERS)):
        ls = [l for l in LINES if l["ch"] == i]
        out.append((ls[0]["start"] - 0.3, ls[-1]["start"] + ls[-1]["dur"] + 0.3))
    return out


def chapter_at(t):
    b = chapter_bounds()
    idx = 0
    for i, (s, e) in enumerate(b):
        if t >= s:
            idx = i
    s, e = b[idx]
    nxt = b[idx + 1][0] if idx + 1 < len(b) else DURATION
    return idx, max(0.0, min(1.0, (t - s) / max(0.1, nxt - s)))


def caption_chunks(max_chars=23, max_words=4):
    """Split each line into on-screen chunks with per-word light-up times."""
    import gfx
    chunks = []
    for l in LINES:
        words = gfx.parse_marks(l["text"])
        groups, cur = [], []
        for w in words:
            cand = " ".join(x for x, _ in cur + [w])
            if cur and (len(cand) > max_chars or len(cur) >= max_words):
                groups.append(cur)
                cur = []
            cur.append(w)
            if w[0].endswith(("—", ",", ".", "?", ":")) and len(" ".join(x for x, _ in cur)) > 10:
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        # dash-only chunk: glue to neighbour
        merged = []
        for g in groups:
            if merged and (len(g) == 1 and len(g[0][0]) <= 2):
                merged[-1] += g
            else:
                merged.append(g)
        total_chars = sum(len(w) + 1 for w, _ in words)
        t = l["start"]
        per = l["dur"] / max(1, total_chars)
        for g in merged:
            ws, gs = [], t
            for w, m in g:
                ws.append((w, m, t))
                t += (len(w) + 1) * per
            chunks.append({"words": ws, "start": gs, "end": t, "line": l["id"]})
    # each chunk stays until the next one starts (or a short hold after its line ends)
    for i, ch in enumerate(chunks):
        nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else ch["end"] + 0.6
        ch["end"] = min(nxt, ch["end"] + 0.9) if nxt - ch["end"] > 1.2 else nxt
    return chunks


def fmt_tc(s):
    m, s = divmod(s, 60)
    return f"{int(m):02d}:{s:05.2f}"


if __name__ == "__main__":
    for l in LINES:
        print(f"{fmt_tc(l['start'])}  +{l['dur']:.1f}s  [{CHAPTERS[l['ch']][1]}] {_plain(l['text'])}")
    print("DURATION", round(DURATION, 2))
