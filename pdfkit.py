"""Small helper layer over reportlab so every assignment PDF looks the same."""
import textwrap
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                                Preformatted, PageBreak, KeepTogether)

BLUE, GREY = colors.HexColor("#2B5C94"), colors.HexColor("#F3F5F8")
body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.2, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=8.6, leading=11.5, spaceAfter=0)
cell = ParagraphStyle("cell", parent=body, fontSize=8.8, leading=11.6, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=BLUE, spaceAfter=4)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BLUE,
                    spaceBefore=12, spaceAfter=5, keepWithNext=1)
cap = ParagraphStyle("cap", parent=body, fontName="Helvetica-Oblique", fontSize=8.5, textColor=colors.grey,
                     alignment=1)
mono = ParagraphStyle("mono", fontName="Courier", fontSize=6.7, leading=8.1)
note = ParagraphStyle("note", parent=body, fontSize=9, leading=12.5)


def clean(s):
    return s.encode("latin-1", "replace").decode("latin-1")


def P(t, st=body):
    return Paragraph(t, st)


def H2(t):
    return Paragraph(t, h2)


def wrap_lines(text, width=112):
    out = []
    for line in clean(text).expandtabs(4).split("\n"):
        if len(line) <= width:
            out.append(line)
            continue
        ind = len(line) - len(line.lstrip())
        out += textwrap.wrap(line, width, subsequent_indent=" " * (ind + 6), drop_whitespace=False,
                             replace_whitespace=False, break_long_words=True)
    return out


def block(text, bg=GREY, chunk=46, title=None):
    lines = wrap_lines(text.rstrip("\n"))
    items = []
    if title:
        items.append(Paragraph("<b>%s</b>" % title, small))
        items.append(Spacer(1, 3))
    for i in range(0, len(lines), chunk):
        t = Table([[Preformatted("\n".join(lines[i:i + chunk]), mono)]], colWidths=[17.0 * cm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        items.append(t)
    return items


def code(path, title=None):
    return block(open(path, encoding="utf-8").read(), GREY, 46, title or path)


def logblock(path, title=None, bg=colors.HexColor("#EEF6EE")):
    import os
    if not os.path.exists(path):
        path = "logs/%s.log" % path
    return block(open(path, encoding="utf-8").read(), bg, 46, title or "Console output (%s)" % path)


def img(path, width_cm=15.5, caption=None):
    iw, ih = ImageReader(path).getSize()
    w = width_cm * cm
    im = Image(path, width=w, height=w * ih / iw)
    items = [im]
    if caption:
        items += [Spacer(1, 2), Paragraph(caption, cap)]
    return [KeepTogether(items), Spacer(1, 6)]


def table(rows, widths, header=True):
    data = []
    for r, row in enumerate(rows):
        data.append([Paragraph(str(c), cellb if (header and r == 0) or ci == 0 else cell)
                     for ci, c in enumerate(row)])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CF")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE7F5")))
    t.setStyle(TableStyle(st))
    return [t, Spacer(1, 8)]


def build(filename, code_id, title, objective, story):
    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(2 * cm, 1.2 * cm, "MealPilot agent  |  Assignment %s" % code_id)
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, "page %d" % d.page)
        c.restoreState()
    doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm, title="Assignment %s - %s" % (code_id, title),
                            author="")
    head = [P("Assignment %s" % code_id, ParagraphStyle("k", parent=body, textColor=colors.grey, spaceAfter=0)),
            P(title, h1)]
    info = Table([[P("<b>Name:</b> ____________________", small), P("<b>Reg. No:</b> ______________", small),
                   P("<b>Agent persona:</b> MealPilot (weekly meal planner for Indian households)", small)]],
                 colWidths=[5.2 * cm, 4.4 * cm, 7.4 * cm])
    info.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    flow = head + [info, H2("Objective"), P(objective)] + story
    doc.build(flow)
