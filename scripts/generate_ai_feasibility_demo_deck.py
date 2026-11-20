"""Generate the Azure Migrate AI Feasibility Assessment product demo deck.

The deck is intentionally self-contained and uses native PowerPoint shapes so it
renders cleanly without external fonts, images, or linked assets. Narration is
stored in speaker notes and mirrored in docs/demo/AI_Feasibility_Product_Demo_Script.md.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo" / "Azure_Migrate_AI_Feasibility_Product_Demo.pptx"
ASSET_DIR = ROOT / "docs" / "demo" / "assets"

# Slide geometry (16:9)
SW = 13.333
SH = 7.5

# Palette
NAVY = "061B2C"
NAVY_2 = "0B2942"
PANEL = "102F49"
PANEL_2 = "153955"
AZURE = "0078D4"
CYAN = "50E6FF"
PURPLE = "8661C5"
MINT = "2DD4A7"
GOLD = "FFB900"
CORAL = "FF6B6B"
WHITE = "F8FAFC"
TEXT = "E7EEF5"
MUTED = "9DB3C8"
LINE = "31536D"
DARK_TEXT = "102030"
LIGHT_BG = "EFF7FC"

FONT_DISPLAY = "Aptos Display"
FONT_BODY = "Aptos"


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def set_bg(slide, color: str = NAVY) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb(color)


def add_rect(slide, x, y, w, h, fill, line=None, radius=True, transparency=0):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.fill.transparency = transparency
    if line:
        shape.line.color.rgb = rgb(line)
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_circle(slide, x, y, d, fill, line=None, transparency=0):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.fill.transparency = transparency
    if line:
        shape.line.color.rgb = rgb(line)
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_line(slide, x1, y1, x2, y2, color=LINE, width=2, dashed=False):
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1),
        Inches(y1),
        Inches(x2),
        Inches(y2),
    )
    line.line.color.rgb = rgb(color)
    line.line.width = Pt(width)
    if dashed:
        line.line.dash_style = 4
    return line


def add_text(
    slide,
    text,
    x,
    y,
    w,
    h,
    *,
    size=18,
    color=TEXT,
    bold=False,
    font=FONT_BODY,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    margin=0.04,
    rotation=0,
    fit=False,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.rotation = rotation
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(margin)
    frame.margin_right = Inches(margin)
    frame.margin_top = Inches(margin)
    frame.margin_bottom = Inches(margin)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    paragraph.font.name = font
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = rgb(color)
    if fit:
        frame.fit_text(font_family=font, max_size=Pt(size))
    return box


def add_rich_text(slide, segments, x, y, w, h, *, size=18, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.03)
    frame.margin_right = Inches(0.03)
    frame.margin_top = Inches(0.02)
    frame.margin_bottom = Inches(0.02)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    for index, segment in enumerate(segments):
        run = paragraph.add_run()
        run.text = segment[0]
        run.font.name = segment[4] if len(segment) > 4 else FONT_BODY
        run.font.size = Pt(segment[3] if len(segment) > 3 else size)
        run.font.bold = segment[2] if len(segment) > 2 else False
        run.font.color.rgb = rgb(segment[1])
        if index == 0:
            run.text = segment[0]
    return box


def add_title(slide, title: str, kicker: str | None = None, subtitle: str | None = None) -> None:
    if kicker:
        add_text(slide, kicker.upper(), 0.65, 0.42, 8.6, 0.3, size=10, color=CYAN, bold=True)
    title_y = 0.72 if kicker else 0.5
    add_text(slide, title, 0.65, title_y, 11.9, 0.58, size=27, color=WHITE, bold=True, font=FONT_DISPLAY)
    if subtitle:
        add_text(slide, subtitle, 0.68, title_y + 0.62, 11.6, 0.46, size=13, color=MUTED)


def add_footer(slide, number: int, label: str = "Proposed concept · Simulator prototype") -> None:
    add_line(slide, 0.65, 7.13, 12.68, 7.13, color=LINE, width=0.8)
    add_text(slide, label, 0.67, 7.18, 7.8, 0.18, size=7.8, color=MUTED)
    add_text(slide, f"{number:02d}", 12.18, 7.16, 0.45, 0.2, size=8, color=MUTED, bold=True, align=PP_ALIGN.RIGHT)


def add_brand(slide) -> None:
    add_text(slide, "AZURE MIGRATE", 10.68, 0.43, 1.52, 0.22, size=8, color=MUTED, bold=True, align=PP_ALIGN.RIGHT)
    slide.shapes.add_picture(
        str(ASSET_DIR / "azure-logo.png"),
        Inches(12.33),
        Inches(0.36),
        width=Inches(0.34),
        height=Inches(0.34),
    )


def add_icon_tile(slide, icon_name: str, x: float, y: float, size: float = 0.72, *, line=LINE):
    add_rect(slide, x, y, size, size, "FFFFFF", line=line, radius=True)
    inset = size * 0.17
    slide.shapes.add_picture(
        str(ASSET_DIR / icon_name),
        Inches(x + inset),
        Inches(y + inset),
        width=Inches(size - 2 * inset),
        height=Inches(size - 2 * inset),
    )


def add_notes(slide, narration: str, cue: str = "") -> None:
    text = narration.strip()
    if cue:
        text += f"\n\nPRESENTER CUE: {cue.strip()}"
    slide.notes_slide.notes_text_frame.text = text


def bullet_list(slide, items, x, y, w, h, *, size=13, color=TEXT, bullet_color=CYAN, gap=0.36):
    for index, item in enumerate(items):
        cy = y + index * gap
        add_circle(slide, x, cy + 0.08, 0.08, bullet_color)
        add_text(slide, item, x + 0.18, cy, w - 0.18, 0.3, size=size, color=color)


def label_chip(slide, text, x, y, w, *, fill=PANEL_2, color=CYAN, line=LINE):
    add_rect(slide, x, y, w, 0.34, fill, line=line, radius=True)
    add_text(slide, text, x, y + 0.005, w, 0.31, size=9, color=color, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)


def metric(slide, value, label, x, y, w, *, accent=CYAN, caveat=None):
    add_rect(slide, x, y, w, 1.2, PANEL, line=LINE)
    add_text(slide, value, x + 0.16, y + 0.14, w - 0.32, 0.44, size=25, color=accent, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
    add_text(slide, label, x + 0.14, y + 0.63, w - 0.28, 0.28, size=10, color=TEXT, bold=True, align=PP_ALIGN.CENTER)
    if caveat:
        add_text(slide, caveat, x + 0.12, y + 0.93, w - 0.24, 0.18, size=7.5, color=MUTED, align=PP_ALIGN.CENTER)


def step_box(slide, number, title, x, y, w, *, active=False):
    fill = AZURE if active else PANEL
    line = CYAN if active else LINE
    add_rect(slide, x, y, w, 0.96, fill, line=line)
    add_circle(slide, x + 0.12, y + 0.18, 0.34, CYAN if active else PANEL_2, line=CYAN)
    add_text(slide, str(number), x + 0.12, y + 0.18, 0.34, 0.32, size=10, color=NAVY if active else CYAN, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    add_text(slide, title, x + 0.54, y + 0.2, w - 0.66, 0.5, size=11.5, color=WHITE, bold=True, valign=MSO_ANCHOR.MIDDLE)


def build_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    blank = prs.slide_layouts[6]

    # Slide 1 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_circle(slide, 9.25, -1.2, 5.2, AZURE, transparency=28)
    add_circle(slide, 10.5, 1.15, 3.2, PURPLE, transparency=30)
    add_circle(slide, 8.45, 4.65, 2.1, CYAN, transparency=72)
    add_brand(slide)
    label_chip(slide, "PRODUCT CONCEPT + WORKING SIMULATOR", 0.75, 0.62, 3.0, fill=PANEL, color=CYAN)
    add_text(slide, "Azure Migrate\nin the AI era", 0.75, 1.35, 7.8, 1.55, size=42, color=WHITE, bold=True, font=FONT_DISPLAY)
    add_text(slide, "AI Feasibility Assessment", 0.78, 3.18, 6.8, 0.58, size=25, color=CYAN, bold=True, font=FONT_DISPLAY)
    add_text(slide, "From discovered application intelligence to an actionable AI modernization decision", 0.8, 3.92, 7.1, 0.85, size=17, color=TEXT)
    add_rect(slide, 8.55, 2.18, 3.55, 2.58, PANEL, line=CYAN)
    add_text(slide, "THE NEW QUESTION", 8.88, 2.48, 2.85, 0.26, size=10, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "Where can AI create\nmeaningful value?", 8.86, 2.95, 2.9, 0.84, size=23, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
    add_text(slide, "…and what would it take\nto make it real?", 8.92, 3.93, 2.8, 0.55, size=13, color=MUTED, align=PP_ALIGN.CENTER)
    add_text(slide, "October 2026", 0.8, 6.48, 2.1, 0.25, size=10, color=MUTED)
    add_footer(slide, 1)
    add_notes(slide, """
