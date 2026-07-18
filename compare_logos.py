"""
Standalone script run inside the container to generate a logo comparison PDF.
Usage: python compare_logos.py
"""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django
django.setup()

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, HRFlowable
from reportlab.lib import colors
from apps.core.logo import make_logo_drawing, make_logo_drawing_v2

buf = BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm)

label = ParagraphStyle('lbl', fontName='Helvetica-Bold', fontSize=11,
                       textColor=colors.HexColor('#1F3A52'), spaceAfter=10)
note  = ParagraphStyle('note', fontName='Helvetica', fontSize=9,
                       textColor=colors.HexColor('#666666'), spaceAfter=0)

el = []

el.append(Paragraph('Logo Option 1 — Navy Badge · Airplane (top-down) · Upright type', label))
el.append(Paragraph('Used in current invoices', note))
el.append(Spacer(1, 12))
el.append(make_logo_drawing(240, 84))   # shown large for comparison

el.append(Spacer(1, 40))
el.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#D9E1F2')))
el.append(Spacer(1, 40))

el.append(Paragraph('Logo Option 2 — Globe · Flight-path Arc · Italic type', label))
el.append(Paragraph('Alternative design', note))
el.append(Spacer(1, 12))
el.append(make_logo_drawing_v2(240, 84))

doc.build(el)
buf.seek(0)
with open('/tmp/logo_comparison.pdf', 'wb') as f:
    f.write(buf.read())
print('OK: /tmp/logo_comparison.pdf written')
