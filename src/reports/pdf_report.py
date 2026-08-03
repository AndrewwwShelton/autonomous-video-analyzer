"""PDF compliance report rendering (M5).

Kept separate from exporter.py because this is presentation, not data assembly, and
because it is the only part of the project that draws anything.

Design notes:

- The verdict is the headline. Whoever opens this wants one answer -- can the video
  be monetised -- and everything after it is supporting evidence.
- The severity palette matches the interface exactly, so a flag that is amber on
  screen is amber on paper.
- A timeline strip is drawn rather than described. It is the single most useful
  artefact in the report: it shows *when* problems cluster, which a table cannot.
- Provenance is printed on every report. A reader must be able to tell whether the
  findings came from real models or the demo stand-ins, without asking.
"""
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

# Mirrors the interface's status palette (validated for contrast and CVD).
SEVERITY = {
    "High": colors.HexColor("#d03b3b"),
    "Medium": colors.HexColor("#ec835a"),
    "Low": colors.HexColor("#fab219"),
}
GOOD = colors.HexColor("#0ca30c")
LIMITED = colors.HexColor("#f5a623")
INK = colors.HexColor("#1a1a1a")
INK_2 = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#d8d8d8")
BAND = colors.HexColor("#f4f4f4")

CATEGORY_COLOUR = {"Weapon": SEVERITY["High"], "Graphic": SEVERITY["High"],
                   "Substance": SEVERITY["Medium"]}


def _fmt_time(seconds) -> str:
    s = int(round(float(seconds or 0)))
    return f"{s // 60}:{s % 60:02d}"


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=19, leading=23,
                                textColor=INK, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9.5, leading=13,
                              textColor=INK_2),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=12, leading=15,
                             textColor=INK, spaceBefore=13, spaceAfter=5),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9, leading=12,
                               textColor=INK),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=8, leading=10.5,
                               textColor=INK),
        "muted": ParagraphStyle("m", parent=base["Normal"], fontSize=8, leading=11,
                                textColor=INK_2),
        "verdict": ParagraphStyle("v", parent=base["Normal"], fontSize=15, leading=19,
                                  alignment=TA_CENTER),
    }


class TimelineStrip(Flowable):
    """Three-lane timeline: audio, visual, ad spots.

    Drawn rather than tabulated because clustering over time is the thing a reviewer
    most needs to see, and no table conveys it.
    """

    LANES = ("Audio", "Visual", "Ad spots")
    LANE_H = 11
    GAP = 4
    LABEL_W = 38

    def __init__(self, width, duration, audio, visual, ad_spots):
        super().__init__()
        self.width = width
        self.duration = max(float(duration or 0), 1.0)
        self.audio, self.visual, self.ad_spots = audio, visual, ad_spots
        self.height = len(self.LANES) * (self.LANE_H + self.GAP) + 12

    def _x(self, t) -> float:
        span = self.width - self.LABEL_W
        return self.LABEL_W + span * min(max(float(t) / self.duration, 0.0), 1.0)

    def draw(self):
        c = self.canv
        track_w = self.width - self.LABEL_W

        for i, lane in enumerate(self.LANES):
            y = self.height - 12 - (i + 1) * self.LANE_H - i * self.GAP
            c.setFont("Helvetica", 6.5)
            c.setFillColor(INK_2)
            c.drawString(0, y + 3, lane)
            c.setFillColor(BAND)
            c.rect(self.LABEL_W, y, track_w, self.LANE_H, stroke=0, fill=1)

            if lane == "Audio":
                marks = [(f["timestamp_start"], f["timestamp_end"],
                          SEVERITY.get(f.get("severity"), INK_2)) for f in self.audio]
            elif lane == "Visual":
                marks = [(f["frame_timestamp"], f["frame_timestamp"],
                          CATEGORY_COLOUR.get(f.get("risk_category"), INK_2))
                         for f in self.visual]
            else:
                marks = [(s["timestamp_start"], s["timestamp_end"], GOOD)
                         for s in self.ad_spots]

            for start, end, colour in marks:
                x1, x2 = self._x(start), self._x(end)
                c.setFillColor(colour)
                c.rect(x1, y, max(2.0, x2 - x1), self.LANE_H, stroke=0, fill=1)

        # Axis ticks at five points across the clip.
        c.setFont("Helvetica", 6)
        c.setFillColor(INK_2)
        for k in range(5):
            t = self.duration * k / 4.0
            c.drawCentredString(self._x(t), 1, _fmt_time(t))


def _table(header, rows, widths, styles, zebra=True):
    data = [[Paragraph(f"<b>{h}</b>", styles["cell"]) for h in header]] + rows
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), BAND))
    t.setStyle(TableStyle(style))
    return t


