/**
 * Transcript Intelligence — Slide Deck Generator
 * Uses pptxgenjs to produce a professional 13-slide deck.
 *
 * Run: node make_slides.js
 * Output: transcript_intelligence.pptx
 */

const pptxgen = require("pptxgenjs");
const path    = require("path");
const fs      = require("fs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10" × 5.625"
pres.author = "Ning Liu";
pres.title  = "Transcript Intelligence";

// ── PALETTE ───────────────────────────────────────────────────────────────────
const C = {
  navy:      "1B2D5B",
  navyDark:  "0F1E3D",
  teal:      "2E86AB",
  tealLight: "A8D8EA",
  coral:     "E07B54",
  slate:     "4A5568",
  light:     "F4F7FA",
  white:     "FFFFFF",
  text:      "2C3E50",
  muted:     "6B7280",
  green:     "48BB78",
  red:       "E53E3E",
  amber:     "ED8936",
  purple:    "6B46C1",
};

const OUTPUTS = path.join(__dirname, "outputs");
const img = (name) => path.join(OUTPUTS, name);

// ── HELPERS ───────────────────────────────────────────────────────────────────
const makeGhost = () => ({
  type: "outer", blur: 10, offset: 3, angle: 135,
  color: "000000", opacity: 0.10,
});

// Header band for content slides
function addHeader(slide, title, subtitle = "") {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.62,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  slide.addText(title, {
    x: 0.35, y: 0, w: 9.3, h: 0.62,
    fontSize: 18, bold: true, color: C.white,
    valign: "middle", margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.35, y: 0.44, w: 9.3, h: 0.22,
      fontSize: 9, color: C.tealLight, margin: 0,
    });
  }
}

// Stat callout box
function addStat(slide, x, y, value, label, color = C.teal) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 2.7, h: 1.3,
    fill: { color: C.white },
    shadow: makeGhost(),
    line: { color: "E5E7EB", width: 1 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.08, h: 1.3,
    fill: { color: color }, line: { color: color },
  });
  slide.addText(value, {
    x: x + 0.15, y: y + 0.08, w: 2.55, h: 0.62,
    fontSize: 32, bold: true, color: C.navy, margin: 0,
  });
  slide.addText(label, {
    x: x + 0.15, y: y + 0.68, w: 2.55, h: 0.55,
    fontSize: 11, color: C.slate, margin: 0,
  });
}

// Insight card (3-column row)
function addInsightCard(slide, x, y, icon, title, body, color = C.teal) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 2.95, h: 2.65,
    fill: { color: C.white },
    shadow: makeGhost(),
    line: { color: "E5E7EB", width: 1 },
  });
  // Color bar top
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 2.95, h: 0.07,
    fill: { color: color }, line: { color: color },
  });
  slide.addText(icon, {
    x: x + 0.15, y: y + 0.18, w: 2.65, h: 0.4,
    fontSize: 20, margin: 0,
  });
  slide.addText(title, {
    x: x + 0.15, y: y + 0.62, w: 2.65, h: 0.4,
    fontSize: 12, bold: true, color: C.navy, margin: 0,
  });
  slide.addText(body, {
    x: x + 0.15, y: y + 1.0, w: 2.65, h: 1.55,
    fontSize: 10, color: C.slate, margin: 0,
  });
}

// ── SLIDE 1: TITLE ────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navyDark };

  // Decorative side bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: C.teal }, line: { color: C.teal },
  });
  // Accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.18, y: 0, w: 0.06, h: 5.625,
    fill: { color: C.coral }, line: { color: C.coral },
  });

  s.addText("TRANSCRIPT INTELLIGENCE", {
    x: 0.55, y: 1.15, w: 9.0, h: 0.5,
    fontSize: 11, bold: true, color: C.tealLight,
    charSpacing: 5, margin: 0,
  });
  s.addText("What 100 Calls Reveal About\nCustomer Health, Product Risk,\nand Team Dynamics", {
    x: 0.55, y: 1.65, w: 8.8, h: 2.1,
    fontSize: 36, bold: true, color: C.white,
    margin: 0,
  });
  s.addText("Feb – Apr 2026  |  100 Transcripts  |  50+ Hours of Conversation", {
    x: 0.55, y: 3.9, w: 8.8, h: 0.4,
    fontSize: 13, color: C.muted, margin: 0,
  });
  s.addShape(pres.shapes.LINE, {
    x: 0.55, y: 3.82, w: 4.0, h: 0,
    line: { color: C.teal, width: 1.5 },
  });
  s.addText("Ning Liu  ·  2026", {
    x: 0.55, y: 4.95, w: 4, h: 0.3,
    fontSize: 10, color: C.muted, margin: 0,
  });
}