Azure Migrate helps customers understand and modernize their on-premises estate. In the AI era, we have an opportunity to extend that journey. Not only helping customers decide how to move an application to Azure, but also helping them identify where AI can create meaningful value—and what it would take to deliver that value responsibly.
""", "Pause briefly on the subtitle. Describe this as the proposed experience demonstrated by the simulator prototype.")

    # Slide 2 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Azure Migrate already builds application intelligence", "THE FOUNDATION", "Discovery becomes a complete application view—not just a list of servers")

    add_text(slide, "DISCOVER", 0.75, 1.67, 2.3, 0.26, size=10, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    inventory = [
        ("virtual-machine.png", "Virtual\nmachines", AZURE),
        ("app-services.png", "Web\napps", MINT),
        ("sql-database.png", "Databases", CORAL),
        ("azure-fileshares.png", "File\nshares", GOLD),
        ("container-instances.png", "Containers", PURPLE),
    ]
    for idx, (icon, label, accent) in enumerate(inventory):
        x = 0.82 + (idx % 2) * 1.12
        y = 2.08 + (idx // 2) * 1.17
        add_icon_tile(slide, icon, x, y, line=accent)
        add_text(slide, label, x - 0.15, y + 0.78, 1.02, 0.38, size=8.5, color=MUTED, align=PP_ALIGN.CENTER)

    add_line(slide, 3.05, 3.35, 4.2, 3.35, color=CYAN, width=2)
    add_rect(slide, 4.2, 2.32, 3.18, 2.15, PANEL, line=CYAN)
    add_text(slide, "APPLICATION", 4.55, 2.63, 2.48, 0.3, size=11, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "BPTco", 4.55, 3.03, 2.48, 0.48, size=26, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
    add_text(slide, "One reviewed boundary\nComponents · Dependencies · Context", 4.52, 3.58, 2.54, 0.58, size=11, color=MUTED, align=PP_ALIGN.CENTER)
    add_line(slide, 7.38, 3.35, 8.43, 3.35, color=CYAN, width=2)

    add_text(slide, "ASSESS AGAINST AZURE", 8.4, 1.67, 4.1, 0.26, size=10, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    targets = [
        ("app-services.png", "App Service", "Web application", MINT),
        ("sql-managed-instance.png", "Azure SQL MI", "SQL workload", CORAL),
        ("kubernetes-services.png", "AKS", "Containers", PURPLE),
    ]
    for idx, (icon, target, source, accent) in enumerate(targets):
        y = 2.18 + idx * 1.15
        add_rect(slide, 8.72, y, 3.45, 0.86, PANEL, line=accent)
        add_icon_tile(slide, icon, 8.87, y + 0.13, 0.58, line=accent)
        add_text(slide, target, 9.55, y + 0.14, 2.3, 0.28, size=13, color=WHITE, bold=True)
        add_text(slide, source, 9.56, y + 0.48, 2.2, 0.2, size=8.5, color=MUTED)

    add_rect(slide, 0.78, 5.73, 11.55, 0.75, NAVY_2, line=LINE)
    add_text(slide, "Application boundary", 1.06, 5.93, 2.1, 0.26, size=11, color=CYAN, bold=True)
    add_text(slide, "Runtime & topology", 3.64, 5.93, 1.9, 0.26, size=11, color=CYAN, bold=True)
    add_text(slide, "Assessed Azure targets", 6.1, 5.93, 2.25, 0.26, size=11, color=CYAN, bold=True)
    add_text(slide, "Readiness & cost context", 8.98, 5.93, 2.75, 0.26, size=11, color=CYAN, bold=True)
    add_footer(slide, 2)
    add_notes(slide, """
