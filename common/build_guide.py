#!/usr/bin/env python3
"""Build one of the guides as a PDF from its light markup source.

Usage: python3 build_guide.py guide.md output.pdf

The source is a light markup, one block per paragraph, blocks separated by
blank lines:
  @header Text                     running header on every page (optional,
                                   defaults to the title)
  @title Text / @subtitle Text     title page heading and subtitle
  # 1. Title / ## 1.1 Title        numbered sections (TOC + PDF bookmarks)
  ### Title                        small unnumbered heading
  ``` ... ```                      code block (verbatim)
  > **Lead :** text                callout (one "> " line per paragraph)
  !! **Lead :** text               red danger box: risk of an unbootable
                                   machine or of data loss (one "!! " line
                                   per paragraph)
  - text                           bullet item
  |= w1 w2 w3 [header]             table: column widths in points,
  | a | b | c |                    then one line per row
  !todo Title                      final boxed "to do" list; lines starting
                                   with "~ " are small notes
  ::: Title ... :::                grey aside box (e.g. ARM notes) holding
                                   paragraphs, bullets and code blocks
  !flow                            vertical flow diagram, then one line per
  Step | description               step; "*" before a step highlights it,
                                   " // " in a description forces a line break
  !img path | caption              screenshot (path relative to the source file),
  crop x0 y0 x1 y1                 then optional lines, in source image pixels:
  box x0 y0 x1 y1 [n]              crop area, red frames with an optional
  width 0.8                        number badge, display width (fraction of
                                   the text width, default 1)
  anything else                    body paragraph
Inline markup: `code` and **bold**.

Every file a code block creates with a quoted here-document
(tee <path> <<'EOF' ... EOF), or opened with ```file <name>, is also
embedded in the PDF as an attachment,
so that it can be extracted byte for byte (copying from a PDF viewer may drop
or reflow whitespace). A small caption under the block names the attachment.
"""
import os
import re
import sys

from pypdf import PdfWriter
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Preformatted,
                                Spacer, Table, TableStyle)
from reportlab.platypus.flowables import Flowable, _listWrapOn
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import ttfonts

# Non-breaking spaces keep inline commands on one line and French punctuation
# attached; map them to plain spaces in the text layer so that copying a
# command from the PDF gives ordinary spaces.
_make_cmap = ttfonts.makeToUnicodeCMap
ttfonts.makeToUnicodeCMap = lambda name, subset: _make_cmap(
    name, [0x20 if cp == 0xA0 else cp for cp in subset])

# Spacing between blocks is additive (space after + space before), everywhere,
# including when KeepTogether measures a group
rl_config.overlapAttachedSpace = 0

# ---------------------------------------------------------------- fonts ----
# Debian/Ubuntu path first, then Arch Linux (ttf-dejavu)
# DEJAVU_DIR overrides; then Debian/Ubuntu, Arch Linux (ttf-dejavu), macOS
FONT_DIRS = [os.environ.get("DEJAVU_DIR", ""), "/usr/share/fonts/truetype/dejavu",
             "/usr/share/fonts/TTF", os.path.expanduser("~/Library/Fonts"),
             "/Library/Fonts"]
FONT_DIR = next((d + "/" for d in FONT_DIRS
                 if d and os.path.exists(os.path.join(d, "DejaVuSans.ttf"))), None)
if FONT_DIR is None:
    sys.exit("DejaVu fonts not found: install them or set DEJAVU_DIR")
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_DIR + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", FONT_DIR + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSansMono", FONT_DIR + "DejaVuSansMono.ttf"))
addMapping("DejaVuSans", 0, 0, "DejaVuSans")
addMapping("DejaVuSans", 1, 0, "DejaVuSans-Bold")
addMapping("DejaVuSans", 0, 1, "DejaVuSans")
addMapping("DejaVuSans", 1, 1, "DejaVuSans-Bold")
for _b in (0, 1):            # inline code inside bold text stays regular mono
    for _i in (0, 1):
        addMapping("DejaVuSansMono", _b, _i, "DejaVuSansMono")

SANS, BOLD, MONO = "DejaVuSans", "DejaVuSans-Bold", "DejaVuSansMono"

