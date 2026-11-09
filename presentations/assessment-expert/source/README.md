# Сборка презентации

1. `python3 make_bg.py assets/dark_bg.jpg` — фон тёмных слайдов.
2. `PPTX_SKILL=<путь к pptx-skill> NODE_PATH=<node_modules с pptxgenjs> node build_deck.js raw.pptx anim_plan.json` — слайды, графики, заметки докладчика.
3. `python3 animate.py raw.pptx anim_plan.json Assessment_Expert_Mukhlisa_Qarabayeva.pptx` — переходы и анимации появления.

Зависимости: pptxgenjs, react-icons, react, react-dom, sharp (npm); lxml, numpy, Pillow (pip).
