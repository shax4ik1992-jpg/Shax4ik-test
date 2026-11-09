// Premium "Become an Assessment Expert" deck — pptxgenjs generator.
// Animations are registered here (objectName -> effect) and injected by animate.py.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const SKILL = process.env.PPTX_SKILL;
const { applyTheme } = require(path.join(SKILL, "scripts/apply_theme.js"));
const OUT = process.argv[2] || "deck.pptx";
const PLAN = process.argv[3] || "anim_plan.json";
const BG = path.join(__dirname, "assets/dark_bg.jpg");

// ---------- Theme ----------
const THEME = {
  name: "Assessment Expert",
  headFontFace: "Georgia",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0E1626", lt1: "FFFFFF", dk2: "17233A", lt2: "F7F7F5",
    accent1: "C29B5F", accent2: "3E7A68", accent3: "A4503C",
    accent4: "5B6B82", accent5: "E3CB9B", accent6: "8A94A6",
    hlink: "8F6B38", folHlink: "5B6B82",
  },
};
const HEAD = "Georgia", BODY = "Calibri";
const K = {
  ink: "0E1626", surf: "17233A", edge: "26354F", paper: "F7F7F5", white: "FFFFFF",
  gold: "C29B5F", goldD: "8F6B38", goldL: "E3CB9B",
  sage: "3E7A68", sageL: "7CC0A8", sageT: "E3EFEA",
  brick: "A4503C", brickL: "E08C74", brickT: "F6E7E2",
  slate: "5B6B82", muted: "5E6675", mist: "A3AEC2", cloud: "D3DAE5",
  line: "E4E4DF", chip: "EFEFEB", foot: "8A8F99",
};
const W = 13.333, X0 = 0.75, CW = 11.83;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.title = "Become an Assessment Expert";
pres.author = "Mukhlisa Qarabayeva";
pres.subject = "Principles of effective English language assessment";
const S = pres.shapes;

// ---------- Animation registry ----------
const ANIM = {};
let slideNo = 0, objN = 0;
const DUR = { fade: 600, float: 750, zoom: 550, wipe: 800 };
function aoPh(type, fx, delay, dur) {
  (ANIM[slideNo] = ANIM[slideNo] || []).push({ name: "ph:" + type, fx, delay, dur: dur || DUR[fx] });
  return {};
}
function ao(fx, delay, dur) {
  const name = `obj_${slideNo}_${++objN}`;
  if (fx) (ANIM[slideNo] = ANIM[slideNo] || []).push({ name, fx, delay, dur: dur || DUR[fx] });
  return { objectName: name };
}

// ---------- Icons ----------
const iconCache = {};
async function icon(name, hex, sw = 1.6) {
  const key = `${name}-${hex}-${sw}`;
  if (iconCache[key]) return iconCache[key];
  let svg = RDS.renderToStaticMarkup(React.createElement(lu[name], { size: 256 }));
  svg = svg.replace(/currentColor/g, "#" + hex).replace(/stroke-width="[\d.]+"/g, `stroke-width="${sw}"`);
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return (iconCache[key] = "image/png;base64," + buf.toString("base64"));
}

// ---------- Primitives ----------
const shadow = () => ({ type: "outer", color: "0E1626", opacity: 0.08, blur: 16, offset: 3, angle: 90 });
function T(s, text, x, y, w, h, o = {}, a = {}) {
  const opts = {
    x, y, w, h, margin: 0, isTextBox: true,
    fontFace: o.font || BODY, fontSize: o.size || 15, color: o.color || K.muted,
    align: o.align || "left", valign: o.valign || "top", ...a,
  };
  if (o.bold) opts.bold = true;
  if (o.italic) opts.italic = true;
  if (o.cs) opts.charSpacing = o.cs;
  if (o.lsm) opts.lineSpacingMultiple = o.lsm;
  if (o.psa) opts.paraSpaceAfter = o.psa;
  s.addText(text, opts);
}
function box(s, x, y, w, h, o = {}, a = {}) {
  const opts = { x, y, w, h, rectRadius: o.r ?? 0.12, fill: { color: o.fill || K.white } };
  opts.line = o.line ? { color: o.line, width: o.lw || 0.75 } : { type: "none" };
  if (o.shadow) opts.shadow = shadow();
  s.addShape(o.r === 0 ? S.RECTANGLE : S.ROUNDED_RECTANGLE, { ...opts, ...a });
}
async function badge(s, x, y, d, ic, circle, glyph, fx, delay, ring) {
  const o = { x, y, w: d, h: d, fill: { color: circle } };
  o.line = ring ? { color: ring, width: 0.75 } : { type: "none" };
  s.addShape(S.OVAL, { ...o, ...ao(fx, delay) });
  const g = d * 0.5;
  s.addImage({ data: await icon(ic, glyph), x: x + (d - g) / 2, y: y + (d - g) / 2, w: g, h: g, altText: ic.replace(/^Lu/, "") + " icon", ...ao(fx, delay) });
}
function eyebrow(s, t) { s.addText(t, { placeholder: "eyebrow", charSpacing: 3 }); }
function title(s, t) { s.addText(t, { placeholder: "title" }); }
function sub(s, t) { s.addText(t, { placeholder: "sub" }); }
function chips(s, items, x, y, h, o = {}) {
  let cx = x;
  for (const it of items) {
    box(s, cx, y, it.w, h, { fill: it.fill || K.chip, r: h / 2, line: it.line }, ao(o.fx, o.delay));
    T(s, it.t, cx, y, it.w, h, { size: o.size || 12.5, color: it.color || K.ink, align: "center", valign: "middle", bold: it.bold }, ao(o.fx, o.delay));
    cx += it.w + (o.gap ?? 0.12);
  }
}
async function callout(s, y, ic, runs, delay, h = 0.82) {
  box(s, X0, y, CW, h, { fill: K.ink, r: 0.1 }, ao("float", delay));
  s.addImage({ data: await icon(ic, K.gold), x: X0 + 0.38, y: y + (h - 0.36) / 2, w: 0.36, h: 0.36, altText: "icon", ...ao("float", delay) });
  T(s, runs, X0 + 1.0, y, CW - 1.3, h, { size: 17, color: K.white, valign: "middle" }, ao("float", delay));
}
function rings(s, cx, cy, base) {
  const rr = [[0.78, 0], [1.38, 22], [1.98, 42], [2.58, 60], [3.18, 74]];
  rr.forEach(([r, tr], i) =>
    s.addShape(S.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color: K.gold, width: 1, transparency: tr }, ...ao("zoom", base + i * 140, 900) }));
  s.addShape(S.OVAL, { x: cx - 0.13, y: cy - 0.13, w: 0.26, h: 0.26, fill: { color: K.gold }, line: { type: "none" }, ...ao("zoom", base - 100, 500) });
}