// ── SLIDE 2: EXECUTIVE SUMMARY ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.light };
  addHeader(s, "Executive Summary", "Three findings every leader needs to know");

  // Large headline
  s.addText("A single outage touched more than half of all meetings.", {
    x: 0.4, y: 0.85, w: 9.2, h: 0.52,
    fontSize: 19, bold: true, color: C.navy, margin: 0,
  });
  s.addText(
    "The Detect pipeline failure (mid-March 2026) created a ripple across all call types — internal war rooms, " +
    "support escalations, and renewal conversations. 55/100 meetings referenced it in some form.",
    {
      x: 0.4, y: 1.35, w: 9.2, h: 0.55,
      fontSize: 12, color: C.slate, margin: 0,
    }
  );

  // Stat boxes
  addStat(s, 0.4,  2.1, "55 / 100",  "meetings touched the Detect outage — 34 as primary focus, 21 as context in renewals/support", C.red);
  addStat(s, 3.5,  2.1, "4.12 avg",  "sentiment for Compliance calls — your #1 value driver", C.green);
  addStat(s, 6.6,  2.1, "21 accts",  "external meetings carry explicit churn signals (49% of all external calls)", C.coral);

  // Footer note
  s.addText("Sentiment scale: 1 (very negative) → 5 (very positive)", {
    x: 0.4, y: 5.2, w: 9, h: 0.2,
    fontSize: 9, color: C.muted, italic: true, margin: 0,
  });
}

// ── SLIDE 3: DATASET OVERVIEW ─────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addHeader(s, "Dataset Overview", "100 transcripts across three distinct call types");

  // Left: stats
  const stats = [
    ["100", "Total meetings"],
    ["3,031", "Minutes of conversation (50.5 hours)"],
    ["Feb 3 – Apr 28, 2026", "Date range (85-day window)"],
    ["3", "Call types: Support · External · Internal"],
    ["4–7", "Pre-existing topic tags per meeting"],
  ];
  stats.forEach(([val, lbl], i) => {
    s.addText(val, {
      x: 0.4, y: 0.9 + i * 0.79, w: 3.4, h: 0.38,
      fontSize: 18, bold: true, color: C.navy, margin: 0,
    });
    s.addText(lbl, {
      x: 0.4, y: 1.26 + i * 0.79, w: 3.4, h: 0.32,
      fontSize: 10, color: C.slate, margin: 0,
    });
    s.addShape(pres.shapes.LINE, {
      x: 0.4, y: 1.57 + i * 0.79, w: 3.2, h: 0,
      line: { color: "E5E7EB", width: 0.75 },
    });
  });

  // Right: chart image
  s.addImage({
    path: img("01_call_type_distribution.png"),
    x: 4.0, y: 0.75, w: 5.6, h: 4.65,
    sizing: { type: "contain", w: 5.6, h: 4.65 },
  });
}