Azure Migrate begins with discovery. It prepares an inventory of virtual machines, web applications, databases, file shares, containers, and supporting dependencies.

Customers can then organize these components as a complete application—a unit that works and moves together. Assessment maps each component to an appropriate Azure target. A web application might map to Azure App Service. SQL Server might map to Azure SQL Managed Instance. A containerized workload might map to Azure Kubernetes Service.

This gives us rich application intelligence: the application boundary, the current technology, assessed Azure targets, dependencies, readiness, and cost context.
""", "Emphasize application intelligence—not just infrastructure inventory.")

    # Slide 3 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Cloud-era answer. AI-era opportunity.", "WHY NOW", "Migration remains essential—but modernization expectations have changed")
    add_rect(slide, 0.76, 1.75, 5.65, 3.28, PANEL, line=AZURE)
    label_chip(slide, "CLOUD ERA", 1.05, 2.02, 1.4, fill=AZURE, color=WHITE, line=AZURE)
    add_text(slide, "Where and how should\nthis application run\nin Azure?", 1.05, 2.63, 4.95, 1.33, size=27, color=WHITE, bold=True, font=FONT_DISPLAY)
    add_text(slide, "Discovery · Readiness · Target services · Cost", 1.08, 4.35, 4.7, 0.3, size=11, color=MUTED)

    add_rect(slide, 6.93, 1.75, 5.65, 3.28, PANEL, line=PURPLE)
    label_chip(slide, "AI ERA", 7.23, 2.02, 1.25, fill=PURPLE, color=WHITE, line=PURPLE)
    add_text(slide, "Where can AI create\nmeaningful value—and\nwhat would it take?", 7.22, 2.63, 4.95, 1.33, size=27, color=WHITE, bold=True, font=FONT_DISPLAY)
    add_text(slide, "Outcome · Data · Integration · Governance · Delivery", 7.24, 4.35, 4.85, 0.3, size=11, color=MUTED)

    add_text(slide, "1", 1.0, 5.55, 0.45, 0.4, size=21, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "How can I use AI in my existing applications—or modernize AI I already run on-premises?", 1.55, 5.55, 10.65, 0.44, size=14.5, color=TEXT, bold=True)
    add_text(slide, "2", 1.0, 6.17, 0.45, 0.4, size=21, color=PURPLE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "What should the next generation of Azure Migrate look like in the AI era?", 1.55, 6.17, 10.65, 0.44, size=14.5, color=TEXT, bold=True)
    add_footer(slide, 3)
    add_notes(slide, """
