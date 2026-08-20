/**
 * Build the Stage 5 Initial Draft presentation.
 *
 *     node docs/deck/build_deck.js
 *
 * Structure follows Initial_Draft_ppt_outliner_for_Specialization_Project.pdf:
 * twelve required sections, in order, ending on the working demonstration.
 *
 * The visual format is the CHRIST Beamer house style, reproduced from the
 * measured geometry of the Presentation-II deck (13.333 x 7.5 in):
 *   nav bar #0A0A0A to y=0.570; navy title band #003061 to y=1.365; black
 *   four-segment footer from y=7.245; Cambria small caps for headings, Calibri
 *   for body. The outline requires the official template be used without
 *   altering its branding, colours or design, so none of this is invented.
 *
 * The outline also states: "Students should present only the work that has
 * actually been completed. Planned or proposed features should not be presented
 * as implemented features." Every figure on these slides is therefore measured
 * from the built system, and the one unfinished item — the accuracy benchmark —
 * is shown as outstanding rather than omitted.
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const A = (f) => path.join(__dirname, "assets", f);
// Screens come from docs/screens so that re-capturing them is the only
// step needed to refresh the deck; nothing has to be copied by hand.
const S = (f) => path.join(__dirname, "..", "screens", f);

const NAV_BG = "0A0A0A";
const NAV_ON = "FFFFFF";
const NAV_OFF = "8A8A8A";
const HAIR = "4A4A4A";
const BAND = "003061";
const BLOCK_TITLE = "003366";
const BLOCK_BODY = "DFE5F0";
const INK = "1A1A1A";
const MUTED = "5A5A5A";
const GOOD = "0B7A3B";
const WARN = "B8860B";
const BAD = "B22121";
const SERIF = "Cambria";
const SANS = "Calibri";

const SECTIONS = ["Introduction", "System Study", "Design", "Implementation",
                  "Testing", "Conclusion"];

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";               // 13.333 x 7.5
pres.author = "Andrew Shelton S";
pres.title = "Autonomous Video Ad-Placement and Contextual Safety Analyzer";

/** Small caps, faked: full-size initial then a 78% uppercase remainder.
 *  Split on hyphens too, or "Ad-Placement" renders as "Ad-placement". */
function smallCaps(text, size, color, bold) {
  const out = [];
  text.split(/(\s+|-)/).forEach((tok) => {
    if (!tok) return;
    if (/^\s+$/.test(tok) || tok === "-") {
      out.push({ text: tok, options: { fontSize: size, color, bold, fontFace: SERIF } });
      return;
    }
    out.push({ text: tok.charAt(0).toUpperCase(),
               options: { fontSize: size, color, bold, fontFace: SERIF } });
    if (tok.length > 1) {
      out.push({ text: tok.slice(1).toUpperCase(),
                 options: { fontSize: size * 0.78, color, bold, fontFace: SERIF } });
    }
  });
  return out;
}

let slideNo = 0;
let total = 0;

function chrome(slide, activeSection) {
  slide.background = { color: "FFFFFF" };

  // Navigation bar
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 0, w: 13.333, h: 0.57, fill: { color: NAV_BG }, line: { color: NAV_BG } });

  let x = 0.30;
  SECTIONS.forEach((name) => {
    const on = name === activeSection;
    const w = 0.14 + name.length * 0.098;
    slide.addText(smallCaps(name, 10.5, on ? NAV_ON : NAV_OFF, on),
      { x, y: 0.05, w, h: 0.47, valign: "middle", align: "left", margin: 0 });
    x += w + 0.14;
  });

  slide.addShape(pres.ShapeType.line,
    { x: 11.06, y: 0.06, w: 0, h: 0.45, line: { color: HAIR, width: 0.75 } });
  slide.addImage({ path: A("cu_logo_light.png"), x: 11.24, y: 0.13, w: 1.62, h: 0.32 });
  slide.addShape(pres.ShapeType.line,
    { x: 13.02, y: 0.06, w: 0, h: 0.45, line: { color: HAIR, width: 0.75 } });

  // Footer
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 7.245, w: 13.333, h: 0.255, fill: { color: NAV_BG }, line: { color: NAV_BG } });
  [0.667, 2.60, 5.87, 12.00].forEach((fx) => {
    slide.addShape(pres.ShapeType.line,
      { x: fx, y: 7.245, w: 0, h: 0.255, line: { color: HAIR, width: 0.75 } });
  });
  const foot = (text, fx, fw) => slide.addText(smallCaps(text, 7.5, NAV_OFF, false),
    { x: fx, y: 7.245, w: fw, h: 0.255, align: "center", valign: "middle", margin: 0 });
  foot("AdSafe Studio", 0.667, 1.93);
  foot("AY 2026-27", 2.60, 3.27);
  foot("Initial Draft - Specialization Project", 5.87, 6.13);
}