// ── SLIDE 4: TOPIC CATEGORIZATION APPROACH ───────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.light };
  addHeader(s, "Task 1: Topic / Theme Categorization", "Why hybrid? Fast, auditable, and the data makes it possible.");

  // Method cards
  const cards = [
    { x: 0.4,  label: "1  EXISTING TOPIC TAGS", body: "Each transcript's pre-processed summary already contains 4–7 topic tags (e.g., \"soc 2 audit\", \"outage remediation\"). These are the raw signal.", color: C.teal },
    { x: 3.55, label: "2  KEYWORD MAPPING", body: "We map those tags to 8 high-level themes using curated keyword lists. 100% of meetings classified in the first pass.", color: C.navy },
    { x: 6.7,  label: "3  MODEL FALLBACK", body: "A language model API is invoked only for meetings where keyword score = 0 (none here). Keeps the pipeline fast with every decision traceable.", color: C.coral },
  ];
  cards.forEach(({ x, label, body, color }) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 0.85, w: 3.0, h: 2.3,
      fill: { color: C.white }, shadow: makeGhost(),
      line: { color: "E5E7EB", width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 0.85, w: 3.0, h: 0.07,
      fill: { color: color }, line: { color: color },
    });
    s.addText(label, {
      x: x + 0.15, y: 1.05, w: 2.7, h: 0.35,
      fontSize: 10, bold: true, color: C.navy, charSpacing: 1, margin: 0,
    });
    s.addText(body, {
      x: x + 0.15, y: 1.45, w: 2.7, h: 1.55,
      fontSize: 10.5, color: C.slate, margin: 0,
    });
  });

  // Theme table
  const themes = [
    ["Incident & Outage Response",         "34", "2.64"],
    ["Compliance & Audit Preparation",      "33", "4.12"],
    ["Renewals & Contract Management",      "14", "3.56"],
    ["Product Development & Planning",       "8", "3.90"],
    ["Technical Support & Bug Resolution",   "6", "2.92"],
    ["Competitive Intelligence",             "3", "2.87"],
  ];
  const hdr = [
    [{ text: "Theme", options: { bold: true, color: C.white, fill: { color: C.navy } } },
     { text: "Count", options: { bold: true, color: C.white, fill: { color: C.navy }, align: "center" } },
     { text: "Avg Sentiment", options: { bold: true, color: C.white, fill: { color: C.navy }, align: "center" } }],
    ...themes.map(([t, c, s2]) => [
      { text: t, options: {} },
      { text: c, options: { align: "center" } },
      { text: s2, options: { align: "center",
          color: parseFloat(s2) < 3 ? C.red : parseFloat(s2) > 3.8 ? C.green : C.slate } },
    ]),
  ];
  s.addTable(hdr, {
    x: 0.4, y: 3.35, w: 9.2, h: 2.05,
    colW: [5.2, 1.5, 2.5],
    border: { pt: 0.5, color: "E5E7EB" },
    fontSize: 10.5,
    align: "left",
  });
}