That assessment is excellent at answering the cloud-era question: where and how should this application run in Azure?

But customers increasingly ask a second question: how can I use AI in this existing application? And, if I already use AI on-premises, how should I modernize that capability in Azure?

This leads to two strategic questions for us. First: how do we help customers find credible AI opportunities in the applications they already own? Second: what should the next generation of Azure Migrate look like in the AI era?
""", "Pause after each strategic question.")

    # Slide 4 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Extend the Azure Migrate journey", "PROPOSED IDEA", "Add an application-level AI modernization decision before design and execution")
    stages = [
        ("1", "Discover", "Estate & workloads", AZURE),
        ("2", "Assess", "Readiness & targets", AZURE),
        ("3", "AI Feasibility", "Value · evidence · path", PURPLE),
        ("4", "Design", "AI-ready architecture", MINT),
        ("5", "Estimate", "Usage & cost range", GOLD),
        ("6", "Modernize", "PoC → pilot → production", CYAN),
    ]
    x = 0.55
    for index, (number, title, detail, accent) in enumerate(stages):
        width = 2.0 if index == 2 else 1.72
        add_rect(slide, x, 2.25, width, 2.15, PANEL if index != 2 else PANEL_2, line=accent)
        add_circle(slide, x + 0.18, 2.48, 0.42, accent)
        add_text(slide, number, x + 0.18, 2.57, 0.42, 0.2, size=9, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, title, x + 0.18, 3.12, width - 0.36, 0.42, size=15 if index != 2 else 17, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
        add_text(slide, detail, x + 0.18, 3.65, width - 0.36, 0.43, size=9, color=MUTED, align=PP_ALIGN.CENTER)
        if index < len(stages) - 1:
            add_text(slide, "→", x + width, 3.0, 0.36, 0.35, size=21, color=LINE, bold=True, align=PP_ALIGN.CENTER)
        x += width + 0.24
    add_rect(slide, 1.45, 5.27, 10.42, 0.72, NAVY_2, line=PURPLE)
    add_rich_text(slide, [
        ("The unit of assessment is ", TEXT, False, 14),
        ("one application + one customer-owned business workflow", CYAN, True, 14),
        (" — not a server, and not the whole organization.", TEXT, False, 14),
    ], 1.72, 5.49, 9.88, 0.3, align=PP_ALIGN.CENTER)
    add_text(slide, "A valid answer may be: PoC candidate · remediate first · adopt/extend · non-AI automation · do not pursue", 1.25, 6.28, 10.85, 0.32, size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
    add_footer(slide, 4)
    add_notes(slide, """