// ---------- Layouts ----------
const FOOT = "BECOME AN ASSESSMENT EXPERT   ·   MUKHLISA QARABAYEVA";
function layout(name, dark) {
  pres.defineSlideMaster({
    title: name,
    background: dark ? { path: BG } : { color: K.paper },
    objects: [
      { text: { text: FOOT, options: { x: X0, y: 6.93, w: 8, h: 0.3, margin: 0, fontFace: BODY, fontSize: 10, charSpacing: 1.5, color: dark ? "6F7A8F" : K.foot, valign: "middle" } } },
      { placeholder: { options: { name: "eyebrow", type: "body", x: X0, y: 0.55, w: 10, h: 0.3, margin: 0, fontFace: BODY, fontSize: 11, bold: true, color: dark ? K.gold : K.goldD, valign: "middle", align: "left" }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.88, w: CW, h: 0.75, margin: 0, fontFace: HEAD, fontSize: 32, color: dark ? K.white : K.ink, valign: "middle", align: "left" }, text: "" } },
      { placeholder: { options: { name: "sub", type: "body", x: X0, y: 1.66, w: CW, h: 0.42, margin: 0, fontFace: BODY, fontSize: 16, color: dark ? K.mist : K.muted, valign: "middle", align: "left" }, text: "" } },
    ],
    slideNumber: { x: 11.83, y: 6.93, w: 0.75, h: 0.3, margin: 0, fontFace: BODY, fontSize: 10, color: dark ? "6F7A8F" : K.foot, align: "right", valign: "middle" },
  });
}
layout("LIGHT", false);
layout("DARK", true);
pres.defineSlideMaster({
  title: "COVER", background: { path: BG },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: X0, y: 1.5, w: 8.4, h: 2.2, margin: 0, fontFace: HEAD, fontSize: 52, color: K.white, valign: "bottom", align: "left" }, text: "" } }],
});
pres.defineSlideMaster({
  title: "CLOSING", background: { path: BG },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: X0, y: 4.3, w: 8.4, h: 1.05, margin: 0, fontFace: HEAD, fontSize: 56, color: K.gold, valign: "middle", align: "left" }, text: "" } }],
});

function newSlide(master, section) {
  if (section) pres.addSection({ title: section });
  slideNo++; objN = 0;
  return pres.addSlide({ masterName: master, sectionTitle: currentSection(section) });
}
let _sec = null;
function currentSection(s) { if (s) _sec = s; return _sec; }

const chartFont = { catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY, dataLabelFontFace: BODY, legendFontFace: BODY, titleFontFace: HEAD };