// ── SLIDE 5: THE OUTAGE NARRATIVE ─────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navyDark };

  // Full-bleed title area
  s.addText("The Outage Ran Through Everything", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, bold: true, color: C.white, margin: 0,
  });
  s.addText("55 of 100 meetings mentioned the outage in some context. 34 had it as their primary focus. It reached every call type.", {
    x: 0.5, y: 0.95, w: 9, h: 0.38,
    fontSize: 13, color: C.tealLight, margin: 0,
  });

  // Timeline
  const events = [
    { label: "Mar 14", desc: "Outage begins\nEvent pipeline fails", x: 0.5,  color: C.red },
    { label: "Mar 15", desc: "Internal war room\n112 support tickets open", x: 2.55, color: C.coral },
    { label: "Mar 16", desc: "Remediation plan\nRedundant nodes deployed", x: 4.6, color: C.amber },
    { label: "Mar 18", desc: "Customer escalations\nBlackridge, Northstar Pharma", x: 6.65, color: C.amber },
    { label: "Mar 24", desc: "Post-mortem\nCircuit breaker pattern live", x: 8.7, color: C.green },
  ];
  s.addShape(pres.shapes.LINE, {
    x: 0.5, y: 2.12, w: 9.0, h: 0,
    line: { color: C.teal, width: 2 },
  });
  events.forEach(({ label, desc, x, color }) => {
    s.addShape(pres.shapes.OVAL, {
      x: x - 0.07, y: 2.05, w: 0.18, h: 0.18,
      fill: { color }, line: { color },
    });
    s.addText(label, {
      x: x - 0.5, y: 2.28, w: 1.5, h: 0.28,
      fontSize: 10, bold: true, color: C.white, align: "center", margin: 0,
    });
    s.addText(desc, {
      x: x - 0.5, y: 2.58, w: 1.5, h: 0.65,
      fontSize: 9, color: C.muted, align: "center", margin: 0,
    });
  });

  // Three-column impact
  const impacts = [
    { title: "Internal", count: "18 meetings", desc: "War rooms, engineering sprints, post-mortems, reliability retros", color: C.teal },
    { title: "External", count: "23 meetings", desc: "Urgent escalations, renewal conversations poisoned by outage context, competitive pressure", color: C.coral },
    { title: "Support", count: "14 meetings", desc: "112 support tickets, 30 from P1/P2 accounts, multiple churn threats", color: C.red },
  ];
  impacts.forEach(({ title, count, desc, color }, i) => {
    const x = 0.5 + i * 3.2;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.55, w: 3.0, h: 1.78,
      fill: { color: "FFFFFF", transparency: 90 },
      line: { color, width: 1.5 },
    });
    s.addText(`${title}  ·  ${count}`, {
      x: x + 0.15, y: 3.7, w: 2.7, h: 0.32,
      fontSize: 11, bold: true, color, margin: 0,
    });
    s.addText(desc, {
      x: x + 0.15, y: 4.07, w: 2.7, h: 1.1,
      fontSize: 10, color: C.white, margin: 0,
    });
  });
}

// ── SLIDE 6: SENTIMENT ANALYSIS ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addHeader(s, "Task 2: Sentiment Analysis by Call Type", "Front-line support is under visible strain; compliance calls are bright spots.");

  s.addImage({
    path: img("03_sentiment_by_call_type.png"),
    x: 0.3, y: 0.75, w: 7.0, h: 4.65,
    sizing: { type: "contain", w: 7.0, h: 4.65 },
  });

  // Right: key takeaways
  const takeaways = [
    { color: C.red,   stat: "2.94",  desc: "Customer Support avg — consistently below neutral (3.0)" },
    { color: C.teal,  stat: "3.71",  desc: "External avg — AMs holding relationships despite outage" },
    { color: C.green, stat: "4.12",  desc: "Compliance meetings avg — your highest-value conversation type" },
    { color: C.coral, stat: "2.64",  desc: "Incident theme avg — the single biggest sentiment drag" },
  ];
  takeaways.forEach(({ color, stat, desc }, i) => {
    const y = 0.85 + i * 1.12;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 7.5, y, w: 2.25, h: 0.95,
      fill: { color: C.light }, line: { color: "E5E7EB", width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 7.5, y, w: 0.08, h: 0.95,
      fill: { color }, line: { color },
    });
    s.addText(stat, {
      x: 7.65, y: y + 0.04, w: 2.0, h: 0.38,
      fontSize: 22, bold: true, color: C.navy, margin: 0,
    });
    s.addText(desc, {
      x: 7.65, y: y + 0.44, w: 2.0, h: 0.44,
      fontSize: 9, color: C.slate, margin: 0,
    });
  });
}

// ── SLIDE 7: SENTIMENT OVER TIME ──────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addHeader(s, "Sentiment Trends Over Time", "The outage created a visible dip in mid-March; external calls recovered fastest.");

  s.addImage({
    path: img("04_sentiment_over_time.png"),
    x: 0.3, y: 0.75, w: 9.4, h: 4.65,
    sizing: { type: "contain", w: 9.4, h: 4.65 },
  });

  // Annotation boxes
  const notes = [
    { text: "Outage window: all three call types dip simultaneously", x: 0.5, y: 5.15, color: C.red },
    { text: "External calls recover first — relationship management absorbing the shock", x: 4.5, y: 5.15, color: C.teal },
  ];
  notes.forEach(({ text, x, y, color }) => {
    s.addText(text, {
      x, y, w: 3.8, h: 0.32,
      fontSize: 9.5, color, italic: true, margin: 0,
    });
  });
}

