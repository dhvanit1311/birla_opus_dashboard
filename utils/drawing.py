"""Layer drawings: isometric SVG cross-section, 2D dimensioned section (SVG/PNG) and DXF export."""
from __future__ import annotations

import io
import math

from utils.ui import esc

SUBSTRATE_COLOURS = {
    "RCC": "#9CA3AF", "Brick & plaster": "#C2410C", "Screed": "#A8A29E",
    "Existing coating": "#94A3B8", "Metal": "#64748B",
}
SUBSTRATE_THICKNESS = {"RCC": 150, "Brick & plaster": 230, "Screed": 50, "Existing coating": 150, "Metal": 6}


def _shade(hex_colour: str, factor: float) -> str:
    h = hex_colour.lstrip("#")
    if len(h) != 6:
        return hex_colour
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 1:
        r, g, b = (int(c + (255 - c) * (factor - 1)) for c in (r, g, b))
    else:
        r, g, b = (int(c * factor) for c in (r, g, b))
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, c)) for c in (r, g, b)))


def _stack(layers: list[dict], substrate: str) -> list[dict]:
    """Bottom-to-top list including the substrate slab."""
    sub = {"layer_name": f"Substrate – {substrate}", "label": substrate, "colour": SUBSTRATE_COLOURS.get(substrate, "#9CA3AF"),
           "thickness": SUBSTRATE_THICKNESS.get(substrate, 150), "code": "", "is_product": False, "coats": 1, "substrate": True}
    out = [sub]
    for l in layers:
        out.append({**l, "substrate": False})
    return out


def _label(l: dict) -> str:
    if l.get("substrate"):
        return l["layer_name"]
    if l.get("is_product"):
        return f"{l['layer_name']} — {l['code']}" + (f" ×{l['coats']}" if l.get("coats", 1) > 1 else "")
    return l["layer_name"]