The proposed idea is an AI Feasibility Assessment as a new step in the Azure Migrate journey.

Discover. Assess. AI Feasibility Assessment. Design. Estimate. Modernize.

It adds an AI modernization layer on top of existing application intelligence. The goal is not to turn every application into an AI project. The goal is to identify which application-and-workflow combinations justify a bounded experiment, which need remediation first, and which should not pursue AI.
""", "Emphasize application plus business workflow.")

    # Slide 5 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Four decisions the assessment must support", "THE DECISION CONTRACT", "A practical answer for the customer—not a generic inventory of AI ideas")
    cards = [
        ("01", "VALUE", "Where can AI create meaningful business or engineering value?", CYAN),
        ("02", "FEASIBILITY", "Is the application, its data, and its integration boundary ready?", MINT),
        ("03", "SOLUTION", "Which Azure services, integrations, and governance controls are required?", PURPLE),
        ("04", "DELIVERY", "What is the pragmatic path from PoC to pilot to production?", GOLD),
    ]
    positions = [(0.8, 1.85), (6.84, 1.85), (0.8, 4.15), (6.84, 4.15)]
    for (number, label, question, accent), (x, y) in zip(cards, positions):
        add_rect(slide, x, y, 5.68, 1.77, PANEL, line=accent)
        add_text(slide, number, x + 0.22, y + 0.23, 0.62, 0.42, size=22, color=accent, bold=True, font=FONT_DISPLAY)
        add_text(slide, label, x + 0.92, y + 0.28, 1.75, 0.3, size=10, color=accent, bold=True)
        add_text(slide, question, x + 0.92, y + 0.7, 4.25, 0.72, size=15, color=WHITE, bold=True, font=FONT_DISPLAY)
    add_text(slide, "The output is a reviewable decision pack with explicit evidence gaps and production gates.", 1.52, 6.42, 10.25, 0.32, size=13, color=MUTED, align=PP_ALIGN.CENTER)
    add_footer(slide, 5)
    add_notes(slide, """
For each selected application, the assessment should answer four practical questions.

Where can AI create meaningful business or engineering value?

Is the application and its data technically ready for that scenario?

Which integrations, Azure services, and security or governance controls are required?

And what is the pragmatic path from proof of concept, to pilot, to production?

The output is a reviewable decision pack with explicit evidence gaps and production gates—not a generic list of AI ideas.
""")

    # Slide 6 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Evidence in. Decision pack out.", "THE EXPERIENCE", "Combine observed application facts with customer-confirmed business intent")
    add_rect(slide, 0.72, 1.7, 3.55, 4.62, PANEL, line=AZURE)
    add_text(slide, "APPLICATION EVIDENCE", 1.02, 2.0, 2.95, 0.3, size=11, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    bullet_list(slide, [
        "Components & application boundary",
        "Runtime, topology & dependencies",
        "Assessment targets & readiness",
        "Migration cost context",
    ], 1.06, 2.55, 2.86, 1.55, size=12.5, bullet_color=AZURE, gap=0.55)
    add_text(slide, "CUSTOMER CONTEXT", 1.02, 4.68, 2.95, 0.3, size=11, color=MINT, bold=True, align=PP_ALIGN.CENTER)
    bullet_list(slide, [
        "Process, users & outcome",
        "Data rights & constraints",
        "Usage, risk & ownership",
    ], 1.06, 5.09, 2.86, 1.0, size=12.5, bullet_color=MINT, gap=0.43)

    add_circle(slide, 5.0, 2.35, 2.35, PURPLE, transparency=15)
    add_circle(slide, 5.25, 2.6, 1.85, NAVY_2, line=CYAN)
    add_text(slide, "EVIDENCE\n+ RULES\n+ BOUNDED AI", 5.28, 3.02, 1.78, 0.82, size=16.5, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    label_chip(slide, "Observed", 4.58, 5.0, 1.05, fill=PANEL, color=CYAN)
    label_chip(slide, "Customer", 5.72, 5.0, 1.05, fill=PANEL, color=MINT)
    label_chip(slide, "Inferred", 4.58, 5.44, 1.05, fill=PANEL, color=GOLD)
    label_chip(slide, "Missing", 5.72, 5.44, 1.05, fill=PANEL, color=CORAL)

    add_rect(slide, 8.03, 1.7, 4.58, 4.62, PANEL, line=PURPLE)
    add_text(slide, "DECISION PACK", 8.35, 2.0, 3.94, 0.3, size=11, color=PURPLE, bold=True, align=PP_ALIGN.CENTER)
    outputs = [
        "AI feasibility summary",
        "Data & integration readiness",
        "Security / governance conditions",
        "Recommended Azure AI services",
        "Indicative cost scenarios",
        "AI-ready architecture extension",
        "PoC → pilot → production gates",
    ]
    bullet_list(slide, outputs, 8.39, 2.52, 3.75, 2.75, size=12.5, bullet_color=PURPLE, gap=0.48)
    add_rect(slide, 8.36, 5.74, 3.9, 0.37, NAVY_2, line=GOLD)
    add_text(slide, "Not an opaque LLM-generated score", 8.45, 5.81, 3.72, 0.19, size=9.5, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 6)
    add_notes(slide, """
