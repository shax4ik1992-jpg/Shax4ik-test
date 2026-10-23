# Gaz videosi — «O‘zbekistonda gaz ko‘p topilyapti, lekin aholiga yetmayapti»

Vertikal (1080×1920, 30 fps, ~2:09) infografik video: 3D relyef xaritalar, globus, HUD, katta raqamlar,
so‘zma-so‘z subtitrlar va **past ovozdagi** effektlar (ovoz yozuvi yo‘q — uni siz yozasiz).

## Tayyor fayllar (`output/`; mp4/wav gitda saqlanmaydi — `render.py` bilan yaratiladi)

| Fayl | Nima |
|---|---|
| `gaz_matnli.mp4` | Subtitrli versiya + effektlar (-26 LUFS) |
| `gaz_toza.mp4` | Subtitrsiz versiya + effektlar — CapCut/Premiere'da o‘zingiz subtitr qo‘shish uchun |
| `sfx.wav` | Faqat effektlar treki (alohida miks qilish uchun) |
| `subtitr_lotin.srt`, `subtitr_kirill.srt` | Ssenariy qatorlari vaqt bilan |
| `../SSENARIY.md` | Ovoz yozish uchun matn: vaqt kodlari, lotin + kirill |

## Ovoz yozish

1. `SSENARIY.md` dagi matnni vaqt kodlariga yaqin tempda o‘qing (taxminan 16 belgi/sek).
2. Montajda ovozni **-14 LUFS** atrofida qo‘ying — effektlar -26 LUFS, ya’ni ovozdan ~12 dB past.
3. Ovoz vaqtlari farq qilsa: har bir qator boshlanish vaqtini `voice_times.json` ga yozing
   (`{"a1": 0.42, "a2": 2.05, ...}`) va qayta render qiling — subtitrlar, animatsiyalar va effektlar
   o‘zi moslashadi.

## Qayta render qilish

```bash
pip install -r requirements.txt          # + ffmpeg kerak
python3 fetch_data.py                    # relyef, chegaralar, shriftlar (~150 MB)
python3 textures.py                      # relyef teksturalari
python3 sfx.py                           # effektlar -> output/sfx.wav
python3 render.py                        # video -> output/*_video.mp4
python3 mux.py                           # video + sfx -> output/gaz_matnli.mp4, gaz_toza.mp4
python3 export_script.py                 # SSENARIY.md + SRT
python3 render.py --stills 12.5 40       # tezkor ko‘rib chiqish kadrlari
```

Brending: `config.py` (`SERIES`, `HANDLE`, `CHANNEL_NAME`). Matn va vaqt: `timeline.py`.
Vizual sahnalar: `scenes.py`. Effektlar: `sfx.py`.

## Ishlatilgan ochiq manbalar (GitHub)

- [tilezen/joerd](https://github.com/tilezen/joerd) — AWS Terrain Tiles (Terrarium) relyef ma’lumotlari
- [nvkelso/natural-earth-vector](https://github.com/nvkelso/natural-earth-vector) — chegaralar, ko‘llar, daryolar
- [google/fonts](https://github.com/google/fonts) — Inter, Unbounded, JetBrains Mono, Instrument Serif (OFL)
- [kyamagu/skia-python](https://github.com/kyamagu/skia-python) — vektor grafika
- [opencv/opencv-python](https://github.com/opencv/opencv-python) — 3D perspektiva (warp)
- [spotify/pedalboard](https://github.com/spotify/pedalboard) — effektlar uchun reverb/kompressor
- [csteinmetz1/pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) — LUFS normalizatsiya
- FFmpeg — kodlash

Barcha effektlar kod bilan sintez qilingan (sample yo‘q) — mualliflik huquqi muammosi yo‘q.

## Faktlar manbalari

Ssenariydagi har bir raqam manbasi — `SSENARIY.md` oxirida. Kon belgilari, quvur tarmog‘i va
import yo‘nalishi **sxematik** (ekranda ham shunday yozilgan).