function titleBand(slide, text) {
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 0.57, w: 13.333, h: 0.795, fill: { color: BAND }, line: { color: BAND } });
  slide.addText(smallCaps(text, 25, "FFFFFF", true),
    { x: 0.72, y: 0.57, w: 11.9, h: 0.795, valign: "middle", align: "left", margin: 0 });
}

function newSlide(section, title) {
  const slide = pres.addSlide();
  slideNo += 1;
  chrome(slide, section);
  if (title) titleBand(slide, title);
  slide.addText(`${slideNo} / ${total}`,
    { x: 12.00, y: 7.245, w: 1.333, h: 0.255, align: "center", valign: "middle",
      fontSize: 7.5, color: NAV_OFF, fontFace: SERIF, margin: 0 });
  return slide;
}

/** A CU "block": navy caption bar over a pale body. */
function block(slide, x, y, w, h, heading, body, opts = {}) {
  const th = 0.42;
  slide.addShape(pres.ShapeType.rect,
    { x, y, w, h: th, fill: { color: opts.headFill || BLOCK_TITLE },
      line: { color: opts.headFill || BLOCK_TITLE } });
  slide.addText(heading,
    { x: x + 0.16, y, w: w - 0.32, h: th, valign: "middle", fontSize: 12.5,
      bold: true, color: "FFFFFF", fontFace: SANS, margin: 0 });
  slide.addShape(pres.ShapeType.rect,
    { x, y: y + th, w, h: h - th, fill: { color: opts.bodyFill || BLOCK_BODY },
      line: { color: opts.bodyFill || BLOCK_BODY } });
  if (body && body.length) {
    slide.addText(body,
      { x: x + 0.20, y: y + th + 0.08, w: w - 0.40, h: h - th - 0.16,
        fontSize: opts.size || 12, color: INK, fontFace: SANS,
        valign: "top", margin: 0, paraSpaceAfter: opts.spaceAfter || 5 });
  }
}

const bullets = (items, opts = {}) => items.map((t, i) => ({
  text: t,
  options: Object.assign({ bullet: true, breakLine: i < items.length - 1 }, opts),
}));

/** booktabs table: top/mid/bottom rules only, no fills, no vertical lines. */
function table(slide, rows, opts) {
  slide.addTable(rows, Object.assign({
    fontFace: SANS, fontSize: 11.5, color: INK, border: { type: "none" },
    align: "left", valign: "middle", autoPage: false,
  }, opts));
}

function rule(slide, x, y, w, width = 1.25) {
  slide.addShape(pres.ShapeType.line,
    { x, y, w, h: 0, line: { color: INK, width } });
}

function figure(slide, file, caption) {
  slide.addImage({ path: A(file), x: 1.55, y: 1.58, w: 10.23, h: 4.90,
                   sizing: { type: "contain", w: 10.23, h: 4.90 } });
  if (caption) {
    slide.addText(caption,
      { x: 0.72, y: 6.60, w: 11.9, h: 0.34, fontSize: 11, italic: true,
        color: MUTED, fontFace: SANS, align: "center", margin: 0 });
  }
}

// ===========================================================================
//  Slides
// ===========================================================================

const build = [];