# --------------------------------------------------------------- colours ---
INK = colors.HexColor("#1f2328")
MUTED = colors.HexColor("#5b6470")
TOC_GREY = colors.HexColor("#40454c")
BLUE = colors.HexColor("#1a8fd0")
CODE_BG = colors.HexColor("#f3f4f6")
RULE = colors.HexColor("#dde1e6")
NOTE_BG = colors.HexColor("#fff7e2")
NOTE_BAR = colors.HexColor("#e9b23c")
STRIPE = colors.HexColor("#f5f6f8")
DANGER_BG = colors.HexColor("#fdecea")
DANGER_BAR = colors.HexColor("#d93025")
DANGER_INK = "#b3261e"
ASIDE_BG = colors.HexColor("#e4e6e9")
ASIDE_BAR = colors.HexColor("#7a828c")
ASIDE_CODE_BG = colors.HexColor("#f8f8f8")

# ---------------------------------------------------------------- layout ---
PAGE_W, PAGE_H = A4
MARGIN = 56.69          # 2 cm
TOP = 66.0
FRAME_W = PAGE_W - 2 * MARGIN

# ---------------------------------------------------------------- styles ---
body = ParagraphStyle("body", fontName=SANS, fontSize=9.5, leading=14, textColor=INK,
                      spaceAfter=6, alignment=TA_LEFT)
title = ParagraphStyle("title", fontName=BOLD, fontSize=26, leading=30, textColor=INK,
                       spaceAfter=2)
subtitle = ParagraphStyle("subtitle", fontName=SANS, fontSize=12, leading=16.5,
                          textColor=MUTED, spaceAfter=12)
h1 = ParagraphStyle("h1", fontName=BOLD, fontSize=19, leading=23, textColor=BLUE,
                    spaceBefore=16, spaceAfter=7)
h2 = ParagraphStyle("h2", fontName=BOLD, fontSize=12.5, leading=16, textColor=INK,
                    spaceBefore=12, spaceAfter=3)
h3 = ParagraphStyle("h3", fontName=BOLD, fontSize=11, leading=14, textColor=INK,
                    spaceBefore=10, spaceAfter=3)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2,
                        bulletFontName="Helvetica", bulletFontSize=10, spaceAfter=3)
note = ParagraphStyle("note", fontName=SANS, fontSize=8.6, leading=12.8, textColor=INK,
                      spaceAfter=4)
note_bullet = ParagraphStyle("note_bullet", parent=note, leftIndent=12, bulletIndent=2,
                             bulletFontName="Helvetica", bulletFontSize=9)
cell = ParagraphStyle("cell", fontName=SANS, fontSize=8.3, leading=11, textColor=INK)
cell_head = ParagraphStyle("cell_head", parent=cell, fontName=BOLD, textColor=colors.white)
code_style = ParagraphStyle("code", fontName=MONO, fontSize=7.3, leading=10, textColor=INK)
todo_title = ParagraphStyle("todo_title", fontName=BOLD, fontSize=11.5, leading=14.5,
                            textColor=BLUE)
todo_line = ParagraphStyle("todo_line", parent=body, spaceAfter=0)
todo_small = ParagraphStyle("todo_small", fontName=SANS, fontSize=8.3, leading=13,
                            textColor=INK)
toc_title = ParagraphStyle("toc_title", parent=h1, spaceBefore=0, spaceAfter=8)
toc_sub = ParagraphStyle("toc_sub", fontName=SANS, fontSize=10, leading=13,
                         textColor=MUTED, spaceAfter=16)

# Word spaces may shrink slightly (5 %) so that a line fits
SHRINK = 0.05
for _st in list(globals().values()):
    if isinstance(_st, ParagraphStyle):
        _st.spaceShrinkage = SHRINK

# Inline code up to this length is never split across two lines
KEEP_CODE_MAX = 45

# Size of inline code relative to the surrounding text style
CODE_SIZE = {"body": 8.6, "note": 8.0, "cell": 7.6, "bullet": 8.4, "small": 7.5}


def french_spacing(text):
    """No line break before : ; ! ? » or after « (French typography)."""
    text = re.sub(r" ([:;!?»])", "\u00a0\\1", text)
    return re.sub(r"« ", "«\u00a0", text)