(async () => {
  let s;

  // ===== 1. COVER =====
  s = newSlide("COVER", "Introduction");
  rings(s, 10.95, 3.75, 250);
  s.addText([
    { text: "Become an", options: { breakLine: true } },
    { text: "Assessment Expert", options: { color: K.gold } },
  ], { placeholder: "title", ...aoPh("title", "float", 450, 900) });
  T(s, "Principles of effective English language assessment", X0, 3.9, 7.6, 0.5, { size: 20, color: K.cloud }, ao("float", 750));
  T(s, "PRESENTED BY", X0, 4.95, 4, 0.3, { size: 10.5, color: K.gold, bold: true, cs: 3 }, ao("fade", 1050));
  T(s, "Qarabayeva Mukhlisa", X0, 5.25, 6, 0.5, { font: HEAD, size: 24, color: K.white }, ao("fade", 1150));
  T(s, "Course: International Standards of English Language Teaching and Assessment", X0, 6.62, 7.6, 0.3, { size: 11, color: "8C97AB", cs: 0.5 }, ao("fade", 1400));
  s.addNotes("Welcome everyone. Today's topic is how to become an assessment expert: the principles that make English language assessment effective. This presentation is part of the course International Standards of English Language Teaching and Assessment.");

  // ===== 2. What makes an assessment effective? =====
  s = newSlide("LIGHT");
  eyebrow(s, "INTRODUCTION");
  title(s, "What makes an assessment effective?");
  sub(s, "A good test is more than a set of questions.");
  {
    const cw = 3.6, gap = (CW - 3 * cw) / 2, y = 2.45, h = 2.6;
    const items = [
      ["01", "Purpose", "What do we need to find out about learners?", "LuTarget"],
      ["02", "Evidence", "What performance or response will show learning?", "LuScanSearch"],
      ["03", "Decision", "How will the results guide teaching and learning?", "LuCompass"],
    ];
    for (let i = 0; i < 3; i++) {
      const x = X0 + i * (cw + gap), d = 250 + i * 200;
      box(s, x, y, cw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.4, y + 0.4, 0.72, items[i][3], K.ink, K.gold, "zoom", d + 150);
      T(s, items[i][0], x + cw - 1.2, y + 0.42, 0.8, 0.5, { font: HEAD, size: 26, color: K.goldL, align: "right" }, ao("float", d));
      T(s, items[i][1], x + 0.4, y + 1.38, cw - 0.8, 0.45, { font: HEAD, size: 22, color: K.ink }, ao("float", d));
      T(s, items[i][2], x + 0.4, y + 1.88, cw - 0.8, 0.7, { size: 15, color: K.muted }, ao("float", d));
      if (i < 2) {
        const ax = x + cw + gap / 2 - 0.18, ay = y + h / 2 - 0.18;
        await badge(s, ax, ay, 0.36, "LuArrowRight", K.white, K.goldD, "zoom", 900 + i * 120, K.line);
      }
    }
    await callout(s, 5.5, "LuCalendarCheck", [
      { text: "Today: ", options: { color: K.gold, bold: true } },
      { text: "six key quality principles, practical examples, and a classroom task." },
    ], 1200);
  }
  s.addNotes("A good test is more than a set of questions. Every effective assessment answers three questions. Purpose: what do we need to find out about learners? Evidence: what performance or response will show learning? Decision: how will the results guide teaching and learning? Today we will look at six key quality principles, practical examples, and a classroom task.");

  // ===== 3. Foundations =====
  s = newSlide("LIGHT");
  eyebrow(s, "FOUNDATIONS");
  title(s, "Assessment: collecting evidence of learning");
  sub(s, "Assessment should support decisions, not simply produce marks.");
  {
    const cw = (CW - 0.3) / 2, y = 2.4, h = 1.62;
    const defs = [
      ["Assessment", "A planned process of collecting and interpreting evidence about what learners know and can do.", "LuClipboardCheck"],
      ["Evaluation", "Using evidence to make a judgement or decision about quality, progress, or achievement.", "LuScale"],
    ];
    for (let i = 0; i < 2; i++) {
      const x = X0 + i * (cw + 0.3), d = 250 + i * 180;
      box(s, x, y, cw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.38, y + 0.38, 0.66, defs[i][2], K.ink, K.gold, "zoom", d + 150);
      T(s, defs[i][0], x + 1.3, y + 0.34, cw - 1.7, 0.42, { font: HEAD, size: 21, color: K.ink }, ao("float", d));
      T(s, defs[i][1], x + 1.3, y + 0.8, cw - 1.65, 0.85, { size: 15, color: K.muted }, ao("float", d));
    }
    // timeline
    const cols = [X0, X0 + 3.6 + 0.515, X0 + 2 * (3.6 + 0.515)];
    const ly = 5.0;
    s.addShape(S.LINE, { x: X0, y: ly, w: CW, h: 0, line: { color: "BFC4CC", width: 1.25, endArrowType: "triangle" }, ...ao("wipe", 750, 1000) });
    const tl = [
      ["BEFORE LEARNING", "Diagnostic", "Identifies learners’ starting points and needs."],
      ["DURING LEARNING", "Formative", "Gives feedback during learning so learners can improve."],
      ["END OF A UNIT OR COURSE", "Summative", "Judges achievement at the end of a unit, course, or period."],
    ];
    for (let i = 0; i < 3; i++) {
      const x = cols[i], d = 900 + i * 300;
      T(s, tl[i][0], x, 4.5, 3.6, 0.3, { size: 10.5, bold: true, color: K.goldD, cs: 2 }, ao("fade", d));
      s.addShape(S.OVAL, { x: x, y: ly - 0.14, w: 0.28, h: 0.28, fill: { color: K.ink }, line: { color: K.paper, width: 2.5 }, ...ao("zoom", d) });
      T(s, tl[i][1], x, 5.3, 3.5, 0.42, { font: HEAD, size: 20, color: K.ink }, ao("float", d + 100));
      T(s, tl[i][2], x, 5.74, 3.45, 0.75, { size: 15, color: K.muted }, ao("float", d + 100));
    }
  }
  s.addNotes("Assessment is a planned process of collecting and interpreting evidence about what learners know and can do. Evaluation uses that evidence to make a judgement or decision. There are three main types: diagnostic assessment before learning, formative assessment during learning, and summative assessment at the end of a unit, course, or period.");

  // ===== 4. The evidence (dark) =====
  s = newSlide("DARK");
  eyebrow(s, "THE EVIDENCE");
  title(s, "Why assessment for learning matters");
  sub(s, "Well-designed classroom assessment and feedback are among the strongest drivers of achievement.");
  {
    T(s, "0.4–0.7", X0, 2.35, 4.8, 1.15, { font: HEAD, size: 72, color: K.gold }, ao("float", 300, 900));
    T(s, "Typical effect sizes of formative assessment — larger than most educational interventions.", X0, 3.6, 4.6, 0.95, { size: 17, color: K.white }, ao("fade", 650));
    T(s, "Black & Wiliam (1998), Inside the Black Box", X0, 4.58, 4.6, 0.3, { size: 11, color: K.mist, italic: true }, ao("fade", 750));
    box(s, X0, 5.15, 4.7, 1.5, { fill: K.surf, line: K.edge }, ao("float", 950));
    T(s, "HOW TO READ IT", X0 + 0.3, 5.32, 4, 0.28, { size: 10.5, bold: true, color: K.gold, cs: 2.5 }, ao("float", 950));
    T(s, "Effect size (d) shows how much a practice raises achievement. Hattie’s “hinge point” d = 0.40 is the average effect of all influences studied.", X0 + 0.3, 5.62, 4.15, 0.95, { size: 14, color: K.cloud }, ao("float", 950));

    const px = 5.85, py = 2.35, pw = CW + X0 - px, ph = 4.3;
    box(s, px, py, pw, ph, { fill: K.surf, line: K.edge }, ao("float", 450));
    T(s, "Effect size on student achievement", px + 0.4, py + 0.32, pw - 0.8, 0.4, { font: HEAD, size: 19, color: K.white }, ao("float", 450));
    T(s, "Hattie (2009), Visible Learning — a synthesis of 800+ meta-analyses", px + 0.4, py + 0.76, pw - 0.8, 0.3, { size: 12, color: K.mist }, ao("float", 450));
    s.addChart(pres.charts.BAR, [{ name: "Effect size (d)", labels: ["Providing formative evaluation", "Feedback", "Average of all influences"], values: [0.90, 0.73, 0.40] }], {
      x: px + 0.25, y: py + 1.2, w: pw - 0.6, h: ph - 1.4, barDir: "bar", barGapWidthPct: 55,
      chartColors: [K.gold, K.gold, K.slate], catAxisOrientation: "maxMin",
      catAxisLabelColor: K.cloud, catAxisLabelFontSize: 13, catAxisLineShow: false,
      valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 1.0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: K.white, dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelFormatCode: "0.00",
      showLegend: false, ...chartFont, ...ao("wipe", 900, 1000),
    });
  }
  s.addNotes("Why does this matter? Black and Wiliam reviewed classroom studies and found that formative assessment produced effect sizes of 0.4 to 0.7, larger than most educational interventions. Hattie's synthesis of more than 800 meta-analyses shows the same picture: formative evaluation (0.90) and feedback (0.73) are well above the average effect of 0.40.");

  // ===== 5. Six principles (dark) =====
  s = newSlide("DARK", "Core principles");
  eyebrow(s, "CORE PRINCIPLES");
  title(s, "Six principles of quality assessment");
  sub(s, "Use them as a checklist when designing a test or classroom task.");
  {
    const P = [
      ["Validity", "Does it assess what it is intended to assess?", "LuCrosshair"],
      ["Reliability", "Would results be reasonably consistent?", "LuRepeat"],
      ["Fairness", "Do all learners have an equitable opportunity?", "LuScale"],
      ["Authenticity", "Does the task reflect meaningful language use?", "LuMessagesSquare"],
      ["Practicality", "Can it be administered and marked realistically?", "LuClock"],
      ["Washback", "What effect does it have on teaching and learning?", "LuRefreshCcw"],
    ];
    const tw = 3.75, gx = (CW - 3 * tw) / 2, th = 1.88;
    for (let i = 0; i < 6; i++) {
      const c = i % 3, r = Math.floor(i / 3), x = X0 + c * (tw + gx), y = 2.42 + r * (th + 0.24), d = 250 + i * 140;
      box(s, x, y, tw, th, { fill: K.surf, line: K.edge }, ao("float", d));
      T(s, "0" + (i + 1), x + 0.32, y + 0.28, 0.8, 0.32, { font: HEAD, size: 15, color: K.gold }, ao("float", d));
      s.addImage({ data: await icon(P[i][2], K.gold), x: x + tw - 0.72, y: y + 0.26, w: 0.4, h: 0.4, altText: P[i][0] + " icon", ...ao("float", d) });
      T(s, P[i][0], x + 0.32, y + 0.66, tw - 0.6, 0.42, { font: HEAD, size: 22, color: K.white }, ao("float", d));
      T(s, P[i][1], x + 0.32, y + 1.12, tw - 0.6, 0.62, { size: 14.5, color: K.mist }, ao("float", d));
    }
    T(s, "Framework adapted from Brown & Abeywickrama (2019) and Bachman & Palmer (1996).", X0, 6.55, 9, 0.28, { size: 10.5, color: "7D889C", italic: true }, ao("fade", 1300));
  }
  s.addNotes("These are the six principles of quality assessment. Validity: does it assess what it is intended to assess? Reliability: would results be reasonably consistent? Fairness: do all learners have an equitable opportunity? Authenticity: does the task reflect meaningful language use? Practicality: can it be administered and marked realistically? Washback: what effect does it have on teaching and learning? Use them as a checklist.");

  // ===== 6. Validity =====
  s = newSlide("LIGHT");
  eyebrow(s, "PRINCIPLE 1");
  title(s, "Validity: are we testing the right thing?");
  sub(s, "A test is valid when the evidence supports the interpretation we want to make.");
  {
    const cw = 5.62, y = 2.42, h = 2.95, xs = [X0, X0 + CW - cw];
    const V = [
      ["Weak alignment", "A speaking test asks learners to write a long grammar essay. The result may reflect writing ability more than speaking ability.", K.brick, "LuX",
        [{ t: "Intended skill: Speaking", w: 2.22 }, { t: "Actually measured: Writing", w: 2.5, fill: K.brickT, color: K.brick, bold: true }]],
      ["Stronger alignment", "To assess speaking, learners complete a short interview, role-play, or presentation using clear speaking criteria.", K.sage, "LuCheck",
        [{ t: "Intended skill: Speaking", w: 2.22 }, { t: "Measured: Speaking", w: 2.0, fill: K.sageT, color: K.sage, bold: true }]],
    ];
    for (let i = 0; i < 2; i++) {
      const x = xs[i], d = 250 + i * 450;
      box(s, x, y, cw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.4, y + 0.4, 0.52, V[i][3], V[i][2], K.white, "zoom", d + 150);
      T(s, V[i][0], x + 1.12, y + 0.4, cw - 1.5, 0.52, { font: HEAD, size: 21, color: V[i][2], valign: "middle" }, ao("float", d));
      T(s, V[i][1], x + 0.4, y + 1.18, cw - 0.8, 1.0, { size: 15.5, color: K.muted }, ao("float", d));
      chips(s, V[i][4], x + 0.4, y + 2.28, 0.4, { fx: "fade", delay: d + 300 });
    }
    await badge(s, X0 + cw + (CW - 2 * cw) / 2 - 0.2, y + h / 2 - 0.2, 0.4, "LuArrowRight", K.white, K.goldD, "zoom", 600, K.line);
    await callout(s, 5.7, "LuClipboardCheck", [
      { text: "Teacher check: ", options: { color: K.gold, bold: true } },
      { text: "Does every task match a learning outcome?" },
    ], 1150);
  }
  s.addNotes("Validity asks: are we testing the right thing? A test is valid when the evidence supports the interpretation we want to make. If a speaking test asks learners to write a grammar essay, it measures writing, not speaking. A stronger design uses an interview, role-play, or presentation with clear speaking criteria. Teacher check: does every task match a learning outcome?");

  // ===== 7. Reliability =====
  s = newSlide("LIGHT");
  eyebrow(s, "PRINCIPLE 2");
  title(s, "Reliability: are results consistent?");
  sub(s, "Reliable assessment reduces the influence of chance and inconsistent marking.");
  {
    const tw = 3.75, gx = (CW - 3 * tw) / 2, y = 2.42, h = 2.4;
    const R = [
      ["Clear rubric", "Use shared criteria and performance descriptors.", "LuListChecks"],
      ["Standard conditions", "Give learners the same instructions, time, and resources.", "LuTimer"],
      ["Marker agreement", "Compare sample answers and discuss borderline scores.", "LuUsers"],
    ];
    for (let i = 0; i < 3; i++) {
      const x = X0 + i * (tw + gx), d = 250 + i * 180;
      box(s, x, y, tw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.4, y + 0.4, 0.66, R[i][2], K.ink, K.gold, "zoom", d + 150);
      T(s, R[i][0], x + 0.4, y + 1.24, tw - 0.55, 0.42, { font: HEAD, size: 20, color: K.ink }, ao("float", d));
      T(s, R[i][1], x + 0.4, y + 1.72, tw - 0.75, 0.55, { size: 15, color: K.muted }, ao("float", d));
    }
    const y2 = 5.08, h2 = 1.45, w1 = 7.75;
    box(s, X0, y2, w1, h2, { shadow: true, line: K.line }, ao("float", 900));
    T(s, "EXAMPLE", X0 + 0.4, y2 + 0.26, 3, 0.28, { size: 10.5, bold: true, color: K.goldD, cs: 2.5 }, ao("float", 900));
    T(s, "Two teachers use the same speaking rubric and agree on what a ‘good response’ looks like.", X0 + 0.4, y2 + 0.58, w1 - 0.8, 0.75, { size: 17, color: K.ink }, ao("float", 900));
    const kx = X0 + w1 + 0.25, kw = CW - w1 - 0.25;
    box(s, kx, y2, kw, h2, { fill: K.ink, r: 0.12 }, ao("float", 1100));
    T(s, "κ ≥ 0.61", kx + 0.35, y2 + 0.18, kw - 0.7, 0.6, { font: HEAD, size: 30, color: K.gold }, ao("float", 1100));
    T(s, "Cohen’s kappa: “substantial” agreement between markers (Landis & Koch, 1977)", kx + 0.35, y2 + 0.78, kw - 0.6, 0.55, { size: 12.5, color: K.cloud }, ao("float", 1100));
  }
  s.addNotes("Reliability means results are consistent. Reliable assessment reduces the influence of chance and inconsistent marking. Use a clear rubric, standard conditions, and marker agreement. For example, two teachers use the same speaking rubric and agree on what a good response looks like. Agreement can be measured: a Cohen's kappa of 0.61 or higher is considered substantial.");

  // ===== 8. Fairness =====
  s = newSlide("LIGHT");
  eyebrow(s, "PRINCIPLE 3");
  title(s, "Fairness: give every learner a fair chance");
  sub(s, "Fair does not always mean identical; it means removing irrelevant barriers.");
  {
    const F = [
      ["Use clear, accessible instructions and explain the task format in advance.", "LuFileText"],
      ["Ensure questions do not depend on cultural knowledge unrelated to the learning objective.", "LuGlobe"],
      ["Provide appropriate accommodations when needed, without changing the skill being assessed.", "LuAccessibility"],
      ["Use transparent criteria so learners understand how their work will be judged.", "LuEye"],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 2.45 + i * 1.0, d = 250 + i * 170;
      await badge(s, X0, y, 0.58, F[i][1], K.ink, K.gold, "zoom", d);
      T(s, F[i][0], X0 + 0.85, y - 0.07, 6.3, 0.72, { size: 16, color: K.ink, valign: "middle" }, ao("float", d));
    }
    const x = 8.25, y = 2.45, w = X0 + CW - x, h = 4.0;
    box(s, x, y, w, h, { fill: K.ink, r: 0.14 }, ao("float", 900));
    s.addImage({ data: await icon("LuLightbulb", K.gold), x: x + 0.4, y: y + 0.4, w: 0.45, h: 0.45, altText: "Lightbulb icon", ...ao("float", 900) });
    T(s, "Quick example", x + 0.4, y + 1.0, w - 0.8, 0.45, { font: HEAD, size: 22, color: K.white }, ao("float", 900));
    T(s, "If listening comprehension is being assessed, avoid penalising a learner for handwriting speed when answers are written.", x + 0.4, y + 1.5, w - 0.75, 1.3, { size: 16, color: K.cloud }, ao("float", 900));
    s.addImage({ data: await icon("LuCheck", K.sageL, 2.2), x: x + 0.4, y: y + 2.98, w: 0.28, h: 0.28, altText: "Check icon", ...ao("fade", 1250) });
    T(s, "Assess: listening comprehension", x + 0.82, y + 2.95, w - 1.1, 0.34, { size: 14, color: K.white, valign: "middle" }, ao("fade", 1250));
    s.addImage({ data: await icon("LuX", K.brickL, 2.2), x: x + 0.4, y: y + 3.42, w: 0.28, h: 0.28, altText: "Cross icon", ...ao("fade", 1400) });
    T(s, "Don’t penalise: handwriting speed", x + 0.82, y + 3.39, w - 1.1, 0.34, { size: 14, color: K.white, valign: "middle" }, ao("fade", 1400));
  }
  s.addNotes("Fairness gives every learner a fair chance. Fair does not always mean identical; it means removing irrelevant barriers. Use clear instructions, avoid unrelated cultural knowledge, provide accommodations without changing the skill, and use transparent criteria. For example, if we assess listening, we should not penalise a learner for slow handwriting.");

  // ===== 9. Authenticity & practicality =====
  s = newSlide("LIGHT");
  eyebrow(s, "PRINCIPLES 4–5");
  title(s, "Authenticity and practicality");
  sub(s, "A useful assessment should feel meaningful and be manageable.");
  {
    const cw = 5.55, y = 2.42, h = 3.1, xs = [X0, X0 + CW - cw];
    const A = [
      ["Authenticity", "Assess language in realistic contexts.", "Learners listen to a travel announcement and identify the platform, departure time, and gate.", "LuMessagesSquare"],
      ["Practicality", "Consider time, class size, resources, and marking workload.", "Use paired role-plays with a short rubric instead of interviewing 30 learners individually.", "LuClock"],
    ];
    for (let i = 0; i < 2; i++) {
      const x = xs[i], d = 250 + i * 350;
      box(s, x, y, cw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.4, y + 0.4, 0.66, A[i][3], K.ink, K.gold, "zoom", d + 150);
      T(s, A[i][0], x + 1.3, y + 0.4, cw - 1.7, 0.66, { font: HEAD, size: 22, color: K.ink, valign: "middle" }, ao("float", d));
      T(s, A[i][1], x + 0.4, y + 1.28, cw - 0.8, 0.62, { size: 16, color: K.ink }, ao("float", d));
      T(s, "EXAMPLE", x + 0.4, y + 2.0, 3, 0.26, { size: 10.5, bold: true, color: K.goldD, cs: 2.5 }, ao("float", d + 200));
      T(s, A[i][2], x + 0.4, y + 2.3, cw - 0.8, 0.62, { size: 15, color: K.muted }, ao("float", d + 200));
    }
    await badge(s, X0 + CW / 2 - 0.3, y + h / 2 - 0.3, 0.6, "LuScale", K.white, K.goldD, "zoom", 900, K.line);
    await callout(s, 5.8, "LuSlidersHorizontal", [
      { text: "Best balance: ", options: { color: K.gold, bold: true } },
      { text: "meaningful evidence that teachers can collect and interpret well." },
    ], 1150, 0.78);
  }
  s.addNotes("Authenticity means assessing language in realistic contexts, for example identifying the platform, departure time, and gate in a travel announcement. Practicality means considering time, class size, resources, and marking workload, for example paired role-plays with a short rubric instead of 30 individual interviews. The best balance is meaningful evidence that teachers can collect and interpret well.");

  // ===== 10. Washback =====
  s = newSlide("LIGHT");
  eyebrow(s, "PRINCIPLE 6");
  title(s, "Washback: assessment changes learning");
  sub(s, "The impact of tests on what teachers teach and what learners focus on.");
  {
    const flow = [["How we assess", 2.2], ["What teachers teach", 2.65], ["What learners focus on", 2.85]];
    let fx = X0;
    for (let i = 0; i < 3; i++) {
      const d = 250 + i * 220;
      box(s, fx, 2.36, flow[i][1], 0.46, { fill: i === 0 ? K.ink : K.white, line: i === 0 ? null : "D5D6D0", r: 0.23 }, ao("fade", d));
      T(s, flow[i][0], fx, 2.36, flow[i][1], 0.46, { size: 13.5, bold: true, color: i === 0 ? K.gold : K.ink, align: "center", valign: "middle" }, ao("fade", d));
      fx += flow[i][1];
      if (i < 2) {
        s.addImage({ data: await icon("LuArrowRight", K.goldD, 2), x: fx + 0.14, y: 2.45, w: 0.28, h: 0.28, altText: "Arrow icon", ...ao("fade", d + 110) });
        fx += 0.56;
      }
    }
    const cw = (CW - 0.3) / 2, y = 3.12, h = 2.3;
    const Wb = [
      ["Positive washback", "A speaking assessment rewards interaction, fluency, and responding to others. Learners practise real communication.", K.sage, "LuTrendingUp"],
      ["Negative washback", "A test rewards only memorised grammar rules. Lessons may become repetitive drills with little communication.", K.brick, "LuTrendingDown"],
    ];
    for (let i = 0; i < 2; i++) {
      const x = X0 + i * (cw + 0.3), d = 900 + i * 300;
      box(s, x, y, cw, h, { shadow: true, line: K.line }, ao("float", d));
      await badge(s, x + 0.4, y + 0.4, 0.6, Wb[i][3], Wb[i][2], K.white, "zoom", d + 150);
      T(s, Wb[i][0], x + 1.2, y + 0.4, cw - 1.6, 0.6, { font: HEAD, size: 21, color: Wb[i][2], valign: "middle" }, ao("float", d));
      T(s, Wb[i][1], x + 0.4, y + 1.2, cw - 0.8, 0.95, { size: 15.5, color: K.muted }, ao("float", d));
    }
    await callout(s, 5.72, "LuTarget", [
      { text: "Design assessments that encourage the learning behaviours we want to see." },
    ], 1600);
  }
  s.addNotes("Washback is the impact of tests on what teachers teach and what learners focus on. Positive washback: a speaking assessment rewards interaction and fluency, so learners practise real communication. Negative washback: a test rewards only memorised grammar rules, so lessons become repetitive drills. We should design assessments that encourage the learning behaviours we want to see.");

  // ===== 11. Putting the principles into practice =====
  s = newSlide("LIGHT", "Classroom application");
  eyebrow(s, "CLASSROOM APPLICATION");
  title(s, "Putting the principles into practice");
  sub(s, "Example: an A2–B1 speaking task about making plans.");
  {
    box(s, X0 + CW - 1.55, 0.5, 1.55, 0.38, { fill: K.ink, r: 0.19 }, ao("fade", 200));
    T(s, "CEFR  A2–B1", X0 + CW - 1.55, 0.5, 1.55, 0.38, { size: 11, bold: true, color: K.gold, align: "center", valign: "middle", cs: 1 }, ao("fade", 200));
    const steps = [
      ["Outcome", "Learners can suggest, accept, and reject plans."],
      ["Task", "Pairs plan a weekend activity and agree on details."],
      ["Evidence", "Teacher observes interaction and listens for target functions."],
      ["Criteria", "Task completion, interaction, intelligibility, and useful language."],
      ["Feedback", "One strength + one next step for each learner."],
    ];
    const colw = 2.2, step = (CW - colw) / 4, nd = 0.62, ny = 2.5;
    s.addShape(S.LINE, { x: X0 + nd / 2, y: ny + nd / 2, w: 4 * step, h: 0, line: { color: "BFC4CC", width: 1.25 }, ...ao("wipe", 250, 1300) });
    for (let i = 0; i < 5; i++) {
      const x = X0 + i * step, d = 300 + i * 260;
      s.addShape(S.OVAL, { x, y: ny, w: nd, h: nd, fill: { color: K.ink }, line: { color: K.paper, width: 3 }, ...ao("zoom", d) });
      T(s, String(i + 1), x, ny, nd, nd, { font: HEAD, size: 18, color: K.gold, align: "center", valign: "middle" }, ao("zoom", d));
      T(s, steps[i][0], x, 3.38, colw, 0.42, { font: HEAD, size: 20, color: K.ink }, ao("float", d + 80));
      T(s, steps[i][1], x, 3.82, colw - 0.1, 1.2, { size: 14.5, color: K.muted }, ao("float", d + 80));
    }
    const by = 5.3, bh = 1.25;
    box(s, X0, by, CW, bh, { shadow: true, line: K.line }, ao("float", 1700));
    T(s, "WHY IT WORKS", X0 + 0.4, by, 1.7, bh, { size: 10.5, bold: true, color: K.goldD, cs: 2.5, valign: "middle" }, ao("float", 1700));
    const why = [
      ["LuCrosshair", "Validity", "the task matches the outcome"],
      ["LuListChecks", "Reliability", "shared criteria for every pair"],
      ["LuRefreshCcw", "Washback", "feedback points to a next step"],
    ];
    for (let j = 0; j < 3; j++) {
      const wx = X0 + 2.35 + j * 3.18;
      s.addImage({ data: await icon(why[j][0], K.goldD), x: wx, y: by + (bh - 0.34) / 2, w: 0.34, h: 0.34, altText: why[j][1] + " icon", ...ao("float", 1800 + j * 120) });
      T(s, [{ text: why[j][1], options: { bold: true, color: K.ink, breakLine: true } }, { text: why[j][2] }], wx + 0.5, by, 2.55, bh, { size: 14, color: K.muted, valign: "middle" }, ao("float", 1800 + j * 120));
    }
  }
  s.addNotes("Here is how the principles work in practice, with an A2 to B1 speaking task about making plans. Outcome: learners can suggest, accept, and reject plans. Task: pairs plan a weekend activity. Evidence: the teacher observes interaction and listens for target functions. Criteria: task completion, interaction, intelligibility, and useful language. Feedback: one strength and one next step for each learner.");

  // ===== 12. Dashboard (dark) =====
  s = newSlide("DARK");
  eyebrow(s, "ASSESSMENT DASHBOARD");
  title(s, "From evidence to decision");
  sub(s, "Speaking task results for a sample A2–B1 class of 24 learners (illustrative data).");
  {
    const kpis = [
      ["24", "Learners assessed", null],
      ["3.1", "Average rubric score (out of 4)", null],
      ["0.78", "Inter-rater agreement (κ)", "Substantial"],
      ["71%", "Met the outcome (score ≥ 3)", null],
    ];
    const tw = (CW - 3 * 0.2) / 4, ty = 2.3, th = 1.2;
    for (let i = 0; i < 4; i++) {
      const x = X0 + i * (tw + 0.2), d = 250 + i * 150;
      box(s, x, ty, tw, th, { fill: K.surf, line: K.edge }, ao("float", d));
      T(s, kpis[i][0], x + 0.3, ty + 0.16, tw - 0.6, 0.6, { font: HEAD, size: 32, color: i === 3 ? K.gold : K.white, valign: "middle" }, ao("float", d));
      T(s, kpis[i][1], x + 0.3, ty + 0.8, tw - 0.5, 0.3, { size: 12.5, color: K.mist }, ao("float", d));
      if (kpis[i][2]) {
        box(s, x + tw - 1.32, ty + 0.3, 1.02, 0.32, { fill: "21463F", r: 0.16 }, ao("fade", d + 300));
        T(s, kpis[i][2], x + tw - 1.32, ty + 0.3, 1.02, 0.32, { size: 10.5, bold: true, color: K.sageL, align: "center", valign: "middle" }, ao("fade", d + 300));
      }
    }
    const py = 3.7, ph = 3.0;
    // Panel A: criteria
    const ax = X0, aw = 4.85;
    box(s, ax, py, aw, ph, { fill: K.surf, line: K.edge }, ao("float", 900));
    T(s, "Average score by criterion", ax + 0.3, py + 0.22, aw - 0.6, 0.35, { font: HEAD, size: 16, color: K.white }, ao("float", 900));
    T(s, "Mean rubric score, 0–4 scale", ax + 0.3, py + 0.56, aw - 0.6, 0.26, { size: 11.5, color: K.mist }, ao("float", 900));
    s.addChart(pres.charts.BAR, [{ name: "Mean score", labels: ["Task completion", "Interaction", "Intelligibility", "Useful language"], values: [3.5, 2.6, 3.3, 3.0] }], {
      x: ax + 0.1, y: py + 0.85, w: aw - 0.3, h: ph - 0.95, barDir: "bar", barGapWidthPct: 50,
      chartColors: [K.gold, K.brickL, K.gold, K.gold], catAxisOrientation: "maxMin",
      catAxisLabelColor: K.cloud, catAxisLabelFontSize: 12, catAxisLineShow: false,
      valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 4, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: K.white, dataLabelFontSize: 12, dataLabelFontBold: true, dataLabelFormatCode: "0.0",
      showLegend: false, ...chartFont, ...ao("wipe", 1100, 1000),
    });
    // Panel B: distribution
    const bx = ax + aw + 0.2, bw = 3.3;
    box(s, bx, py, bw, ph, { fill: K.surf, line: K.edge }, ao("float", 1050));
    T(s, "Score distribution", bx + 0.3, py + 0.22, bw - 0.6, 0.35, { font: HEAD, size: 16, color: K.white }, ao("float", 1050));
    T(s, "Learners per rubric band", bx + 0.3, py + 0.56, bw - 0.6, 0.26, { size: 11.5, color: K.mist }, ao("float", 1050));
    s.addChart(pres.charts.DOUGHNUT, [{ name: "Learners", labels: ["Emerging (1)", "Developing (2)", "Secure (3)", "Strong (4)"], values: [2, 5, 11, 6] }], {
      x: bx + 0.1, y: py + 0.85, w: bw - 0.2, h: ph - 0.95, holeSize: 58,
      chartColors: [K.brickL, "8A94A6", K.gold, K.goldL], dataBorder: { pt: 1.5, color: K.surf },
      showValue: true, showPercent: false, showLabel: false, dataLabelColor: K.ink, dataLabelFontSize: 11, dataLabelFontBold: true,
      showLegend: true, legendPos: "r", legendColor: K.cloud, legendFontSize: 10.5, ...chartFont, ...ao("zoom", 1250, 800),
    });
    // Panel C: decision
    const cx = bx + bw + 0.2, cw = X0 + CW - cx;
    box(s, cx, py, cw, ph, { fill: K.gold, r: 0.12 }, ao("float", 1500));
    T(s, "DECISION", cx + 0.3, py + 0.25, cw - 0.6, 0.28, { size: 10.5, bold: true, color: K.ink, cs: 3 }, ao("float", 1500));
    T(s, "Next lesson: practise interaction", cx + 0.3, py + 0.58, cw - 0.55, 0.8, { font: HEAD, size: 19, color: K.ink }, ao("float", 1500));
    T(s, [
      { text: "Model the target functions", options: { bullet: { indent: 14 }, breakLine: true } },
      { text: "Repeat the task in 2 weeks", options: { bullet: { indent: 14 }, breakLine: true } },
      { text: "One strength + one next step", options: { bullet: { indent: 14 } } },
    ], cx + 0.3, py + 1.48, cw - 0.45, 1.3, { size: 14, color: K.ink, psa: 6 }, ao("float", 1650));
  }
  s.addNotes("This dashboard shows how evidence becomes a decision. The data is illustrative: a class of 24 learners did the speaking task. The average score is 3.1 out of 4, and 71 percent met the outcome. Two teachers agreed well (kappa 0.78, substantial). Interaction is the weakest criterion, so the decision is clear: the next lesson practises interaction, and learners get one strength and one next step.");

  // ===== 13. Challenge =====
  s = newSlide("LIGHT");
  eyebrow(s, "CLASS ACTIVITY");
  title(s, "Assessment expert challenge");
  sub(s, "In pairs or small groups, improve this assessment idea.");
  {
    const y = 2.42, h = 2.95;
    const w1 = 4.95;
    box(s, X0, y, w1, h, { shadow: true, line: K.line }, ao("float", 250));
    T(s, "THE ORIGINAL TASK", X0 + 0.4, y + 0.36, w1 - 0.8, 0.28, { size: 10.5, bold: true, color: K.brick, cs: 2.5 }, ao("float", 250));
    T(s, "A teacher wants to assess speaking. Learners complete 20 multiple-choice grammar questions in 10 minutes.", X0 + 0.4, y + 0.72, w1 - 0.8, 1.3, { size: 17, color: K.ink }, ao("float", 250));
    chips(s, [{ t: "20 questions", w: 1.3 }, { t: "Multiple choice", w: 1.55 }, { t: "10 minutes", w: 1.2 }], X0 + 0.4, y + 2.22, 0.4, { fx: "fade", delay: 550 });
    const x2 = X0 + w1 + 0.22, w2 = 4.4;
    box(s, x2, y, w2, h, { fill: K.ink, r: 0.12 }, ao("float", 500));
    s.addImage({ data: await icon("LuLightbulb", K.gold), x: x2 + w2 - 0.8, y: y + 0.32, w: 0.4, h: 0.4, altText: "Lightbulb icon", ...ao("float", 500) });
    T(s, "YOUR CHALLENGE", x2 + 0.4, y + 0.36, w2 - 1.4, 0.28, { size: 10.5, bold: true, color: K.gold, cs: 2.5 }, ao("float", 500));
    T(s, [
      { text: "Identify at least TWO problems using today’s principles.", options: { breakLine: true } },
      { text: "Redesign the task in 2 minutes." },
    ], x2 + 0.4, y + 0.72, w2 - 0.8, 1.9, { size: 17, color: K.white, psa: 8 }, ao("float", 500));
    const x3 = x2 + w2 + 0.22, w3 = X0 + CW - x3;
    box(s, x3, y, w3, h, { shadow: true, line: K.line }, ao("zoom", 800));
    s.addImage({ data: await icon("LuTimer", K.goldD), x: x3 + (w3 - 0.46) / 2, y: y + 0.42, w: 0.46, h: 0.46, altText: "Timer icon", ...ao("zoom", 800) });
    T(s, "2:00", x3, y + 1.05, w3, 0.8, { font: HEAD, size: 42, color: K.ink, align: "center", valign: "middle" }, ao("zoom", 800));
    T(s, "minutes to redesign", x3, y + 1.92, w3, 0.35, { size: 13, color: K.muted, align: "center" }, ao("zoom", 800));
    T(s, "BE READY TO EXPLAIN", X0, 5.66, 4, 0.28, { size: 10.5, bold: true, color: K.goldD, cs: 2.5 }, ao("fade", 1100));
    const qs = [["What skill is assessed?", 3.15], ["Is the task fair?", 2.45], ["How could marking be more reliable?", 4.3]];
    let qx = X0;
    for (let i = 0; i < 3; i++) {
      const d = 1200 + i * 150;
      box(s, qx, 6.0, qs[i][1], 0.52, { fill: K.white, line: "D5D6D0", r: 0.26 }, ao("float", d));
      s.addImage({ data: await icon("LuCircleHelp", K.goldD), x: qx + 0.2, y: 6.0 + 0.12, w: 0.28, h: 0.28, altText: "Question icon", ...ao("float", d) });
      T(s, qs[i][0], qx + 0.58, 6.0, qs[i][1] - 0.7, 0.52, { size: 14.5, color: K.ink, valign: "middle", bold: true }, ao("float", d));
      qx += qs[i][1] + 0.2;
    }
  }
  s.addNotes("Now it is your turn. A teacher wants to assess speaking, but learners complete 20 multiple-choice grammar questions in 10 minutes. In pairs or small groups, identify at least two problems using today's principles, and redesign the task in two minutes. Be ready to explain: What skill is assessed? Is the task fair? How could marking be more reliable?");

  // ===== 14. Debrief radar =====
  s = newSlide("LIGHT");
  eyebrow(s, "CHALLENGE DEBRIEF");
  title(s, "Scoring the task against the six principles");
  sub(s, "Original task vs. a redesigned paired role-play (teacher judgement, 1–5 scale).");
  {
    const cx = X0, cy = 2.35, cw = 6.0, ch = 4.3;
    box(s, cx, cy, cw, ch, { shadow: true, line: K.line }, ao("float", 250));
    s.addChart(pres.charts.RADAR, [
      { name: "Original: 20 grammar MCQs", labels: ["Validity", "Reliability", "Fairness", "Authenticity", "Practicality", "Washback"], values: [1, 4, 3, 1, 5, 1] },
      { name: "Redesign: paired role-play + rubric", labels: ["Validity", "Reliability", "Fairness", "Authenticity", "Practicality", "Washback"], values: [5, 4, 4, 5, 3, 5] },
    ], {
      x: cx + 0.15, y: cy + 0.15, w: cw - 0.3, h: ch - 0.3, radarStyle: "marker",
      chartColors: [K.brick, K.sage], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 7,
      valAxisMinVal: 0, valAxisMaxVal: 5, valAxisMajorUnit: 1, valAxisHidden: true, valAxisLineShow: false,
      catAxisLabelColor: K.ink, catAxisLabelFontSize: 12, valGridLine: { color: "E1E1DC", size: 0.75 },
      showLegend: true, legendPos: "b", legendColor: K.muted, legendFontSize: 11.5, ...chartFont, ...ao("zoom", 450, 900),
    });
    const rx = 7.05, rw = X0 + CW - rx;
    T(s, "WHAT WENT WRONG", rx, 2.35, rw, 0.28, { size: 10.5, bold: true, color: K.brick, cs: 2.5 }, ao("fade", 700));
    const wrong = [
      ["Validity", "Measures grammar knowledge, not speaking ability."],
      ["Authenticity", "No real interaction or communicative purpose."],
      ["Washback", "Rewards memorised rules instead of speaking practice."],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 2.72 + i * 0.64, d = 800 + i * 150;
      s.addImage({ data: await icon("LuX", K.brick, 2.4), x: rx, y: y + 0.04, w: 0.26, h: 0.26, altText: "Cross icon", ...ao("float", d) });
      T(s, [{ text: wrong[i][0], options: { bold: true, color: K.ink, breakLine: true } }, { text: wrong[i][1] }], rx + 0.42, y - 0.02, rw - 0.42, 0.6, { size: 14, color: K.muted }, ao("float", d));
    }
    T(s, "THE REDESIGN", rx, 4.68, rw, 0.28, { size: 10.5, bold: true, color: K.sage, cs: 2.5 }, ao("fade", 1350));
    T(s, "Pairs plan a weekend activity (3 minutes per pair), scored with a shared 4-criterion speaking rubric; two teachers moderate sample recordings.", rx, 4.98, rw, 0.8, { size: 14.5, color: K.muted }, ao("float", 1400));
    box(s, rx, 5.85, rw, 0.8, { fill: K.ink, r: 0.1 }, ao("float", 1700));
    s.addImage({ data: await icon("LuQuote", K.gold), x: rx + 0.3, y: 5.85 + 0.22, w: 0.36, h: 0.36, altText: "Quote icon", ...ao("float", 1700) });
    T(s, "A reliable test of the wrong skill is still not a valid test.", rx + 0.85, 5.85, rw - 1.05, 0.8, { font: HEAD, size: 16, italic: true, color: K.white, valign: "middle" }, ao("float", 1700));
  }
  s.addNotes("Let's score the task against the six principles. The original multiple-choice task is reliable and practical, but validity, authenticity, and washback are very low, because it measures grammar knowledge, not speaking. A paired role-play with a shared rubric is much stronger. Remember: a reliable test of the wrong skill is still not a valid test.");

  // ===== 15. Three questions (dark) =====
  s = newSlide("DARK", "Wrap-up");
  eyebrow(s, "CHECK YOUR UNDERSTANDING");
  title(s, "Three questions to discuss");
  {
    const Q = [
      "What is the difference between validity and reliability?",
      "Give one example of positive washback in an English class.",
      "How can a teacher make a speaking assessment fair?",
    ];
    for (let i = 0; i < 3; i++) {
      const y = 2.2 + i * 1.38, d = 300 + i * 300;
      box(s, X0, y, CW, 1.12, { fill: K.surf, line: K.edge }, ao("float", d));
      T(s, "0" + (i + 1), X0 + 0.45, y, 0.9, 1.12, { font: HEAD, size: 30, color: K.gold, valign: "middle" }, ao("float", d));
      T(s, Q[i], X0 + 1.55, y, CW - 2.0, 1.12, { size: 21, color: K.white, valign: "middle" }, ao("float", d));
    }
  }
  s.addNotes("To check your understanding, let's discuss three questions. One: what is the difference between validity and reliability? Two: give one example of positive washback in an English class. Three: how can a teacher make a speaking assessment fair?");

  // ===== 16. References =====
  s = newSlide("LIGHT");
  eyebrow(s, "SOURCES");
  title(s, "References and further reading");
  sub(s, "Key texts behind the principles, examples, and figures in this presentation.");
  {
    const refs = [
      ["Bachman, L. F., & Palmer, A. S. (1996).", "Language testing in practice.", " Oxford University Press."],
      ["Black, P., & Wiliam, D. (1998).", "Inside the black box: Raising standards through classroom assessment.", " Phi Delta Kappan, 80(2), 139–148."],
      ["Brown, H. D., & Abeywickrama, P. (2019).", "Language assessment: Principles and classroom practices", " (3rd ed.). Pearson."],
      ["Council of Europe. (2020).", "Common European Framework of Reference for Languages: Companion volume.", " Council of Europe Publishing."],
      ["Hattie, J. (2009).", "Visible learning: A synthesis of over 800 meta-analyses relating to achievement.", " Routledge."],
      ["Hughes, A., & Hughes, J. (2020).", "Testing for language teachers", " (3rd ed.). Cambridge University Press."],
      ["Landis, J. R., & Koch, G. G. (1977).", "The measurement of observer agreement for categorical data.", " Biometrics, 33(1), 159–174."],
    ];
    const colw = (CW - 0.5) / 2;
    for (let i = 0; i < refs.length; i++) {
      const c = i < 4 ? 0 : 1, r = i < 4 ? i : i - 4, x = X0 + c * (colw + 0.5), y = 2.45 + r * 0.98, d = 200 + i * 110;
      T(s, String(i + 1).padStart(2, "0"), x, y, 0.55, 0.35, { font: HEAD, size: 15, color: K.goldD }, ao("fade", d));
      T(s, [
        { text: refs[i][0] + " ", options: { bold: true, color: K.ink } },
        { text: refs[i][1], options: { italic: true } },
        { text: refs[i][2] },
      ], x + 0.6, y, colw - 0.6, 0.85, { size: 13, color: K.muted }, ao("fade", d));
    }
    T(s, "Dashboard figures on slide 12 are illustrative, created for teaching purposes.", X0 + colw + 0.5 + 0.6, 2.45 + 3 * 0.98, colw - 0.6, 0.6, { size: 12, italic: true, color: K.foot }, ao("fade", 1100));
  }
  s.addNotes("These are the main sources behind the principles, examples, and research figures in this presentation.");

  // ===== 17. Closing =====
  s = newSlide("CLOSING");
  rings(s, 10.95, 3.75, 250);
  T(s, "KEY MESSAGE", X0, 1.25, 5, 0.3, { size: 11, bold: true, color: K.gold, cs: 3 }, ao("fade", 400));
  T(s, "Assess the learning outcome, collect trustworthy evidence, and use results to help learners improve.", X0, 1.65, 7.4, 2.3, { font: HEAD, size: 30, italic: true, color: K.white, lsm: 1.1 }, ao("float", 600, 1000));
  s.addText("Thank you!", { placeholder: "title", ...aoPh("title", "zoom", 1300, 700) });
  T(s, "Qarabayeva Mukhlisa", X0, 5.5, 6, 0.4, { size: 16, color: K.cloud }, ao("fade", 1700));
  T(s, "Course: International Standards of English Language Teaching and Assessment", X0, 6.62, 7.6, 0.3, { size: 11, color: "8C97AB", cs: 0.5 }, ao("fade", 1800));
  s.addNotes("Key message: assess the learning outcome, collect trustworthy evidence, and use results to help learners improve. Thank you for your attention.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  fs.writeFileSync(PLAN, JSON.stringify(ANIM, null, 1));
  console.log("written", OUT, "slides:", slideNo);
})().catch((e) => { console.error(e); process.exit(1); });