// 1 — Title
build.push(() => {
  const slide = pres.addSlide();
  slideNo += 1;
  slide.background = { color: "FFFFFF" };
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 0, w: 13.333, h: 0.57, fill: { color: NAV_BG }, line: { color: NAV_BG } });
  slide.addImage({ path: A("cu_logo_light.png"), x: 11.24, y: 0.13, w: 1.62, h: 0.32 });

  slide.addText(smallCaps("Autonomous Video Ad-Placement", 30, BAND, true),
    { x: 0.9, y: 1.28, w: 11.5, h: 0.62, align: "center", valign: "middle", margin: 0 });
  slide.addText(smallCaps("and Contextual Safety Analyzer", 30, BAND, true),
    { x: 0.9, y: 1.92, w: 11.5, h: 0.62, align: "center", valign: "middle", margin: 0 });

  slide.addText("Initial Draft  ·  BCA Specialization Project",
    { x: 0.9, y: 2.66, w: 11.5, h: 0.34, align: "center", fontSize: 14,
      color: MUTED, fontFace: SANS, margin: 0 });

  rule(slide, 4.6, 3.16, 4.13, 1);

  const team = [
    ["Andrew Shelton S", "2441609"], ["Akash Ganesh", "2441604"],
    ["Andrew Judah", "2441608"], ["Ramona Elisha Mary", "2441646"],
  ];
  team.forEach(([name, reg], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    slide.addText([
      { text: name, options: { fontSize: 13.5, bold: true, color: INK, fontFace: SANS } },
      { text: `   ${reg}`, options: { fontSize: 12, color: MUTED, fontFace: SANS } },
    ], { x: 2.5 + col * 4.3, y: 3.42 + row * 0.44, w: 4.1, h: 0.38,
         align: "center", valign: "middle", margin: 0 });
  });

  slide.addText([
    { text: "Under the guidance of  ", options: { fontSize: 12, color: MUTED, fontFace: SANS } },
    { text: "Dr. Chanti", options: { fontSize: 13, bold: true, color: INK, fontFace: SANS } },
    { text: ",  Assistant Professor", options: { fontSize: 12, color: MUTED, fontFace: SANS } },
  ], { x: 0.9, y: 4.52, w: 11.5, h: 0.34, align: "center", margin: 0 });

  slide.addImage({ path: A("cu_crest.png"), x: 6.27, y: 5.02, w: 0.80, h: 0.80 });
  slide.addText("Department of Computer Science  ·  School of Sciences",
    { x: 0.9, y: 5.92, w: 11.5, h: 0.3, align: "center", fontSize: 12,
      color: INK, fontFace: SANS, margin: 0 });
  slide.addText("CHRIST (Deemed to be University), Bengaluru  ·  August 2026",
    { x: 0.9, y: 6.20, w: 11.5, h: 0.3, align: "center", fontSize: 11.5,
      color: MUTED, fontFace: SANS, margin: 0 });

  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 7.245, w: 13.333, h: 0.255, fill: { color: NAV_BG }, line: { color: NAV_BG } });
  slide.addNotes("Offline tool that audits video for advertiser-suitability risks and ad placement surfaces before publication. Everything runs locally.");
});

// 2 — Agenda
build.push(() => {
  const slide = newSlide("Introduction", "Agenda");
  const items = [
    ["01", "Problem Statement", "why automated demonetization needs a pre-check"],
    ["02", "Objectives", "eight measurable goals"],
    ["03", "Existing vs Proposed", "what is wrong and what replaces it"],
    ["04", "Requirements", "functional, non-functional, hardware and software"],
    ["05", "Design and Models", "architecture, use case, DFD, activity, class, ER"],
    ["06", "Implementation", "stack, modules and individual contribution"],
    ["07", "Testing and Results", "169 tests and what real video revealed"],
    ["08", "Working System", "live demonstration, conclusion, future work"],
  ];
  items.forEach(([n, title, sub], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.72 + col * 6.05, y = 1.72 + row * 1.30;
    slide.addText(n, { x, y, w: 0.62, h: 0.62, align: "center", valign: "middle",
                       fontSize: 20, bold: true, color: "C9D4E6", fontFace: SERIF, margin: 0 });
    slide.addText(title, { x: x + 0.66, y: y - 0.02, w: 5.2, h: 0.36, fontSize: 14.5,
                           bold: true, color: BAND, fontFace: SANS, valign: "middle", margin: 0 });
    slide.addText(sub, { x: x + 0.66, y: y + 0.32, w: 5.2, h: 0.34, fontSize: 11.5,
                         color: MUTED, fontFace: SANS, valign: "middle", margin: 0 });
  });
});

// 3 — Problem Statement
build.push(() => {
  const slide = newSlide("Introduction", "Problem Statement");
  block(slide, 0.72, 1.62, 5.83, 2.28, "What is the problem?", bullets([
    "Advertiser-suitability is decided automatically, after publication.",
    "The verdict arrives with no explanation and no context.",
    "Appeals resolve after the period of peak viewership has passed.",
  ]), { size: 12.5 });
  block(slide, 6.78, 1.62, 5.83, 2.28, "Who faces it?", bullets([
    "Independent creators who depend on advertising revenue.",
    "Educational, journalistic and documentary channels, whose subject matter is assessed identically to gratuitous use.",
  ]), { size: 12.5 });
  block(slide, 0.72, 4.10, 11.89, 2.32, "Why does it matter?", bullets([
    "A video earns most of its revenue in its first days — exactly the window an appeal cannot recover.",
    "Creators have no way to predict the outcome before publishing: the alternatives are to publish and find out, to self-review manually, or to upload footage to a commercial third party.",
    "None of those is available to an individual working on unreleased or confidential material.",
  ]), { size: 12.5 });
  slide.addNotes("The core failure is not detection accuracy — it is that a detection is treated as a fact rather than as evidence needing context.");
});

