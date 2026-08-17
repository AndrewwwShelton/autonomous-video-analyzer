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


if __name__ == "__main__":
    print("writing diagrams to", OUT)
    architecture()
    use_case()
    dfd()
    activity()
    class_diagram()
    er_diagram()
    print("done")