The experience combines two evidence streams. Azure Migrate contributes observed application facts: components, dependencies, runtime, assessed targets, and migration findings. The customer contributes the business meaning: the process to improve, users, desired outcome, data constraints, compliance needs, and expected usage.

The assessment then produces a feasibility summary, data and integration readiness, governance considerations, evidence-backed opportunities, recommended Azure AI services, indicative cost scenarios, an AI-ready architecture extension, and a PoC roadmap.

The key design principle is explainability. Observed facts, customer-provided context, inferred assumptions, and missing evidence remain visibly separate. Rules and deterministic calculations control the decision pack. Generative AI can improve the narrative, but it does not silently invent readiness or cost.
""", "Point to the evidence labels and the not-an-opaque-score statement.")

    # Slide 7 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Live demo | BPTco document processing", "PRODUCT WALKTHROUGH", "From discovered application to a versioned AI-ready architecture")
    metric(slide, "60%", "Less manual data entry", 0.85, 1.75, 2.65, accent=CYAN, caveat="Customer target · not observed")
    metric(slide, "50%", "Faster document processing", 3.78, 1.75, 2.65, accent=MINT, caveat="Customer target · not observed")
    metric(slide, "95%", "Critical-field accuracy", 6.71, 1.75, 2.65, accent=GOLD, caveat="PoC target · validate by field")
    add_rect(slide, 9.65, 1.75, 2.82, 1.2, PANEL, line=PURPLE)
    add_text(slide, "GUARDRAILS", 9.87, 1.95, 2.38, 0.25, size=10, color=PURPLE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "Controlled access · Human approval · Audit trail", 9.9, 2.27, 2.32, 0.45, size=10.5, color=TEXT, bold=True, align=PP_ALIGN.CENTER)

    route = [
        (1, "Overview", False),
        (2, "Application group", False),
        (3, "Base architecture", False),
        (4, "AI assessment", True),
        (5, "AI-ready design", True),
    ]
    x = 0.78
    for number, title, active in route:
        step_box(slide, number, title, x, 3.55, 2.25, active=active)
        x += 2.48
    add_rect(slide, 1.35, 5.23, 10.58, 0.93, NAVY_2, line=CYAN)
    add_text(slide, "SWITCH TO LIVE PRODUCT", 1.65, 5.43, 3.0, 0.27, size=11, color=CYAN, bold=True)
    add_text(slide, "Discover → select BPTco → assess document workflow → generate decision pack → view AI-ready landing zone", 4.03, 5.38, 7.55, 0.42, size=12.5, color=WHITE, bold=True, align=PP_ALIGN.RIGHT)
    add_text(slide, "The live experience demonstrates assessment and architecture planning; deployment is a deliberate next step.", 1.1, 6.52, 11.1, 0.28, size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
    add_footer(slide, 7)
    add_notes(slide, """
