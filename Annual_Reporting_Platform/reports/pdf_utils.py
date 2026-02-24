"""
pdf_utils.py  —  ReportLab PDF generation for DCIT Reports
Place this file in your reports/ app directory.
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as rl_canvas


# ── Colour palette ────────────────────────────────────────────
UWI_BLUE   = colors.HexColor('#1e3a8a')
UWI_LIGHT  = colors.HexColor('#dbeafe')
GRAY_MID   = colors.HexColor('#6b7280')
GRAY_LIGHT = colors.HexColor('#f3f4f6')
BLACK      = colors.black


# ── Shared styles ─────────────────────────────────────────────
def _styles():
    return {
        'cover_title': ParagraphStyle(
            'cover_title',
            fontName='Times-Bold', fontSize=22,
            leading=28, alignment=TA_CENTER,
            textColor=UWI_BLUE, spaceAfter=6,
        ),
        'cover_sub': ParagraphStyle(
            'cover_sub',
            fontName='Times-Roman', fontSize=13,
            leading=18, alignment=TA_CENTER,
            textColor=GRAY_MID, spaceAfter=4,
        ),
        'toc_heading': ParagraphStyle(
            'toc_heading',
            fontName='Times-Bold', fontSize=13,
            leading=18, alignment=TA_LEFT,
            textColor=UWI_BLUE, underlineWidth=1,
            underlineColor=UWI_BLUE,
        ),
        'toc_entry': ParagraphStyle(
            'toc_entry',
            fontName='Times-Roman', fontSize=11,
            leading=18, leftIndent=18,
            textColor=UWI_BLUE, underlineWidth=0.5,
            underlineColor=UWI_BLUE,
        ),
        'section_heading': ParagraphStyle(
            'section_heading',
            fontName='Times-Bold', fontSize=14,
            leading=20, textColor=UWI_BLUE,
            spaceBefore=10, spaceAfter=4,
        ),
        'meta_label': ParagraphStyle(
            'meta_label',
            fontName='Helvetica-Bold', fontSize=9,
            leading=14, textColor=GRAY_MID,
            spaceAfter=1,
        ),
        'meta_value': ParagraphStyle(
            'meta_value',
            fontName='Helvetica', fontSize=10,
            leading=14, textColor=BLACK,
            spaceAfter=6,
        ),
        'body': ParagraphStyle(
            'body',
            fontName='Times-Roman', fontSize=11,
            leading=16, textColor=BLACK,
            spaceBefore=6, spaceAfter=6,
        ),
        'badge': ParagraphStyle(
            'badge',
            fontName='Helvetica-Bold', fontSize=8,
            leading=12, textColor=UWI_BLUE,
        ),
        'page_num': ParagraphStyle(
            'page_num',
            fontName='Times-Roman', fontSize=9,
            alignment=TA_RIGHT, textColor=GRAY_MID,
        ),
    }


def _toc_row(number, title, page_str, styles):
    """Build a single dotted TOC row."""
    label = f"{number}.    {title}" if number else title
    dots  = '.' * max(5, 90 - len(label) - len(page_str))
    text  = f'<u>{label}{dots}{page_str}</u>'
    indent = 36 if number else 0
    style = ParagraphStyle(
        'toc_r',
        fontName='Times-Roman', fontSize=11,
        leading=18, leftIndent=indent,
        textColor=UWI_BLUE,
    )
    return Paragraph(text, style)


# ═══════════════════════════════════════════════════════════════
#  ANNUAL REPORT PDF
# ═══════════════════════════════════════════════════════════════

def generate_annual_pdf(reports, year):
    """
    Returns a BytesIO containing the annual report PDF.
    reports  : queryset of Report objects
    year     : int
    """
    buf    = BytesIO()
    s      = _styles()
    W, H   = A4
    margin = 2.5 * cm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin,  bottomMargin=margin,
        title=f'DCIT Annual Report {year}',
        author='University of the West Indies – DCIT',
    )

    story = []

    # ── Cover page ────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        'University of the West Indies',
        ParagraphStyle('u', fontName='Times-Roman', fontSize=14,
                       alignment=TA_CENTER, textColor=GRAY_MID)
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        'Department of Computing and Information Technology',
        ParagraphStyle('d', fontName='Times-Bold', fontSize=15,
                       alignment=TA_CENTER, textColor=UWI_BLUE)
    ))
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width='100%', thickness=2, color=UWI_BLUE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f'Annual Report {year}', s['cover_title']))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f'01 August {year - 1} \u2013 31 July {year}',
        s['cover_sub']
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=UWI_BLUE))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f'Total Submissions: {len(reports)}',
        ParagraphStyle('tot', fontName='Times-Roman', fontSize=12,
                       alignment=TA_CENTER, textColor=GRAY_MID)
    ))
    story.append(PageBreak())

    # ── Table of Contents ────────────────────────────────────
    story.append(Paragraph(
        'Guidelines for the Preparation of the Narrative Sections '
        'of the Annual &amp; Faculty Reports',
        s['toc_heading']
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f'01 August {year - 1} \u2013 31 July {year}',
        ParagraphStyle('dp', fontName='Times-Bold', fontSize=11,
                       leading=16, textColor=UWI_BLUE)
    ))
    story.append(Spacer(1, 0.5 * cm))

    for i, report in enumerate(reports, start=1):
        title = report.title
        story.append(_toc_row(i, title, str(i + 2), s))

    story.append(PageBreak())

    # ── Report Sections ──────────────────────────────────────
    for i, report in enumerate(reports, start=1):

        # Section heading
        story.append(Paragraph(
            f'{i}.&nbsp;&nbsp;&nbsp;{report.title}',
            s['section_heading']
        ))
        story.append(HRFlowable(width='100%', thickness=0.5, color=UWI_LIGHT))
        story.append(Spacer(1, 0.3 * cm))

        # Metadata table
        meta_rows = [
            ['DATE', str(report.date_of_report)],
            ['SUBMITTED BY', report.user.get_full_name() if hasattr(report.user, 'get_full_name') else report.user.username],
        ]
        committees = list(report.committees.all())
        if committees:
            meta_rows.append(['COMMITTEE', ', '.join(str(c) for c in committees)])
        if report.category:
            meta_rows.append(['CATEGORY', report.category.name])

        participants = list(report.participants.all())
        if participants:
            meta_rows.append(['PARTICIPANTS', ', '.join(p.name for p in participants)])

        meta_table_data = [
            [
                Paragraph(row[0], s['meta_label']),
                Paragraph(row[1], s['meta_value']),
            ]
            for row in meta_rows
        ]
        meta_table = Table(meta_table_data, colWidths=[3.5 * cm, None])
        meta_table.setStyle(TableStyle([
            ('VALIGN',    (0, 0), (-1, -1), 'TOP'),
            ('ROWPADDING',(0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4 * cm))

        # Body
        story.append(Paragraph(report.description, s['body']))
        story.append(Spacer(1, 0.5 * cm))

        if i < len(reports):
            story.append(HRFlowable(width='100%', thickness=0.3,
                                    color=GRAY_MID, dash=(2, 4)))
            story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
#  MY REPORTS PDF  (single user)
# ═══════════════════════════════════════════════════════════════

def generate_my_reports_pdf(reports, user):
    """
    Returns a BytesIO containing a PDF of the user's own reports.
    """
    buf    = BytesIO()
    s      = _styles()
    margin = 2.5 * cm

    full_name = user.get_full_name() or user.username

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin,  bottomMargin=margin,
        title=f'My Reports – {full_name}',
        author=full_name,
    )

    story = []

    # ── Cover ─────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        'University of the West Indies – DCIT',
        ParagraphStyle('u2', fontName='Times-Roman', fontSize=13,
                       alignment=TA_CENTER, textColor=GRAY_MID)
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=2, color=UWI_BLUE))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph('My Reports', s['cover_title']))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(full_name, s['cover_sub']))
    if user.email:
        story.append(Paragraph(user.email, s['cover_sub']))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=UWI_BLUE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f'Total Reports: {len(reports)}',
        ParagraphStyle('tot2', fontName='Times-Roman', fontSize=11,
                       alignment=TA_CENTER, textColor=GRAY_MID)
    ))
    story.append(PageBreak())

    # ── Table of Contents ────────────────────────────────────
    story.append(Paragraph('Table of Contents', s['toc_heading']))
    story.append(Spacer(1, 0.5 * cm))
    for i, report in enumerate(reports, start=1):
        story.append(_toc_row(i, report.title, str(i + 2), s))
    story.append(PageBreak())

    # ── Report sections ──────────────────────────────────────
    for i, report in enumerate(reports, start=1):
        story.append(Paragraph(
            f'{i}.&nbsp;&nbsp;&nbsp;{report.title}',
            s['section_heading']
        ))
        story.append(HRFlowable(width='100%', thickness=0.5, color=UWI_LIGHT))
        story.append(Spacer(1, 0.3 * cm))

        meta_rows = [['DATE', str(report.date_of_report)]]
        committees = list(report.committees.all())
        if committees:
            meta_rows.append(['COMMITTEE', ', '.join(str(c) for c in committees)])
        if report.category:
            meta_rows.append(['CATEGORY', report.category.name])
        participants = list(report.participants.all())
        if participants:
            meta_rows.append(['PARTICIPANTS', ', '.join(p.name for p in participants)])

        meta_table_data = [
            [Paragraph(r[0], s['meta_label']), Paragraph(r[1], s['meta_value'])]
            for r in meta_rows
        ]
        meta_table = Table(meta_table_data, colWidths=[3.5 * cm, None])
        meta_table.setStyle(TableStyle([
            ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
            ('ROWPADDING',  (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(report.description, s['body']))
        story.append(Spacer(1, 0.5 * cm))

        if i < len(reports):
            story.append(HRFlowable(width='100%', thickness=0.3,
                                    color=GRAY_MID, dash=(2, 4)))
            story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    buf.seek(0)
    return buf