// 4 — Objectives
build.push(() => {
  const slide = newSlide("Introduction", "Objectives");
  const objectives = [
    "Analyse video entirely on local hardware, with nothing sent to any external service.",
    "Transcribe speech with word-level timestamps and match restricted terminology.",
    "Detect visual risks — weapons, alcohol, tobacco — in sampled frames.",
    "Identify continuous empty regions suitable for advertisement placement.",
    "Distinguish content rendered inside a game from genuine filmed footage.",
    "Produce a compliance verdict together with the reasoning that produced it.",
    "Export findings as formatted PDF, CSV and JSON reports.",
    "Present everything through a web interface with a navigable audit timeline.",
  ];
  objectives.forEach((text, i) => {
    const y = 1.66 + i * 0.665;
    slide.addShape(pres.ShapeType.ellipse,
      { x: 0.80, y: y + 0.06, w: 0.42, h: 0.42, fill: { color: BAND }, line: { color: BAND } });
    slide.addText(String(i + 1),
      { x: 0.80, y: y + 0.06, w: 0.42, h: 0.42, align: "center", valign: "middle",
        fontSize: 12, bold: true, color: "FFFFFF", fontFace: SANS, margin: 0 });
    slide.addText(text,
      { x: 1.40, y, w: 11.2, h: 0.55, valign: "middle", fontSize: 13,
        color: INK, fontFace: SANS, margin: 0 });
  });
});