Let’s see the proposed experience in the Azure Migrate simulator. Discovery and assessment are already complete. We will start with the BPTco application, inspect its current Azure architecture, capture a document-processing outcome, generate an AI Feasibility Assessment, and then see exactly where the proposed AI services fit in the application landing zone.
""", "Switch cleanly from PowerPoint to the browser after the final sentence.")

    # Slide 8 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "What the demo demonstrates", "FROM CONTEXT TO DECISION", "Four connected capabilities—one traceable application/workflow decision")
    proof = [
        ("01", "Reuse context", "Start with the reviewed application boundary, dependencies, and assessed Azure targets.", AZURE),
        ("02", "Capture intent", "Add the customer-owned process, users, outcomes, constraints, and usage assumptions.", MINT),
        ("03", "Explain the decision", "Keep evidence, gaps, service rationale, costs, and PoC gates visible and reviewable.", GOLD),
        ("04", "Extend the design", "Replace the base view only when the customer selects a linked AI-ready assessment revision.", PURPLE),
    ]
    for idx, (number, title, detail, accent) in enumerate(proof):
        x = 0.72 + idx * 3.13
        add_rect(slide, x, 1.8, 2.82, 4.22, PANEL, line=accent)
        add_circle(slide, x + 0.26, 2.08, 0.56, accent)
        add_text(slide, number, x + 0.26, 2.23, 0.56, 0.2, size=10, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, title, x + 0.26, 2.89, 2.3, 0.48, size=18, color=WHITE, bold=True, font=FONT_DISPLAY)
        add_text(slide, detail, x + 0.26, 3.62, 2.3, 1.32, size=12.5, color=TEXT)
        add_line(slide, x + 0.26, 5.36, x + 2.48, 5.36, color=accent, width=2)
        add_text(slide, ["Observed", "Customer-provided", "Deterministic", "Version-linked"][idx], x + 0.26, 5.53, 2.26, 0.25, size=9, color=accent, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "A qualified modernization conversation—not a generic AI brainstorm.", 1.1, 6.42, 11.05, 0.35, size=15, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 8)
    add_notes(slide, """
This demonstration connects four things that are usually separated.

It reuses existing application intelligence. It captures the customer's business intent and outcome. It produces an explainable, evidence-backed decision pack. And it carries the approved scenario into an AI-ready architecture without losing the base application design.

The result is a qualified modernization conversation and a practical handoff—not a generic AI brainstorm.
""")

    # Slide 9 -----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "The larger vision", "NEXT-GENERATION AZURE MIGRATE", "Keep migration as the foundation—add the next modernization decision")
    add_rect(slide, 0.8, 1.8, 5.3, 3.7, PANEL, line=AZURE)
    label_chip(slide, "TODAY", 1.12, 2.1, 1.0, fill=AZURE, color=WHITE, line=AZURE)
    add_text(slide, "“How do I move\nthis application\nto Azure?”", 1.17, 2.85, 4.5, 1.55, size=30, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
    add_text(slide, "Placement · Readiness · Cost · Migration plan", 1.2, 4.72, 4.45, 0.3, size=10, color=MUTED, align=PP_ALIGN.CENTER)

    add_text(slide, "+", 6.18, 3.08, 0.78, 0.75, size=38, color=CYAN, bold=True, align=PP_ALIGN.CENTER)

    add_rect(slide, 7.0, 1.8, 5.55, 3.7, PANEL, line=PURPLE)
    label_chip(slide, "AI ERA", 7.33, 2.1, 1.15, fill=PURPLE, color=WHITE, line=PURPLE)
    add_text(slide, "“How can I transform\nthis application with AI—\nand what would it take?”", 7.35, 2.72, 4.86, 1.68, size=27, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)
    add_text(slide, "Business value · Feasibility · AI-ready design · Delivery gates", 7.4, 4.72, 4.76, 0.3, size=10, color=MUTED, align=PP_ALIGN.CENTER)

    add_rect(slide, 1.75, 5.93, 9.84, 0.64, NAVY_2, line=CYAN)
    add_text(slide, "The migration decision becomes the launch point for the next wave of application value.", 2.0, 6.11, 9.35, 0.28, size=13.5, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 9)
    add_notes(slide, """
The larger vision is simple.

Azure Migrate has traditionally helped answer: how do I move this application to Azure?

In the AI era, it can also help answer: how can I transform this application with AI, and what would it take to get there?

