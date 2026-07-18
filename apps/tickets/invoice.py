from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from apps.core.company import COMPANY
from apps.core.logo import make_logo_drawing
from .utils import get_display_amount

# ── Palette ────────────────────────────────────────────────────────────────────
_NAVY   = colors.HexColor('#1F3A52')
_BLUE   = colors.HexColor('#2E75B6')
_LIGHT  = colors.HexColor('#EEF2F7')
_STRIPE = colors.HexColor('#F5F7FA')
_GREY   = colors.HexColor('#666666')
_DIVIDER = colors.HexColor('#D9E1F2')
_WHITE  = colors.white
_BLACK  = colors.black


def _cv(value, record_currency, exchange_rate, display_currency):
    return float(get_display_amount(value, record_currency, exchange_rate, display_currency))


def _fmt(val):
    return f'{val:,.2f}'


def _para(text, style):
    return Paragraph(str(text), style)


def generate_ticket_invoice(ticket, display_currency, optional_fields):
    """
    optional_fields: set of strings from {'payment_type', 'description', 'issued_date'}
    Returns a BytesIO containing the PDF.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    # ── Styles ──────────────────────────────────────────────────────────────────
    def sty(name, **kw):
        defaults = dict(fontName='Helvetica', fontSize=10, leading=15, spaceAfter=0)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    s_normal   = sty('N')
    s_bold     = sty('B', fontName='Helvetica-Bold')
    s_right    = sty('R', alignment=TA_RIGHT)
    s_vname    = sty('VN', fontName='Helvetica-Bold', fontSize=13, alignment=TA_RIGHT, textColor=_NAVY)
    s_vsub     = sty('VS', fontSize=9, alignment=TA_RIGHT, textColor=_GREY)
    s_title    = sty('T', fontName='Helvetica-Bold', fontSize=26, leading=32,
                     alignment=TA_CENTER, textColor=_NAVY, spaceAfter=4)
    s_label    = sty('L', fontSize=9, textColor=_GREY, leading=14)
    s_value    = sty('V', fontName='Helvetica-Bold', fontSize=10, leading=14)
    s_footer   = sty('F', fontSize=9, textColor=_GREY, leading=13)
    s_footer_b = sty('FB', fontName='Helvetica-Bold', fontSize=10, leading=14)

    el = []   # flowables

    # ── HEADER: logo left, vendor info right ────────────────────────────────────
    logo = make_logo_drawing(150, 52)
    vendor = ticket.vendor
    vendor_block = [
        _para(vendor.name,    s_vname),
        _para(vendor.email,   s_vsub),
        _para(vendor.company, s_vsub),
    ]
    hdr = Table([[logo, vendor_block]], colWidths=['45%', '55%'])
    hdr.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',   (1, 0), (1, 0),   'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(hdr)
    el.append(Spacer(1, 14))
    el.append(HRFlowable(width='100%', thickness=2, color=_NAVY, spaceAfter=10))

    # ── INVOICE TITLE ───────────────────────────────────────────────────────────
    el.append(_para('INVOICE', s_title))
    el.append(HRFlowable(width='100%', thickness=1, color=_DIVIDER, spaceBefore=14, spaceAfter=14))

    # ── INVOICE DETAILS TABLE ───────────────────────────────────────────────────
    rows = [
        [_para('Invoice No', s_label),   _para(ticket.invoice_no,       s_value)],
        [_para('Client',     s_label),   _para(ticket.customer_name,    s_value)],
    ]
    if 'issued_date' in optional_fields:
        rows.append([_para('Issued Date',   s_label), _para(str(ticket.issued_date), s_value)])
    if 'payment_type' in optional_fields:
        rows.append([_para('Payment Type',  s_label), _para(ticket.payment_type,     s_value)])

    detail_tbl = Table(rows, colWidths=[3.5 * cm, None])
    detail_tbl.setStyle(TableStyle([
        ('VALIGN',         (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',     (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
        ('LEFTPADDING',    (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 0),
    ]))
    el.append(detail_tbl)
    el.append(Spacer(1, 20))

    # ── LINE ITEMS TABLE ────────────────────────────────────────────────────────
    c = lambda v: _cv(v, ticket.currency, ticket.exchange_rate, display_currency)

    th_sty = sty('TH', fontName='Helvetica-Bold', fontSize=9,
                  textColor=_WHITE, alignment=TA_CENTER)
    td_sty = sty('TD', fontSize=9)
    td_r   = sty('TDR', fontSize=9, alignment=TA_RIGHT)

    def th(t): return _para(t, th_sty)
    def td(t): return _para(str(t), td_sty)
    def tdr(t): return _para(str(t), td_r)

    item_rows = [[th('Description'), th('Qty'), th(f'Rate ({display_currency})'), th(f'Amount ({display_currency})')]]

    types = [
        ('Adult Ticket',  ticket.adt_qty, ticket.adt_rate),
        ('Child Ticket',  ticket.chd_qty, ticket.chd_rate),
        ('Infant Ticket', ticket.inf_qty, ticket.inf_rate),
    ]
    for label, qty, rate in types:
        if qty:
            conv_rate = c(rate)
            item_rows.append([td(label), tdr(qty), tdr(_fmt(conv_rate)), tdr(_fmt(conv_rate * qty))])

    total = c(ticket.total_amount)
    item_rows.append(['', '', _para('TOTAL', sty('TOT', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT)),
                      _para(_fmt(total), sty('TOTR', fontName='Helvetica-Bold', fontSize=11, alignment=TA_RIGHT, textColor=_NAVY))])

    n = len(item_rows)
    items_tbl = Table(item_rows, colWidths=[None, 2 * cm, 4 * cm, 4 * cm])
    items_tbl.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',    (0, 0), (-1, 0),   _NAVY),
        ('ROWBACKGROUNDS',(0, 1), (-1, n-2), [_WHITE, _STRIPE]),
        # Total row
        ('BACKGROUND',    (0, n-1), (-1, n-1), _LIGHT),
        ('LINEABOVE',     (0, n-1), (-1, n-1), 1.5, _NAVY),
        # Grid
        ('GRID',          (0, 0), (-1, n-2), 0.3, _DIVIDER),
        ('LINEBELOW',     (0, n-1), (-1, n-1), 0.3, _DIVIDER),
        # Padding
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    el.append(items_tbl)

    # ── DESCRIPTION (optional) ──────────────────────────────────────────────────
    if 'description' in optional_fields and ticket.description:
        el.append(Spacer(1, 14))
        el.append(_para('<b>Note:</b>', s_bold))
        el.append(Spacer(1, 4))
        el.append(_para(ticket.description, s_normal))

    # ── FOOTER ──────────────────────────────────────────────────────────────────
    el.append(Spacer(1, 52))
    el.append(HRFlowable(width='100%', thickness=1, color=_DIVIDER))
    el.append(Spacer(1, 10))

    company_block = [
        _para(COMPANY['name'],         s_footer_b),
        _para(f"Account No: {COMPANY['account_no']}", s_footer),
        _para(f"Bank: {COMPANY['bank']}",             s_footer),
        _para(f"Account Name: {COMPANY['account_name']}", s_footer),
    ]
    footer_logo = make_logo_drawing(130, 46)
    footer_tbl = Table([[company_block, footer_logo]], colWidths=['60%', '40%'])
    footer_tbl.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN',   (1, 0), (1, 0),   'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(footer_tbl)

    doc.build(el)
    buf.seek(0)
    return buf
