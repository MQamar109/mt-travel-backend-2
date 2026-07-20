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
from apps.core.invoice_footer import invoice_footer_flowables
from apps.core.logo import make_logo_drawing
from apps.tickets.utils import get_display_amount

# ── Palette ────────────────────────────────────────────────────────────────────
_NAVY   = colors.HexColor('#1F3A52')
_LIGHT  = colors.HexColor('#EEF2F7')
_STRIPE = colors.HexColor('#F5F7FA')
_GREY   = colors.HexColor('#666666')
_DIVIDER = colors.HexColor('#D9E1F2')
_WHITE  = colors.white


def _cv(value, record_currency, exchange_rate, display_currency):
    return float(get_display_amount(value, record_currency, exchange_rate, display_currency))


def _fmt(val):
    return f'{val:,.2f}'


def _para(text, style):
    return Paragraph(str(text), style)


def generate_hotel_invoice(hotel, display_currency, optional_fields, billing=None):
    """
    optional_fields: set of strings from {'payment_type', 'issued_date'}
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
    s_vname    = sty('VN', fontName='Helvetica-Bold', fontSize=13, alignment=TA_RIGHT, textColor=_NAVY)
    s_vsub     = sty('VS', fontSize=9,  alignment=TA_RIGHT, textColor=_GREY)
    s_title    = sty('T',  fontName='Helvetica-Bold', fontSize=26, leading=32,
                     alignment=TA_CENTER, textColor=_NAVY, spaceAfter=4)
    s_label    = sty('L',  fontSize=9,  textColor=_GREY, leading=14)
    s_value    = sty('V',  fontName='Helvetica-Bold', fontSize=10, leading=14)
    s_footer   = sty('F',  fontSize=9,  textColor=_GREY, leading=13)
    s_footer_b = sty('FB', fontName='Helvetica-Bold', fontSize=10, leading=14)

    el = []

    # ── HEADER ──────────────────────────────────────────────────────────────────
    logo = make_logo_drawing(150, 52)
    vendor = hotel.vendor
    vendor_block = [
        _para(vendor.name,    s_vname),
        _para(vendor.email,   s_vsub),
        _para(vendor.company, s_vsub),
    ]
    hdr = Table([[logo, vendor_block]], colWidths=['45%', '55%'])
    hdr.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (1, 0), (1, 0),   'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(hdr)
    el.append(Spacer(1, 14))
    el.append(HRFlowable(width='100%', thickness=2, color=_NAVY, spaceAfter=10))

    # ── INVOICE TITLE ───────────────────────────────────────────────────────────
    el.append(_para('INVOICE', s_title))
    el.append(HRFlowable(width='100%', thickness=1, color=_DIVIDER, spaceBefore=14, spaceAfter=14))

    # ── INVOICE DETAILS ─────────────────────────────────────────────────────────
    rows = [
        [_para('Reservation No', s_label), _para(hotel.reservation_no,  s_value)],
        [_para('Guest',          s_label), _para(hotel.guest_name,       s_value)],
        [_para('Hotel',          s_label), _para(hotel.hotel_name,       s_value)],
        [_para('Check-In',       s_label), _para(str(hotel.check_in),    s_value)],
        [_para('Check-Out',      s_label), _para(str(hotel.check_out),   s_value)],
        [_para('Nights',         s_label), _para(str(hotel.nights),      s_value)],
    ]
    if 'issued_date' in optional_fields:
        rows.append([_para('Issued Date',  s_label), _para(str(hotel.issued_date),  s_value)])
    if 'payment_type' in optional_fields:
        rows.append([_para('Payment Type', s_label), _para(hotel.payment_type,      s_value)])

    detail_tbl = Table(rows, colWidths=[3.8 * cm, None])
    detail_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    el.append(detail_tbl)
    el.append(Spacer(1, 20))

    # ── LINE ITEMS TABLE ────────────────────────────────────────────────────────
    c = lambda v: _cv(v, hotel.currency, hotel.exchange_rate, display_currency)

    th_sty = sty('TH', fontName='Helvetica-Bold', fontSize=9,
                  textColor=_WHITE, alignment=TA_CENTER)
    td_sty = sty('TD', fontSize=9)
    td_r   = sty('TDR', fontSize=9, alignment=TA_RIGHT)
    sec_sty = sty('SEC', fontName='Helvetica-Bold', fontSize=9, textColor=_GREY)

    def th(t): return _para(t, th_sty)
    def td(t): return _para(str(t), td_sty)
    def tdr(t): return _para(str(t), td_r)
    def sec(t): return _para(t, sec_sty)

    col_w = [None, 4 * cm, 4 * cm, 4 * cm]
    item_rows = [[
        th('Description'),
        th('Detail'),
        th(f'Rate ({display_currency})'),
        th(f'Amount ({display_currency})'),
    ]]
    sep_indices = []   # rows that are section dividers

    # ── Room rows ──
    room_types = [
        ('Single Room', hotel.single_qty, hotel.single_rate),
        ('Double Room', hotel.double_qty, hotel.double_rate),
        ('Triple Room', hotel.triple_qty, hotel.triple_rate),
        ('Quad Room',   hotel.quad_qty,   hotel.quad_rate),
    ]
    has_rooms = any(qty for _, qty, _ in room_types)
    if has_rooms:
        for label, qty, rate in room_types:
            if qty:
                conv_rate = c(rate)
                amount = conv_rate * qty * hotel.nights
                detail = f'{qty} rm × {hotel.nights} nts'
                item_rows.append([td(label), td(detail), tdr(_fmt(conv_rate)), tdr(_fmt(amount))])

        # Room subtotal
        room_total = c(hotel.total_room_amount)
        sep_indices.append(len(item_rows))
        item_rows.append([
            sec('Room Sub-total'), '', '',
            _para(_fmt(room_total), sty('RST', fontName='Helvetica-Bold', fontSize=9,
                                         alignment=TA_RIGHT, textColor=_NAVY)),
        ])

    # ── Meal rows ──
    if hotel.meals:
        meal_types = [
            ('Breakfast (BF)', hotel.bf_rate),
            ('Lunch (LU)',     hotel.lu_rate),
            ('Dinner (DI)',    hotel.di_rate),
        ]
        for label, rate in meal_types:
            if rate:
                conv_rate = c(rate)
                amount = conv_rate * hotel.total_guests * hotel.nights
                detail = f'{hotel.total_guests}G × {hotel.nights} nts'
                item_rows.append([td(label), td(detail), tdr(_fmt(conv_rate)), tdr(_fmt(amount))])

        # Meal subtotal
        meal_total = c(hotel.total_meal_amount)
        sep_indices.append(len(item_rows))
        item_rows.append([
            sec('Meal Sub-total'), '', '',
            _para(_fmt(meal_total), sty('MST', fontName='Helvetica-Bold', fontSize=9,
                                         alignment=TA_RIGHT, textColor=_NAVY)),
        ])

    # ── Grand total ──
    grand_total = c(hotel.total_amount)
    total_row_idx = len(item_rows)
    item_rows.append([
        '', '',
        _para('TOTAL', sty('TOT', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT)),
        _para(_fmt(grand_total), sty('TOTR', fontName='Helvetica-Bold', fontSize=11,
                                      alignment=TA_RIGHT, textColor=_NAVY)),
    ])

    n = len(item_rows)
    style_cmds = [
        ('BACKGROUND',    (0, 0),           (-1, 0),            _NAVY),
        ('BACKGROUND',    (0, total_row_idx), (-1, total_row_idx), _LIGHT),
        ('LINEABOVE',     (0, total_row_idx), (-1, total_row_idx), 1.5, _NAVY),
        ('GRID',          (0, 0),           (-1, n-2),          0.3, _DIVIDER),
        ('LINEBELOW',     (0, n-1),         (-1, n-1),          0.3, _DIVIDER),
        ('TOPPADDING',    (0, 0),           (-1, -1),           6),
        ('BOTTOMPADDING', (0, 0),           (-1, -1),           6),
        ('LEFTPADDING',   (0, 0),           (-1, -1),           8),
        ('RIGHTPADDING',  (0, 0),           (-1, -1),           8),
        ('VALIGN',        (0, 0),           (-1, -1),           'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1),           (-1, n-2),          [_WHITE, _STRIPE]),
    ]
    # Sub-total rows: lighter shade + top border
    for idx in sep_indices:
        style_cmds += [
            ('BACKGROUND', (0, idx), (-1, idx), _LIGHT),
            ('LINEABOVE',  (0, idx), (-1, idx), 0.5, _NAVY),
        ]

    items_tbl = Table(item_rows, colWidths=col_w)
    items_tbl.setStyle(TableStyle(style_cmds))
    el.append(items_tbl)

    # ── FOOTER ──────────────────────────────────────────────────────────────────
    el.append(Spacer(1, 52))
    el.append(HRFlowable(width='100%', thickness=1, color=_DIVIDER))
    el.append(Spacer(1, 10))

    el.append(invoice_footer_flowables(billing or COMPANY, s_footer_b, s_footer, _DIVIDER))

    doc.build(el)
    buf.seek(0)
    return buf
