"""
ReportLab Drawing of the MT Travel logo — two options.

Option 1 (make_logo_drawing):
  Navy circular badge with white top-down airplane + "MT / T R A V E L" wordmark.

Option 2 (make_logo_drawing_v2):
  Light-blue globe with latitude lines, blue flight-path arc + italic "MT / T R A V E L".
"""
import math
from reportlab.graphics.shapes import Drawing, Ellipse, Line, Path, Polygon, String
from reportlab.lib.colors import HexColor, white

_NAVY  = HexColor('#1F3A52')
_BLUE  = HexColor('#2E75B6')
_MUTED = HexColor('#6A9AB8')   # lower-wing underside


def make_logo_drawing(w=160, h=56):
    """
    Return a ReportLab Drawing of the logo at the requested size.

    Navy circular badge with a sleek top-down airplane banking up-right, plus a
    "MT / TRAVEL" wordmark.
    """
    d = Drawing(w, h)
    sx = w / 160
    sy = h / 56

    def px(x): return x * sx
    def py(y): return y * sy

    # ── Circular badge background ─────────────────────────────────────────────
    d.add(Ellipse(px(26), py(28), 22 * sx, 22 * sy, fillColor=_NAVY, strokeColor=None))

    # ── Sleek top-down airplane, banking toward the upper-right ───────────────
    # Authored pointing "up" (north) in centred local coords, then rotated -45°
    # so the nose points north-east. Two-tone wings give a subtle sense of depth.
    pcx, pcy = 24.6, 26.6              # plane centre within the badge (native units)
    th = math.radians(-45)
    ca, cb = math.cos(th), math.sin(th)

    def poly(local, color):
        flat = []
        for x, y in local:
            xr = x * ca - y * cb
            yr = x * cb + y * ca
            flat += [px(pcx + xr), py(pcy + yr)]
        d.add(Polygon(flat, fillColor=color, strokeColor=None))

    # Contrail streak behind the tail (drawn first, sits underneath)
    poly([(1.0, -12), (-1.0, -12), (0, -20)], _MUTED)

    # Main wings — swept back; near wing muted for depth, far wing white
    poly([(1.4, 4.5), (15.0, -8.5), (1.4, -3.0)], _MUTED)
    poly([(-1.4, 4.5), (-15.0, -8.5), (-1.4, -3.0)], white)

    # Tail stabilisers
    poly([(0.9, -7.0), (6.2, -13.0), (0.9, -10.0)], _MUTED)
    poly([(-0.9, -7.0), (-6.2, -13.0), (-0.9, -10.0)], white)

    # Fuselage — slender, rounded nose, tapered tail
    poly([
        (0.0, 17.5),
        (1.1, 14.5), (1.7, 8.0), (1.8, 0.0), (1.5, -8.0),
        (0.0, -12.5),
        (-1.5, -8.0), (-1.8, 0.0), (-1.7, 8.0), (-1.1, 14.5),
    ], white)

    # Cockpit accent — small diamond near the nose
    poly([(0.0, 11.5), (1.4, 9.0), (0.0, 6.5), (-1.4, 9.0)], _BLUE)

    # ── Wordmark ──────────────────────────────────────────────────────────────
    d.add(String(px(58), py(30), 'MT',
                 fontName='Helvetica-Bold', fontSize=21 * sy,
                 fillColor=_NAVY, textAnchor='start'))
    d.add(Line(px(58), py(25), px(155), py(25),
               strokeColor=_BLUE, strokeWidth=0.7 * sx))
    d.add(String(px(58), py(13), 'T R A V E L',
                 fontName='Helvetica', fontSize=9 * sy,
                 fillColor=_BLUE, textAnchor='start'))

    return d


# ─────────────────────────────────────────────────────────────────────────────
# Logo Option 2: globe with latitude grid, curved flight-path arc, italic type
# ─────────────────────────────────────────────────────────────────────────────

_OCEAN  = HexColor('#D4EEF8')   # light-blue ocean fill
_LGRID  = HexColor('#1F3A52')   # grid lines (same navy, drawn thin)


def make_logo_drawing_v2(w=160, h=56):
    """Globe icon with flight-path arc + italic MT / TRAVEL wordmark."""
    d = Drawing(w, h)
    sx = w / 160
    sy = h / 56

    def px(x): return x * sx
    def py(y): return y * sy

    cx, cy = px(26), py(28)
    rx, ry = 21 * sx, 21 * sy

    # ── Globe ────────────────────────────────────────────────────────────────
    # Ocean fill
    d.add(Ellipse(cx, cy, rx, ry, fillColor=_OCEAN, strokeColor=None))
    # Globe outline
    d.add(Ellipse(cx, cy, rx, ry, fillColor=None, strokeColor=_NAVY, strokeWidth=1.5 * sx))

    # Latitude lines (flat ellipses at different Y offsets)
    d.add(Ellipse(cx, cy,             rx,        ry * 0.18,   # equator
                  fillColor=None, strokeColor=_LGRID, strokeWidth=0.8 * sx))
    d.add(Ellipse(cx, cy + ry * 0.60, rx * 0.80, ry * 0.13,  # ~45° N
                  fillColor=None, strokeColor=_LGRID, strokeWidth=0.5 * sx))
    d.add(Ellipse(cx, cy - ry * 0.60, rx * 0.80, ry * 0.13,  # ~45° S
                  fillColor=None, strokeColor=_LGRID, strokeWidth=0.5 * sx))

    # Meridian (thin vertical ellipse)
    d.add(Ellipse(cx, cy, rx * 0.10, ry,
                  fillColor=None, strokeColor=_LGRID, strokeWidth=0.8 * sx))

    # ── Flight-path arc (cubic Bézier over the globe, lower-left → upper-right) ──
    x1, y1 = cx - rx * 0.78, cy - ry * 0.45   # start (SW of globe)
    x2, y2 = cx + rx * 0.82, cy + ry * 0.48   # end   (NE of globe)
    ctrl_y  = cy + ry * 1.1                    # peak well above globe

    arc = Path(fillColor=None, strokeColor=_BLUE, strokeWidth=1.6 * sx)
    arc.moveTo(x1, y1)
    arc.curveTo(cx - rx * 0.5, ctrl_y,
                cx + rx * 0.5, ctrl_y,
                x2, y2)
    d.add(arc)

    # Arrowhead at the NE end of the arc (pointing ~28° above horizontal)
    angle = math.radians(28)
    sz    = 4.5 * sx
    tip_x  = x2 + sz * math.cos(angle)
    tip_y  = y2 + sz * math.sin(angle)
    b1x = x2 + sz * 0.42 * math.cos(angle + math.pi / 2)
    b1y = y2 + sz * 0.42 * math.sin(angle + math.pi / 2)
    b2x = x2 + sz * 0.42 * math.cos(angle - math.pi / 2)
    b2y = y2 + sz * 0.42 * math.sin(angle - math.pi / 2)
    d.add(Polygon([tip_x, tip_y, b1x, b1y, b2x, b2y],
                  fillColor=_BLUE, strokeColor=None))

    # ── Wordmark (italic for a sense of motion) ───────────────────────────────
    d.add(String(px(58), py(30), 'MT',
                 fontName='Helvetica-BoldOblique', fontSize=21 * sy,
                 fillColor=_NAVY, textAnchor='start'))

    d.add(Line(px(58), py(25), px(155), py(25),
               strokeColor=_BLUE, strokeWidth=0.7 * sx))

    d.add(String(px(58), py(13), 'T R A V E L',
                 fontName='Helvetica-Oblique', fontSize=9 * sy,
                 fillColor=_BLUE, textAnchor='start'))

    return d