def inline(text, ctx="body"):
    """Convert `code` and **bold** markup to ReportLab paragraph XML."""
    out = []
    in_bold = False         # **bold** may span inline code: track it across parts
    for i, part in enumerate(re.split(r"(`[^`]*`)", text)):
        if i % 2:
            code = part[1:-1]
            code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if len(code) <= KEEP_CODE_MAX:
                code = code.replace(" ", "\u00a0")   # keep short commands unbroken
            out.append(f'<font name="{MONO}" size="{CODE_SIZE[ctx]}">{code}</font>')
        else:
            part = french_spacing(part)
            part = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            pieces = part.split("**")
            part = pieces[0]
            for piece in pieces[1:]:
                in_bold = not in_bold
                part += ("<b>" if in_bold else "</b>") + piece
            out.append(part)
    if in_bold:
        out.append("</b>")
    return "".join(out)


# ----------------------------------------------------------- attachments ---
HEREDOC = re.compile(r"tee (?:-a )?(\S+) <<'EOF'\n(.*?)\nEOF(?:\n|$)", re.S)
FILE_FENCE = re.compile(r"^```file (\S+)\n(.*?)\n```", re.S | re.M)


class CodeText(str):
    """Code block text; .attach is the attachment name from ```file <name>."""
    attach = None

attach_caption = ParagraphStyle("attach_caption", parent=body, fontSize=7.5, leading=10,
                                textColor=MUTED, spaceBefore=-6, spaceAfter=9)


def collect_attachments(src):
    """Map each here-document target path to (attachment name, content)."""
    found = {}
    used = {}
    for m in HEREDOC.finditer(src):
        path, content = m.group(1), m.group(2) + "\n"
        if path in found:
            continue
        name = os.path.basename(path)
        if name in used and used[name] != content:
            parent = os.path.basename(os.path.dirname(path)) or "file"
            name = parent + "_" + name
        used[name] = content
        found[path] = (name, content)
    for m in FILE_FENCE.finditer(src):
        found["file:" + m.group(1)] = (m.group(1), m.group(2) + "\n")
    return found


def embed_attachments(pdf_path, attachments):
    if not attachments:
        return
    writer = PdfWriter(clone_from=pdf_path)
    for name, content in sorted(set(attachments.values())):
        writer.add_attachment(name, content.encode("utf-8"))
    with open(pdf_path, "wb") as fh:
        writer.write(fh)


# ------------------------------------------------------------- flowables ---
class CodeBox(Flowable):
    """Long code block that can break across pages (a table cell cannot)."""
    PAD_L, PAD_R, PAD_T, PAD_B = 8, 8, 7, 5

    def __init__(self, pre, width, background):
        super().__init__()
        self.pre, self.width, self.background = pre, width, background
        self.spaceBefore, self.spaceAfter = 3, 9

    def wrap(self, aw, ah):
        _, h = self.pre.wrap(self.width - self.PAD_L - self.PAD_R, ah)
        self.height = h + self.PAD_T + self.PAD_B
        return self.width, self.height

    def split(self, aw, ah):
        inner = ah - self.PAD_T - self.PAD_B
        if inner < 3 * code_style.leading:
            return []
        parts = self.pre.split(self.width - self.PAD_L - self.PAD_R, inner)
        if len(parts) < 2:
            return []
        boxes = [CodeBox(part, self.width, self.background) for part in parts]
        boxes[0].spaceAfter = 0
        boxes[-1].spaceBefore = 0
        return boxes

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.background)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.restoreState()
        self.pre.drawOn(c, self.PAD_L, self.PAD_B)


