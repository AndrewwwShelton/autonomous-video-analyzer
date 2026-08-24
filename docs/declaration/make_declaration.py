"""Fill in the CHRIST AI Usage and Contribution Declaration for this project.

    python docs/declaration/make_declaration.py

Writes AI_Declaration_AdSafe.pdf to the repository root.

The blank form is ~/Downloads/AI_Disclosure_for_Project_submission_.pdf. That
original is a LaTeX document and there is no TeX toolchain on this machine, so
this reproduces its structure -- same title, same section numbering, same table
columns, same order -- with the fields filled in, rather than overlaying text
onto the original's fixed-size cells, which the real content overflows.

Everything entered here is drawn from the project record and the git history.
Two fields are deliberately left blank because they cannot be derived from the
repository: the class Section, and the signature cells. Nobody should sign this
except the students named in it.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = Path(__file__).resolve().parents[2] / "AI_Declaration_AdSafe.pdf"

SERIF = "Times-Roman"
SERIF_B = "Times-Bold"
SERIF_I = "Times-Italic"
RULE = colors.black
BLANK = " " * 40          # a line for a field we must not invent

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Normal"], fontName=SERIF_B,
                    fontSize=14.5, leading=19, alignment=TA_CENTER,
                    spaceAfter=2)
H2 = ParagraphStyle("H2", parent=styles["Normal"], fontName=SERIF_B,
                    fontSize=12, leading=15, spaceBefore=13, spaceAfter=7)
H3 = ParagraphStyle("H3", parent=styles["Normal"], fontName=SERIF_B,
                    fontSize=11, leading=14, spaceBefore=11, spaceAfter=6)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontName=SERIF,
                      fontSize=10, leading=13.5, alignment=TA_JUSTIFY,
                      spaceAfter=6)
NOTE = ParagraphStyle("NOTE", parent=BODY, fontName=SERIF_I, fontSize=9,
                      leading=12)
CELL = ParagraphStyle("CELL", parent=styles["Normal"], fontName=SERIF,
                      fontSize=8.6, leading=11)
CELL_B = ParagraphStyle("CELL_B", parent=CELL, fontName=SERIF_B)
CELL_C = ParagraphStyle("CELL_C", parent=CELL, alignment=TA_CENTER)
FIELD = ParagraphStyle("FIELD", parent=styles["Normal"], fontName=SERIF,
                       fontSize=10.5, leading=15)
FIELD_B = ParagraphStyle("FIELD_B", parent=FIELD, fontName=SERIF_B)


def p(text, style=CELL):
    return Paragraph(text, style)


GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.6, RULE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.93, 0.93)),
])


# --------------------------------------------------------------- the content

TITLE = ("Autonomous Video Ad-Placement and Contextual Safety Analyzer "
         "(AdSafe Studio)")

DETAILS = [
    ("Project Title:", TITLE),
    ("Programme:", "Bachelor of Computer Applications (BCA) &mdash; BCA482-5, "
                   "Specialization Project"),
    ("Semester / Section:", "V / 5BCA-B"),
    ("Academic Year:", "2026&ndash;27"),
    ("Project Guide:", "Dr. Chanti.S, Assistant Professor, "
                       "Department of Computer Science"),
]

TOOLS = [
    ["1",
     "Claude (Anthropic)<br/>Opus 5 and Opus 4.8,<br/>used through the "
     "Claude&nbsp;Code CLI",
     "Code generation and refactoring; debugging; algorithm and methodology "
     "suggestions; drafting of the report, presentation and project "
     "documentation; generation of diagrams and figures.",
     "Implementation of all four modules; Stage&nbsp;5 report; presentation "
     "deck; supporting documentation. Nearly every commit in the project "
     "repository records an AI co-author."],
    ["2", "", "", ""],
    ["3", "", "", ""],
    ["4", "", "", ""],
]

ASSISTANCE = [
    ("Concept clarification / learning", "Yes",
     "Behaviour of YOLOv8 and Whisper; SQLite WAL journaling and foreign-key "
     "enforcement; CSS flex and grid sizing rules."),
    ("Brainstorming / idea generation", "Yes",
     "Approaches for locating advertisement surfaces, and for distinguishing "
     "rendered game content from filmed content."),
    ("Literature / research assistance", "Yes",
     "Sourcing published demonetization statistics used to justify the "
     "problem; verifying which risk classes the Open Images V7 taxonomy can "
     "actually supply."),
    ("Programming / code generation", "Yes",
     "Source code across the backend, frontend and AI pipeline was drafted "
     "with AI assistance and then reviewed, tested and modified by us."),
    ("Code debugging", "Yes",
     "Startup traceback caused by a NumPy&nbsp;2 ABI mismatch; partial data "
     "loss on demo reset; missed weapon detections on real footage; "
     "horizontal layout overflow; a race that suppressed the progress bar."),
    ("Algorithm / methodology suggestions", "Yes",
     "Maximal-rectangle search for free advertisement space; temporal-variance "
     "detection of persistent overlays; multi-scale inference for objects at "
     "differing distances."),
    ("Data analysis / interpretation", "Yes",
     "Interpreting mAP@50 against observed behaviour on real video, which led "
     "us to reject fine-tuning run&nbsp;2 despite its better validation "
     "scores."),
    ("Report writing / documentation", "Yes",
     "Drafting the Stage&nbsp;5 report in the prescribed format, and the "
     "README, roadmap and project record."),
    ("Grammar / language improvement", "Yes",
     "Editing and rephrasing throughout the report and the presentation."),
    ("Images / diagrams", "Yes",
     "All twelve system-model and project-planning diagrams were generated "
     "programmatically with matplotlib; the interface screenshots are "
     "captured by a script."),
    ("Other", "Yes",
     "Generation of the presentation deck; automation of screenshot capture "
     "and of layout regression checks."),
]

INTERACTIONS = [
    ("22 Jul 2026", "Claude Code",
     "Scaffold the application: FastAPI backend, React interface, SQLite "
     "schema, with a deterministic stand-in for each AI engine.",
     "Generated code was read, run and extended by us; retained as the "
     "project baseline."),
    ("01 Aug 2026", "Claude Code",
     "Replace the stand-in transcriber with faster-whisper, including "
     "word-level timestamps required by the AudioFlags schema.",
     "Integrated after we tested it against sample audio and confirmed the "
     "timestamps aligned."),
    ("02&ndash;03 Aug 2026", "Claude Code",
     "Prepare an Open Images V7 subset and fine-tune YOLOv8 for the project's "
     "risk classes.",
     "We ran the training ourselves. Run&nbsp;1 was accepted (mAP@50 0.566); "
     "run&nbsp;2 was rejected after we tested it on real video."),
    ("03 Aug 2026", "Claude Code",
     "Design and implement the free-space advertisement placement algorithm.",
     "Implemented, then verified by us against sample footage before "
     "acceptance."),
    ("07 Aug 2026", "Claude Code",
     "Diagnose why a firearm visible in real footage was not detected, and "
     "propose a correction.",
     "Multi-scale inference adopted only after we confirmed it worked on both "
     "a distant and a close-up clip."),
    ("07 Aug 2026", "Claude Code",
     "Detect persistent on-screen overlays so that weapons rendered inside a "
     "game are weighed differently from filmed ones.",
     "We tested it on real gameplay footage; the stability threshold was "
     "changed to a relative one because the first version missed real HUDs."),
    ("16&ndash;17 Aug 2026", "Claude Code",
     "Draft the Stage&nbsp;5 report in the prescribed LaTeX format and "
     "generate the system-model diagrams.",
     "Reviewed and corrected by us; several diagrams were regenerated after "
     "we found geometry errors on inspection."),
    ("20 Aug 2026", "Claude Code",
     "Automate capture of the interface screenshots, and correct the defects "
     "that the automation exposed.",
     "Fixes reviewed and accepted after the full test suite (169 tests) was "
     "re-run and passed."),
]

STUDENTS = [
    ("1", "Andrew Shelton S", "2441609"),
    ("2", "Akash Ganesh", "2441604"),
    ("3", "Andrew Judah", "2441608"),
    ("4", "Ramona Elisha Mary", "2441646"),
    ("5", "", ""),
]

CONFIRMATIONS = [
    "We have reviewed and verified all AI-assisted content incorporated into "
    "the project.",
    "We understand and can explain the concepts, methodology, implementation, "
    "code, analysis, results, and conclusions presented in the project.",
    "We have not knowingly submitted AI-generated work as our original work "
    "without appropriate review or acknowledgement.",
    "AI tools have not been used to fabricate or manipulate data, results, "
    "observations, references, or research evidence.",
    "Any AI-generated code used in the project has been tested, understood, "
    "and modified where necessary.",
    "We accept full responsibility for the accuracy, originality, and academic "
    "integrity of the submitted work.",
]


def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="AI Usage and Contribution Declaration — AdSafe Studio",
        author="Andrew Shelton S, Akash Ganesh, Andrew Judah, "
               "Ramona Elisha Mary")
    W = doc.width
    s = []

    s.append(Paragraph("ARTIFICIAL INTELLIGENCE (AI) USAGE", H1))
    s.append(Paragraph("AND CONTRIBUTION DECLARATION", H1))
    s.append(Paragraph("5 BCA SPECIALIZATION PROJECT", H1))
    s.append(Spacer(1, 14))

    # ---------------------------------------------------------- 1. Details
    s.append(Paragraph("1. Project Details", H2))
    rows = [[Paragraph(k, FIELD_B), Paragraph(v, FIELD)] for k, v in DETAILS]
    t = Table(rows, colWidths=[4.3 * cm, W - 4.3 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (1, 0), (1, -1), 0.5, RULE),
    ]))
    s.append(t)

    # ------------------------------------------------------ 2. Declaration
    s.append(Paragraph("2. AI Usage Declaration", H2))
    for text in (
        "We, the undersigned students, declare that Artificial Intelligence "
        "(AI) tools, wherever used during the preparation and development of "
        "this project, were used as supportive tools with academic "
        "responsibility.",
        "We have disclosed the AI tools used and the nature of their "
        "contribution below. We understand that the use of AI tools does not "
        "replace our responsibility for the academic, technical, and "
        "intellectual work submitted as part of this project.",
        "All AI-assisted content, code, suggestions, or analysis incorporated "
        "into the project has been reviewed, verified, tested, and "
        "appropriately modified by us.",
    ):
        s.append(Paragraph(text, BODY))

    s.append(Paragraph("2.1 AI Tools Used", H3))
    head = [p("S<br/>No.", CELL_B), p("AI Tool", CELL_B),
            p("Purpose of Use", CELL_B), p("Project Section / Stage", CELL_B)]
    body = [[p(c[0], CELL_C), p(c[1]), p(c[2]), p(c[3])] for c in TOOLS]
    t = Table([head] + body,
              colWidths=[1.1 * cm, 4.0 * cm, 6.2 * cm, W - 11.3 * cm],
              rowHeights=[None, None, 1.0 * cm, 1.0 * cm, 1.0 * cm])
    t.setStyle(GRID)
    s.append(t)
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "Rows 2&ndash;4 are left blank for any further tool used by an "
        "individual team member. faster-whisper and Ultralytics YOLOv8 are "
        "not listed above: they are pretrained models that form part of the "
        "delivered system itself rather than authoring aids, and they are "
        "documented in the implementation chapter of the report.", NOTE))

    s.append(PageBreak())

    # ----------------------------------------------- 2.2 Nature of assistance
    s.append(Paragraph("2.2 Nature of AI Assistance", H3))
    s.append(Paragraph(
        "Tick or mark the applicable options and provide a brief description "
        "where necessary.", BODY))
    head = [p("Type of Assistance", CELL_B), p("Used", CELL_B),
            p("Brief Description", CELL_B)]
    body = [[p(a), p("<b>Yes</b>", CELL_C), p(c)] for a, _, c in ASSISTANCE]
    t = Table([head] + body, colWidths=[5.4 * cm, 1.4 * cm, W - 6.8 * cm],
              repeatRows=1)
    t.setStyle(GRID)
    s.append(t)

    # ------------------------------------------------- 3. Responsibility
    s.append(Paragraph("3. Student Responsibility and Authenticity", H2))
    s.append(Paragraph("We confirm that:", BODY))
    for i, c in enumerate(CONFIRMATIONS, 1):
        s.append(Paragraph(f"{i}.&nbsp;&nbsp;{c}", ParagraphStyle(
            f"c{i}", parent=BODY, leftIndent=16, firstLineIndent=-16,
            spaceAfter=5)))

    s.append(PageBreak())

    # --------------------------------------------- 3.1 Interaction record
    s.append(Paragraph("3.1 Significant AI Interaction Record", H3))
    s.append(Paragraph(
        "Complete this section when AI has been substantially used for code, "
        "methodology, analysis, content generation, or other project "
        "development activities.", BODY))
    head = [p("Date", CELL_B), p("AI Tool", CELL_B),
            p("Purpose / Query", CELL_B), p("How the Output Was Used", CELL_B)]
    body = [[p(d), p(tool), p(q), p(u)] for d, tool, q, u in INTERACTIONS]
    t = Table([head] + body,
              colWidths=[2.3 * cm, 2.1 * cm, 6.0 * cm, W - 10.4 * cm],
              repeatRows=1)
    t.setStyle(GRID)
    s.append(t)
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "Note: The Project Guide or Evaluation Committee may request "
        "supporting AI interaction records where necessary. The full record is "
        "preserved in the project's version control history, in which nearly "
        "every commit carries an AI co-author trailer and each commit message "
        "states what was changed and why. The table above lists the most "
        "significant interactions, not every one.", NOTE))

    # ------------------------------------------------- Student declaration
    # Its own page. Everything that gets signed -- students, guide and
    # coordinator -- belongs together; letting it flow left the guide's
    # signature block stranded alone on a page of its own.
    s.append(PageBreak())
    block = [Paragraph("Student Declaration", H2),
             Paragraph(
                 "We certify that the information provided in this document "
                 "is true and complete to the best of our knowledge. We "
                 "understand that failure to disclose significant AI usage or "
                 "misrepresentation of AI-generated work may be treated as a "
                 "violation of academic integrity.", BODY)]
    head = [p("No.", CELL_B), p("Student Name", CELL_B),
            p("Register Number", CELL_B), p("Signature", CELL_B)]
    body = [[p(n, CELL_C), p(nm), p(rn, CELL_C), p("")]
            for n, nm, rn in STUDENTS]
    t = Table([head] + body,
              colWidths=[1.2 * cm, W - 9.7 * cm, 3.6 * cm, 4.9 * cm],
              rowHeights=[None] + [0.95 * cm] * len(STUDENTS))
    t.setStyle(GRID)
    block.append(t)
    s.append(KeepTogether(block))
    s.append(Spacer(1, 16))

    sign = Table([[Paragraph("Date: " + "_" * 26, FIELD),
                   Paragraph("Place: Bengaluru, Karnataka", FIELD)]],
                 colWidths=[W / 2, W / 2])
    sign.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s.append(sign)
    s.append(Spacer(1, 22))

    guide = [[Paragraph("<b>Project Guide</b>", ParagraphStyle(
                  "g", parent=FIELD, alignment=TA_CENTER)),
              Paragraph("<b>Project Coordinator</b>", ParagraphStyle(
                  "c", parent=FIELD, alignment=TA_CENTER))],
             [Paragraph("Name: Dr. Chanti.S", FIELD),
              Paragraph("Name: " + "_" * 24, FIELD)],
             [Paragraph("Signature: " + "_" * 20, FIELD),
              Paragraph("Signature: " + "_" * 20, FIELD)]]
    t = Table(guide, colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 1), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    s.append(t)

    doc.build(s, onFirstPage=_page_number, onLaterPages=_page_number)
    print(f"wrote {OUT}")


def _page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont(SERIF, 9.5)
    canvas.drawCentredString(A4[0] / 2, 1.1 * cm, str(canvas.getPageNumber()))
    canvas.restoreState()


if __name__ == "__main__":
    build()
