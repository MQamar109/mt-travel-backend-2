from reportlab.platypus import Paragraph, Table, TableStyle

from apps.core.company import COMPANY
from apps.core.logo import make_logo_drawing


def invoice_footer_flowables(billing, s_footer_b, s_footer, divider_color):
    """Shared invoice footer: company / bank block + logo."""
    billing = billing or COMPANY
    company_block = [
        Paragraph(billing.get('name', COMPANY['name']), s_footer_b),
        Paragraph(f"Account No: {billing.get('account_no', '')}", s_footer),
        Paragraph(f"Bank: {billing.get('bank', '')}", s_footer),
        Paragraph(f"Account Name: {billing.get('account_name', '')}", s_footer),
    ]
    footer_logo = make_logo_drawing(130, 46)
    footer_tbl = Table([[company_block, footer_logo]], colWidths=['60%', '40%'])
    footer_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return footer_tbl