def isometric_svg(layers: list[dict], substrate: str = "RCC", selected: str | None = None, title: str = "") -> str:
    stack = _stack(layers, substrate)
    n = len(stack)
    W, Dp, step = 430.0, 150.0, min(64.0, 300.0 / max(n, 1))
    c30, s30 = math.cos(math.radians(30)), 0.5
    heights = [44.0] + [max(14.0, min(24.0, 12 + 4 * math.log1p(max(l.get("thickness", 0), 0)))) for l in stack[1:]]
    total_h = sum(heights)
    ox, oy = 150.0, total_h + 50.0
    label_x = ox + W * c30 + 50

    def P(x, y, z):
        return f"{ox + (x - z) * c30:.1f},{oy + (x + z) * s30 - y:.1f}"

    polys, anchors = [], []
    y0 = 0.0
    for i, l in enumerate(stack):
        h = heights[i]
        x0 = i * step
        x1 = W
        col = l.get("colour") or "#9CA3AF"
        is_sel = selected is not None and l.get("layer_name") == selected
        stroke = "#EF1F51" if is_sel else "#FFFFFF"
        sw = 3 if is_sel else 0.9
        top = [P(x0, y0 + h, 0), P(x1, y0 + h, 0), P(x1, y0 + h, Dp), P(x0, y0 + h, Dp)]
        front = [P(x0, y0, Dp), P(x1, y0, Dp), P(x1, y0 + h, Dp), P(x0, y0 + h, Dp)]
        side = [P(x1, y0, 0), P(x1, y0, Dp), P(x1, y0 + h, Dp), P(x1, y0 + h, 0)]
        left = [P(x0, y0, 0), P(x0, y0, Dp), P(x0, y0 + h, Dp), P(x0, y0 + h, 0)]
        g = ["<g>"]
        g.append(f'<polygon points="{" ".join(left)}" fill="{_shade(col, 0.62)}" stroke="{stroke}" stroke-width="{sw}"/>')
        g.append(f'<polygon points="{" ".join(front)}" fill="{_shade(col, 0.85)}" stroke="{stroke}" stroke-width="{sw}"/>')
        g.append(f'<polygon points="{" ".join(side)}" fill="{_shade(col, 0.7)}" stroke="{stroke}" stroke-width="{sw}"/>')
        g.append(f'<polygon points="{" ".join(top)}" fill="{_shade(col, 1.22)}" stroke="{stroke}" stroke-width="{sw}"/>')
        if l.get("substrate"):
            # concrete speckle on the front face
            for k in range(14):
                px = x0 + 12 + (k * 53) % int(max(x1 - x0 - 24, 30))
                py = y0 + 8 + (k * 17) % int(max(h - 14, 10))
                sx, sy = map(float, P(px, py, Dp).split(","))
                g.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="1.6" fill="rgba(0,0,0,.18)"/>')
        g.append("</g>")
        polys.append("".join(g))
        ax, ay = map(float, P(x1, y0 + h / 2, Dp / 2).split(","))
        anchors.append((ax, ay, l, is_sel))
        y0 += h

    # Labels: top layer first, spaced evenly to avoid overlaps.
    min_gap = 30.0
    top_y = 34.0
    label_rows = []
    for idx, (ax, ay, l, is_sel) in enumerate(reversed(anchors)):
        ly = max(top_y + idx * min_gap, ay - 40 if idx == 0 else 0)
        label_rows.append((ax, ay, ly, l, is_sel))
    # Re-space so labels are monotonic.
    fixed, last = [], -1e9
    for ax, ay, ly, l, is_sel in label_rows:
        ly = max(ly, last + min_gap)
        fixed.append((ax, ay, ly, l, is_sel))
        last = ly
    leaders = []
    for ax, ay, ly, l, is_sel in fixed:
        col = l.get("colour") or "#9CA3AF"
        weight = 800 if is_sel else 600
        leaders.append(
            f'<path d="M{ax:.1f},{ay:.1f} L{label_x - 14:.1f},{ly:.1f} L{label_x - 4:.1f},{ly:.1f}" fill="none" '
            f'stroke="#6B7280" stroke-width="1"/><circle cx="{ax:.1f}" cy="{ay:.1f}" r="3" fill="#1A1A2E"/>'
            f'<rect x="{label_x:.1f}" y="{ly - 9:.1f}" width="12" height="12" rx="3" fill="{col}"/>'
            f'<text x="{label_x + 18:.1f}" y="{ly + 1.5:.1f}" font-size="13" font-weight="{weight}" fill="#1A1A2E">{esc(_label(l))}</text>'
        )
    height = max(oy + (W + Dp) * s30 + 20, last + 40)
    width = label_x + 300
    ttl = f'<text x="16" y="24" font-size="15" font-weight="800" fill="#52489E">{esc(title)}</text>' if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" '
        f'style="width:100%;height:auto;max-width:{width:.0f}px;font-family:Plus Jakarta Sans,Segoe UI,Arial,sans-serif">'
        f'<rect width="100%" height="100%" fill="#FFFFFF"/>{ttl}{"".join(polys)}{"".join(leaders)}'
        f'<text x="16" y="{height - 8:.0f}" font-size="11" fill="#6B7280">Illustrative cross-section · not to scale · SAMPLE</text>'
        "</svg>"
    )


