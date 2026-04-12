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
    HRFlowable, Table, TableStyle, Flowable
)
from reportlab.pdfbase.pdfmetrics import stringWidth


# ── Colour palette ────────────────────────────────────────────
UWI_BLUE   = colors.HexColor('#1e3a8a')
UWI_LIGHT  = colors.HexColor('#dbeafe')
GRAY_MID   = colors.HexColor('#6b7280')
BLACK      = colors.black

# ── Page geometry ─────────────────────────────────────────────
MARGIN     = 2.5 * cm
PAGE_W     = A4[0]
TEXT_W     = PAGE_W - 2 * MARGIN   # ≈ 453 pt


# ═══════════════════════════════════════════════════════════════
#  Custom TOC Entry Flowable
#  Measures actual rendered widths so dots always fill exactly
# ═══════════════════════════════════════════════════════════════

class TOCEntry(Flowable):
    """
    Renders one TOC line:
      [indent]  N.  Title ............... page
    Uses pdfmetrics.stringWidth() so dots fill precisely regardless
    of title length or font proportions.
    """
    FONT      = 'Times-Roman'
    FONT_SIZE = 11
    LINE_H    = 20      # total flowable height (pt)
    BASELINE  = 5       # distance from bottom of flowable to text baseline

    def __init__(self, number, title, page_str, width=None, bold=False):
        Flowable.__init__(self)
        self.number    = number
        self.title     = title
        self.page_str  = str(page_str)
        self.width     = width or TEXT_W
        self.bold      = bold
        self.font      = 'Times-Bold' if bold else 'Times-Roman'
        self.font_size = 12 if bold else 11
        self.indent    = 0.5 * cm if number else 0
        self.height    = 22 if bold else 20

    def draw(self):
        c = self.canv
        c.setFillColor(UWI_BLUE)
        c.setFont(self.font, self.font_size)

        label = f"{self.number}.    {self.title}" if self.number else self.title

        # Measure actual pixel widths
        label_w = stringWidth(label,         self.font, self.font_size)
        page_w  = stringWidth(self.page_str, self.font, self.font_size)
        dot_w   = stringWidth('.',           self.font, self.font_size)

        # Space available for dots (4pt gap before page number)
        available = self.width - self.indent - label_w - page_w - 4
        num_dots  = max(3, int(available / dot_w))
        dots      = '.' * num_dots

        y = self.BASELINE

        # Draw title
        c.drawString(self.indent, y, label)
        # Draw dots immediately after title
        c.drawString(self.indent + label_w, y, dots)
        # Draw page number flush right
        c.drawRightString(self.width, y, self.page_str)

        # Underline everything
        c.setStrokeColor(UWI_BLUE)
        c.setLineWidth(0.5)
        c.line(self.indent, y - 2, self.width, y - 2)


# ── Shared paragraph styles ───────────────────────────────────
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
        'toc_main_heading': ParagraphStyle(
            'toc_main_heading',
            fontName='Times-Bold', fontSize=12,
            leading=17, textColor=UWI_BLUE,
            spaceAfter=0,
        ),
        'toc_date_line': ParagraphStyle(
            'toc_date_line',
            fontName='Times-Bold', fontSize=11,
            leading=16, textColor=UWI_BLUE,
            spaceBefore=4, spaceAfter=8,
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
    }


# ── Cover page builder ────────────────────────────────────────
def _cover(story, title_line, date_line, total):
    s = _styles()
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
    story.append(Paragraph(title_line, s['cover_title']))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(date_line, s['cover_sub']))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=UWI_BLUE))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f'Total Submissions: {total}',
        ParagraphStyle('tot', fontName='Times-Roman', fontSize=12,
                       alignment=TA_CENTER, textColor=GRAY_MID)
    ))
    story.append(PageBreak())


# ── TOC page builder ─────────────────────────────────────────
def _toc_page(story, heading_text, date_text, reports):
    s = _styles()
    # Heading — the long bold guidelines title
    story.append(Paragraph(heading_text, s['toc_main_heading']))
    story.append(Spacer(1, 0.15 * cm))
    # Date line
    story.append(Paragraph(date_text, s['toc_date_line']))

    # One TOCEntry per report
    for i, report in enumerate(reports, start=1):
        story.append(TOCEntry(
            number=i,
            title=report.title,
            page_str=str(i + 2),   # page estimate (cover=1, toc=2, reports from 3)
            width=TEXT_W,
        ))
    story.append(PageBreak())