// ── SLIDE 8: INSIGHT 1 — CHURN RISK ──────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.light };
  addHeader(s, "Insight 1: Churn Risk Radar", "21 of 43 external meetings contain explicit churn signals — tied to outage fallout.");

  s.addImage({
    path: img("05_churn_risk.png"),
    x: 0.3, y: 0.75, w: 6.5, h: 4.65,
    sizing: { type: "contain", w: 6.5, h: 4.65 },
  });

  // Right panel
  s.addText("Top At-Risk Accounts", {
    x: 7.0, y: 0.85, w: 2.8, h: 0.35,
    fontSize: 12, bold: true, color: C.navy, margin: 0,
  });

  const accounts = [
    { name: "Blackridge Investments", score: "1.6", risk: "CRITICAL" },
    { name: "Cobalt Software",        score: "1.8", risk: "CRITICAL" },
    { name: "Northstar Pharma",       score: "2.1", risk: "HIGH" },
    { name: "Helix Data",             score: "2.3", risk: "HIGH" },
    { name: "Meridian Capital",       score: "2.4", risk: "HIGH" },
    { name: "Quantum Edge",           score: "2.4", risk: "HIGH" },
    { name: "Summit Trust",           score: "2.4", risk: "WATCH" },
    { name: "Ironworks Corp",         score: "2.6", risk: "WATCH" },
  ];
  accounts.forEach(({ name, score, risk }, i) => {
    const y = 1.3 + i * 0.48;
    const riskColor = risk === "CRITICAL" ? C.red : risk === "HIGH" ? C.coral : C.amber;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.95, y, w: 2.9, h: 0.4,
      fill: { color: C.white }, line: { color: "E5E7EB", width: 0.75 },
    });
    s.addText(name, {
      x: 7.05, y: y + 0.04, w: 1.85, h: 0.32,
      fontSize: 9.5, color: C.text, margin: 0,
    });
    s.addText(score, {
      x: 8.5, y: y + 0.04, w: 0.4, h: 0.32,
      fontSize: 9.5, bold: true, color: riskColor, align: "center", margin: 0,
    });
  });

  s.addText("→ Recommendation: Exec outreach to top 5 accounts within 2 weeks.", {
    x: 7.0, y: 5.22, w: 2.85, h: 0.32,
    fontSize: 9, bold: true, color: C.navy, margin: 0,
  });
}

// ── SLIDE 9: INSIGHT 2 — SPEAKER DYNAMICS ────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addHeader(s, "Insight 2: Speaker Dynamics as a Call Health Signal", "Talk-time imbalance correlates with lower sentiment — especially in external calls.");

  s.addImage({
    path: img("06_speaker_dynamics.png"),
    x: 0.3, y: 0.75, w: 7.0, h: 4.5,
    sizing: { type: "contain", w: 7.0, h: 4.5 },
  });

  // Right: explanation
  const points = [
    { emoji: "📊", title: "The Metric", body: "Gini coefficient of talk-time share per meeting. 0 = perfectly balanced; 1 = one person monopolizes the call." },
    { emoji: "📉", title: "The Finding", body: "Higher Gini (more imbalanced) correlates with lower sentiment across all call types. Customers who can't speak feel unheard." },
    { emoji: "🎯", title: "Who Cares", body: "Support team leads can use per-rep Gini as a coaching tool. CS managers spot pattern: reps dominating renewal calls correlate with lower renewal rates." },
    { emoji: "⚙️", title: "How to Build", body: "Automate Gini computation per rep per quarter. Flag calls where host talk-share > 70% in external/support calls." },
  ];
  points.forEach(({ emoji, title, body }, i) => {
    const y = 0.85 + i * 1.17;
    s.addText(`${emoji}  ${title}`, {
      x: 7.4, y, w: 2.4, h: 0.3,
      fontSize: 10.5, bold: true, color: C.navy, margin: 0,
    });
    s.addText(body, {
      x: 7.4, y: y + 0.3, w: 2.4, h: 0.78,
      fontSize: 9.5, color: C.slate, margin: 0,
    });
    if (i < 3) {
      s.addShape(pres.shapes.LINE, {
        x: 7.4, y: y + 1.1, w: 2.35, h: 0,
        line: { color: "E5E7EB", width: 0.75 },
      });
    }
  });
}