def _verdict_block(verdict: str, styles, width):
    monetizable = verdict == "Monetizable"
    colour = GOOD if monetizable else LIMITED
    label = ("Monetizable — no blocking issues found" if monetizable
             else "Restricted — review before publishing")
    para = Paragraph(f'<font color="{colour.hexval()}"><b>{label}</b></font>',
                     styles["verdict"])
    t = Table([[para]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.1, colour),
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(colour.red, colour.green,
                                                      colour.blue, alpha=0.08)),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def _page_furniture(canvas, doc, filename: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(INK_2)
    canvas.drawString(doc.leftMargin, 12 * mm,
                      f"AdSafe Studio compliance report — {filename}")
    canvas.drawRightString(A4[0] - doc.rightMargin, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.line(doc.leftMargin, 15 * mm, A4[0] - doc.rightMargin, 15 * mm)
    canvas.restoreState()


def _provenance(data: dict) -> str:
    """Name the engines behind the findings, so demo output is never mistaken for real."""
    models = sorted({f.get("detection_model") or "unknown" for f in data["audio_flags"]})
    if not models:
        return ("No speech findings, so no transcription engine is recorded for this "
                "video.")
    demo = [m for m in models if "demo" in m.lower()]
    text = "Speech findings produced by: " + ", ".join(models) + "."
    if demo:
        text += (" <b>These are demonstration stand-ins, not real model output, and "
                 "must not be treated as an audit result.</b>")
    return text


def build_pdf(data: dict, out_path) -> None:
    """Render the gathered audit data to a PDF at out_path."""
    styles = _styles()
    video = data["video"]
    audio, visual, spots = data["audio_flags"], data["visual_flags"], data["ad_spots"]

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=f"Compliance report — {video['filename']}",
        author="AdSafe Studio",
    )
    width = doc.width
    story = []

    story.append(Paragraph("Video Compliance &amp; Ad-Placement Report", styles["title"]))
    story.append(Paragraph(
        f"{video['filename']} &nbsp;·&nbsp; {_fmt_time(video['duration_sec'])} "
        f"&nbsp;·&nbsp; {video.get('resolution_width')}×{video.get('resolution_height')} "
        f"&nbsp;·&nbsp; generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
        styles["sub"]))
    story.append(Spacer(1, 9))
    story.append(_verdict_block(data["compliance_status"], styles, width))
    story.append(Spacer(1, 11))

    inventory = sum(s["timestamp_end"] - s["timestamp_start"] for s in spots)
    summary = _table(
        ["Audio flags", "Visual risks", "Premium ad spots", "Ad inventory"],
        [[Paragraph(f'<font size="13">{len(audio)}</font>', styles["cell"]),
          Paragraph(f'<font size="13">{len(visual)}</font>', styles["cell"]),
          Paragraph(f'<font size="13">{len(spots)}</font>', styles["cell"]),
          Paragraph(f'<font size="13">{round(inventory)}s</font>', styles["cell"])]],
        [width / 4.0] * 4, styles, zebra=False)
    story.append(summary)

    story.append(Paragraph("Timeline", styles["h2"]))
    story.append(TimelineStrip(width, video["duration_sec"], audio, visual, spots))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Red and amber mark compliance risks; green marks advertisement inventory.",
        styles["muted"]))

    # ---- audio
    story.append(Paragraph("Speech findings", styles["h2"]))
    if audio:
        rows = []
        for f in audio:
            colour = SEVERITY.get(f.get("severity"), INK_2).hexval()
            rows.append([
                Paragraph(_fmt_time(f["timestamp_start"]), styles["cell"]),
                Paragraph(f'<b>{f["word_flagged"]}</b>', styles["cell"]),
                Paragraph(f'<font color="{colour}"><b>{f.get("severity") or "-"}</b></font>',
                          styles["cell"]),
                Paragraph((f.get("transcript_context") or "").strip() or "-", styles["cell"]),
            ])
        story.append(_table(["At", "Term", "Severity", "Context"], rows,
                            [42, 78, 58, width - 178], styles))
    else:
        story.append(Paragraph("No restricted speech detected.", styles["body"]))

    # ---- visual
    story.append(Paragraph("Visual findings", styles["h2"]))
    if visual:
        rows = []
        for f in visual:
            colour = CATEGORY_COLOUR.get(f.get("risk_category"), INK_2).hexval()
            rows.append([
                Paragraph(_fmt_time(f["frame_timestamp"]), styles["cell"]),
                Paragraph(f'<b>{f["object_detected"]}</b>', styles["cell"]),
                Paragraph(f'<font color="{colour}"><b>{f.get("risk_category") or "-"}</b></font>',
                          styles["cell"]),
                Paragraph(f'{f["confidence_score"]:.2f}', styles["cell"]),
                Paragraph(f.get("bounding_box_json") or "-", styles["cell"]),
            ])
        story.append(_table(["At", "Object", "Category", "Conf.", "Region"], rows,
                            [42, 96, 68, 40, width - 246], styles))
    else:
        story.append(Paragraph("No visual risks detected.", styles["body"]))

    # ---- ad spots
    story.append(Paragraph("Advertisement placement opportunities", styles["h2"]))
    if spots:
        rows = []
        for s in spots:
            rows.append([
                Paragraph(f'{_fmt_time(s["timestamp_start"])}–{_fmt_time(s["timestamp_end"])}',
                          styles["cell"]),
                Paragraph(f'{s["timestamp_end"] - s["timestamp_start"]:.1f}s', styles["cell"]),
                Paragraph((s.get("spot_type") or "-").replace("_", " "), styles["cell"]),
                Paragraph(f'{(s.get("suitability_score") or 0):.2f}', styles["cell"]),
                Paragraph(s.get("bounding_box_json") or "-", styles["cell"]),
            ])
        story.append(_table(["Window", "Duration", "Surface", "Score", "Region"], rows,
                            [72, 52, 78, 42, width - 244], styles))
    else:
        story.append(Paragraph(
            "No advertisement surfaces met the minimum persistence threshold.",
            styles["body"]))

    # ---- provenance
    story.append(Spacer(1, 14))
    story.append(KeepTogether([
        Paragraph("Provenance", styles["h2"]),
        Paragraph(_provenance(data), styles["muted"]),
        Spacer(1, 3),
        Paragraph(
            "Analysis was performed entirely on the local machine; no media left this "
            "device. Findings are advisory and are intended to direct human review, "
            "not to replace it.",
            styles["muted"]),
    ]))

    render = lambda c, d: _page_furniture(c, d, video["filename"])   # noqa: E731
    doc.build(story, onFirstPage=render, onLaterPages=render)
