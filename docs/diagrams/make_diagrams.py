"""Generate the system model diagrams required by the Stage 5 presentation.

    python docs/diagrams/make_diagrams.py

Writes PNGs to docs/diagrams/out/. The same files serve two documents: the
presentation slides, and the figure placeholders in docs/InitialDraft/main.tex.

Drawn in matplotlib rather than a diagramming tool for two reasons: graphviz is
not installed on this machine, and hand-placed geometry gives the control needed
to keep every label legible at projector size, which auto-layout does not.

Two conventions here exist because breaking them produced real defects:

**Both axes span 0-100 regardless of figure size.** An earlier version set the y
limit to 100*h/w and then wrote coordinates as though it were 100; anything past
the shorter axis went negative and two ER entities were drawn off-canvas.

**Box heights are computed before layout, not after.** `stack_height()` gives the
height of a class or entity box from its row count, so a row of boxes can be
placed knowing where its bottom edge lands. Without it the bottom row of both the
class and ER diagrams was drawn below y=0 and clipped.

Because the axes are scaled independently, a visually square shape needs its
height multiplied by w/h -- `Canvas.sq()` does that, and circles are drawn as
ellipses for the same reason. Large shapes take an explicit height instead: a
"square" diamond on a 13:7 canvas is 41 y-units tall, big enough that two of them
overlapped and their branch labels landed on top of the shapes.

Palette is the CHRIST deck palette so the diagrams do not look imported.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches             # noqa: E402
import matplotlib.pyplot as plt                  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#003061"
PALE = "#DFE5F0"
WASH = "#EFF3FA"
RULE = "#9FB2CE"
GREY = "#4A4A4A"
INK = "#1A1A1A"
RED = "#B22121"
GOLD = "#C08B2E"
GREEN = "#0B7A3B"
FONT = "Calibri"
STAR = "*"          # Calibri has no BLACK STAR glyph; it renders as tofu.

HEAD, ROW, PAD = 6.0, 4.2, 2.4


class Canvas:
    def __init__(self, w, h):
        self.fig, self.ax = plt.subplots(figsize=(w, h))
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.axis("off")
        self.fig.subplots_adjust(0, 0, 1, 1)
        self.ratio = w / h

    def sq(self, x_units):
        """Height rendering as visually equal to `x_units` of width."""
        return x_units * self.ratio

    def save(self, name):
        self.fig.savefig(OUT / name, dpi=200, facecolor="white",
                         bbox_inches="tight", pad_inches=0.12)
        plt.close(self.fig)
        print(f"  {name}")


def stack_height(n_rows, rule=0.0):
    return HEAD + ROW * n_rows + PAD + rule


def box(ax, x, y, w, h, text="", fill=NAVY, fg="white", size=10, bold=True,
        edge=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=1.1",
                                linewidth=1.4, edgecolor=edge or fill,
                                facecolor=fill, zorder=2))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=fg,
                fontsize=size, fontweight="bold" if bold else "normal",
                fontname=FONT, zorder=4, linespacing=1.35)
    return (x + w / 2, y + h / 2)


def label(ax, x, y, text, size=9, colour=INK, bold=False, ha="left",
          va="center", italic=False):
    ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=colour,
            fontweight="bold" if bold else "normal",
            style="italic" if italic else "normal", fontname=FONT, zorder=4,
            linespacing=1.4)


def arrow(ax, p1, p2, text=None, size=7.4, colour=GREY, rad=0.0, style="-|>",
          dash=None, tx=0.0, ty=0.0):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=12, linewidth=1.3,
        color=colour, zorder=1, connectionstyle=f"arc3,rad={rad}",
        linestyle=dash or "solid", shrinkA=2, shrinkB=3))
    if text:
        ax.text((p1[0] + p2[0]) / 2 + tx, (p1[1] + p2[1]) / 2 + ty, text,
                ha="center", va="center", fontsize=size, color=INK,
                fontname=FONT, zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))


def footnote(ax, text):
    label(ax, 50, 2.5, text, size=8.2, colour=GREY, ha="center", italic=True)


def diamond(ax, cx, cy, w, h, text, colour=RED):
    """Decision node. Height is explicit — never derived from the width."""
    ax.add_patch(patches.Polygon(
        [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)],
        facecolor="white", edgecolor=colour, lw=1.6, zorder=2))
    label(ax, cx, cy, text, size=8.0, colour=colour, bold=True, ha="center")
    return h / 2


def stack_box(ax, x, y_top, w, name, rows, head_fill=NAVY):
    """A class or entity box. `rows` is a list of (text, kind) where kind is
    'pk', 'fk', 'op' or ''."""
    ops = [r for r in rows if r[1] == "op"]
    h = stack_height(len(rows), 1.4 if ops else 0.0)
    ax.add_patch(patches.Rectangle((x, y_top - h), w, h, facecolor="white",
                                   edgecolor=NAVY, lw=1.5, zorder=2))
    ax.add_patch(patches.Rectangle((x, y_top - HEAD), w, HEAD,
                                   facecolor=head_fill, edgecolor=head_fill,
                                   lw=1.5, zorder=3))
    label(ax, x + w / 2, y_top - HEAD / 2, name, size=8.6, colour="white",
          bold=True, ha="center")

    yy = y_top - HEAD - 3.0
    drew_rule = False
    for text, kind in rows:
        if kind == "op" and not drew_rule:
            ax.plot([x, x + w], [yy + ROW / 2, yy + ROW / 2], color=RULE,
                    lw=1.1, zorder=4)
            yy -= 1.4
            drew_rule = True
        if kind in ("pk", "fk"):
            label(ax, x + 1.4, yy, kind.upper(), size=6.4,
                  colour=RED if kind == "pk" else GOLD, bold=True)
            label(ax, x + 6.4, yy, text, size=7.0)
        else:
            label(ax, x + 1.6, yy, text, size=7.2,
                  colour=NAVY if kind == "op" else INK, italic=(kind == "op"))
        yy -= ROW
    return (x, y_top, w, h)


def top_of(b):
    return (b[0] + b[2] / 2, b[1])


def bottom_of(b):
    return (b[0] + b[2] / 2, b[1] - b[3])


# ---------------------------------------------------------------- architecture

def architecture():
    c = Canvas(13, 7)
    ax = c.ax

    def layer(y, h, name, sub, fill=PALE):
        box(ax, 3, y, 94, h, fill=fill, edge=RULE)
        label(ax, 6, y + h - 4.5, name, size=10.5, colour=NAVY, bold=True)
        if sub:
            label(ax, 6, y + h - 10.5, sub, size=8.8)

    layer(85, 13, "PRESENTATION LAYER",
          "React 18 + Vite   ·   seven screens   ·   audit timeline")
    layer(66, 13, "CONTROLLER LAYER",
          "FastAPI + Uvicorn   ·   15 REST endpoints   ·   range-served media")
    layer(30, 29, "AI ENGINE LAYER", "", fill=WASH)
    layer(9, 13, "DATA LAYER",
          "SQLite   ·   WAL journal   ·   enforced foreign keys   ·   6 tables")

    label(ax, 33, 54.5,
          "Orchestrator  —  engines run SEQUENTIALLY  (no memory contention, one database writer)",
          size=8.6, colour=RED, bold=True)

    engines = [
        ("Audio & NLP", "extract → transcribe\n→ match"),
        ("Vision", "sample → detect\nat two scales"),
        (f"Ad Placement {STAR}", "free space →\ntrack ≥ 5 s"),
        (f"Overlay Context {STAR}", "temporal mean →\nverdict input"),
    ]
    w, gap, x0 = 20.5, 2.4, 6.0
    for i, (name, detail) in enumerate(engines):
        x = x0 + i * (w + gap)
        box(ax, x, 33.5, w, 17, fill="white", edge=NAVY)
        label(ax, x + w / 2, 45.5, name, size=9.2, colour=NAVY, bold=True,
              ha="center")
        label(ax, x + w / 2, 38.5, detail, size=8.0, ha="center")

    arrow(ax, (50, 85), (50, 79), colour=NAVY)
    arrow(ax, (50, 66), (50, 59), colour=NAVY)
    arrow(ax, (50, 30), (50, 22), colour=NAVY)

    footnote(ax, f"{STAR} own work.   One frame decode, three consumers: the same "
                 "detections feed risk flags, the occupancy mask and the overlay accumulator.")
    c.save("architecture.png")


# ------------------------------------------------------------------- use case

def use_case():
    c = Canvas(12, 7)
    ax = c.ax

    ax.add_patch(FancyBboxPatch((28, 9), 68, 84,
                                boxstyle="round,pad=0,rounding_size=1.4",
                                linewidth=1.6, edgecolor=NAVY,
                                facecolor="#F8FAFD", zorder=1))
    label(ax, 62, 89, "AdSafe Studio", size=11, colour=NAVY, bold=True,
          ha="center")

    ax.add_patch(Ellipse((12, 62), 5.2, c.sq(5.2), fill=False, lw=1.8,
                         edgecolor=INK, zorder=3))
    ax.plot([12, 12], [62 - c.sq(2.6), 45], color=INK, lw=1.8, zorder=3)
    ax.plot([7.4, 16.6], [55, 55], color=INK, lw=1.8, zorder=3)
    ax.plot([12, 8], [45, 36], color=INK, lw=1.8, zorder=3)
    ax.plot([12, 16], [45, 36], color=INK, lw=1.8, zorder=3)
    label(ax, 12, 31, "Creator", size=10.5, bold=True, ha="center")

    cases = ["Upload Video", "Run Analysis", "View Findings",
             "Navigate Audit Timeline", "Configure Detection Settings",
             "Edit Restricted Dictionary", "Export Report", "Delete Video"]
    top, step = 80, 9.2
    for i, name in enumerate(cases):
        cy = top - i * step
        ax.add_patch(Ellipse((62, cy), 56, c.sq(4.2), facecolor="white",
                             edgecolor=NAVY, lw=1.3, zorder=2))
        label(ax, 62, cy, name, size=9.2, ha="center")
        arrow(ax, (17, 55), (34.5, cy), colour=GREY, style="-")

    footnote(ax, "One actor: the system is a single-user offline tool, so it has no "
                 "authenticated roles.")
    c.save("use_case.png")


# ------------------------------------------------------------------------ DFD

def dfd():
    c = Canvas(13, 7)
    ax = c.ax

    box(ax, 2, 74, 15, 12, "Creator", fill=PALE, fg=NAVY, edge=NAVY, size=10)
    box(ax, 2, 46, 15, 12, "Local Model\nStore", fill=PALE, fg=NAVY, edge=NAVY,
        size=9)

    rows = [
        [("1.0", "Video\nIngestion"), ("2.0", "Audio Extract\n& Transcribe"),
         ("3.0", "Keyword\nMatching")],
        [("4.0", "Frame\nSampling"), ("5.0", "Object\nDetection"),
         ("6.0", "Ad Surface\nDetection")],
        [("9.0", "Report\nGeneration"), ("8.0", "Verdict\nDetermination"),
         ("7.0", "Overlay\nContext")],
    ]
    xs, ys, bw, bh = [24, 42, 60], [76, 50, 24], 15, 15
    pos = {}
    for r, row in enumerate(rows):
        for col, (num, name) in enumerate(row):
            x, y = xs[col], ys[r]
            box(ax, x, y, bw, bh, f"{num}\n{name}", size=8.4)
            pos[num] = (x, y)

    sx, sy, sw, sh = 78, 49, 15, 12
    ax.add_patch(patches.Rectangle((sx, sy), sw, sh, facecolor="white",
                                   edgecolor="none", zorder=2))
    for yy in (sy, sy + sh):
        ax.plot([sx, sx + sw], [yy, yy], color=NAVY, lw=1.6, zorder=3)
    ax.plot([sx, sx], [sy, sy + sh], color=NAVY, lw=1.6, zorder=3)
    label(ax, sx + 1.6, sy + sh - 2.8, "D1", size=8.4, colour=NAVY, bold=True)
    label(ax, sx + sw / 2 + 1.5, sy + sh / 2 - 1.5, "SQLite\nData Store",
          size=8.6, ha="center")
    store = (sx + sw / 2, sy + sh / 2)

    arrow(ax, (17, 80), (24, 83.5), "video file", 7.2)
    arrow(ax, (17, 52), (24, 57.5), "weights", 7.2)
    arrow(ax, (39, 83.5), (42, 83.5))
    arrow(ax, (57, 83.5), (60, 83.5))
    arrow(ax, (31.5, 76), (31.5, 65), colour=NAVY)
    arrow(ax, (39, 57.5), (42, 57.5))
    arrow(ax, (57, 57.5), (60, 57.5))
    arrow(ax, (67.5, 50), (67.5, 39), colour=NAVY)
    arrow(ax, (60, 31.5), (57, 31.5))
    arrow(ax, (42, 31.5), (39, 31.5))

    for num in ("3.0", "5.0", "6.0"):
        x, y = pos[num]
        arrow(ax, (x + bw, y + bh / 2), store, rad=-0.14, colour=GOLD)
    arrow(ax, store, (57, 35), rad=0.2, colour=GOLD)

    # Return path hugs the left margin; the label is pushed clear of the
    # Local Model Store box, which the midpoint would otherwise sit on top of.
    arrow(ax, (24, 31.5), (9.5, 31.5), colour=NAVY)
    arrow(ax, (9.5, 31.5), (9.5, 74), colour=NAVY)
    label(ax, 10.8, 68, "verdict,\nfindings,\nreport", size=7.4)

    label(ax, 50, 13, "No data flow crosses an external boundary — the property "
                      "that distinguishes this system from a cloud service.",
          size=8.2, colour=GREY, ha="center", italic=True)
    c.save("dfd_level1.png")


# ------------------------------------------------------------------- activity

def activity():
    c = Canvas(13, 7)
    ax = c.ax
    lx = 25

    ax.add_patch(Ellipse((lx, 95.5), 3.4, c.sq(3.4), facecolor=INK, zorder=3))
    steps = ["Upload video", "Validate format, record metadata",
             "Extract audio track", "Transcribe and match terms",
             "Sample frames", "Detect objects, surfaces and overlay",
             "Merge surfaces across time"]
    y, h, gap = 82, 8.0, 3.2
    prev, last_mid = (lx, 93.8), None
    for s in steps:
        box(ax, lx - 21, y, 42, h, s, size=8.6)
        arrow(ax, prev, (lx, y + h), colour=NAVY)
        prev, last_mid = (lx, y), y + h / 2
        y -= (h + gap)

    dw, dh = 26, 17
    d1x, d1y = 63, 76
    h1 = diamond(ax, d1x, d1y, dw, dh, "high-severity\nspoken term?")
    arrow(ax, (lx + 21, last_mid), (d1x - dw / 2, d1y), colour=NAVY, rad=-0.28)

    box(ax, 86, d1y - 4, 13, 8, "RESTRICTED", fill=RED, size=8.0)
    arrow(ax, (d1x + dw / 2, d1y), (86, d1y), "yes", 7.2, colour=RED, ty=2.8)

    d2x, d2y = 63, 45
    h2 = diamond(ax, d2x, d2y, dw, dh, "weapon findings +\noverlay evidence?")
    arrow(ax, (d1x, d1y - h1), (d2x, d2y + h2), colour=NAVY)
    label(ax, d1x + 2.2, (d1y - h1 + d2y + h2) / 2, "no", size=7.2)

    box(ax, 86, d2y - 4, 13, 8, "REVIEW", fill=GOLD, size=8.0)
    arrow(ax, (d2x + dw / 2, d2y), (86, d2y), "yes", 7.2, colour=GOLD, ty=2.8)

    box(ax, 56.5, 17, 13, 8, "MONETIZABLE", fill=GREEN, size=7.2)
    arrow(ax, (d2x, d2y - h2), (63, 25), colour=GREEN)
    label(ax, d2x + 2.2, 30, "no", size=7.2)

    ex, ey = 92.5, 8.5
    ax.add_patch(Ellipse((ex, ey), 4.2, c.sq(4.2), facecolor="white",
                         edgecolor=INK, lw=1.6, zorder=3))
    ax.add_patch(Ellipse((ex, ey), 2.5, c.sq(2.5), facecolor=INK, zorder=4))
    for src in ((92.5, d1y - 4), (92.5, d2y - 4), (69.5, 21)):
        arrow(ax, src, (ex, ey + c.sq(2.3)), colour=GREY, rad=-0.16)

    footnote(ax, "Every path terminates in a verdict, and each verdict carries the "
                 "reasoning that produced it.")
    c.save("activity.png")


# ---------------------------------------------------------------------- class

def class_diagram():
    c = Canvas(13, 7)
    ax = c.ax

    ob = stack_box(ax, 36, 96, 28, "Orchestrator",
                   [("- video_id : int", ""), ("- demo : bool", ""),
                    ("+ process_video()", "op"), ("+ assess_compliance()", "op")])
    tb = stack_box(ax, 1, 62, 30, "FasterWhisperTranscriber",
                   [("- model_size : str", ""), ("+ transcribe()", "op")])
    yb = stack_box(ax, 35, 62, 30, "YoloDetector",
                   [("- weights : tuple", ""), ("- max_imgsz : int", ""),
                    ("+ detect_frame()", "op")])
    vb = stack_box(ax, 69, 62, 30, "OverlayAccumulator",
                   [("- sum, sumsq", ""), ("- n : int", ""),
                    ("+ add()", "op"), ("+ report()", "op")])
    rb = stack_box(ax, 1, 29, 30, "Repository",
                   [("- db_path : Path", ""), ("+ insert_visual_flags()", "op"),
                    ("+ get_video()", "op")])
    db = stack_box(ax, 35, 29, 30, "Detection",
                   [("+ label : str", ""), ("+ confidence : float", ""),
                    ("+ box : list", ""), ("+ timestamp : float", "")])
    sb = stack_box(ax, 69, 29, 30, "AdSpotParams",
                   [("- work_width : int", ""), ("- min_area_frac : float", "")])

    for target in (tb, yb, vb):
        arrow(ax, bottom_of(ob), top_of(target), colour=GREY)
    # Down the left margin, not through the transcriber: the orchestrator owns
    # the repository, and routing it via FasterWhisperTranscriber's lower edge
    # drew an ownership that does not exist in the code.
    arrow(ax, (ob[0], ob[1] - ob[3] / 2), (rb[0] + rb[2] / 2, rb[1]),
          colour=GREY, rad=0.34)
    arrow(ax, bottom_of(yb), top_of(db), "produces", 7.2, colour=NAVY)
    arrow(ax, top_of(sb), bottom_of(vb), colour=GREY, style="-", dash=(0, (4, 3)))
    c.save("class_diagram.png")


# ------------------------------------------------------------------------- ER

def er_diagram():
    c = Canvas(13, 7)
    ax = c.ax

    vm = stack_box(ax, 35, 96, 30, "VideoMetadata",
                   [("video_id", "pk"), ("filename", ""), ("duration_sec", ""),
                    ("processed_status", ""), ("overlay_context", "")])

    # Four children on ONE row. A three-plus-two layout put the second row's
    # boxes below y=0, where they were drawn off-canvas entirely.
    kids = [
        ("AudioFlags", [("audio_flag_id", "pk"), ("video_id", "fk"),
                        ("word_flagged", ""), ("severity", ""),
                        ("detection_model", "")]),
        ("VisualFlags", [("visual_flag_id", "pk"), ("video_id", "fk"),
                         ("object_detected", ""), ("risk_category", ""),
                         ("detection_model", "")]),
        ("AdSpots", [("spot_id", "pk"), ("video_id", "fk"), ("spot_type", ""),
                     ("suitability_score", "")]),
        ("AuditReports", [("report_id", "pk"), ("video_id", "fk"),
                          ("report_type", ""), ("compliance_status", "")]),
    ]
    kw, gap, x0 = 23.0, 2.0, 1.5
    boxes = [stack_box(ax, x0 + i * (kw + gap), 58, kw, name, cols)
             for i, (name, cols) in enumerate(kids)]

    stack_box(ax, 35, 22, 30, "SystemConfig",
              [("config_key", "pk"), ("config_value", ""), ("config_type", "")])

    for b in boxes:
        arrow(ax, bottom_of(vm), top_of(b), "1 : N", 7.0, colour=NAVY, style="-")

    label(ax, 68, 18, "independent —\nholds application settings", size=7.4,
          colour=GREY, italic=True)
    label(ax, 1.5, 12, "PK   primary key", size=7.4, colour=RED, bold=True)
    label(ax, 1.5, 7.5, "FK   foreign key", size=7.4, colour=GOLD, bold=True)
    label(ax, 1.5, 3, "Every child relationship is ON DELETE CASCADE.",
          size=7.4, colour=GREY, italic=True)
    c.save("er_diagram.png")
# ------------------------------------------------------------------------ wbs

def wbs():
    c = Canvas(13, 6.4)
    ax = c.ax

    box(ax, 30, 90, 40, 8, "ADSAFE STUDIO\nSpecialization Project", size=10)

    phases = [
        ("1   ANALYSIS AND\nSPECIFICATION", [
            "1.1  Requirement gathering\nand justification",
            "1.2  System analysis",
            "1.3  Software requirement\nspecification"]),
        ("2   DESIGN", [
            "2.1  Database and\narchitecture design",
            "2.2  User interface\ndesign"]),
        ("3   IMPLEMENTATION", [
            "3.1  Audio engine",
            "3.2  Vision engine",
            "3.3  Advertisement\nplacement algorithm",
            "3.4  Model training",
            "3.5  Report generation"]),
        ("4   VALIDATION", [
            "4.1  Accuracy\nbenchmarking",
            "4.2  Testing and\ndocumentation"]),
    ]

    colw, gap, x0 = 22.5, 2.5, 1.25
    centres = [x0 + i * (colw + gap) + colw / 2 for i in range(4)]

    # Trunk: root down to a spanning rail, then a drop into each phase.
    ax.plot([50, 50], [90, 86.5], color=RULE, lw=1.4, zorder=1)
    ax.plot([centres[0], centres[-1]], [86.5, 86.5], color=RULE, lw=1.4,
            zorder=1)
    for cx in centres:
        ax.plot([cx, cx], [86.5, 83], color=RULE, lw=1.4, zorder=1)

    for i, (name, leaves) in enumerate(phases):
        x = x0 + i * (colw + gap)
        box(ax, x, 74, colw, 9, name, size=8.6)

        spine = x + 1.8
        lx, lw_ = x + 4.0, colw - 4.0
        last_cy = None
        for j, leaf in enumerate(leaves):
            y = 68 - j * 9.0 - 7
            cy = y + 3.5
            box(ax, lx, y, lw_, 7, leaf, fill=WASH, fg=INK, size=6.5,
                bold=False, edge=RULE)
            ax.plot([spine, lx], [cy, cy], color=RULE, lw=1.2, zorder=1)
            last_cy = cy
        ax.plot([spine, spine], [74, last_cy], color=RULE, lw=1.2, zorder=1)

    label(ax, 50, 16,
          "Twelve work packages across four phases. Packages 3.1 to 3.5 "
          "correspond to the four implementation modules of Table 3.3.",
          size=8.2, colour=GREY, ha="center", italic=True)
    c.save("wbs.png")


# ----------------------------------------------------------------------- pert

PERT_RX = 3.8


def _pert_node(c, ax, cx, cy, tid, weeks, critical):
    rx = PERT_RX
    ry = c.sq(rx)
    fill = NAVY if critical else "white"
    fg = "white" if critical else NAVY
    ax.add_patch(Ellipse((cx, cy), rx * 2, ry * 2, facecolor=fill,
                         edgecolor=NAVY, lw=1.5, zorder=3))
    label(ax, cx, cy + 2.2, tid, size=9.0, colour=fg, bold=True, ha="center")
    label(ax, cx, cy - 3.0, f"{weeks} w", size=6.8, colour=fg, ha="center")
    return (cx, cy, rx, ry)


def _pert_edge(ax, a, b, critical=False):
    """Trim the arrow to the two ellipse boundaries.

    Nodes must be spaced wider than the sum of their radii or the trimmed
    arrow has no length left and renders as nothing -- T11 to T12 disappeared
    entirely the first time this was drawn.
    """
    (x1, y1, rx1, ry1), (x2, y2, rx2, ry2) = a, b
    dx, dy = x2 - x1, y2 - y1
    d = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / d, dy / d
    t1 = 1.0 / ((ux / rx1) ** 2 + (uy / ry1) ** 2) ** 0.5
    t2 = 1.0 / ((ux / rx2) ** 2 + (uy / ry2) ** 2) ** 0.5
    ax.add_patch(FancyArrowPatch(
        (x1 + ux * t1, y1 + uy * t1), (x2 - ux * t2, y2 - uy * t2),
        arrowstyle="-|>", mutation_scale=13,
        linewidth=2.1 if critical else 1.2,
        color=RED if critical else GREY, zorder=1))


def pert():
    c = Canvas(13, 7)
    ax = c.ax

    crit = {"T1", "T2", "T3", "T4", "T7", "T9", "T10", "T11", "T12"}
    placed = {}
    spec = [
        ("T1", 4.5, 62, 1), ("T2", 15, 62, 1), ("T3", 25.5, 62, 1),
        ("T4", 36, 62, 1),
        ("T5", 50, 88, 2), ("T6", 50, 72, 1), ("T7", 50, 54, 2),
        ("T8", 50, 38, 1),
        ("T9", 62, 54, 1), ("T10", 74, 62, 1), ("T11", 85, 62, 1),
        ("T12", 96, 62, 1),
    ]
    for tid, x, y, weeks in spec:
        placed[tid] = _pert_node(c, ax, x, y, tid, weeks, tid in crit)

    links = [
        ("T1", "T2"), ("T2", "T3"), ("T3", "T4"),
        ("T4", "T5"), ("T4", "T6"), ("T4", "T7"), ("T4", "T8"),
        ("T7", "T9"),
        ("T5", "T10"), ("T6", "T10"), ("T8", "T10"), ("T9", "T10"),
        ("T10", "T11"), ("T11", "T12"),
    ]
    for a, b in links:
        _pert_edge(ax, placed[a], placed[b], a in crit and b in crit)

    names = ("T1 requirements   T2 analysis   T3 SRS   T4 design   "
             "T5 interface   T6 audio engine\n"
             "T7 vision engine   T8 placement algorithm   T9 model training   "
             "T10 reporting   T11 benchmarking   T12 testing")
    label(ax, 50, 22, names, size=7.4, colour=GREY, ha="center")

    ax.add_patch(patches.Rectangle((2, 6), 96, 9, facecolor=WASH,
                                   edgecolor=RULE, lw=1.0, zorder=1))
    label(ax, 5, 11.8, "CRITICAL PATH", size=8.0, colour=RED, bold=True)
    label(ax, 5, 8.4,
          "T1 - T2 - T3 - T4 - T7 - T9 - T10 - T11 - T12   =   10 weeks",
          size=7.8, colour=INK)
    label(ax, 55, 11.8,
          "Total scheduled effort is 14 weeks (Table 3.2).", size=7.6,
          colour=GREY)
    label(ax, 55, 8.4,
          "The difference is slack on the parallel branches T5, T6 and T8.",
          size=7.6, colour=GREY)
    c.save("pert.png")


# ---------------------------------------------------------------------- gantt

GANTT_TASKS = [
    ("T1", "Requirement gathering", 1, 1),
    ("T2", "System analysis", 2, 1),
    ("T3", "SRS preparation", 3, 1),
    ("T4", "Database and architecture design", 4, 1),
    ("T5", "User interface design", 5, 2),
    ("T6", "Audio engine", 7, 1),
    ("T7", "Vision engine", 8, 2),
    ("T8", "Advertisement placement algorithm", 10, 1),
    ("T9", "Model training and evaluation", 11, 1),
    ("T10", "Report generation", 12, 1),
    ("T11", "Accuracy benchmarking", 13, 1),
    ("T12", "Testing and documentation", 14, 1),
]
GANTT_CRITICAL = {"T1", "T2", "T3", "T4", "T7", "T9", "T10", "T11", "T12"}


def gantt():
    c = Canvas(13, 7)
    ax = c.ax

    left, right = 28.0, 96.0
    week = (right - left) / 14.0
    top, bottom = 86.0, 16.0
    pitch = (top - bottom) / len(GANTT_TASKS)

    for i in range(15):
        x = left + i * week
        ax.plot([x, x], [bottom - 1, top + 1], color=RULE, lw=0.7,
                zorder=0, alpha=0.55)
    for i in range(14):
        label(ax, left + (i + 0.5) * week, top + 4.6, f"W{i + 1}", size=7.0,
              colour=NAVY, bold=True, ha="center")

    ax.plot([left - 0.4, right], [top + 1, top + 1], color=NAVY, lw=1.3,
            zorder=1)

    for i, (tid, name, start, dur) in enumerate(GANTT_TASKS):
        cy = top - (i + 0.5) * pitch
        label(ax, 1.5, cy, tid, size=7.4, colour=NAVY, bold=True)
        label(ax, 6.5, cy, name, size=7.4, colour=INK)
        ax.add_patch(patches.Rectangle(
            (left + (start - 1) * week, cy - 1.9), dur * week, 3.8,
            facecolor=NAVY if tid in GANTT_CRITICAL else PALE,
            edgecolor=NAVY, lw=1.1, zorder=2))
        label(ax, left + (start - 1 + dur) * week + 1.2, cy,
              f"{dur} w", size=6.6, colour=GREY)

    ax.add_patch(patches.Rectangle((28, 6.5), 3.6, 3.2, facecolor=NAVY,
                                   edgecolor=NAVY, zorder=2))
    label(ax, 33, 8.1, "on the critical path", size=7.4, colour=INK)
    ax.add_patch(patches.Rectangle((60, 6.5), 3.6, 3.2, facecolor=PALE,
                                   edgecolor=NAVY, zorder=2))
    label(ax, 65, 8.1, "carries slack", size=7.4, colour=INK)
    c.save("gantt.png")


# ------------------------------------------------------------------- dfd zero

def _ellipse_edge(cx, cy, rx, ry, y, right):
    dy = max(-0.94, min(0.94, (y - cy) / ry))
    dx = rx * (1 - dy * dy) ** 0.5
    return (cx + dx if right else cx - dx, y)


def dfd_level0():
    c = Canvas(13, 6.6)
    ax = c.ax

    cx, cy, rx = 50.0, 57.0, 15.5
    ry = c.sq(rx)

    box(ax, 2, 44, 19, 26, "CREATOR", size=9.5)
    box(ax, 79, 44, 19, 26, "LOCAL\nMODEL STORE", size=9.5)

    ax.add_patch(Ellipse((cx, cy), rx * 2, ry * 2, facecolor=PALE,
                         edgecolor=NAVY, lw=1.8, zorder=2))
    label(ax, cx, cy + 5.5, "0", size=11, colour=NAVY, bold=True, ha="center")
    label(ax, cx, cy - 2.0, "VIDEO ANALYSIS\nSYSTEM", size=9.5, colour=NAVY,
          bold=True, ha="center")

    for y, text in ((68, "video file"), (60, "analysis request")):
        arrow(ax, (21, y), _ellipse_edge(cx, cy, rx, ry, y, right=False), text,
              size=7.4, ty=2.2)
    for y, text in ((51, "compliance verdict and findings"),
                    (43, "exported report")):
        arrow(ax, _ellipse_edge(cx, cy, rx, ry, y, right=False), (21, y), text,
              size=7.4, ty=2.2)
    for y, text in ((64, "transcription model"), (52, "detection weights")):
        arrow(ax, (79, y), _ellipse_edge(cx, cy, rx, ry, y, right=True), text,
              size=7.4, ty=2.2)

    label(ax, 50, 94, "CONTEXT DIAGRAM", size=9.0, colour=NAVY, bold=True,
          ha="center")
    label(ax, 50, 17,
          "No data flow crosses to any external service. The model store is a "
          "directory on the same machine,\nso the diagram has no third entity "
          "-- which is the property that distinguishes this system from a "
          "cloud service.",
          size=7.8, colour=RED, ha="center")
    c.save("dfd_level0.png")


# ------------------------------------------------------------------- sequence

def sequence():
    c = Canvas(13, 7)
    ax = c.ax

    label(ax, 50, 97,
          "Engines run one after another -- a single database writer, and no "
          "contention for memory.",
          size=7.8, colour=RED, bold=True, ha="center")

    actors = [("INTERFACE", 9), ("API", 25), ("ORCHESTRATOR", 43),
              ("AUDIO ENGINE", 60), ("VISION ENGINE", 76), ("DATABASE", 92)]
    lanes = {}
    for name, x in actors:
        box(ax, x - 7.6, 86, 15.2, 7, name, size=7.4)
        ax.plot([x, x], [86, 9], color=RULE, lw=1.1, linestyle=(0, (4, 3)),
                zorder=0)
        lanes[name.split()[0]] = x

    ui, api = lanes["INTERFACE"], lanes["API"]
    orc, aud = lanes["ORCHESTRATOR"], lanes["AUDIO"]
    vis, db = lanes["VISION"], lanes["DATABASE"]

    # Orchestrator holds the pipeline open for its whole run.
    ax.add_patch(patches.Rectangle((orc - 1.5, 22), 3.0, 50, facecolor=PALE,
                                   edgecolor=NAVY, lw=1.0, zorder=2))

    msgs = [
        (ui, api, 82, "POST /api/videos/{id}/analyze", None),
        (api, ui, 76, "202 Accepted -- queued", "dashed"),
        (api, orc, 70, "run_pipeline(video_id)", None),
        (orc, aud, 63, "extract -> transcribe -> match", None),
        (aud, db, 56, "insert AudioFlags", None),
        (orc, vis, 49, "sample frames -> detect at two scales", None),
        (vis, db, 42, "insert VisualFlags", None),
        (orc, vis, 35, "free-space scan -> track >= 5 s", None),
        (vis, db, 28, "insert AdSpots", None),
        (orc, db, 22, "write verdict and reasoning", None),
        (ui, api, 15, "GET /api/videos/{id}   (polled)", None),
        (api, ui, 9, "verdict, findings, progress", "dashed"),
    ]
    for x1, x2, y, text, dash in msgs:
        arrow(ax, (x1, y), (x2, y), text, size=6.8, ty=2.4, dash=dash)

    footnote(ax, "The API returns before the analysis completes, so the "
                 "interface stays responsive and polls for progress.")
    c.save("sequence.png")


# ---------------------------------------------------------------- incremental

def incremental():
    c = Canvas(13, 7)
    ax = c.ax

    phases = ["Analysis", "Design", "Implementation", "Testing", "Evaluation"]
    increments = [
        "Increment 1  --  Skeleton: database, API, interface, deterministic "
        "stand-in for every engine",
        "Increment 2  --  Audio engine: extraction, transcription, keyword "
        "matching",
        "Increment 3  --  Vision engine: object detection, free-space "
        "placement algorithm",
        "Increment 4  --  Overlay context, verdict reasoning, accuracy "
        "benchmarking",
    ]

    pw, pgap, h = 11.0, 1.1, 10.0
    rows = [6.0, 28.5, 51.0, 73.5]
    for i, (base, title) in enumerate(zip(rows, increments)):
        x0 = 2.0 + i * 7.0
        # Offset from the row start so the staircase connector, which rises at
        # x0 + 12.5, does not run straight through the text.
        label(ax, x0 + 22, base + h + 3.0, title, size=7.8, colour=NAVY,
              bold=True)
        for j, phase in enumerate(phases):
            x = x0 + j * (pw + pgap)
            box(ax, x, base, pw, h, phase,
                fill=NAVY if j == 0 else PALE,
                fg="white" if j == 0 else NAVY, size=7.0)
            if j:
                arrow(ax, (x - pgap - 0.2, base + h / 2),
                      (x - 0.2, base + h / 2), colour=GREY)
        end_x = x0 + 4 * (pw + pgap) + pw
        box(ax, end_x + 2.0, base + 1.4, 13.5, h - 2.8,
            f"Working\nsystem {i + 1}", fill=WASH, fg=NAVY, size=7.0,
            edge=RULE)

    for i in range(3):
        nx0 = 2.0 + (i + 1) * 7.0
        arrow(ax, (nx0 + 5.5, rows[i] + h + 0.5), (nx0 + 5.5, rows[i + 1] - 0.5),
              colour=NAVY, dash="dashed")

    footnote(ax, "Each increment replaces one stand-in with a working "
                 "implementation. The pipeline runs from increment 1 onward, "
                 "so there is no phase in which the system does not operate.")
    c.save("incremental.png")
# --------------------------------------------------------------- state chart

def state_diagram():
    c = Canvas(13, 7)
    ax = c.ax

    def state(x, y, w, h, name, sub=""):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0,rounding_size=2.2",
                                    linewidth=1.8, edgecolor=NAVY,
                                    facecolor=PALE, zorder=2))
        label(ax, x + w / 2, y + h - (5.4 if sub else h / 2), name, size=9.4,
              colour=NAVY, bold=True, ha="center")
        if sub:
            label(ax, x + w / 2, y + h - 11.4, sub, size=7.0, colour=GREY,
                  ha="center")
        return (x, y, w, h)

    def right(b):
        return (b[0] + b[2], b[1] + b[3] / 2)

    def left(b):
        return (b[0], b[1] + b[3] / 2)

    def top(b):
        return (b[0] + b[2] / 2, b[1] + b[3])

    def bottom(b):
        return (b[0] + b[2] / 2, b[1])

    ax.add_patch(Ellipse((5, 69), 3.0, c.sq(3.0), facecolor=NAVY,
                         edgecolor=NAVY, zorder=3))

    pending = state(13, 61, 21, 16, "pending", "queued, never analysed")
    running = state(42, 61, 24, 16, "processing", "engines running in turn")
    done = state(74, 61, 23, 16, "completed", "verdict written")
    failed = state(42, 26, 24, 16, "failed", "engine raised an error")

    arrow(ax, (6.6, 69), left(pending), "upload", 7.4, ty=2.6)
    arrow(ax, right(pending), left(running), "run checks", 7.4, ty=2.6)
    arrow(ax, right(running), left(done), "pipeline finished", 7.4, ty=2.6)
    arrow(ax, bottom(running), top(failed), colour=GREY)
    label(ax, 55.5, 51, "unrecoverable error", size=7.4, colour=INK)

    # Re-run returns a completed video to processing, over the top.
    ax.plot([85.5, 85.5], [77, 90], color=GREY, lw=1.3, zorder=1)
    ax.plot([85.5, 54], [90, 90], color=GREY, lw=1.3, zorder=1)
    arrow(ax, (54, 90), (54, 77), colour=GREY)
    label(ax, 70, 92.2, "re-run checks", size=7.4, colour=INK, ha="center")

    # A failed video can be run again, underneath.
    ax.plot([66, 71], [34, 34], color=GREY, lw=1.3, zorder=1)
    ax.plot([71, 71], [34, 47], color=GREY, lw=1.3, zorder=1)
    ax.plot([71, 60], [47, 47], color=GREY, lw=1.3, zorder=1)
    arrow(ax, (60, 47), (60, 61), colour=GREY)
    label(ax, 72.6, 40, "retry", size=7.4, colour=INK)

    ax.add_patch(Ellipse((88, 45), 4.4, c.sq(4.4), facecolor="white",
                         edgecolor=NAVY, lw=1.6, zorder=3))
    ax.add_patch(Ellipse((88, 45), 2.4, c.sq(2.4), facecolor=NAVY,
                         edgecolor=NAVY, zorder=4))
    arrow(ax, (85.5, 61), (88, 49.6), colour=GREY)
    label(ax, 90.6, 55, "record\ndeleted", size=7.4, colour=INK)

    label(ax, 4, 14,
          "A completed video also carries one of three advertiser-suitability "
          "verdicts — Monetizable, Review or Restricted — with the reasoning "
          "that produced it.\nThe verdict is an attribute of the completed "
          "state rather than a state of its own: it is recomputed from "
          "scratch on every re-run.",
          size=7.8, colour=RED)
    footnote(ax, "Lifecycle of a VideoMetadata record. The schema constrains "
                 "processed_status to exactly these four values.")
    c.save("state_diagram.png")


# -------------------------------------------------------- control flow chart

def control_flow():
    c = Canvas(13, 7.6)
    ax = c.ax

    BW, BH = 34.0, 8.6
    LX, RX = 8.0, 58.0
    LCX, RCX = LX + BW / 2, RX + BW / 2
    rows = [88.0, 76.2, 64.4, 52.6, 40.8, 29.0, 17.2]
    RAIL = 2.2                      # outside both columns, so nothing crosses

    def step(x, i, text, fill=PALE, fg=NAVY):
        y = rows[i] - BH
        box(ax, x, y, BW, BH, text, fill=fill, fg=fg, size=7.5, bold=False,
            edge=RULE)
        return (x + BW / 2, y, y + BH)

    def terminal(x, i, text, fill=NAVY, fg="white"):
        y = rows[i] - BH
        ax.add_patch(FancyBboxPatch((x + 6, y), BW - 12, BH,
                                    boxstyle="round,pad=0,rounding_size=4.2",
                                    linewidth=1.6, edgecolor=NAVY,
                                    facecolor=fill, zorder=2))
        label(ax, x + BW / 2, y + BH / 2, text, size=8.2, colour=fg,
              bold=True, ha="center")
        return (x + BW / 2, y, y + BH)

    def down(a, b):
        arrow(ax, (a[0], a[1]), (b[0], b[2]), colour=GREY)

    label(ax, LX, 94.5, "AUDIO AND LANGUAGE STAGE", size=8.4, colour=NAVY,
          bold=True)
    a0 = terminal(LX, 0, "START · analyse(video_id)")
    a1 = step(LX, 1, "Read pipeline configuration\nfrom SystemConfig")
    a2 = step(LX, 2, "Extract the audio track to WAV\n(per-process filename)")
    dy = rows[3] - BH / 2
    # Height 11, not 17: at 17 the diamond's lower vertex reached past the top
    # of the next box and swallowed its own "yes" exit arrow.
    diamond(ax, LCX, dy, 28, 11, "audio track\npresent?")
    a4 = step(LX, 4, "Transcribe with faster-whisper,\nword-level timestamps")
    a5 = step(LX, 5, "Match each word against the\nrestricted dictionary")
    a6 = step(LX, 6, "Write AudioFlags rows, each\nrecording its engine")

    down(a0, a1)
    down(a1, a2)
    arrow(ax, (LCX, a2[1]), (LCX, dy + 5.5), colour=GREY)
    arrow(ax, (LCX, dy - 5.5), (LCX, a4[2]), colour=GREY)
    label(ax, LCX + 2.2, dy - 7.4, "yes", size=7.0, colour=INK)
    down(a4, a5)
    down(a5, a6)

    label(ax, RX, 94.5, "VISION, PLACEMENT AND VERDICT STAGE", size=8.4,
          colour=NAVY, bold=True)
    b0 = step(RX, 0, "Sample frames at the configured\nrate (1 fps)")
    b1 = step(RX, 1, "Detect at 640 px and at native\nwidth; merge by IoU → VisualFlags")
    b2 = step(RX, 2, "Persistent-overlay analysis\n(streaming temporal variance)")
    b3 = step(RX, 3, "Free-space scan: largest clear\nrectangle in each frame")
    b4 = step(RX, 4, "Keep only surfaces that persist\nfor five seconds or more")
    b5 = step(RX, 5, "assess_compliance(): verdict\nand its printed reasoning",
              fill=WASH)
    b6 = terminal(RX, 6, "END · status completed", fill="white", fg=NAVY)

    for a, b in ((b0, b1), (b1, b2), (b2, b3), (b3, b4), (b4, b5), (b5, b6)):
        down(a, b)

    # Both the "no" branch and the finished audio stage join one rail that runs
    # outside the left column and over the top, so no connector crosses a box.
    ax.plot([LCX - 14, RAIL], [dy, dy], color=GREY, lw=1.3, zorder=1)
    label(ax, LCX - 13.0, dy + 2.6, "no", size=7.0, colour=INK)
    ax.plot([LCX, LCX], [a6[1], 9.0], color=GREY, lw=1.3, zorder=1)
    ax.plot([LCX, RAIL], [9.0, 9.0], color=GREY, lw=1.3, zorder=1)
    ax.plot([RAIL, RAIL], [9.0, 97.0], color=GREY, lw=1.3, zorder=1)
    ax.plot([RAIL, RCX], [97.0, 97.0], color=GREY, lw=1.3, zorder=1)
    arrow(ax, (RCX, 97.0), (RCX, rows[0]), colour=GREY)
    label(ax, 30, 6.2, "audio stage complete", size=7.0, colour=INK)

    footnote(ax, "The engines run strictly in sequence: a single database "
                 "writer, and no contention for memory between Whisper "
                 "and YOLO.")
    c.save("control_flow.png")


if __name__ == "__main__":
    print("writing diagrams to", OUT)
    architecture()
    use_case()
    dfd()
    activity()
    class_diagram()
    er_diagram()
    wbs()
    pert()
    gantt()
    dfd_level0()
    sequence()
    incremental()
    state_diagram()
    control_flow()
    print("done")