// ── SLIDE 10: INSIGHT 3 — ACTION ITEMS ────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.light };
  addHeader(s, "Insight 3: Action Item Load — Who's Carrying the Weight?", "High AI counts cluster around outage meetings. Three accounts appear in AIs across 5+ meetings each.");

  s.addImage({
    path: img("07_action_items.png"),
    x: 0.3, y: 0.75, w: 7.0, h: 4.5,
    sizing: { type: "contain", w: 7.0, h: 4.5 },
  });

  // Right panel: findings
  s.addText("Key Findings", {
    x: 7.5, y: 0.9, w: 2.3, h: 0.32,
    fontSize: 12, bold: true, color: C.navy, margin: 0,
  });
  const findings = [
    "Internal incident calls generate 2× more action items than average.",
    "Northstar Pharma, Blackridge, and Meridian Capital appear in AIs across 5+ separate meetings — systemic issues, not one-offs.",
    "More action items → lower sentiment. High-burden meetings correlate with stress.",
    "Tracking AI completion rates per rep or team could surface accountability gaps.",
  ];
  findings.forEach((f, i) => {
    s.addShape(pres.shapes.OVAL, {
      x: 7.5, y: 1.38 + i * 0.97, w: 0.28, h: 0.28,
      fill: { color: C.navy }, line: { color: C.navy },
    });
    s.addText(String(i + 1), {
      x: 7.5, y: 1.38 + i * 0.97, w: 0.28, h: 0.28,
      fontSize: 9, bold: true, color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(f, {
      x: 7.88, y: 1.35 + i * 0.97, w: 1.9, h: 0.85,
      fontSize: 9.5, color: C.slate, margin: 0,
    });
  });
}

// ── SLIDE 11: ADDITIONAL INSIGHTS ────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addHeader(s, "What Else Can We See? — Three More Insight Opportunities", "Beyond the required tasks — ideas for stakeholders who'd get the most value.");

  addInsightCard(
    s, 0.35, 0.88, "🏥",
    "Customer Health Score",
    "Composite per-account score combining: sentiment trend (last 30 days) + churn signal count + support ticket volume + days since last positive touchpoint.\n\nWho: CS leadership\nImpact: Turns 100 scattered transcripts into one weekly dashboard per account.",
    C.teal
  );
  addInsightCard(
    s, 3.53, 0.88, "🔍",
    "Competitive Intelligence Tracker",
    "Extract every competitor mention across transcripts. Track: which product module is cited, call outcome (churned / retained / escalated), mention frequency week-over-week.\n\nWho: Product & Sales leadership\nImpact: PM teams get signal months before formal win/loss reports.",
    C.coral
  );
  addInsightCard(
    s, 6.7, 0.88, "🎯",
    "Rep Talk-Listen Ratio Coaching",
    "Per-rep stats: avg talk-time share, Gini per call type, correlation between their Gini and meeting sentiment outcome. Flag reps where high Gini → low sentiment.\n\nWho: Support managers, CS leads\nImpact: \"Listen more\" goes from vague feedback to measurable, coachable behavior.",
    C.purple
  );

  // Bottom note
  s.addText(
    "Each of these could be built as a Transcript Intelligence module on top of the existing pipeline, with no new data collection required.",
    {
      x: 0.35, y: 3.8, w: 9.3, h: 0.4,
      fontSize: 11, italic: true, color: C.muted, margin: 0,
    }
  );
}