def section_svg(layers: list[dict], substrate: str = "RCC", title: str = "", for_png: bool = False) -> str:
    """2D section with dimensioned (exaggerated) layer thicknesses and a title block."""
    stack = _stack(layers, substrate)
    draw_h = [60.0] + [max(14.0, min(36.0, 14 + 6 * math.log1p(max(l.get("thickness", 0), 0)))) for l in stack[1:]]
    left, sec_w = 40.0, 420.0
    top = 60.0
    total = sum(draw_h)
    width, height = 900.0, top + total + 170
    font = "Helvetica, Arial, sans-serif" if for_png else "Plus Jakarta Sans, Segoe UI, Arial, sans-serif"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" '
           f'height="{height:.0f}" style="font-family:{font}">',
           f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="#FFFFFF"/>',
           f'<text x="{left}" y="34" font-size="18" font-weight="bold" fill="#52489E">{esc(title or "Waterproofing section")}</text>']
    y = top + total
    for i, l in enumerate(stack):
        h = draw_h[i]
        y -= h
        col = l.get("colour") or "#9CA3AF"
        out.append(f'<rect x="{left}" y="{y:.1f}" width="{sec_w}" height="{h:.1f}" fill="{col}" fill-opacity="0.85" stroke="#1A1A2E" stroke-width="1"/>')
        if l.get("substrate"):
            for k in range(0, int(sec_w), 18):  # hatch
                out.append(f'<line x1="{left + k:.1f}" y1="{y + h:.1f}" x2="{left + min(k + h, sec_w):.1f}" y2="{y + h - min(h, sec_w - k):.1f}" stroke="rgba(0,0,0,.25)" stroke-width="1"/>')
        # dimension line
        dx = left + sec_w + 24
        out.append(f'<line x1="{dx}" y1="{y:.1f}" x2="{dx}" y2="{y + h:.1f}" stroke="#1A1A2E" stroke-width="1"/>'
                   f'<line x1="{dx - 5}" y1="{y:.1f}" x2="{dx + 5}" y2="{y:.1f}" stroke="#1A1A2E" stroke-width="1"/>'
                   f'<line x1="{dx - 5}" y1="{y + h:.1f}" x2="{dx + 5}" y2="{y + h:.1f}" stroke="#1A1A2E" stroke-width="1"/>')
        th = l.get("thickness", 0) or 0
        th_txt = f"{th:g} mm" if th else "—"
        out.append(f'<text x="{dx + 10}" y="{y + h / 2 + 4:.1f}" font-size="12" font-weight="bold" fill="#1A1A2E">{esc(th_txt)}</text>')
        out.append(f'<text x="{dx + 80}" y="{y + h / 2 + 4:.1f}" font-size="12.5" fill="#1A1A2E">{esc(_label(l))}</text>')
    # title block
    tb_y = top + total + 30
    out.append(f'<rect x="{left}" y="{tb_y:.1f}" width="{width - 2 * left:.0f}" height="110" fill="#F6F4FF" stroke="#52489E" stroke-width="1.5"/>')
    out.append(f'<line x1="{left}" y1="{tb_y + 36:.1f}" x2="{width - left:.0f}" y2="{tb_y + 36:.1f}" stroke="#52489E"/>')
    out.append(f'<text x="{left + 12}" y="{tb_y + 24:.1f}" font-size="15" font-weight="bold" fill="#EF1F51">ILLUSTRATIVE DETAIL – NOT FOR CONSTRUCTION</text>')
    out.append(f'<text x="{left + 12}" y="{tb_y + 58:.1f}" font-size="12.5" fill="#1A1A2E">Project: Birla Opus Prime – System Builder prototype</text>')
    out.append(f'<text x="{left + 12}" y="{tb_y + 78:.1f}" font-size="12.5" fill="#1A1A2E">Detail: {esc(title)}</text>')
    out.append(f'<text x="{left + 12}" y="{tb_y + 98:.1f}" font-size="12.5" fill="#1A1A2E">Scale: NTS (thicknesses exaggerated) · Values SAMPLE</text>')
    out.append("</svg>")
    return "".join(out)