// 5 — Existing vs Proposed
build.push(() => {
  const slide = newSlide("System Study", "Existing System vs Proposed System");
  const rows = [
    [{ text: "", options: { border: [{ type: "none" }, { type: "none" },
        { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Existing approaches", options: { bold: true, align: "center",
        border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Proposed system", options: { bold: true, align: "center", color: BAND,
        border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["When the verdict arrives", "after publication", { text: "before publication", options: { bold: true, color: GOOD } }],
    ["Explanation given", "none", { text: "reasoning on every verdict", options: { bold: true, color: GOOD } }],
    ["Context considered", "no", { text: "rendered vs filmed content", options: { bold: true, color: GOOD } }],
    ["Where footage goes", "uploaded to a third party", { text: "never leaves the machine", options: { bold: true, color: GOOD } }],
    ["Recurring cost", "subscription or lost revenue", { text: "none", options: { bold: true, color: GOOD } }],
    ["Ad placement", "located by hand in an editor", { text: "located automatically", options: { bold: true, color: GOOD } }],
    [{ text: "Coverage", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "whole platform catalogue", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "one creator's own library", options: { italic: true, color: MUTED,
        border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  table(slide, rows, { x: 0.90, y: 1.78, w: 11.55, colW: [3.35, 4.05, 4.15],
                       rowH: 0.44, fontSize: 12.5 });
  slide.addText([
    { text: "The trade is deliberate:  ", options: { bold: true, color: BAND, fontSize: 12, fontFace: SANS } },
    { text: "narrower coverage, in exchange for advance warning, an explanation, and privacy.",
      options: { fontSize: 12, color: INK, fontFace: SANS } },
  ], { x: 0.90, y: 6.42, w: 11.55, h: 0.4, valign: "middle", margin: 0 });
});

// 6 — Functional and non-functional requirements
build.push(() => {
  const slide = newSlide("System Study", "System Requirements");
  block(slide, 0.72, 1.62, 5.83, 4.70, "Functional", bullets([
    "FR1  Video ingestion — MP4, MOV, AVI, validated before upload.",
    "FR2  Audio analysis — 16 kHz extraction, word-level transcription, dictionary matching.",
    "FR3  Visual analysis — frame sampling, detection at two resolutions, risk categorisation.",
    "FR4  Ad placement — occupancy and texture masks, largest free rectangles, ≥ 5 s persistence.",
    "FR5  Overlay context — per-pixel temporal statistics across sampled frames.",
    "FR6  Compliance verdict — Monetizable, Review or Restricted, with reasoning.",
    "FR7  Report generation — PDF, CSV and JSON with an archive of what was produced.",
  ]), { size: 11.5, spaceAfter: 7 });
  block(slide, 6.78, 1.62, 5.83, 4.70, "Non-functional", bullets([
    "Performance — analysis within roughly twice the video's duration, on a laptop with no GPU.",
    "Reliability — a failed video does not affect others; re-analysis is idempotent.",
    "Privacy — no content transmitted anywhere; all models held locally.",
    "Usability — four breakpoints, light and dark, every finding navigable to its timestamp.",
    "Integrity — constraints enforced in the database, not only in application code.",
    "Accountability — every finding records the engine that produced it.",
  ]), { size: 11.5, spaceAfter: 7 });
});

// 7 — Hardware and software requirements
build.push(() => {
  const slide = newSlide("System Study", "Hardware and Software Requirements");
  const hw = [
    [{ text: "Component", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Requirement", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["Processor", "Intel Core i5 or equivalent"],
    ["Memory", "8 GB RAM minimum"],
    ["Storage", "5 GB for models and analysis data"],
    ["Graphics", "not required — used if present"],
    [{ text: "Display", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "1280 x 720 minimum", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  const sw = [
    [{ text: "Component", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Version", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["Operating system", "Windows 10+, Linux, macOS"],
    ["Language runtime", "Python 3.12"],
    ["Database", "SQLite 3"],
    ["Node runtime", "Node.js 22 (interface build)"],
    [{ text: "Browser", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "any with HTML5 video", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  slide.addText("Hardware", { x: 0.90, y: 1.66, w: 5.4, h: 0.34, fontSize: 14,
                              bold: true, color: BAND, fontFace: SANS, margin: 0 });
  table(slide, hw, { x: 0.90, y: 2.06, w: 5.45, colW: [2.10, 3.35], rowH: 0.46 });
  slide.addText("Software", { x: 7.00, y: 1.66, w: 5.4, h: 0.34, fontSize: 14,
                              bold: true, color: BAND, fontFace: SANS, margin: 0 });
  table(slide, sw, { x: 7.00, y: 2.06, w: 5.45, colW: [2.10, 3.35], rowH: 0.46 });

  block(slide, 0.90, 5.10, 11.55, 1.22, "Verified, not assumed", [
    { text: "The whole pipeline has been run on an Intel i5-1235U with no CUDA device. " +
            "Analysis takes roughly the video's own duration: 45 s for a 25 s clip, " +
            "including transcription and detection at two resolutions.",
      options: { fontSize: 12, fontFace: SANS, color: INK } },
  ]);
});

// 8-13 — Diagrams
const diagrams = [
  ["System Architecture", "architecture.png",
   "Four layers. The engines run sequentially, and one frame decode serves three consumers."],
  ["Use Case Diagram", "use_case.png",
   "One actor: a single-user offline tool has no authenticated roles."],
  ["Data Flow Diagram (Level 1)", "dfd_level1.png",
   "Nine processes and one data store. No flow crosses an external boundary."],
  ["Activity Diagram", "activity.png",
   "The analysis sequence, ending in one of three verdicts."],
  ["Class Diagram", "class_diagram.png",
   "Principal classes, named as they are in the implementation."],
  ["Entity Relationship Diagram", "er_diagram.png",
   "Six tables in third normal form; every child cascades on delete."],
];
diagrams.forEach(([title, file, caption]) => {
  build.push(() => {
    const slide = newSlide("Design", title);
    figure(slide, file, caption);
  });
});

// 14 — Database design
build.push(() => {
  const slide = newSlide("Design", "Database Design");
  const rows = [
    [{ text: "Table", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Primary key", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Foreign key", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Key constraint", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["VideoMetadata", "video_id", "—", "processed_status in 4 states"],
    ["AudioFlags", "audio_flag_id", "video_id", "severity in Low / Medium / High"],
    ["VisualFlags", "visual_flag_id", "video_id", "risk_category in Weapon / Substance / Graphic"],
    ["AdSpots", "spot_id", "video_id", "timestamps and box not null"],
    ["AuditReports", "report_id", "video_id", "report_type in PDF / CSV / JSON"],
    [{ text: "SystemConfig", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "config_key", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "—", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "config_type in string / int / float / json", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  table(slide, rows, { x: 0.85, y: 1.74, w: 11.65, colW: [2.45, 2.15, 1.75, 5.30],
                       rowH: 0.46, fontSize: 11.5 });
  block(slide, 0.85, 5.32, 11.65, 1.00, "Integrity is enforced by the database, not the caller", [
    { text: "Foreign keys are switched on per connection — SQLite disables them by default — " +
            "and every child cascades on delete, so a removed video leaves no orphaned findings. " +
            "Write-ahead logging lets the interface read while analysis writes.",
      options: { fontSize: 11.5, fontFace: SANS, color: INK } },
  ]);
});

// 15 — Technology stack
build.push(() => {
  const slide = newSlide("Implementation", "Technology Stack");
  const groups = [
    ["Language and runtime", ["Python 3.12", "Node.js 22", "JavaScript (ES2022)"]],
    ["Backend", ["FastAPI", "Uvicorn", "SQLite 3 with WAL"]],
    ["AI and vision", ["faster-whisper (CTranslate2)", "Ultralytics YOLOv8", "OpenCV", "NumPy"]],
    ["Frontend", ["React 18", "Vite 5", "react-router 6", "hand-written CSS system"]],
    ["Reporting", ["ReportLab (PDF)", "pandas (CSV)", "imageio-ffmpeg"]],
    ["Tooling", ["pytest — 169 tests", "Git", "matplotlib (diagrams)"]],
  ];
  groups.forEach(([name, items], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.72 + col * 4.02, y = 1.68 + row * 2.46;
    block(slide, x, y, 3.80, 2.24, name,
      bullets(items, { fontSize: 11.5 }), { size: 11.5, spaceAfter: 5 });
  });
});

// 16 — Modules implemented
build.push(() => {
  const slide = newSlide("Implementation", "Modules Implemented");
  const mods = [
    ["Audio and NLP", "faster-whisper with word timestamps; phrase and word-boundary matching against a 43-term dictionary.", GOOD],
    ["Vision", "COCO plus a fine-tuned risk model, run at two resolutions per frame and merged.", GOOD],
    ["Ad placement", "occupancy and texture masks, largest-rectangle search, ≥ 5 s persistence.", GOOD],
    ["Overlay context", "streaming per-pixel statistics; distinguishes rendered from filmed content.", GOOD],
    ["Orchestration", "sequential stages, background execution, progress reporting, per-stage engine naming.", GOOD],
    ["Reporting", "PDF with a drawn timeline, plus CSV and JSON, each stating its provenance.", GOOD],
  ];
  mods.forEach(([name, detail], i) => {
    const y = 1.70 + i * 0.86;
    slide.addShape(pres.ShapeType.rect,
      { x: 0.80, y, w: 0.10, h: 0.72, fill: { color: BAND }, line: { color: BAND } });
    slide.addText(name,
      { x: 1.06, y, w: 2.85, h: 0.72, valign: "middle", fontSize: 13, bold: true,
        color: BAND, fontFace: SANS, margin: 0 });
    slide.addText(detail,
      { x: 3.95, y, w: 7.55, h: 0.72, valign: "middle", fontSize: 11.5,
        color: INK, fontFace: SANS, margin: 0 });
    slide.addText("built",
      { x: 11.60, y, w: 0.95, h: 0.72, valign: "middle", align: "right",
        fontSize: 11, bold: true, color: GOOD, fontFace: SANS, margin: 0 });
  });
});

// 17 — Individual contribution
build.push(() => {
  const slide = newSlide("Implementation", "Individual Contribution");
  const people = [
    ["Andrew Shelton S", "2441609", "Module 3 — Orchestration, database and API",
     ["Six-table schema, WAL and foreign key enforcement, repository layer",
      "Sequential orchestrator with per-stage engine selection",
      "15 REST endpoints; compliance verdict and its reasoning"]],
    ["Akash Ganesh", "2441604", "Module 1 — Audio and natural language engine",
     ["Audio extraction to 16 kHz via bundled ffmpeg",
      "faster-whisper integration with word-level timestamps",
      "Keyword matcher and the restricted-term dictionary"]],
    ["Andrew Judah", "2441608", "Module 2 — Vision, ad placement and overlay",
     ["Frame sampling and multi-scale object detection",
      "Free-space advertisement placement algorithm",
      "Persistent-overlay detection and the temporal tracker"]],
    ["Ramona Elisha Mary", "2441646", "Module 4 — Web interface and reporting",
     ["Seven React screens, four breakpoints, light and dark themes",
      "Audit timeline with click-to-seek navigation",
      "PDF, CSV and JSON report generation"]],
  ];
  people.forEach(([name, reg, role, items], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.72 + col * 6.05, y = 1.62 + row * 2.42;
    slide.addShape(pres.ShapeType.rect,
      { x, y, w: 5.83, h: 0.46, fill: { color: BLOCK_TITLE }, line: { color: BLOCK_TITLE } });
    slide.addText([
      { text: name, options: { fontSize: 12.5, bold: true, color: "FFFFFF", fontFace: SANS } },
      { text: `   ${reg}`, options: { fontSize: 10.5, color: "B9C7DC", fontFace: SANS } },
    ], { x: x + 0.16, y, w: 5.5, h: 0.46, valign: "middle", margin: 0 });
    slide.addShape(pres.ShapeType.rect,
      { x, y: y + 0.46, w: 5.83, h: 1.72, fill: { color: BLOCK_BODY }, line: { color: BLOCK_BODY } });
    slide.addText(role,
      { x: x + 0.20, y: y + 0.52, w: 5.45, h: 0.30, fontSize: 11.5, bold: true,
        color: BAND, fontFace: SANS, margin: 0 });
    slide.addText(bullets(items, { fontSize: 10.5 }),
      { x: x + 0.20, y: y + 0.84, w: 5.45, h: 1.28, fontSize: 10.5, color: INK,
        fontFace: SANS, valign: "top", margin: 0, paraSpaceAfter: 4 });
  });
});

// 18 — Testing
build.push(() => {
  const slide = newSlide("Testing", "Testing and Validation");
  const rows = [
    [{ text: "Area", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "What is covered", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Tests", options: { bold: true, align: "right", border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["Data layer", "schema, constraints, cascade delete, config migrations", { text: "12", options: { align: "right" } }],
    ["Audio engine", "transcription contract, phrase matching, severity rules", { text: "17", options: { align: "right" } }],
    ["Vision engine", "label mapping, multi-scale merge, class-list drift guards", { text: "31", options: { align: "right" } }],
    ["Ad placement", "largest-rectangle search, masks, temporal tracking", { text: "26", options: { align: "right" } }],
    ["Overlay context", "translucent HUD, letterboxing, static camera, real footage", { text: "20", options: { align: "right" } }],
    ["Verdict logic", "three states and the limits of the overlay exemption", { text: "16", options: { align: "right" } }],
    ["Reports and API", "PDF/CSV/JSON output, endpoints, validation, error paths", { text: "47", options: { align: "right" } }],
    [{ text: "Total", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "across 12 files, run before every commit", options: { italic: true, color: MUTED, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "169", options: { bold: true, align: "right", color: GOOD, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  table(slide, rows, { x: 0.85, y: 1.72, w: 11.65, colW: [2.35, 7.60, 1.70],
                       rowH: 0.42, fontSize: 11.5 });
  block(slide, 0.85, 5.72, 11.65, 0.66, "Validation and error handling", [
    { text: "Checks at three levels — interface, API boundary and database. Unsupported formats, " +
            "duplicate dictionary terms and out-of-range settings are rejected; a video with no audio " +
            "track is analysed visually rather than failed.",
      options: { fontSize: 11, fontFace: SANS, color: INK } },
  ]);
});

// 19 — Results from real video
build.push(() => {
  const slide = newSlide("Testing", "Results on Real Video");
  slide.addText("Four real clips were analysed. Each exposed a defect that synthetic footage had hidden.",
    { x: 0.85, y: 1.62, w: 11.65, h: 0.32, fontSize: 12.5, color: INK,
      fontFace: SANS, margin: 0 });
  const rows = [
    [{ text: "Clip", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "What it exposed", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "Outcome", options: { bold: true, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
    ["Firearms news report", "detection ran at 640 px, shrinking a distant weapon below what the network resolves",
     { text: "0 → 13 detections", options: { bold: true, color: GOOD } }],
    ["Air pistol review", "raising resolution fixed the first clip and broke this one — the relationship is inverted",
     { text: "detect at two scales", options: { bold: true, color: GOOD } }],
    ["Gameplay capture", "a real HUD is translucent and its contents change, so it is not pixel-static",
     { text: "judge stability relative to the frame", options: { bold: true, color: GOOD } }],
    [{ text: "Firearms news report (audio)", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "transcription was perfect; the nine-word dictionary matched none of it", options: { border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } },
     { text: "43-term vocabulary", options: { bold: true, color: GOOD, border: [{ type: "none" }, { type: "none" }, { pt: 1.25, color: INK }, { type: "none" }] } }],
  ];
  table(slide, rows, { x: 0.85, y: 2.06, w: 11.65, colW: [3.05, 6.20, 2.40],
                       rowH: 0.60, fontSize: 11.5 });

  block(slide, 0.85, 4.86, 5.70, 1.52, "Model accuracy (Open Images validation)", [
    { text: "mAP@50 0.566   ·   precision 0.569   ·   recall 0.548\n" +
            "11 classes, trained for this project — no pretrained model covers this taxonomy.",
      options: { fontSize: 11, fontFace: SANS, color: INK } },
  ]);
  block(slide, 6.80, 4.86, 5.70, 1.52, "Still outstanding", [
    { text: "The benchmark against labelled creator footage has 0 of 20 clips labelled, " +
            "so no accuracy figure on real video is claimed. The harness refuses to publish " +
            "one below its evidence threshold.",
      options: { fontSize: 11, fontFace: SANS, color: INK } },
  ], { headFill: BAD });
});

// 20 — Working system
build.push(() => {
  const slide = newSlide("Testing", "Working System");
  slide.addImage({ path: S("03-video-detail.png"), x: 0.72, y: 1.62, w: 7.30, h: 4.11 });
  slide.addText("Video detail — three-state verdict with its printed reasoning, the demo-output " +
                "banner, the audit timeline, and the engine recorded against every finding",
    { x: 0.72, y: 5.80, w: 7.30, h: 0.44, fontSize: 10.5, italic: true,
      color: MUTED, fontFace: SANS, align: "center", margin: 0 });
  slide.addImage({ path: S("02-content.png"), x: 8.28, y: 1.62, w: 4.33, h: 2.44 });
  slide.addText("Content library",
    { x: 8.28, y: 4.10, w: 4.33, h: 0.28, fontSize: 10.5, italic: true,
      color: MUTED, fontFace: SANS, align: "center", margin: 0 });
  slide.addImage({ path: S("06-settings.png"), x: 8.28, y: 4.46, w: 4.33, h: 2.44 });
  slide.addText("Settings and detection coverage",
    { x: 8.28, y: 6.92, w: 4.33, h: 0.26, fontSize: 10.5, italic: true,
      color: MUTED, fontFace: SANS, align: "center", margin: 0 });
  slide.addNotes("Demonstrate live: upload a clip, run checks in real mode, open the timeline, export the PDF.");
});

// 21 — Conclusion and future work
build.push(() => {
  const slide = newSlide("Conclusion", "Conclusion and Future Work");
  block(slide, 0.72, 1.62, 5.83, 4.70, "Achieved", bullets([
    "A complete offline pipeline: transcription, detection, ad placement and overlay context.",
    "A risk model trained for this project, since no pretrained model covers the taxonomy.",
    "Two original components — the free-space placement algorithm and overlay detection.",
    "A three-state verdict that explains itself, replacing a binary rule that restricted gameplay for rendered weapons.",
    "169 automated tests; every defect found is kept as a regression test.",
    "Validated against real video, not only against generated footage.",
  ]), { size: 11.5, spaceAfter: 8 });
  block(slide, 6.78, 1.62, 5.83, 4.70, "Future work", bullets([
    "Label the 20 benchmark clips and publish a measured accuracy figure.",
    "Retrain with augmentation drawn from video rather than photographs.",
    "Suppress advertisement placement over detected overlay regions.",
    "Extend transcription beyond English.",
    "Batch analysis across a whole library.",
  ]), { size: 11.5, spaceAfter: 8 });
});

// 22 — Thank you
build.push(() => {
  const slide = pres.addSlide();
  slideNo += 1;
  slide.background = { color: "FFFFFF" };
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 0, w: 13.333, h: 0.57, fill: { color: NAV_BG }, line: { color: NAV_BG } });
  slide.addImage({ path: A("cu_logo_light.png"), x: 11.24, y: 0.13, w: 1.62, h: 0.32 });
  slide.addText(smallCaps("Thank You", 40, BAND, true),
    { x: 0.9, y: 2.66, w: 11.5, h: 0.9, align: "center", valign: "middle", margin: 0 });
  rule(slide, 5.4, 3.72, 2.53, 1);
  slide.addText("Questions are welcome — and a live demonstration is ready.",
    { x: 0.9, y: 3.94, w: 11.5, h: 0.36, align: "center", fontSize: 14,
      color: MUTED, fontFace: SANS, margin: 0 });
  slide.addImage({ path: A("cu_crest.png"), x: 6.37, y: 4.62, w: 0.60, h: 0.60 });
  slide.addShape(pres.ShapeType.rect,
    { x: 0, y: 7.245, w: 13.333, h: 0.255, fill: { color: NAV_BG }, line: { color: NAV_BG } });
});

total = build.length;
build.forEach((fn) => fn());

const out = path.join(__dirname, "..", "..", "Initial_Draft_AdSafe.pptx");
pres.writeFile({ fileName: out }).then(() => {
  console.log(`wrote ${out}`);
  console.log(`${total} slides`);
});