// ── SLIDE 12: RECOMMENDATIONS ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navyDark };

  s.addText("Recommendations", {
    x: 0.5, y: 0.25, w: 9, h: 0.52,
    fontSize: 28, bold: true, color: C.white, margin: 0,
  });
  s.addText("Five actions, ranked by urgency:", {
    x: 0.5, y: 0.78, w: 9, h: 0.28,
    fontSize: 12, color: C.tealLight, margin: 0,
  });

  const recs = [
    { num: "01", urgency: "NOW",      color: C.red,   title: "Executive outreach to top 5 at-risk accounts",
      body: "Blackridge, Cobalt Software, Northstar Pharma, Helix Data, Meridian Capital — all show active churn signals. Assign a named exec sponsor to each within 2 weeks." },
    { num: "02", urgency: "NOW",      color: C.red,   title: "Automate churn signal alerting",
      body: "Pipe key_moments type=churn_signal into a real-time alert for CS teams. This data already exists in the transcript summaries — it just isn't surfaced." },
    { num: "03", urgency: "SOON",     color: C.coral, title: "Double down on the compliance motion",
      body: "33 meetings, avg sentiment 4.12. Compliance (SOC 2, HIPAA, PCI DSS) is your highest-sentiment product area. Sales and CS should lead with it." },
    { num: "04", urgency: "SOON",     color: C.coral, title: "Launch talk-time analytics for rep coaching",
      body: "Use Gini coefficient to identify reps who dominate calls. Correlated with lower customer sentiment — a coaching opportunity backed by data." },
    { num: "05", urgency: "QUARTER",  color: C.amber, title: "Build the Customer Health Score dashboard",
      body: "Aggregate per-account sentiment trend + churn signals + support volume into one weekly view for CS leadership. Turns reactive firefighting into proactive management." },
  ];

  recs.forEach(({ num, urgency, color, title, body }, i) => {
    const y = 1.2 + i * 0.83;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y, w: 9.2, h: 0.75,
      fill: { color: "FFFFFF", transparency: 92 },
      line: { color: "FFFFFF", transparency: 80, width: 0.5 },
    });
    s.addText(num, {
      x: 0.55, y: y + 0.08, w: 0.55, h: 0.55,
      fontSize: 16, bold: true, color, align: "center", margin: 0,
    });
    s.addText(`${urgency}  ·  ${title}`, {
      x: 1.2, y: y + 0.06, w: 7.5, h: 0.3,
      fontSize: 11.5, bold: true, color: C.white, margin: 0,
    });
    s.addText(body, {
      x: 1.2, y: y + 0.36, w: 7.5, h: 0.35,
      fontSize: 10, color: C.muted, margin: 0,
    });
  });
}

// ── SLIDE 13: CLOSING ─────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: C.teal }, line: { color: C.teal },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.18, y: 0, w: 0.06, h: 5.625,
    fill: { color: C.coral }, line: { color: C.coral },
  });

  s.addText("The pipeline is live.", {
    x: 0.6, y: 1.3, w: 8.8, h: 0.65,
    fontSize: 34, bold: true, color: C.white, margin: 0,
  });
  s.addText(
    "100 transcripts processed. 8 themes identified. 21 at-risk accounts surfaced.\n" +
    "The infrastructure to run this continuously on every future call is already in place.",
    {
      x: 0.6, y: 2.1, w: 8.8, h: 0.9,
      fontSize: 14, color: C.tealLight, margin: 0,
    }
  );
  s.addShape(pres.shapes.LINE, {
    x: 0.6, y: 3.15, w: 4.5, h: 0,
    line: { color: C.teal, width: 1.5 },
  });
  s.addText("Pipeline  ·  Notebook  ·  Slide deck  ·  Video demo", {
    x: 0.6, y: 3.3, w: 9, h: 0.35,
    fontSize: 12, color: C.muted, margin: 0,
  });
  s.addText("Ning Liu  ·  ningliu365@gmail.com", {
    x: 0.6, y: 4.9, w: 5, h: 0.3,
    fontSize: 11, color: C.muted, margin: 0,
  });
}

// ── WRITE ──────────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "transcript_intelligence.pptx" })
  .then(() => console.log("✓ transcript_intelligence.pptx written"))
  .catch((e) => console.error("Error:", e));