def code_block(text, width=FRAME_W, background=CODE_BG):
    pre = Preformatted(text, code_style)
    if text.count("\n") > 45:
        return CodeBox(pre, width, background)
    t = Table([[pre]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    t.spaceBefore, t.spaceAfter = 3, 9
    return t


def callout(paras):
    content = [Paragraph(inline(p, "note"), note) for p in paras]
    content[-1].style = ParagraphStyle("note_last", parent=note, spaceAfter=0)
    t = Table([[content]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NOTE_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, NOTE_BAR),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    t.spaceBefore, t.spaceAfter = 4, 12
    return t


def aside(title_text, blocks):
    """Grey box with a bold title, for side notes such as ARM differences."""
    inner_w = FRAME_W - 22
    content = [Paragraph(f"<b>{inline(title_text, 'note')}</b>", note)]
    for kind, data in blocks:
        if kind == "code":
            content.append(code_block(data, inner_w, ASIDE_CODE_BG))
        elif kind == "bullet":
            content.append(Paragraph(inline(data, "note"), note_bullet, bulletText="\u2022"))
        elif kind == "table":
            widths, rows, header = data
            # Scale the columns down so the table fits inside the grey box
            scale = min(1.0, inner_w / sum(widths))
            tbl = data_table([w * scale for w in widths], rows, header)
            tbl.spaceBefore, tbl.spaceAfter = 2, 8
            content.append(tbl)
        else:  # paragraphs, and anything else rendered as text
            text = data if isinstance(data, str) else " ".join(data)
            content.append(Paragraph(inline(text, "note"), note))
    last = content[-1]
    if isinstance(last, Paragraph):
        last.style = ParagraphStyle("note_last", parent=last.style, spaceAfter=0)
    else:
        last.spaceAfter = 0
    t = Table([[content]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ASIDE_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ASIDE_BAR),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    t.spaceBefore, t.spaceAfter = 4, 12
    return t


def danger(paras):
    """Red box for steps that can leave the machine unbootable or lose data."""
    content = []
    for p in paras:
        xml = inline(p, "note")
        # the bold lead, if any, is shown in red
        xml = re.sub(r"^<b>(.*?)</b>", rf'<font color="{DANGER_INK}"><b>\1</b></font>', xml)
        content.append(Paragraph(xml, note))
    content[-1].style = ParagraphStyle("note_last", parent=note, spaceAfter=0)
    t = Table([[content]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DANGER_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, DANGER_BAR),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    t.spaceBefore, t.spaceAfter = 4, 12
    return t


def data_table(widths, rows, header):
    data = []
    for r, row in enumerate(rows):
        st = cell_head if (header and r == 0) else cell
        data.append([Paragraph(inline(c, "cell"), st) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5.1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.1),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, STRIPE]),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BLUE))
    t.setStyle(TableStyle(style))
    t.spaceBefore, t.spaceAfter = 4, 14
    return t


def todo_box(title_text, lines):
    content = [Paragraph(inline(title_text), todo_title)]
    for ln in lines:
        if ln.startswith("~ "):
            content.append(Paragraph(inline(ln[2:], "small"), todo_small))
        else:
            content.append(Paragraph(inline(ln), todo_line))
    t = Table([[content]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    t.spaceBefore, t.spaceAfter = 18, 0
    return t


class FlowDiagram(Flowable):
    """Vertical chain of boxes joined by arrows, each with a note on its right."""
    BOX_W, BOX_H, GAP, NOTE_X = 150, 29, 13, 168

    def __init__(self, steps):
        super().__init__()
        self.steps = steps          # list of (label, description, highlighted)
        self.label_style = ParagraphStyle("flow_label", fontName=BOLD, fontSize=7.8,
                                          leading=9.5, textColor=INK, alignment=1)
        self.note_style = ParagraphStyle("flow_note", fontName=SANS, fontSize=7.8,
                                         leading=9.8, textColor=INK)
        self.spaceBefore, self.spaceAfter = 6, 14

    def wrap(self, aW, aH):
        self.width = aW
        n = len(self.steps)
        self.height = n * self.BOX_H + (n - 1) * self.GAP
        return aW, self.height

    def draw(self):
        c = self.canv
        note_w = self.width - self.NOTE_X
        for i, (label, desc, hot) in enumerate(self.steps):
            top = self.height - i * (self.BOX_H + self.GAP)
            y = top - self.BOX_H
            c.setLineWidth(1 if hot else 0.6)
            c.setStrokeColor(BLUE if hot else RULE)
            c.setFillColor(colors.HexColor("#e8f4fc") if hot else CODE_BG)
            c.roundRect(0, y, self.BOX_W, self.BOX_H, 4, stroke=1, fill=1)
            lab = Paragraph(inline(label), self.label_style)
            _, lh = lab.wrap(self.BOX_W - 8, self.BOX_H)
            lab.drawOn(c, 4, y + (self.BOX_H - lh) / 2)
            # connector and note
            mid = y + self.BOX_H / 2
            c.setStrokeColor(RULE)
            c.setLineWidth(0.6)
            c.line(self.BOX_W + 4, mid, self.NOTE_X - 6, mid)
            note = Paragraph(inline(desc).replace(" // ", "<br/>"), self.note_style)
            _, nh = note.wrap(note_w, self.BOX_H * 2)
            note.drawOn(c, self.NOTE_X, mid - nh / 2)
            # arrow to the next box
            if i < len(self.steps) - 1:
                x = self.BOX_W / 2
                c.setStrokeColor(MUTED)
                c.setFillColor(MUTED)
                c.line(x, y, x, y - self.GAP + 4)
                p = c.beginPath()
                p.moveTo(x - 3, y - self.GAP + 4)
                p.lineTo(x + 3, y - self.GAP + 4)
                p.lineTo(x, y - self.GAP)
                p.close()
                c.drawPath(p, stroke=0, fill=1)


class Keep(KeepTogether):
    """KeepTogether that measures its group with additive spacing, as the frame does."""

    def wrap(self, aW, aH):
        dims = []
        W, H = _listWrapOn(self._content, aW, self.canv, mergeSpace=0, dims=dims)
        self._H = H
        self._H0 = dims and dims[0][1] or 0
        self._wrapInfo = aW, aH
        return W, 0xffffff  # force a split, like KeepTogether


class TocAnchor(Spacer):
    """Invisible TOC and outline entry (used for the final "to do" box)."""

    def __init__(self, text, level=0):
        super().__init__(0, 0)
        self.toc_level = level
        self.plain = text


class Heading(Paragraph):
    """A numbered heading that feeds the table of contents and the outline."""

    def __init__(self, text, style, level):
        super().__init__(inline(text), style)
        self.toc_level = level
        self.plain = re.sub(r"[`*]", "", text)


# -------------------------------------------------------------- document ---
class GuideDoc(BaseDocTemplate):
    def __init__(self, filename, doc_title, header, **kw):
        super().__init__(filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=TOP, bottomMargin=MARGIN, title=doc_title,
                         creator="build_guide.py", **kw)
        self.header_text = header
        frame = Frame(MARGIN, MARGIN, FRAME_W, PAGE_H - TOP - MARGIN, id="f",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                      overlapAttachedSpace=0)
        self.addPageTemplates([
            PageTemplate("toc", frames=[frame], onPage=self.decorate_toc),
            PageTemplate("body", frames=[frame], onPage=self.decorate_body),
        ])
        self.seq = 0
        self.body_start = None

    def handle_documentBegin(self):
        super().handle_documentBegin()
        self.seq = 0
        self.body_start = None

    # page furniture
    def _header(self, canv):
        canv.saveState()
        canv.setFont(SANS, 7.5)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN, PAGE_H - 37.0, self.header_text)
        canv.setStrokeColor(INK)
        canv.setLineWidth(0.6)
        canv.line(MARGIN, PAGE_H - 40.4, PAGE_W - MARGIN, PAGE_H - 40.4)
        canv.restoreState()

    def _footer(self, canv, text):
        canv.saveState()
        canv.setFont(SANS, 7.5)
        canv.setFillColor(MUTED)
        canv.drawRightString(PAGE_W - MARGIN, 34.0, text)
        canv.restoreState()

    def decorate_toc(self, canv, doc):
        self._header(canv)
        self._footer(canv, "Sommaire")

    def decorate_body(self, canv, doc):
        if self.body_start is None:
            self.body_start = canv.getPageNumber()
        self._header(canv)
        self._footer(canv, f"Page {canv.getPageNumber() - self.body_start + 1}")

    def afterFlowable(self, flowable):
        if isinstance(flowable, (Heading, TocAnchor)):
            self.seq += 1
            key = f"h{self.seq}"
            canv = self.canv
            canv.bookmarkPage(key)
            canv.addOutlineEntry(flowable.plain, key, level=flowable.toc_level,
                                 closed=(flowable.toc_level == 0))
            start = self.body_start or canv.getPageNumber()
            page = canv.getPageNumber() - start + 1
            self.notify("TOCEntry", (flowable.toc_level, flowable.plain, page, key))


def make_toc():
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle("toc0", fontName=BOLD, fontSize=10, leading=12.4, textColor=INK,
                       leftIndent=0, firstLineIndent=0, spaceBefore=2.4, spaceAfter=0),
        ParagraphStyle("toc1", fontName=SANS, fontSize=9, leading=10.6, textColor=TOC_GREY,
                       leftIndent=22, firstLineIndent=0, spaceBefore=0, spaceAfter=0),
    ]
    for st in toc.levelStyles:
        st.spaceShrinkage = SHRINK
    return toc


# ----------------------------------------------------------- screenshots ---
img_caption = ParagraphStyle("img_caption", fontName=SANS, fontSize=7.8, leading=10.5,
                             textColor=MUTED, spaceBefore=3, spaceAfter=8)
BOX_RED = (217, 48, 37)


def screenshot(spec, base_dir):
    """Screenshot with red frames and number badges drawn on it, plus a caption."""
    from io import BytesIO
    from PIL import Image as PILImage, ImageDraw, ImageFont
    from reportlab.platypus import Image as RLImage

    img = PILImage.open(os.path.join(base_dir, spec["path"])).convert("RGB")
    ox, oy = 0.0, 0.0
    if spec["crop"]:
        ox, oy = spec["crop"][0], spec["crop"][1]
        img = img.crop(tuple(int(round(v)) for v in spec["crop"]))
    # draw at 2x so that frames and badges stay smooth once scaled down
    k = 2
    img = img.resize((img.width * k, img.height * k), PILImage.LANCZOS)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_DIR + "DejaVuSans-Bold.ttf", 11 * k)
    for (x0, y0, x1, y1), label in spec["boxes"]:
        r = [(x0 - ox) * k, (y0 - oy) * k, (x1 - ox) * k, (y1 - oy) * k]
        draw.rounded_rectangle(r, radius=4 * k, outline=BOX_RED, width=2 * k)
        if label:
            rad = 8 * k
            cx, cy = r[0], r[1]
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=BOX_RED)
            draw.text((cx, cy), label, fill="white", font=font, anchor="mm")
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    buf.seek(0)
    width = FRAME_W * spec["width"]
    height = width * img.height / img.width
    max_h = 0.55 * (PAGE_H - TOP - MARGIN)
    if height > max_h:
        width, height = width * max_h / height, max_h
    pic = RLImage(buf, width=width, height=height)
    frame = Table([[pic]], colWidths=[width])
    frame.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    frame.hAlign = "CENTER"
    parts = [Spacer(1, 2), frame]
    if spec["caption"]:
        cap = ParagraphStyle("img_caption_c", parent=img_caption, alignment=1)
        parts.append(Paragraph(inline(spec["caption"]), cap))
    return KeepTogether(parts)


