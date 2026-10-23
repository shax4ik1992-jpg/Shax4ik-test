"""Write the voice-over script (Latin + Cyrillic, with timecodes) and SRT subtitles from timeline.py.

  python3 export_script.py -> SSENARIY.md, output/subtitr_lotin.srt, output/subtitr_kirill.srt
"""
import os
import re

import timeline as TL

ROOT = os.path.dirname(os.path.abspath(__file__))

SPECIAL = {
    "stansiyalar": "станциялар", "stansiyalariga": "станцияларига", "stansiyalari": "станциялари",
    "sentabrda": "сентябрда", "sentabr": "сентябрь",
}
PAIRS = [("o‘", "ў"), ("g‘", "ғ"), ("O‘", "Ў"), ("G‘", "Ғ"), ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
         ("ch", "ч"), ("Ch", "Ч"), ("yo", "ё"), ("Yo", "Ё"), ("yu", "ю"), ("Yu", "Ю"), ("ya", "я"), ("Ya", "Я"),
         ("ye", "е"), ("Ye", "Е"), ("’", "ъ")]
SINGLE = dict(zip("abdefghijklmnopqrstuvxyzABDEFGHIJKLMNOPQRSTUVXYZ",
                  "абдефгҳижклмнопқрстувхйзАБДЕФГҲИЖКЛМНОПҚРСТУВХЙЗ"))


SOURCES = [
    ("Patron koni: 2,5 mlrd m³ zaxira, Mirishkor, 3 296–3 339 m, 500 ming m³/kun (7.09.2026)",
     "https://interfax.com/newsroom/top-stories/119006/"),
    ("Patron koni (o‘zbekcha)", "https://anhor.uz/uz/news/qashqadaryoda-2-5-mlrd-kub-metr-zaxirali-yangi-gaz-koni-topildi"),
    ("Kunlik iste’mol ~154 mln m³, tanqislik 6 mln m³/kun (vazir, 11.12.2025)",
     "https://caliber.az/en/post/minister-uzbekistan-faces-daily-gas-shortage-of-six-million-cubic-metres"),
    ("Qishki ustuvorlik: aholi, ijtimoiy obyektlar, IES; mavsumiy iste’molchilar uziladi",
     "https://www.uzdaily.uz/en/gas-deficit-of-6-million-cubic-meters-causes-temporary-restrictions-at-cng-filling-stations/"),
    ("Konlarning 85% qurib bormoqda; Mo‘ynoq: 2 quduq ~3 mln m³/kun (16.12.2025)",
     "https://kun.uz/en/news/2025/12/16/uzbekistan-steps-up-exploration-to-steady-gas-production-trend"),
    ("Qazib olish: 2019 — 60,7; 2022 — 51,67; 2023 — 46,71; 2024 — 44,59 mlrd m³",
     "https://kun.uz/en/news/2025/03/27/uzbekistans-gas-and-electricity-output-declines-as-production-struggles-continue"),
    ("2025-yil: 42,3 mlrd m³ (dastlabki)",
     "https://daryo.uz/en/2026/01/25/uzbekistan-produces-423bn-cubic-meters-of-natural-gas-in-2025/"),
    ("2026 I chorak: 9,6 vs 11,3 mlrd m³ (−15%); import $360,5 mln (×2,2)",
     "https://kun.uz/en/news/2026/05/07/uzbekistans-natural-gas-production-falls-by-15-in-first-quarter"),
    ("Aholi 38,38 mln (1.04.2026), +684,9 ming / yil",
     "https://kun.uz/en/news/2026/04/16/uzbekistans-population-nears-384-million-with-18-annual-growth"),
    ("Tarmoqdagi yo‘qotish: 2026 I yarim yil 7,6% = 797 mln m³",
     "https://kun.uz/en/news/2026/07/22/uzbekistan-needs-8-billion-to-modernize-energy-infrastructure-shavkat-mirziyoyev"),
    ("Rossiya gazi: 2024 — 5,64; 2025 — 6,48 mlrd m³ (Gazprom hisoboti)",
     "https://kun.uz/en/news/2026/06/09/gazprom-increased-gas-supplies-to-uzbekistan-by-15-percent-in-2025-ae0af1"),
    ("2030 rejasi 62 → 48,5 mlrd m³",
     "https://www.kun.uz/en/news/2026/02/18/uzbekistan-revises-2030-gas-production-target-to-485-billion-cubic-meters"),
]
CALC = [
    "2 500 mln m³ ÷ 154 mln m³/kun ≈ 16 kun",
    "60,7 → 42,3 mlrd m³ = −30% (deyarli uchdan biri)",
    "11,3 − 9,6 = 1,7 mlrd m³ / 90 kun ≈ 19 mln m³/kun; yangi quduqlar 3 + 0,5 = 3,5 → ~5 barobar",
    "797 ÷ 2 500 ≈ 32% ≈ uchdan bir",
]


