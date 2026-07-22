"""Shared helpers for PDF/Excel ledger exports (wrapping long text)."""
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph


def _escape_pdf_text(value):
    if value is None or value == '':
        return '—'
    s = str(value)
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def pdf_cell_paragraph(value, font_size=6, align=TA_CENTER):
    style = ParagraphStyle(
        name='LedgerCell',
        fontName='Helvetica',
        fontSize=font_size,
        leading=font_size + 2,
        alignment=align,
        wordWrap='CJK',
    )
    return Paragraph(_escape_pdf_text(value), style)


def text_column_indices(headers):
    """Columns that should wrap (exclude numeric / index columns)."""
    indices = []
    for i, header in enumerate(headers):
        h = header.lower()
        if h in ('no', '#') or 'amount' in h or 'balance' in h or 'no of' in h:
            continue
        if h in ('nts',) or h.endswith(' qty'):
            continue
        indices.append(i)
    return indices


def pdf_row_cells(row, text_indices, *, font_size=6):
    """Convert a data row to ReportLab table cells with wrapping on text columns."""
    text_set = set(text_indices)
    cells = []
    for i, val in enumerate(row):
        if isinstance(val, float):
            cells.append(f'{val:,.2f}')
        elif isinstance(val, int) and i == 0:
            cells.append(str(val))
        elif i in text_set:
            cells.append(pdf_cell_paragraph(val, font_size=font_size))
        elif val is None:
            cells.append('—')
        else:
            cells.append(str(val))
    return cells


def proportional_col_widths(headers, usable_width, name_boost=2.5):
    """Assign column widths; reserve space for amount, payment type, and balance."""
    weights = []
    for header in headers:
        h = header.lower()
        if 'balance' in h or 'amount' in h:
            weights.append(1.15)
        elif 'payment' in h or h == 'type':
            weights.append(1.05)
        elif 'name' in h or 'customer' in h or 'client' in h or h == 'guest':
            weights.append(name_boost)
        elif 'invoice' in h or 'res' in h:
            weights.append(1.25)
        elif 'date' in h or 'issued' in h:
            weights.append(1.1)
        elif h in ('no', '#'):
            weights.append(0.45)
        else:
            weights.append(1.0)
    total = sum(weights) or 1
    return [usable_width * w / total for w in weights]