# ---------------------------------------------------------------- parser ---
def parse(src):
    lines = src.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            text = CodeText("\n".join(lines[i + 1:j]))
            info = ln[3:].strip()
            if info.startswith("file "):
                text.attach = info[5:].strip()
            blocks.append(("code", text))
            i = j + 1
            continue
        if ln.startswith("::: "):
            j = i + 1
            while lines[j].strip() != ":::":
                j += 1
            blocks.append(("aside", (ln[4:].strip(), parse("\n".join(lines[i + 1:j])))))
            i = j + 1
            continue
        # gather the block until a blank line
        j = i
        while j < len(lines) and lines[j].strip():
            j += 1
        chunk = lines[i:j]
        i = j
        first = chunk[0]
        if first.startswith("@header "):
            blocks.append(("header", first[8:]))
        elif first.startswith("@title "):
            blocks.append(("title", first[7:]))
        elif first.startswith("@subtitle "):
            blocks.append(("subtitle", " ".join([first[10:]] + chunk[1:])))
        elif first.startswith("### "):
            blocks.append(("h3", first[4:]))
        elif first.startswith("## "):
            blocks.append(("h2", first[3:]))
        elif first.startswith("# "):
            blocks.append(("h1", first[2:]))
        elif first.startswith("> "):
            blocks.append(("callout", [c[2:] for c in chunk]))
        elif first.startswith("!! "):
            blocks.append(("danger", [c[3:] for c in chunk]))
        elif first.startswith("- "):
            blocks.append(("bullet", " ".join([first[2:]] + chunk[1:])))
        elif first.startswith("|="):
            spec = first[2:].split()
            header = "header" in spec
            widths = [float(w) for w in spec if w != "header"]
            rows = []
            for r in chunk[1:]:
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", r.strip())[1:-1]]
                rows.append([c.replace("\\|", "|") for c in cells])
            blocks.append(("table", (widths, rows, header)))
        elif first == "!flow":
            steps = []
            for r in chunk[1:]:
                label, desc = [x.strip() for x in r.split("|", 1)]
                hot = label.startswith("*")
                steps.append((label.lstrip("*").strip(), desc, hot))
            blocks.append(("flow", steps))
        elif first.startswith("!todo "):
            blocks.append(("todo", (first[6:], chunk[1:])))
        elif first.startswith("!img "):
            path, _, caption = first[5:].partition("|")
            spec = {"path": path.strip(), "caption": caption.strip(), "crop": None,
                    "boxes": [], "width": 1.0}
            for r in chunk[1:]:
                word, *args = r.split()
                if word == "crop":
                    spec["crop"] = tuple(float(a) for a in args)
                elif word == "box":
                    spec["boxes"].append((tuple(float(a) for a in args[:4]),
                                          args[4] if len(args) > 4 else None))
                elif word == "width":
                    spec["width"] = float(args[0])
                else:
                    sys.exit(f"unknown !img option: {r}")
            blocks.append(("image", spec))
        else:
            blocks.append(("para", " ".join(chunk)))
    return blocks