def svg_to_png(svg: str, zoom: float = 2.0) -> bytes:
    """Render SVG to PNG via PyMuPDF; falls back to a Pillow placeholder if unavailable."""
    try:
        import pymupdf as fitz

        doc = fitz.open(stream=svg.encode("utf-8"), filetype="svg")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    except Exception:  # noqa: BLE001
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (900, 400), "white")
        ImageDraw.Draw(img).text((20, 20), "Section preview unavailable - download SVG/DXF instead.", fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "#9CA3AF").lstrip("#")
    if len(h) != 6:
        h = "9CA3AF"
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def section_dxf(layers: list[dict], substrate: str = "RCC", title: str = "") -> bytes:
    """AutoCAD DXF (R2010): one closed rectangle + solid hatch per layer, text labels, title block."""
    import ezdxf

    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # millimetres
    msp = doc.modelspace()
    for name, colour in (("WP-LAYERS", 5), ("WP-TEXT", 7), ("WP-DIMS", 1), ("TITLE-BLOCK", 6)):
        if name not in doc.layers:
            doc.layers.add(name, color=colour)
    stack = _stack(layers, substrate)
    width = 1000.0
    y = 0.0
    for l in stack:
        h = 150.0 if l.get("substrate") else max(12.0, min(40.0, 12 + 8 * math.log1p(max(l.get("thickness", 0), 0))))
        pts = [(0, y), (width, y), (width, y + h), (0, y + h)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "WP-LAYERS"})
        hatch = msp.add_hatch(dxfattribs={"layer": "WP-LAYERS"})
        hatch.rgb = _hex_to_rgb(l.get("colour"))
        hatch.paths.add_polyline_path(pts, is_closed=True)
        th = l.get("thickness", 0) or 0
        msp.add_line((width + 40, y), (width + 40, y + h), dxfattribs={"layer": "WP-DIMS"})
        msp.add_line((width + 30, y), (width + 50, y), dxfattribs={"layer": "WP-DIMS"})
        msp.add_line((width + 30, y + h), (width + 50, y + h), dxfattribs={"layer": "WP-DIMS"})
        msp.add_text(f"{th:g} mm" if th else "-", height=9,
                     dxfattribs={"layer": "WP-DIMS", "insert": (width + 60, y + h / 2 - 4)})
        msp.add_text(_label(l).replace("—", "-").replace("×", "x"), height=10,
                     dxfattribs={"layer": "WP-TEXT", "insert": (width + 160, y + h / 2 - 5)})
        y += h
    # Title block
    tb = [(0, -170), (1700, -170), (1700, -40), (0, -40)]
    msp.add_lwpolyline(tb, close=True, dxfattribs={"layer": "TITLE-BLOCK"})
    msp.add_text("ILLUSTRATIVE DETAIL - NOT FOR CONSTRUCTION", height=22,
                 dxfattribs={"layer": "TITLE-BLOCK", "insert": (20, -80)})
    msp.add_text(f"Birla Opus Prime - System Builder prototype | {title}".replace("–", "-"), height=12,
                 dxfattribs={"layer": "TITLE-BLOCK", "insert": (20, -115)})
    msp.add_text("Scale: NTS (thicknesses exaggerated). All values SAMPLE.", height=12,
                 dxfattribs={"layer": "TITLE-BLOCK", "insert": (20, -145)})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def crack_gauge_svg(width_mm: float) -> str:
    """Small crack-gauge card with four bands; highlights the active band and marks the width."""
    bands = [("Hairline", "&lt; 0.3", "#06AD80", 0, 0.3), ("Fine", "0.3–1", "#FFC000", 0.3, 1),
             ("Medium", "1–3", "#F26625", 1, 3), ("Structural", "&gt; 3", "#EF1F51", 3, 5)]
    x, out = 10.0, []
    band_w = 115.0
    for i, (name, rng, col, lo, hi) in enumerate(bands):
        active = (lo <= width_mm < hi) or (i == 3 and width_mm >= 3) or (i == 0 and 0 < width_mm < 0.3)
        if width_mm <= 0:
            active = False
        op = 1 if active else 0.28
        out.append(f'<rect x="{x}" y="14" width="{band_w - 6}" height="46" rx="8" fill="{col}" fill-opacity="{op}" '
                   f'stroke="{"#1A1A2E" if active else "none"}" stroke-width="2"/>')
        out.append(f'<text x="{x + (band_w - 6) / 2}" y="34" text-anchor="middle" font-size="13" font-weight="800" fill="#1A1A2E">{name}</text>')
        out.append(f'<text x="{x + (band_w - 6) / 2}" y="51" text-anchor="middle" font-size="12" fill="#1A1A2E">{rng} mm</text>')
        x += band_w
    # gauge lines of increasing width
    gx = 10.0
    for w in (0.1, 0.2, 0.3, 0.5, 1, 1.5, 2, 3, 4, 5):
        stroke = max(w * 1.6, 0.6)
        col = "#EF1F51" if abs(w - width_mm) < 0.26 or (width_mm > 0 and w == min((0.1, 0.2, 0.3, 0.5, 1, 1.5, 2, 3, 4, 5), key=lambda v: abs(v - width_mm))) else "#1A1A2E"
        out.append(f'<line x1="{gx + 6}" y1="72" x2="{gx + 6}" y2="100" stroke="{col}" stroke-width="{stroke:.1f}"/>')
        out.append(f'<text x="{gx + 6}" y="114" text-anchor="middle" font-size="10" fill="#6B7280">{w:g}</text>')
        gx += 45
    band = 0 if width_mm < 0.3 else 1 if width_mm <= 1 else 2 if width_mm <= 3 else 3
    pos = 10 + band * band_w + (band_w - 6) / 2
    out.append(f'<path d="M{pos:.0f},12 l-7,-9 h14 z" fill="#1A1A2E"/>' if width_mm > 0 else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 470 122" width="470" height="122" style="'
            f'font-family:Plus Jakarta Sans,Segoe UI,Arial,sans-serif">{"".join(out)}</svg>')