Migration remains the foundation. AI Feasibility adds the next modernization decision at exactly the point where the customer already understands the application and is choosing its future.
""")

    # Slide 10 ----------------------------------------------------------------
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    add_brand(slide)
    add_title(slide, "Scale through the existing ecosystem", "OPERATING MODEL", "Qualify the opportunity in Azure Migrate; build through the right platform and delivery team")
    add_rect(slide, 0.8, 1.68, 3.3, 3.95, PANEL, line=AZURE)
    add_text(slide, "EXISTING MIGRATION ECOSYSTEM", 1.08, 1.98, 2.74, 0.42, size=10, color=AZURE, bold=True, align=PP_ALIGN.CENTER)
    for idx, name in enumerate(["CMF", "SA Desk", "Cloud solution architects", "Systems integrators & partners"]):
        add_rect(slide, 1.08, 2.67 + idx * 0.68, 2.72, 0.49, NAVY_2, line=LINE)
        add_text(slide, name, 1.18, 2.78 + idx * 0.68, 2.52, 0.22, size=10.5, color=TEXT, bold=True, align=PP_ALIGN.CENTER)

    add_circle(slide, 5.08, 2.18, 3.15, PURPLE, transparency=15)
    add_circle(slide, 5.45, 2.55, 2.4, NAVY_2, line=CYAN)
    add_text(slide, "AZURE MIGRATE", 5.76, 3.02, 1.78, 0.28, size=10, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "AI Feasibility\nAssessment", 5.7, 3.48, 1.9, 0.68, size=20, color=WHITE, bold=True, font=FONT_DISPLAY, align=PP_ALIGN.CENTER)

    add_rect(slide, 9.22, 1.68, 3.3, 3.95, PANEL, line=PURPLE)
    add_text(slide, "EXPANDED AI DELIVERY ECOSYSTEM", 9.48, 1.98, 2.78, 0.42, size=10, color=PURPLE, bold=True, align=PP_ALIGN.CENTER)
    for idx, name in enumerate(["Microsoft Foundry", "Azure Frontier", "AI field engineers", "Forward Deployed Engineers"]):
        add_rect(slide, 9.5, 2.67 + idx * 0.68, 2.72, 0.49, NAVY_2, line=LINE)
        add_text(slide, name, 9.6, 2.78 + idx * 0.68, 2.52, 0.22, size=10.5, color=TEXT, bold=True, align=PP_ALIGN.CENTER)

    add_line(slide, 4.08, 3.72, 5.18, 3.72, color=CYAN, width=2)
    add_line(slide, 8.06, 3.72, 9.2, 3.72, color=PURPLE, width=2)
    add_text(slide, "Qualified handoff", 4.0, 4.05, 1.25, 0.22, size=8.5, color=MUTED, align=PP_ALIGN.CENTER)
    add_text(slide, "Platform + delivery", 8.0, 4.05, 1.25, 0.22, size=8.5, color=MUTED, align=PP_ALIGN.CENTER)

    add_rect(slide, 0.92, 5.95, 11.5, 0.65, NAVY_2, line=GOLD)
    add_text(slide, "NEXT STEP", 1.17, 6.14, 1.18, 0.22, size=10, color=GOLD, bold=True)
    add_text(slide, "Bounded design-partner validation · Human-reviewed recommendations · Measurable path to customer-owned PoC", 2.35, 6.08, 9.75, 0.33, size=12.5, color=WHITE, bold=True, align=PP_ALIGN.RIGHT)
    add_text(slide, "Azure Migrate qualifies the opportunity. Platforms and delivery teams build it. Customers own data authorization and production acceptance.", 1.07, 6.72, 11.2, 0.28, size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
    add_footer(slide, 10)
    add_notes(slide, """
Azure Migrate already works through a broad ecosystem—including CMF, SA Desk, cloud solution architects, systems integrators, and other delivery partners.

AI Feasibility can extend those relationships with a better-qualified application opportunity and a versioned handoff. It can also create new collaboration paths with Microsoft Foundry, Azure Frontier, AI field engineers, and Forward Deployed Engineers.

Azure Migrate owns the application-to-opportunity decision experience. Platform and delivery teams validate and build the solution. The customer retains ownership of business value, data authorization, and production acceptance.

The next step is a bounded design-partner validation: human-reviewed recommendations, clear evidence gates, and measurable movement from qualified opportunity to customer-owned PoC.

Azure Migrate helps us understand the application. AI Feasibility helps the customer decide how that application can create new value in the AI era.
""", "Hold the final slide for three seconds after the closing line.")

    # Add document properties.
    prs.core_properties.title = "Azure Migrate AI Feasibility Assessment — Product Demo"
    prs.core_properties.subject = "Professional product demo deck for the proposed AI Feasibility Assessment experience"
    prs.core_properties.author = "Azure Migrate Simulations"
    prs.core_properties.keywords = "Azure Migrate, AI Feasibility, Microsoft Foundry, CTD, modernization"
    prs.core_properties.comments = "Product concept and simulator prototype; not a production Azure Migrate feature or Azure pricing quote."
    return prs


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    presentation = build_deck()
    presentation.save(OUTPUT)
    print(f"Generated {OUTPUT}")
    print(f"Slides: {len(presentation.slides)}")


if __name__ == "__main__":
    main()
