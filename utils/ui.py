"""Visual building blocks: CSS, hero header, banner, stepper, cards, chips, badges, plotly template."""
from __future__ import annotations

import html
from typing import Callable, Iterable

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Brand palette ---------------------------------------------------------------
PURPLE = "#52489E"
DEEP = "#2E2470"
GREEN = "#06AD80"
PINK = "#EF1F51"
AMBER = "#FFC000"
ORANGE = "#F26625"
BLUE = "#4472C4"
LAVENDER = "#F6F4FF"
MINT = "#EFFAF6"
CREAM = "#FFF6E5"
TEXT = "#1A1A2E"
MUTED = "#6B7280"

TIER_COLOURS = {"Good": GREEN, "Better": AMBER, "Best": PINK}
PALETTE = [PURPLE, GREEN, PINK, AMBER, ORANGE, BLUE, DEEP, "#8B5CF6", "#14B8A6", "#F472B6"]
PASTELS = [
    ("#F6F4FF", "#E7E2FF"), ("#EFFAF6", "#D4F5E8"), ("#FFF6E5", "#FFE7B8"), ("#FFEFF3", "#FFD3DE"),
    ("#EEF4FF", "#D6E4FF"), ("#FFF1E8", "#FFD9C2"), ("#F3F0FF", "#DCD5FF"), ("#ECFDF5", "#C8F2DF"),
    ("#FEF9E7", "#FDEBB0"), ("#FDF2F8", "#FBD5EA"), ("#F0F9FF", "#CDEBFF"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def icon_html(icon: str, size: int = 34) -> str:
    """Render a ':material/name:' icon or an emoji as HTML."""
    icon = (icon or "").strip()
    if icon.startswith(":material/") and icon.endswith(":"):
        name = icon[len(":material/"):-1]
        return f'<span class="msr" style="font-size:{size}px">{esc(name)}</span>'
    return f'<span style="font-size:{size}px;line-height:1">{esc(icon or "◆")}</span>'


# CSS --------------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0..1,0&display=block');

html, body, .stApp, .stMarkdown, button, input, textarea, select {{
  font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, -apple-system, sans-serif;
}}
[data-testid="stIconMaterial"], .msr {{
  font-family: 'Material Symbols Rounded' !important;
  font-weight: normal; font-style: normal; line-height: 1; letter-spacing: normal;
  text-transform: none; display: inline-block; white-space: nowrap; direction: ltr;
  -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased;
}}
.stApp {{ font-size: 15px; color: {TEXT}; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3, h4 {{ color: {PURPLE}; font-weight: 800 !important; letter-spacing: -0.01em; }}
.stApp [data-testid="stMarkdownContainer"] h2, .stApp [data-testid="stMarkdownContainer"] h3, .stApp [data-testid="stMarkdownContainer"] h4 {{ color: {PURPLE}; }}
p, li, label, .stMarkdown {{ font-size: 15px; }}

@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes glow {{ 0%,100% {{ box-shadow: 0 0 0 4px rgba(82,72,158,.18); }} 50% {{ box-shadow: 0 0 0 9px rgba(82,72,158,.10); }} }}

/* Prototype banner */
.proto-banner {{
  background: #FFF3CC; border: 1px solid #FFE08A; color: #6B4E00; border-radius: 10px;
  padding: 6px 14px; font-size: 13.5px; margin-bottom: 12px; display:flex; gap:8px; align-items:center;
}}

/* Hero */
.hero {{
  background: linear-gradient(120deg, {PURPLE} 0%, {DEEP} 48%, {PINK} 130%);
  border-radius: 20px; padding: 28px 34px; color: #fff; position: relative; overflow: hidden;
  box-shadow: 0 14px 40px rgba(46,36,112,.28); margin-bottom: 18px; animation: fadeUp .5s ease both;
}}
.hero:after {{
  content:""; position:absolute; right:-80px; top:-80px; width:300px; height:300px; border-radius:50%;
  background: radial-gradient(circle, rgba(255,255,255,.18), rgba(255,255,255,0) 70%);
}}
.hero .wordmark {{ font-size: 12.5px; letter-spacing: .22em; text-transform: uppercase; opacity:.85; font-weight:700; }}
.hero h1 {{ color:#fff !important; font-size: 2.15rem; margin: 6px 0 4px 0; padding:0; }}
.hero .sub {{ font-size: 16px; opacity:.92; }}
.hero .page-tag {{ display:inline-block; margin-top:12px; background: rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3);
  padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight:600; }}

/* Stepper */
.stepper {{ display:flex; align-items:flex-start; justify-content:space-between; margin: 6px 0 18px 0; position:relative; }}
.stepper .step {{ flex:1; text-align:center; position:relative; z-index:1; }}
.stepper .step:not(:last-child):after {{
  content:""; position:absolute; top:19px; left:calc(50% + 22px); width:calc(100% - 44px); height:4px; border-radius:4px; background:#E5E7EB; z-index:-1;
}}
.stepper .step.done:not(:last-child):after {{ background: {GREEN}; }}
.stepper .dot {{ width:40px; height:40px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  font-weight:800; background:#E5E7EB; color:{MUTED}; font-size:15px; }}
.stepper .done .dot {{ background:{GREEN}; color:#fff; }}
.stepper .current .dot {{ background:{PURPLE}; color:#fff; animation: glow 2s infinite; }}
.stepper .lbl {{ font-size: 13px; color:{MUTED}; margin-top:6px; font-weight:600; }}
.stepper .current .lbl {{ color:{PURPLE}; }}

/* Choice cards: container key 'card_*' + overlay button key 'cardbtn_*' */
[class*="st-key-card_"] {{ position: relative; }}
[class*="st-key-cardbtn_"] {{ position:absolute !important; inset:0; z-index:5; margin:0 !important; }}
[class*="st-key-cardbtn_"] div, [class*="st-key-cardbtn_"] button {{ width:100% !important; height:100% !important; }}
[class*="st-key-cardbtn_"] button {{ opacity:0 !important; cursor:pointer; }}
.pcard {{
  border-radius: 16px; padding: 20px 18px 18px 18px; min-height: 150px; border: 2px solid rgba(82,72,158,.10);
  box-shadow: 0 4px 14px rgba(26,26,46,.07); transition: transform .18s ease, box-shadow .18s ease, border-color .18s;
  animation: fadeUp .45s ease both; position: relative; color:{TEXT};
}}
[class*="st-key-card_"]:hover .pcard {{ transform: translateY(-4px); box-shadow: 0 14px 28px rgba(82,72,158,.20); border-color: rgba(82,72,158,.35); }}
.pcard.selected {{ border: 3px solid {PURPLE}; box-shadow: 0 10px 26px rgba(82,72,158,.28); }}
.pcard .tick {{ position:absolute; top:10px; right:12px; width:28px; height:28px; border-radius:50%; background:{GREEN};
  color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:16px; }}
.pcard .ttl {{ font-weight: 800; font-size: 17px; margin-top: 10px; color:{DEEP}; }}
.pcard .dsc {{ font-size: 14px; color:{MUTED}; margin-top: 4px; line-height:1.4; }}
.pcard .msr {{ color:{PURPLE}; }}

/* Generic info card */
.icard {{ background:#fff; border-radius:14px; padding:16px 18px; box-shadow: 0 4px 16px rgba(26,26,46,.07);
  border:1px solid #EEEAFB; animation: fadeUp .45s ease both; margin-bottom: 10px; }}
.icard h4 {{ margin:0 0 6px 0; font-size:17px; }}
.icard.lav {{ background:{LAVENDER}; }} .icard.mint {{ background:{MINT}; }} .icard.cream {{ background:{CREAM}; }}
.icard.pinkish {{ background:#FFEFF3; }}
.grad-card {{ border-radius:16px; padding:18px; color:#fff; min-height:140px; box-shadow: 0 10px 24px rgba(26,26,46,.15);
  animation: fadeUp .45s ease both; margin-bottom:8px; }}
.grad-card h4 {{ color:#fff !important; margin:6px 0 4px 0; font-size:17px; }}
.grad-card p {{ color: rgba(255,255,255,.92); font-size:14px; margin:0; }}

/* Chips */
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin: 6px 0 8px 0; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; padding: 6px 12px; border-radius:999px; font-size:13.5px;
  font-weight:700; line-height:1.2; }}
.chip.purple {{ background:#ECE9FB; color:{PURPLE}; }} .chip.green {{ background:#DDF6EE; color:#04795A; }}
.chip.pink {{ background:#FFE2E9; color:#C3123E; }} .chip.amber {{ background:#FFF0C2; color:#8A6400; }}
.chip.orange {{ background:#FFE6D8; color:#B5460F; }} .chip.blue {{ background:#E2EAFA; color:#2F55A0; }}
.chip.grey {{ background:#F1F2F4; color:#4B5563; }}
.sample {{ display:inline-block; background:#FFF0C2; color:#8A6400; border:1px solid #FFE08A; border-radius:6px;
  font-size:11px; font-weight:800; padding:1px 6px; margin-left:6px; vertical-align:middle; letter-spacing:.03em; }}

/* KPI card */
.kpi {{ border-radius:16px; padding:16px 18px; color:#fff; box-shadow: 0 10px 22px rgba(26,26,46,.14); animation: fadeUp .45s ease both; margin-bottom:8px; }}
.kpi .v {{ font-size: 26px; font-weight: 800; line-height:1.15; }}
.kpi .l {{ font-size: 13.5px; opacity: .92; font-weight:600; }}

/* Timeline (method statement) */
.tl {{ border-left: 4px solid #E7E2FF; margin-left: 16px; padding-left: 22px; }}
.tl-item {{ position:relative; margin-bottom: 16px; animation: fadeUp .4s ease both; }}
.tl-item .n {{ position:absolute; left:-42px; top:0; width:36px; height:36px; border-radius:50%; background:{PURPLE}; color:#fff;
  font-weight:800; display:flex; align-items:center; justify-content:center; box-shadow:0 0 0 4px #fff; }}
.tl-item h5 {{ margin:4px 0 6px 0; color:{DEEP}; font-size:16px; font-weight:800; }}
.tl-item ul {{ margin: 0 0 0 0; padding-left: 18px; }}
.tl-item li {{ font-size:14.5px; margin-bottom:3px; }}
.hold {{ color:{ORANGE}; font-weight:700; font-size:13px; }}

/* Step cards (application steps) */
.scard {{ background: linear-gradient(160deg,#fff, {LAVENDER}); border-radius:16px; padding:16px; text-align:center; min-height:150px;
  border:1px solid #E7E2FF; box-shadow: 0 4px 14px rgba(26,26,46,.06); animation: fadeUp .45s ease both; margin-bottom:10px; }}
.scard .num {{ display:inline-block; background:{PINK}; color:#fff; border-radius:999px; padding:2px 10px; font-weight:800; font-size:12px; }}
.scard .t {{ font-weight:800; color:{DEEP}; margin-top:6px; }}
.scard .d {{ font-size:14px; color:{MUTED}; margin-top:4px; }}

/* Buttons */
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {{
  background: linear-gradient(120deg, {PURPLE}, {DEEP}); border: none; font-weight:700; border-radius: 12px;
  box-shadow: 0 6px 16px rgba(82,72,158,.28);
}}
.stButton button, .stDownloadButton button {{ border-radius: 12px; font-weight:600; }}
.stButton button:hover {{ transform: translateY(-1px); }}
.st-key-get_system button {{
  background: linear-gradient(110deg, {PURPLE}, {PINK}) !important; font-size: 18px !important; padding: 14px 20px !important;
  border-radius: 14px !important; box-shadow: 0 10px 24px rgba(239,31,81,.30) !important; color:#fff !important; border:none !important;
}}
[class*="st-key-actbtn_"] button {{ min-height: 52px; font-size: 15px; }}

/* Laptop mock-up frame */
.laptop {{ animation: fadeUp .6s ease both; background:#1F1B3A; border-radius: 18px 18px 6px 6px; padding: 12px 12px 14px 12px; box-shadow: 0 18px 36px rgba(26,26,46,.25); }}
.laptop .screen {{ background:#fff; border-radius:10px; overflow:hidden; }}
.laptop-base {{ height: 14px; background: linear-gradient(#D1D5DB,#9CA3AF); border-radius: 0 0 16px 16px; margin: 0 -18px; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ background:{LAVENDER}; border-radius:10px 10px 0 0; padding: 8px 14px; font-weight:700; }}
.stTabs [aria-selected="true"] {{ background:{PURPLE} !important; color:#fff !important; }}
.stTabs [aria-selected="true"] p {{ color:#fff !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {LAVENDER} 0%, #fff 70%); }}
.sel-row {{ display:flex; justify-content:space-between; align-items:center; font-size:14px; }}
.sel-k {{ color:{MUTED}; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }}
.sel-v {{ color:{DEEP}; font-weight:700; }}

/* Quote */
.quote {{ background:#fff; border-left: 6px solid {PINK}; border-radius: 12px; padding: 14px 16px; box-shadow: 0 4px 14px rgba(26,26,46,.06);
  font-style: italic; margin-bottom: 10px; min-height: 120px; }}
.quote .who {{ font-style: normal; color:{MUTED}; font-size:13px; margin-top:8px; font-weight:700; }}

/* Severity badge */
.sev {{ display:inline-block; padding: 8px 14px; border-radius: 12px; color:#fff; font-weight:800; font-size:15px; }}

@media (max-width: 640px) {{
  .hero {{ padding: 20px; }} .hero h1 {{ font-size: 1.5rem; }}
  .stepper .lbl {{ display:none; }} .stepper .dot {{ width:32px; height:32px; }}
  .stepper .step:not(:last-child):after {{ top:15px; }}
  .pcard {{ min-height: 120px; }}
}}
</style>
"""


def svg_img(svg: str, max_width: int | None = None, extra_style: str = "") -> str:
    """Embed an SVG as a base64 <img> (st.html sanitises inline SVG away)."""
    import base64

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    mw = f"max-width:{max_width}px;" if max_width else ""
    return f'<img alt="drawing" src="data:image/svg+xml;base64,{b64}" style="width:100%;height:auto;{mw}display:block;{extra_style}"/>'


def show_svg(svg: str, max_width: int | None = None, wrapper_style: str = "") -> None:
    st.markdown(f'<div style="{wrapper_style}">{svg_img(svg, max_width)}</div>', unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def banner() -> None:
    st.markdown(
        '<div class="proto-banner">⚠️ <b>Prototype for illustration purposes only.</b> '
        "Products, data and documents are indicative.</div>",
        unsafe_allow_html=True,
    )


def hero(page_tag: str = "", title: str = "Prime System Builder",
         subtitle: str = "Waterproofing systems for specifiers, builders and contractors") -> None:
    banner()
    tag = f'<div class="page-tag">{esc(page_tag)}</div>' if page_tag else ""
    st.markdown(
        f'<div class="hero"><div class="wordmark">Birla Opus Prime</div>'
        f"<h1>{esc(title)}</h1><div class='sub'>{esc(subtitle)}</div>{tag}</div>",
        unsafe_allow_html=True,
    )


def stepper(current: int, labels: list[str]) -> None:
    parts = []
    for i, lbl in enumerate(labels, start=1):
        state = "done" if i < current else "current" if i == current else ""
        mark = "✓" if i < current else str(i)
        parts.append(f'<div class="step {state}"><div class="dot">{mark}</div><div class="lbl">{esc(lbl)}</div></div>')
    st.markdown(f'<div class="stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def sample_badge() -> str:
    return '<span class="sample">SAMPLE</span>'


def chip(label: str, colour: str = "purple", icon: str = "") -> str:
    return f'<span class="chip {colour}">{esc(icon) + " " if icon else ""}{label}</span>'


def chips(items: Iterable[str]) -> None:
    st.markdown(f'<div class="chips">{"".join(items)}</div>', unsafe_allow_html=True)


def kpi(value: str, label: str, colour: str = PURPLE, sample: bool = False) -> None:
    badge = sample_badge() if sample else ""
    st.markdown(
        f'<div class="kpi" style="background:linear-gradient(135deg,{colour},{_darken(colour)})">'
        f'<div class="v">{esc(value)}</div><div class="l">{esc(label)}{badge}</div></div>',
        unsafe_allow_html=True,
    )


def info_card(title: str, body_html: str, tone: str = "") -> None:
    st.markdown(f'<div class="icard {tone}"><h4>{title}</h4>{body_html}</div>', unsafe_allow_html=True)


def grad_card(icon: str, title: str, body: str, c1: str, c2: str) -> None:
    st.markdown(
        f'<div class="grad-card" style="background:linear-gradient(135deg,{c1},{c2})">'
        f'{icon_html(icon, 30)}<h4>{esc(title)}</h4><p>{esc(body)}</p></div>',
        unsafe_allow_html=True,
    )


def _darken(hex_colour: str, factor: float = 0.72) -> str:
    h = hex_colour.lstrip("#")
    if len(h) != 6:
        return hex_colour
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(int(r * factor), int(g * factor), int(b * factor))


def choice_grid(items: list[dict], key_prefix: str, selected: str | None,
                on_select: Callable[[str], None], n_cols: int = 3) -> None:
    """Grid of large clickable cards. items: dicts with value, title, desc, icon.

    Each card is a keyed container holding the card HTML plus a real st.button that is
    stretched invisibly over the card, so a click anywhere on the card is a Streamlit click.
    """
    for start in range(0, len(items), n_cols):
        cols = st.columns(n_cols, gap="medium")
        for j, item in enumerate(items[start:start + n_cols]):
            idx = start + j
            c1, c2 = PASTELS[idx % len(PASTELS)]
            is_sel = selected == item["value"]
            with cols[j]:
                with st.container(key=f"card_{key_prefix}_{idx}"):
                    tick = '<div class="tick">✓</div>' if is_sel else ""
                    st.markdown(
                        f'<div class="pcard {"selected" if is_sel else ""}" '
                        f'style="background:linear-gradient(135deg,{c1},{c2});animation-delay:{idx * 0.04:.2f}s">'
                        f'{tick}{icon_html(item.get("icon", ""), 38)}'
                        f'<div class="ttl">{esc(item["title"])}</div><div class="dsc">{esc(item.get("desc", ""))}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.button(item["title"], key=f"cardbtn_{key_prefix}_{idx}", on_click=on_select,
                              args=(item["value"],), width="stretch")


# Plotly template ----------------------------------------------------------------
def register_plotly_template() -> None:
    if "prime" in pio.templates:
        return
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", color=TEXT, size=13),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", colorway=PALETTE,
        xaxis=dict(showgrid=False, zeroline=False, linecolor="#E5E7EB", ticks=""),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", zeroline=False, linecolor="#E5E7EB"),
        title=dict(font=dict(color=PURPLE, size=16), x=0.01),
        legend=dict(orientation="h", y=-0.18, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=50, b=30),
        hoverlabel=dict(bgcolor="#fff", bordercolor=PURPLE, font=dict(color=TEXT)),
    )
    pio.templates["prime"] = tpl
    pio.templates.default = "prime"


def plot(fig, key: str) -> None:
    """Render a plotly figure with the brand template (not Streamlit's theme)."""
    register_plotly_template()
    fig.update_layout(template="prime", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    st.plotly_chart(fig, theme=None, key=key, config={"displaylogo": False})
