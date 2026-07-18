import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Spacer
from apps.core.logo import make_logo_drawing

doc = SimpleDocTemplate('/tmp/logo_preview.pdf', pagesize=A4,
                        topMargin=40, leftMargin=40)
el = [make_logo_drawing(360, 126), Spacer(1, 40), make_logo_drawing(150, 52)]
doc.build(el)
print("OK")