# ── Report sections builder ──────────────────────────────────
def _report_sections(story, reports, include_author=True):
    s = _styles()
    for i, report in enumerate(reports, start=1):
        story.append(Paragraph(
            f'{i}.&nbsp;&nbsp;&nbsp;{report.title}',
            s['section_heading']
        ))
        story.append(HRFlowable(width='100%', thickness=0.5, color=UWI_LIGHT))
        story.append(Spacer(1, 0.3 * cm))

        meta_rows = [['DATE', str(report.date_of_report)]]
        if include_author:
            meta_rows.insert(0, ['SUBMITTED BY',
                                  report.user.get_full_name() or report.user.username])
        committees = list(report.committees.all())
        if committees:
            meta_rows.append(['COMMITTEE', ', '.join(str(c) for c in committees)])
        if report.category:
            meta_rows.append(['CATEGORY', report.category.name])
        participants = list(report.participants.all())
        if participants:
            meta_rows.append(['PARTICIPANTS', ', '.join(p.name for p in participants)])

        meta_data = [
            [Paragraph(r[0], s['meta_label']), Paragraph(r[1], s['meta_value'])]
            for r in meta_rows
        ]
        meta_table = Table(meta_data, colWidths=[3.5 * cm, None])
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


# ═══════════════════════════════════════════════════════════════
#  ANNUAL REPORT PDF  (date-range aware)
# ═══════════════════════════════════════════════════════════════

def generate_date_range_pdf(reports, date_from, date_to, label=None):
    """
    Generate an annual-style PDF for any arbitrary date range.

    Args:
        reports   : queryset/list already filtered to the date range
        date_from : datetime.date – range start
        date_to   : datetime.date – range end
        label     : short title string, e.g. "2024", "2023/2024",
                    or "01 Jan 2024 – 30 Jun 2024".  Auto-derived if None.
    """
    if label is None:
        label = (f'{date_from.strftime("%d %B %Y")} \u2013 '
                 f'{date_to.strftime("%d %B %Y")}')

    date_str = (f'{date_from.strftime("%d %B %Y")} \u2013 '
                f'{date_to.strftime("%d %B %Y")}')

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f'DCIT Annual Report {label}',
        author='University of the West Indies \u2013 DCIT',
    )
    story = []

    _cover(story,
           title_line=f'Annual Report {label}',
           date_line=date_str,
           total=len(reports))

    _toc_page(story,
              heading_text='Guidelines for the Preparation of the Narrative '
                           'Sections of the Annual &amp; Faculty Reports',
              date_text=date_str,
              reports=reports)

    _report_sections(story, reports, include_author=True)

    doc.build(story)
    buf.seek(0)
    return buf


# Keep the old name as a thin wrapper so nothing else breaks
def generate_annual_pdf(reports, year):
    from datetime import date
    return generate_date_range_pdf(
        reports,
        date_from=date(year, 1, 1),
        date_to=date(year, 12, 31),
        label=str(year),
    )


# ═══════════════════════════════════════════════════════════════
#  MY REPORTS PDF  (single user)
# ═══════════════════════════════════════════════════════════════

def generate_my_reports_pdf(reports, user):
    buf       = BytesIO()
    full_name = user.get_full_name() or user.username

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f'My Reports – {full_name}',
        author=full_name,
    )
    story = []
    s = _styles()

    # Cover
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

    # TOC
    _toc_page(story,
              heading_text='Table of Contents',
              date_text=f'Submitted by {full_name}',
              reports=reports)

    _report_sections(story, reports, include_author=False)

    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
#  ACADEMIC YEAR PDF  (Aug 1 – Jul 31)
# ═══════════════════════════════════════════════════════════════

def generate_academic_pdf(reports, start_year):
    buf      = BytesIO()
    end_year = start_year + 1
    date_str = f'01 August {start_year} \u2013 31 July {end_year}'

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f'DCIT Academic Report {start_year}/{end_year}',
        author='University of the West Indies – DCIT',
    )
    story = []

    _cover(story,
           title_line=f'Academic Year Report {start_year}/{end_year}',
           date_line=date_str,
           total=len(reports))

    _toc_page(story,
              heading_text='Guidelines for the Preparation of the Narrative '
                           'Sections of the Annual &amp; Faculty Reports',
              date_text=date_str,
              reports=reports)

    _report_sections(story, reports, include_author=True)

    doc.build(story)
    buf.seek(0)
    return buf