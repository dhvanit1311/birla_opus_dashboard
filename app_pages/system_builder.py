"""Page 1 – System Builder: 6-step wizard from persona to a complete waterproofing system."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import data as D
from utils import documents as DOC
from utils import drawing as DR
from utils import logic as L
from utils import ui
from utils.state import (SITE_DEFAULTS, init_state, layer_dialog, load_project, reset_wizard,
                         simple_dialog, support_dialog)
from utils.ui import chip, chips, esc, sample_badge

init_state()
ss = st.session_state

STEP_LABELS = ["Who are you?", "Project type", "Surface", "Site details", "Your system", "Key enablers"]
PANELS = [("Method Statement", ":material/assignment:"), ("BOQ Calculator", ":material/calculate:"),
          ("TDS / PIS Library", ":material/description:"), ("CAD / BIM Details", ":material/architecture:"),
          ("Spec / Tender Text", ":material/article:"), ("Application Steps", ":material/format_list_numbered:"),
          ("Project Pack", ":material/folder_zip:"), ("Get Support", ":material/support_agent:")]
TIER_LABEL = {"Good": "🟢 Good", "Better": "🟡 Better", "Best": "🔴 Best"}
EXPOSURES = ["Direct sun/UV", "Foot traffic", "Vehicle traffic", "Ponding water", "Constant immersion"]
CLIMATES = ["Coastal humid", "Hot dry", "Composite", "Heavy rainfall", "Cold"]


@st.cache_data(show_spinner=False)
def tds_bytes(code: str) -> bytes:
    return DOC.tds_pdf(code)


@st.cache_data(show_spinner=False)
def tds_preview(code: str) -> bytes | None:
    return DOC.pdf_preview_png(DOC.tds_pdf(code))


# ---------------------------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------------------------
def choose_persona(value: str) -> None:
    ss.persona, ss.step, ss.active_panel = value, 2, None


def choose_segment(value: str) -> None:
    ss.segment, ss.step = value, 3


def choose_surface(value: str) -> None:
    ss.surface, ss.step = value, 4
    surf = D.row_dict(D.surfaces(), "surface", value)
    if not D.as_bool(surf.get("needs_pressure", False)):
        ss.site["pressure"] = "None"
        ss.pop("site_pressure", None)


def go_step(n: int) -> None:
    ss.step = n


def on_tier_change() -> None:
    val = ss.get("tier_ctl")
    if val:
        ss.tier = val


def on_layer_pick() -> None:
    ss.open_layer = True


def set_panel(name: str) -> None:
    ss.active_panel = name


def on_pack_download() -> None:
    if ss.get("pack_downloads", 0) == 0:
        ss.fire_balloons = True
    ss.pack_downloads = ss.get("pack_downloads", 0) + 1


# ---------------------------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------------------------
def sidebar() -> None:
    with st.sidebar:
        st.markdown("### Your selections")
        site = ss.site
        area = L.effective_area(site, ss.surface) if ss.step >= 5 else D.num(site.get("area"))
        rows = [("Persona", ss.persona, 1), ("Segment", ss.segment, 2), ("Surface", ss.surface, 3),
                ("Area", f"{area:,.0f} sq ft" if ss.step >= 5 else None, 4)]
        with st.container(border=True):
            for label, value, step in rows:
                c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
                c1.markdown(f"<div class='sel-k'>{label}</div><div class='sel-v'>{esc(value or '—')}</div>",
                            unsafe_allow_html=True)
                c2.button("Edit", key=f"sb_edit_{step}", on_click=go_step, args=(step,), type="tertiary",
                          disabled=value is None and step > ss.step, icon=":material/edit:")
        st.button("Start over", key="sb_reset", on_click=reset_wizard, icon=":material/restart_alt:", width="stretch")
        st.markdown("<div class='icard lav'><h4>Need help?</h4><p style='margin:0;font-size:14px'>"
                    "Our technical sales team can help you pick and price a system.</p></div>", unsafe_allow_html=True)
        if st.button("Talk to an expert", key="sb_expert", type="primary", icon=":material/support_agent:", width="stretch"):
            support_dialog()


# ---------------------------------------------------------------------------------------------
# Steps 1–3: card grids
# ---------------------------------------------------------------------------------------------
def step_persona() -> None:
    st.markdown("## Who are you?")
    st.caption("Your choice tailors what we show first – documents, costs or site steps.")
    df = D.personas()
    items = [{"value": r["persona"], "title": r["persona"], "desc": D.text(r["description"]), "icon": D.text(r["icon"])}
             for _, r in df.iterrows()]
    ui.choice_grid(items, "persona", ss.persona, choose_persona, n_cols=3)


def step_segment() -> None:
    st.markdown("## What type of project?")
    df = D.segments()
    items = [{"value": r["segment"], "title": r["segment"], "desc": D.text(r["description"]), "icon": D.text(r["icon"])}
             for _, r in df.iterrows()]
    ui.choice_grid(items, "segment", ss.segment, choose_segment, n_cols=3)
    st.button("Back", key="back_2", on_click=go_step, args=(1,), icon=":material/arrow_back:")


def step_surface() -> None:
    st.markdown("## Which surface?")
    seg = L.segment_info(ss.segment)
    if seg.get("modifier_notes"):
        st.info(f"**{ss.segment}:** {seg['modifier_notes']}", icon=":material/tune:")
    df = D.surfaces()
    items = [{"value": r["surface"], "title": r["surface"], "desc": D.text(r["description"]), "icon": D.text(r["icon"])}
             for _, r in df.iterrows()]
    ui.choice_grid(items, "surface", ss.surface, choose_surface, n_cols=4)
    st.button("Back", key="back_3", on_click=go_step, args=(2,), icon=":material/arrow_back:")


# ---------------------------------------------------------------------------------------------
# Step 4: site form
# ---------------------------------------------------------------------------------------------
def step_site() -> None:
    st.markdown("## Tell us about the site")
    site = ss.site
    for k, v in SITE_DEFAULTS.items():
        ss.setdefault(f"site_{k}", site.get(k, v))
    surf = D.row_dict(D.surfaces(), "surface", ss.surface)
    needs_pressure = D.as_bool(surf.get("needs_pressure", False))
    needs_crack = D.as_bool(surf.get("needs_crack_check", False))
    mandatory = "repair_prep" in L.modifiers(ss.segment)

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### 📐 Area")
            mode = st.segmented_control("Area input", ["Enter sq ft", "Length × Width (ft)"], key="site_area_mode")
            if mode == "Length × Width (ft)":
                c1, c2 = st.columns(2)
                length = c1.number_input("Length (ft)", min_value=1.0, max_value=5000.0, step=1.0, key="site_length")
                width = c2.number_input("Width (ft)", min_value=1.0, max_value=5000.0, step=1.0, key="site_width")
                area = length * width
            else:
                area = st.number_input("Area (sq ft)", min_value=10.0, max_value=5_000_000.0, step=50.0, key="site_area")
            floors = 1
            if ss.surface in L.WET_SURFACES:
                floors = st.number_input("Number of floors / units (optional multiplier)", 1, 2000, key="site_floors")
            total = area * floors
            ui.chips([chip(f"Total area: {total:,.0f} sq ft", "purple", "📏"),
                      chip(f"≈ {total * 0.092903:,.0f} m²", "blue")])
        with st.container(border=True):
            st.markdown("#### 🧱 Substrate & condition")
            c1, c2 = st.columns(2)
            c1.selectbox("Surface condition", ["New", "Existing – good", "Existing – damaged"], key="site_condition")
            c2.selectbox("Substrate", ["RCC", "Brick & plaster", "Screed", "Existing coating", "Metal"], key="site_substrate")
            st.pills("Exposure", EXPOSURES, selection_mode="multi", key="site_exposure")
            if needs_pressure:
                st.radio("Water pressure", ["None", "Positive side", "Negative side"], horizontal=True, key="site_pressure",
                         help="Positive side = water pushes against the face being waterproofed. Negative side = "
                              "treating from the inside, against the water.")
        with st.container(border=True):
            st.markdown("#### 📍 Location & preference")
            c1, c2 = st.columns(2)
            c1.text_input("City", key="site_city")
            c2.selectbox("Climate zone", CLIMATES, key="site_climate")
            st.segmented_control("Preference", ["Value", "Premium", "Luxury", "Show me all three"], key="site_preference")
    with right:
        with st.container(border=True):
            title = "#### 🔍 Crack check (Demo-Kit, digital)"
            st.markdown(title + ("  <span class='chip pink'>Mandatory for this segment</span>" if mandatory else ""),
                        unsafe_allow_html=True)
            if not needs_crack:
                st.caption("Crack check is optional for this surface.")
            w = st.slider("Crack width (mm)", 0.0, 5.0, step=0.1, key="site_crack_w")
            st.slider("Crack depth (mm)", 0.0, 50.0, step=1.0, key="site_crack_d")
            sev = L.crack_severity(w)
            st.markdown(f"<span class='sev' style='background:{sev['colour']}'>{sev['label']}</span>"
                        f"<p style='margin-top:8px'>{esc(sev['note'])}</p>", unsafe_allow_html=True)
            ui.show_svg(DR.crack_gauge_svg(w), 470)
            if sev["band"] == 3:
                st.error("Refer to a structural engineer before waterproofing.", icon=":material/report:")
            if mandatory:
                st.checkbox("I have measured the cracks on site", key="site_crack_done")
        seg = L.segment_info(ss.segment)
        if seg.get("modifier_notes"):
            st.markdown(f"<div class='icard cream'><h4>Segment note</h4><p style='margin:0'>{esc(seg['modifier_notes'])}</p></div>",
                        unsafe_allow_html=True)

    c1, c2 = st.columns([1, 3])
    c1.button("Back", key="back_4", on_click=go_step, args=(3,), icon=":material/arrow_back:")
    if c2.button("Get my system", key="get_system", icon=":material/arrow_forward:", icon_position="right", width="stretch"):
        if mandatory and needs_crack and not ss.get("site_crack_done"):
            st.error("Crack check is mandatory for repair / CHS projects – measure cracks and tick the box.",
                     icon=":material/warning:")
            return
        new_site = {k: ss.get(f"site_{k}", v) for k, v in SITE_DEFAULTS.items()}
        new_site["exposure"] = list(new_site.get("exposure") or [])
        if new_site["area_mode"] == "Length × Width (ft)":
            new_site["area"] = float(new_site["length"]) * float(new_site["width"])
        if not needs_pressure:
            new_site["pressure"] = "None"
        new_site["preference"] = new_site.get("preference") or "Premium"
        ss.site = new_site
        ss.tier = L.default_tier(new_site["preference"], ss.segment)
        ss.pop("tier_ctl", None)
        ss.step, ss.active_panel, ss.selected_layer = 5, None, None
        st.rerun()


# ---------------------------------------------------------------------------------------------
# Step 5: results helpers
# ---------------------------------------------------------------------------------------------
def boq_key(system: dict) -> str:
    return f"boq_{system['system_id']}_{int(system['area'])}_{len(system['layers'])}"


def boq_current(system: dict) -> pd.DataFrame:
    """Base BOQ with any edits from the data editor applied, recomputed."""
    df = L.boq_table(system, system["area"], 10)
    state = ss.get(boq_key(system)) or {}
    edits = state.get("edited_rows", {}) if isinstance(state, dict) else {}
    for idx, changes in edits.items():
        i = int(idx)
        if 0 <= i < len(df):
            for col, val in changes.items():
                if col in df.columns:
                    df.at[i, col] = val
    return L.recompute_boq(df)


def labour_rate() -> float:
    return float(ss.get("boq_labour", 12.0))


def ctx() -> dict:
    return {"persona": ss.persona, "segment": ss.segment, "surface": ss.surface, "site": ss.site}


def persona_row() -> dict:
    return D.row_dict(D.personas(), "persona", ss.persona)


def persona_strip(system: dict, tot: dict) -> None:
    p = persona_row()
    prio = set(D.split_pipes(p.get("priority_sections")))
    st.markdown(f"<div class='icard lav'><h4>{ui.icon_html(D.text(p.get('icon')), 22)} {esc(ss.persona)} view</h4>"
                f"<p style='margin:0'>{esc(D.text(p.get('welcome_line')))}</p></div>", unsafe_allow_html=True)
    if "cost" in prio:  # Builder / Developer
        c = st.columns(4)
        with c[0]:
            ui.kpi(f"₹{tot['per_sqft']:,.0f}/sq ft", "Cost per sq ft", ui.PURPLE, True)
        with c[1]:
            ui.kpi(L.inr(tot["grand"]), "Total cost (material + labour)", ui.PINK, True)
        with c[2]:
            ui.kpi(f"{system['warranty']:g} years", "System warranty", ui.GREEN, True)
        with c[3]:
            ui.kpi(f"{system['app_days']} days", "Estimated timeline", ui.ORANGE, True)
        refs = D.load("sample_projects.csv")
        refs = refs[refs["surface"] == ss.surface]
        if not refs.empty:
            st.markdown("**Reference projects** " + sample_badge(), unsafe_allow_html=True)
            chips([chip(f"🏢 {esc(r['project'])} · {esc(r['city'])} · {int(D.num(r['area_sqft'])):,} sq ft", "blue")
                   for _, r in refs.head(3).iterrows()])
    if "compliance" in prio:  # PMC / Specifier
        st.markdown("**Compliance** " + sample_badge(), unsafe_allow_html=True)
        chips([chip("✔ " + esc(s), "green") for s in system["standards"]] or [chip("Standards on request", "grey")])
        with st.expander("QA checklist (first look)", expanded=True, icon=":material/checklist:"):
            sections = L.method_statement(system, ctx())
            qa = next((s for s in sections if s["title"] == "QA checklist"), {"items": []})
            cols = st.columns(2)
            for i, item in enumerate(qa["items"][:10]):
                cols[i % 2].checkbox(item["text"], key=f"qa_first_{system['system_id']}_{i}")
    if "coverage" in prio:  # Contractor / Applicator
        prods = list({l["code"]: l for l in system["layers"] if l["is_product"]}.values())
        coats_by_code = {}
        for l in system["layers"]:
            if l["is_product"]:
                coats_by_code[l["code"]] = coats_by_code.get(l["code"], 0) + l["coats"]
        chips([chip(f"🧴 {esc(l['code'])}: {l['coverage']:g} sq ft/{esc(l['unit'])}/coat × {coats_by_code[l['code']]}", "purple") for l in prods]
              + [chip(f"Total coats: {system['total_coats']}", "pink")])
        chips([chip(f"⏱ {esc(l['code'])}: recoat {esc(l['recoat'])} h · cure {esc(l['cure'])} d", "amber") for l in prods
               if l["recoat"] not in ("—",)])
        sev = L.crack_severity(D.num(ss.site.get("crack_w")))
        tools = L.tools_list(system)
        chips([chip(f"Crack check: {sev['label']} ({D.num(ss.site.get('crack_w')):.1f} mm)", "orange")]
              + [chip("🛠 " + esc(t.split(',')[0]), "grey") for t in tools[:5]])
        club_card()


def club_card() -> None:
    st.markdown(
        "<div class='grad-card' style='background:linear-gradient(120deg,#2E2470,#52489E 60%,#EF1F51)'>"
        f"{ui.icon_html(':material/workspace_premium:', 30)}<h4>Join the Prime Applicator Club</h4>"
        "<p>🥈 <b>Silver</b> – training + digital certificate · 🥇 <b>Gold</b> – points on every pack, site leads · "
        "💎 <b>Platinum</b> – co-branded warranty, priority tech support. <span class='sample'>SAMPLE</span></p></div>",
        unsafe_allow_html=True)
    if st.button("Register interest", key="club_register", icon=":material/how_to_reg:"):
        simple_dialog("Prime Applicator Club – register interest", "Tell us about your firm and pick a tier (sample tiers).",
                      "Tier", ["Silver", "Gold", "Platinum"])


def persona_card() -> None:
    persona = ss.persona or ""
    if persona.startswith("Builder"):
        ui.grad_card(":material/verified_user:", "System warranty + single point of contact",
                     "One accountable Prime team from specification to handover, with a system warranty "
                     "backed by a signed ponding / test report (sample terms).", ui.GREEN, "#04795A")
        if st.button("Request warranty details", key="pc_warranty", icon=":material/verified:"):
            simple_dialog("System warranty details", "We'll share sample warranty terms for this system.",
                          "Project stage", ["Design", "Tender", "Construction", "Handover"])
    elif persona.startswith("PMC"):
        ui.grad_card(":material/school:", "CPD seminar for your team",
                     "A 60-minute CPD session on systems-based waterproofing specs, method statements and QA.",
                     ui.PURPLE, ui.DEEP)
        if st.button("Book a CPD session", key="pc_cpd", icon=":material/event:"):
            simple_dialog("Book a CPD session", "Choose a preferred month – our specifier team will confirm.",
                          "Preferred month", ["October 2026", "November 2026", "December 2026", "January 2027"])
    else:
        club_card()


# ---------------------------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------------------------
def panel_method(system: dict) -> None:
    sections = L.method_statement(system, ctx())
    st.markdown(f"### Method statement – {esc(system['system_name'])} {sample_badge()}", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("Download Word (.docx)", data=lambda: DOC.method_statement_docx(system, ctx(), sections),
                       file_name=f"Method_Statement_{system['system_id']}.docx", icon=":material/description:", type="primary",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="ms_docx")
    c2.download_button("Download PDF", data=lambda: DOC.method_statement_pdf(system, ctx(), sections),
                       file_name=f"Method_Statement_{system['system_id']}.pdf", mime="application/pdf",
                       icon=":material/picture_as_pdf:", key="ms_pdf")
    html = ["<div class='tl'>"]
    qa = None
    for n, sec in enumerate(sections, 1):
        if sec["title"] == "QA checklist":
            qa = (n, sec)
            continue
        items = "".join(f"<li>{esc(i['text'])}" + (f" <span class='hold'>⏳ {esc(i['hold'])}</span>" if i.get("hold") else "")
                        + "</li>" for i in sec["items"])
        html.append(f"<div class='tl-item' style='animation-delay:{n * 0.03:.2f}s'><div class='n'>{n}</div>"
                    f"<h5>{esc(sec['title'])}</h5><ul>{items}</ul></div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
    if qa:
        n, sec = qa
        with st.container(border=True):
            st.markdown(f"**{n}. QA checklist** – tick as you inspect")
            cols = st.columns(2)
            done = 0
            for i, item in enumerate(sec["items"]):
                if cols[i % 2].checkbox(item["text"], key=f"qa_{system['system_id']}_{i}"):
                    done += 1
            st.progress(done / max(len(sec["items"]), 1), text=f"{done}/{len(sec['items'])} checks complete")


def panel_boq(system: dict) -> None:
    st.markdown(f"### BOQ calculator {sample_badge()}", unsafe_allow_html=True)
    st.caption("Edit coverage, coats, area, wastage, pack size or rate – quantities, packs and amounts recalculate.")
    key = boq_key(system)
    base = boq_current(system)
    edited = st.data_editor(
        base, key=key, hide_index=True, width="stretch", num_rows="fixed",
        disabled=["Item", "Product code", "Unit", "Quantity", "Packs needed", "Amount (₹)"],
        column_config={
            "Wastage %": st.column_config.NumberColumn(min_value=0, max_value=50, step=1, format="%d%%"),
            "Rate per pack (₹)": st.column_config.NumberColumn(format="₹%d", min_value=0),
            "Amount (₹)": st.column_config.NumberColumn(format="₹%d"),
            "Quantity": st.column_config.NumberColumn(format="%.1f"),
            "Coats": st.column_config.NumberColumn(min_value=0, max_value=6, step=1),
            "Area (sq ft)": st.column_config.NumberColumn(min_value=0, format="%.0f"),
        })
    df = L.recompute_boq(edited)
    c1, c2 = st.columns([1, 3])
    lr = c1.number_input("Labour rate (₹/sq ft, optional)", 0.0, 500.0, value=labour_rate(), step=1.0, key="boq_labour_in")
    ss.boq_labour = lr
    tot = L.totals(df, lr, system["area"])
    k = st.columns(4)
    with k[0]:
        ui.kpi(L.inr(tot["material"]), "Material", ui.PURPLE, True)
    with k[1]:
        ui.kpi(L.inr(tot["labour"]), "Labour", ui.ORANGE, True)
    with k[2]:
        ui.kpi(L.inr(tot["grand"]), "Grand total", ui.PINK, True)
    with k[3]:
        ui.kpi(f"₹{tot['per_sqft']:,.1f}", "Per sq ft", ui.GREEN, True)
    left, right = st.columns([3, 2])
    with left:
        cost = df[df["Amount (₹)"] > 0]
        layer_cols = [l["colour"] for l in system["layers"]]
        colours = [layer_cols[i] if i < len(layer_cols) else ui.PALETTE[i % len(ui.PALETTE)] for i in cost.index]
        fig = go.Figure(go.Pie(labels=cost["Item"], values=cost["Amount (₹)"], hole=0.58, sort=False,
                               marker=dict(colors=colours,
                                           line=dict(color="#fff", width=2)),
                               textinfo="percent", hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>"))
        fig.update_layout(title="Cost by layer (sample)", height=360, showlegend=True,
                          annotations=[dict(text=f"<b>{L.inr(tot['material'])}</b><br>material", showarrow=False, font_size=14)])
        ui.plot(fig, key="boq_donut")
    with right:
        st.markdown("#### Downloads")
        st.download_button("Download Excel (.xlsx)", data=lambda: DOC.boq_xlsx(df, lr, system["area"], system, ctx()),
                           file_name=f"BOQ_{system['system_id']}.xlsx", type="primary", icon=":material/table_view:",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="boq_xlsx", width="stretch")
        st.download_button("Download PDF", data=lambda: DOC.boq_pdf(df, tot, system, ctx()),
                           file_name=f"BOQ_{system['system_id']}.pdf", mime="application/pdf",
                           icon=":material/picture_as_pdf:", key="boq_pdf", width="stretch")
        st.caption("The Excel file keeps live formulas for quantity, packs, amounts and totals.")


def tds_cards(codes: list[str], key_prefix: str) -> None:
    prods = D.products()
    cols = st.columns(3)
    for i, code in enumerate(codes):
        p = D.row_dict(prods, "code", code)
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"<div style='border-left:6px solid {D.text(p.get('colour_hex'), ui.PURPLE)};padding-left:10px'>"
                            f"<b style='font-size:18px;color:{ui.DEEP}'>{esc(code)}</b>{sample_badge()}<br>"
                            f"<span style='color:{ui.MUTED}'>{esc(D.text(p.get('name')))}</span></div>", unsafe_allow_html=True)
                chips([chip(esc(D.text(p.get("technology"))), "purple")])
                b1, b2 = st.columns(2)
                pkey = f"{key_prefix}_prev_{code}"
                if b1.button("Preview", key=f"{key_prefix}_pbtn_{code}", icon=":material/visibility:", width="stretch"):
                    ss[pkey] = not ss.get(pkey, False)
                b2.download_button("PDF", data=lambda c=code: tds_bytes(c), file_name=f"TDS_{code}.pdf",
                                   mime="application/pdf", key=f"{key_prefix}_dl_{code}", icon=":material/download:",
                                   width="stretch")
                if ss.get(pkey):
                    img = tds_preview(code)
                    if img:
                        st.image(img, caption=f"TDS {code} – page 1 (illustrative)")
                    else:
                        st.warning("Preview unavailable – download the PDF instead.")


def panel_tds(system: dict) -> None:
    st.markdown("### TDS / PIS library for this system")
    st.caption("Illustrative templates generated on click – not official TDS.")
    codes = list(dict.fromkeys(l["code"] for l in system["layers"] if l["is_product"]))
    tds_cards(codes, "sys")


def panel_cad(system: dict) -> None:
    st.markdown(f"### CAD / BIM details {sample_badge()}", unsafe_allow_html=True)
    title = system["system_name"]
    svg = DR.section_svg(system["layers"], ss.site.get("substrate", "RCC"), title)
    ui.show_svg(svg, None, "background:#fff;border-radius:14px;border:1px solid #EEEAFB;padding:6px")
    c = st.columns(4)
    sub = ss.site.get("substrate", "RCC")
    c[0].download_button("Download PNG", data=lambda: DR.svg_to_png(DR.section_svg(system["layers"], sub, title, True)),
                         file_name=f"Section_{system['system_id']}.png", mime="image/png", icon=":material/image:",
                         key="cad_png", width="stretch")
    c[1].download_button("Download SVG", data=svg, file_name=f"Section_{system['system_id']}.svg", mime="image/svg+xml",
                         icon=":material/polyline:", key="cad_svg", width="stretch")
    c[2].download_button("Download DXF (AutoCAD)", data=lambda: DR.section_dxf(system["layers"], sub, title),
                         file_name=f"Section_{system['system_id']}.dxf", mime="application/dxf", type="primary",
                         icon=":material/architecture:", key="cad_dxf", width="stretch")
    if c[3].button("Request BIM file", key="cad_bim", icon=":material/view_in_ar:", width="stretch"):
        support_dialog(f"Please share BIM (RVT/IFC) objects for {title} – {ss.surface}, approx. {system['area']:,.0f} sq ft.",
                       "Technical consultation")
    st.info("BIM (RVT/IFC) objects available on request — prototype.", icon=":material/info:")


def panel_spec(system: dict) -> None:
    st.markdown(f"### Specification / tender text {sample_badge()}", unsafe_allow_html=True)
    text = L.spec_text(system, ctx())
    if "cpwd_spec" in L.modifiers(ss.segment):
        st.success("Government segment: CPWD-style item description and IS clause included below.", icon=":material/gavel:")
    st.code(text, language=None, wrap_lines=True)
    st.download_button("Download .txt", data=text, file_name=f"Spec_{system['system_id']}.txt", mime="text/plain",
                       icon=":material/download:", key="spec_txt", type="primary")


def panel_steps(system: dict) -> None:
    st.markdown("### Application steps – site version")
    steps = L.application_steps(system, ctx())
    for start in range(0, len(steps), 4):
        cols = st.columns(4)
        for j, s in enumerate(steps[start:start + 4]):
            cols[j].markdown(f"<div class='scard' style='animation-delay:{(start + j) * .05:.2f}s'><span class='num'>STEP {start + j + 1}</span>"
                             f"<div style='font-size:40px;margin-top:6px'>{s['icon']}</div><div class='t'>{esc(s['title'])}</div>"
                             f"<div class='d'>{esc(s['line'])}</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("#### 🧰 Tools checklist")
            for i, t in enumerate(L.tools_list(system)):
                st.checkbox(t, key=f"tool_{system['system_id']}_{i}")
    dos, donts = L.dos_donts(system)
    with c2:
        with st.container(border=True):
            st.markdown("#### ✅ Do's")
            for d in dos:
                st.markdown(f"- {d}")
            st.markdown("#### ⛔ Don'ts")
            for d in donts:
                st.markdown(f"- {d}")
    with c3:
        with st.container(border=True):
            st.markdown("#### ⏱ Curing & recoat times " + sample_badge(), unsafe_allow_html=True)
            rows = [{"Product": l["code"], "Dry (h)": l["dry"], "Recoat (h)": l["recoat"], "Full cure (days)": l["cure"]}
                    for l in system["layers"] if l["is_product"]]
            st.dataframe(pd.DataFrame(rows).drop_duplicates(), hide_index=True, width="stretch")


def panel_pack(system: dict) -> None:
    st.markdown("### Project pack")
    st.markdown("One ZIP with everything for this project: cover sheet, method statement PDF, BOQ Excel, "
                "TDS PDFs for every product, the DXF section and the spec text.")
    chips([chip("📄 Cover sheet", "purple"), chip("📋 Method statement", "blue"), chip("📊 BOQ.xlsx", "green"),
           chip("📑 TDS PDFs", "amber"), chip("📐 Section.dxf", "orange"), chip("📝 Spec.txt", "pink")])
    df = boq_current(system)
    lr = labour_rate()
    sections = L.method_statement(system, ctx())
    spec = L.spec_text(system, ctx())
    sub = ss.site.get("substrate", "RCC")
    st.download_button("Download Project Pack (.zip)",
                       data=lambda: DOC.project_pack_zip(system, ctx(), sections, df, lr, spec, sub),
                       file_name=f"Prime_Project_Pack_{system['system_id']}.zip", mime="application/zip", type="primary",
                       icon=":material/folder_zip:", key="pack_zip", on_click=on_pack_download)
    if ss.get("pack_downloads", 0):
        st.success(f"Project pack downloaded {ss.pack_downloads} time(s) this session.", icon=":material/celebration:")


# ---------------------------------------------------------------------------------------------
# Step 5 + 6: results
# ---------------------------------------------------------------------------------------------
def step_results() -> None:
    if not (ss.persona and ss.segment and ss.surface):
        st.warning("Please complete steps 1–3 first.")
        st.button("Go to step 1", on_click=go_step, args=(1,), key="res_back")
        return
    if ss.pop("fire_balloons", False):
        st.balloons()
    tier = ss.tier or L.default_tier(ss.site.get("preference"), ss.segment)
    system = L.recommend(ss.surface, tier, ss.site, ss.segment)
    if not system:
        st.warning(f"No system configured for **{ss.surface}** in `data/systems.csv`. Add rows for this surface.")
        return
    ss.current_system_name = system["system_name"]
    base_boq = boq_current(system)
    tot = L.totals(base_boq, labour_rate(), system["area"])

    st.markdown("## Your recommended system")
    persona_strip(system, tot)

    ss.setdefault("tier_ctl", tier)
    c1, c2 = st.columns([2, 3], vertical_alignment="center")
    with c1:
        st.segmented_control("Tier", L.TIERS, key="tier_ctl", format_func=lambda t: TIER_LABEL.get(t, t),
                             on_change=on_tier_change)
    with c2:
        if ss.site.get("preference") == "Show me all three":
            st.caption("You asked to see all three tiers – switch tiers or open *Compare tiers* on the right.")
        if "upgrade_tier" in L.modifiers(ss.segment):
            st.caption("Heavy-traffic segment – the higher tier is suggested by default.")

    left, right = st.columns([3, 2], gap="large")
    with left:
        svg = DR.isometric_svg(system["layers"], ss.site.get("substrate", "RCC"), ss.selected_layer, system["system_name"])
        st.markdown(f"<div class='laptop'><div class='screen'>{ui.svg_img(svg)}</div></div><div class='laptop-base'></div>",
                    unsafe_allow_html=True)
        layers = system["layers"]
        pkey = f"layer_pill_{system['system_id']}_{len(layers)}"
        sel = st.pills("Click a layer for details", list(range(len(layers))), key=pkey, on_change=on_layer_pick,
                       format_func=lambda i: f"{layers[i]['layer_name']}" + (f" · {layers[i]['code']}" if layers[i]["is_product"] else ""))
        ss.selected_layer = layers[sel]["layer_name"] if sel is not None else None
        if ss.pop("open_layer", False) and sel is not None:
            layer_dialog(layers[sel])
    with right:
        tc = ui.TIER_COLOURS.get(system["tier"], ui.PURPLE)
        summary_chips = "".join([
            chip("🛡 {:g}-yr warranty".format(system["warranty"]), "green"),
            chip("🧱 {} layers".format(system["n_layers"]), "purple"),
            chip("🖌 {} coats".format(system["total_coats"]), "blue"),
            chip("₹{:,.0f}/sq ft".format(tot["per_sqft"]), "pink"),
            chip("📅 ~{} days".format(system["app_days"]), "amber"),
            sample_badge()])
        tier_upper = esc(system["tier"].upper())
        name = esc(system["system_name"])
        st.markdown(f"<div class='icard' style='border-top:6px solid {tc}'>"
                    f"<div style='font-size:12px;font-weight:800;color:{tc};letter-spacing:.08em'>{tier_upper} TIER</div>"
                    f"<h3 style='margin:4px 0 8px 0'>{name}</h3>"
                    f"<div class='chips'>{summary_chips}</div></div>", unsafe_allow_html=True)
        st.markdown("**Why this system**")
        for w in system["why_tailored"]:
            st.markdown(f"- {w}")
        st.markdown("**Compliance**")
        chips([chip(esc(s), "green") for s in system["standards"]] or [chip("—", "grey")])
        for n in system["notes"]:
            st.caption("ℹ️ " + n)
        if "repair_prep" in L.modifiers(ss.segment) or ss.site.get("condition") == "Existing – damaged":
            sev = L.crack_severity(D.num(ss.site.get("crack_w")))
            st.warning(f"**Before you start:** remove loose / failed coatings and treat cracks first. "
                       f"Site crack check: **{sev['label']}** – {sev['note']}", icon=":material/construction:")
        if "low_odour" in L.modifiers(ss.segment):
            st.info("Low-odour, water-based options highlighted. Plan zone-by-zone work for minimal downtime.",
                    icon=":material/air:")
        with st.expander("Compare tiers", expanded=ss.site.get("preference") == "Show me all three",
                         icon=":material/compare_arrows:"):
            comp = L.tier_comparison(ss.surface, ss.site, ss.segment)
            st.dataframe(comp, hide_index=True, width="stretch")
            st.caption("All values sample / illustrative.")

    # Action bar
    st.markdown("### Your documents & tools")
    default = D.text(persona_row().get("default_tab"), "Method Statement")
    active = ss.active_panel or default
    for row in (PANELS[:4], PANELS[4:]):
        cols = st.columns(4)
        for col, (name, icon) in zip(cols, row):
            if name == "Get Support":
                if col.button(name, key="actbtn_support", icon=icon, width="stretch"):
                    support_dialog()
            else:
                col.button(name, key=f"actbtn_{name}", icon=icon, width="stretch", on_click=set_panel, args=(name,),
                           type="primary" if name == active else "secondary")
    with st.container(border=True):
        {"Method Statement": panel_method, "BOQ Calculator": panel_boq, "TDS / PIS Library": panel_tds,
         "CAD / BIM Details": panel_cad, "Spec / Tender Text": panel_spec, "Application Steps": panel_steps,
         "Project Pack": panel_pack}.get(active, panel_method)(system)

    # Persona-specific card (contractor's club card is already shown first in the persona strip)
    if not (ss.persona or "").startswith("Contractor"):
        persona_card()

    # Step 6 – Key enablers
    st.markdown("## Key enablers")
    enablers = [("samples", ":material/apartment:", "Sample projects", "Ready example specs for common structures.", ui.PURPLE, ui.DEEP),
                ("tds", ":material/description:", "TDS / PIS library", "One-click access to every product document.", ui.GREEN, "#04795A"),
                ("learning", ":material/school:", "Builder learning programmes", "Workshops, CPD sessions and site visits.", ui.ORANGE, ui.PINK),
                ("sales", ":material/support_agent:", "Technical sales team", "Dedicated experts for specifiers and projects.", ui.BLUE, ui.PURPLE)]
    cols = st.columns(4)
    for col, (k, icon, title, body, c1_, c2_) in zip(cols, enablers):
        with col:
            ui.grad_card(icon, title, body, c1_, c2_)
            if col.button("Open", key=f"enab_{k}", icon=":material/arrow_forward:", width="stretch"):
                if k == "samples":
                    ss.enabler_open = not ss.get("enabler_open", False)
                else:
                    ss.rc_tab = {"tds": "TDS / PIS Library", "learning": "Learning Programmes",
                                 "sales": "Technical Sales Team"}[k]
                    st.switch_page("app_pages/resource_centre.py")
    if ss.get("enabler_open"):
        with st.container(border=True):
            st.markdown(f"### Sample project specs {sample_badge()}", unsafe_allow_html=True)
            projects = D.load("sample_projects.csv")
            cols = st.columns(3)
            for i, (_, r) in enumerate(projects.head(6).iterrows()):
                with cols[i % 3]:
                    st.markdown(f"<div class='icard'><h4>{esc(r['project'])}</h4>"
                                f"<div class='chips'>{chip(esc(r['surface']), 'purple')}{chip(esc(r['city']), 'blue')}</div>"
                                f"<p style='margin:0;color:{ui.MUTED};font-size:14px'>{esc(r['segment'])} · "
                                f"{int(D.num(r['area_sqft'])):,} sq ft · {esc(r['system_id'])}</p></div>", unsafe_allow_html=True)
                    if st.button("Use this spec", key=f"use_spec_sb_{i}", icon=":material/input:"):
                        load_project(r.to_dict())
                        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("Start a new system", key="res_restart", on_click=reset_wizard, icon=":material/restart_alt:")


# ---------------------------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------------------------
ui.hero("System Builder")
sidebar()
ui.stepper(min(ss.step, 6), STEP_LABELS)
if ss.persona and ss.step < 5:
    p = persona_row()
    st.caption(f"{ss.persona}: {D.text(p.get('welcome_line'))}")
{1: step_persona, 2: step_segment, 3: step_surface, 4: step_site}.get(ss.step, step_results)()