def build(src_path, out_path):
    src = open(src_path, encoding="utf-8").read()
    blocks = parse(src)
    attachments = collect_attachments(src)
    doc_title = next((d for k, d in blocks if k == "title"), "Guide")
    header = next((d for k, d in blocks if k == "header"), doc_title)
    story = [
        Paragraph("Sommaire", toc_title),
        Paragraph(inline(doc_title), toc_sub),
        make_toc(),
        NextPageTemplate("body"),
        PageBreak(),
    ]
    pending = []        # headings and lead-in paragraphs waiting for their content

    def emit(flowable, keep_with_next=False):
        pending.append(flowable)
        if not keep_with_next:
            story.append(Keep(pending[:]) if len(pending) > 1 else pending[0])
            pending.clear()

    for kind, data in blocks:
        if kind == "title":
            emit(Paragraph(inline(data), title))
        elif kind == "subtitle":
            emit(Paragraph(inline(data), subtitle))
        elif kind == "h1":
            emit(Heading(data, h1, 0), True)
        elif kind == "h2":
            emit(Heading(data, h2, 1), True)
        elif kind == "h3":
            emit(Paragraph(inline(data), h3), True)
        elif kind == "para":
            # an introductory paragraph ending with ":" stays with what follows
            emit(Paragraph(inline(data), body), data.rstrip().endswith(":"))
        elif kind == "bullet":
            emit(Paragraph(inline(data, "bullet"), bullet, bulletText="\u2022"))
        elif kind == "code":
            files = [attachments[m.group(1)][0] for m in HEREDOC.finditer(data + "\n")
                     if m.group(1) in attachments]
            if getattr(data, "attach", None):
                files.append(attachments["file:" + data.attach][0])
            if files:
                emit(code_block(data), True)
                label = "Fichier joint au PDF" if len(files) == 1 else "Fichiers joints au PDF"
                emit(Paragraph(label + " : " + ", ".join(
                    "<font face='%s'>%s</font>" % (MONO, f) for f in files), attach_caption))
            else:
                emit(code_block(data))
        elif kind == "callout":
            emit(callout(data), data[-1].rstrip().endswith(":"))
        elif kind == "danger":
            emit(danger(data), data[-1].rstrip().endswith(":"))
        elif kind == "table":
            emit(data_table(*data))
        elif kind == "aside":
            emit(aside(*data))
        elif kind == "flow":
            emit(FlowDiagram(data))
        elif kind == "todo":
            emit(TocAnchor(data[0]), True)
            emit(todo_box(*data))
        elif kind == "image":
            emit(screenshot(data, os.path.dirname(os.path.abspath(src_path))))
    if pending:
        story.extend(pending)
    doc = GuideDoc(out_path, doc_title, header)
    doc.multiBuild(story)
    embed_attachments(out_path, attachments)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