def to_cyrillic(text):
    def word(w):
        low = w.lower()
        if low in SPECIAL:
            c = SPECIAL[low]
            return c.capitalize() if w[0].isupper() else c
        out = w
        for a, b in PAIRS:
            out = out.replace(a, b)
        res = []
        for i, ch in enumerate(out):
            if ch in "eE" and (i == 0 or not out[i - 1].isalpha()):
                res.append("э" if ch == "e" else "Э")
            else:
                res.append(SINGLE.get(ch, ch))
        return "".join(res)
    return re.sub(r"[A-Za-z‘’ʻ]+", lambda m: word(m.group(0)), text)


def plain(s):
    for m in "*^~":
        s = s.replace(m, "")
    return s


def srt_time(s):
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(r):02d},{int(round((r - int(r)) * 1000)):03d}"


def main():
    rows = []
    for l in TL.LINES:
        rows.append((l, plain(l["text"]), to_cyrillic(plain(l["text"]))))
    md = ["# Ssenariy / Сценарий — «O‘zbekistonda gaz ko‘p topilyapti, lekin yetmayapti»", "",
          f"Davomiyligi: **{TL.fmt_tc(TL.DURATION)}** · 1080×1920 · 30 fps", "",
          "Ovoz yozishda har bir qatorni ko‘rsatilgan vaqtda boshlang (taxminiy temp: "
          f"{TL.C.CHARS_PER_SEC:.0f} belgi/sek). Ovoz tayyor bo‘lgach, vaqtlarni `voice_times.json` ga yozib, "
          "videoni qayta render qilish mumkin — subtitr va effektlar ovozga avtomatik moslashadi.", ""]
    ch = -1
    for l, lat, cyr in rows:
        if l["ch"] != ch:
            ch = l["ch"]
            num, name = TL.CHAPTERS[ch]
            md += ["", f"## {num} · {name}", "", "| Vaqt | Lotin | Кирилл |", "|---|---|---|"]
        md.append(f"| `{TL.fmt_tc(l['start'])}` | {lat} | {cyr} |")
    md += ["", "---", "", "## Butun matn (o‘qish uchun) / Тўлиқ матн", ""]
    ch = -1
    for l, lat, cyr in rows:
        if l["ch"] != ch:
            ch = l["ch"]
            md.append("")
        md.append(cyr)
    md += ["", "---", "", "## Hisob-kitoblar", ""] + [f"- {x}" for x in CALC]
    md += ["", "## Manbalar", ""] + [f"- [{t}]({u})" for t, u in SOURCES]
    md += ["", "_Kon belgilari, quvur tarmog‘i va import yo‘nalishi videoda sxematik ko‘rsatilgan._"]
    with open(os.path.join(ROOT, "SSENARIY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    for name, idx in (("subtitr_lotin.srt", 1), ("subtitr_kirill.srt", 2)):
        out = []
        for i, r in enumerate(rows):
            l = r[0]
            out += [str(i + 1), f"{srt_time(l['start'])} --> {srt_time(l['start'] + l['dur'])}", r[idx], ""]
        with open(os.path.join(ROOT, "output", name), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
    print("SSENARIY.md + SRT written")


if __name__ == "__main__":
    main()
