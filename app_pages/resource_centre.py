"""Page 2 – Resource Centre: TDS/PIS library, sample projects, learning, sales team, FAQs."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import data as D
from utils import documents as DOC
from utils import ui
from utils.state import event_dialog, init_state, load_project, simple_dialog, support_dialog
from utils.ui import chip, chips, esc, sample_badge

init_state()
ss = st.session_state

TABS = ["TDS / PIS Library", "Sample Projects", "Learning Programmes", "Technical Sales Team", "FAQs"]
TYPE_COLOURS = {"Workshop": "purple", "CPD": "green", "Site visit": "orange", "Applicator training": "pink"}
SEG_COLOURS = {s: c for s, c in zip(
    ["New construction – residential", "Repair & renovation", "Housing society / CHS redevelopment",
     "Commercial & Industrial (C&I)", "Government / PWD / CPWD", "Schools & colleges", "Hospitals & healthcare",
     "Hotels & hospitality", "Small infrastructure"], ui.PALETTE)}


@st.cache_data(show_spinner=False)
def tds_bytes(code: str) -> bytes:
    return DOC.tds_pdf(code)


@st.cache_data(show_spinner=False)
def pis_bytes(code: str) -> bytes:
    return DOC.pis_pdf(code)


@st.cache_data(show_spinner=False)
def tds_preview(code: str) -> bytes | None:
    return DOC.pdf_preview_png(DOC.tds_pdf(code))


def make_tabs(labels: list[str], default: str | None):
    try:
        return st.tabs(labels, default=default if default in labels else None)
    except TypeError:  # older Streamlit without `default`
        return st.tabs(labels)


# -------------------------------------------------------------------------------------------
def tab_library() -> None:
    prods = D.products()
    if prods.empty:
        return
    techs = sorted(prods["technology"].dropna().unique())
    surfaces = list(D.surfaces()["surface"])
    c1, c2, c3 = st.columns([2, 2, 2])
    q = c1.text_input("Search", placeholder="e.g. B70, membrane, tank", key="rc_search", icon=":material/search:")
    tsel = c2.multiselect("Technology", techs, key="rc_tech")
    ssel = c3.multiselect("Surface", surfaces, key="rc_surf")
    df = prods.copy()
    if q:
        ql = q.lower()
        df = df[df.apply(lambda r: ql in " ".join(str(v) for v in r.values).lower(), axis=1)]
    if tsel:
        df = df[df["technology"].isin(tsel)]
    if ssel:
        df = df[df["surfaces"].apply(lambda s: any(x in D.split_pipes(s) for x in ssel))]
    codes = list(df["code"])
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown(f"**{len(codes)} product(s)** {sample_badge()} – illustrative TDS / PIS generated on click.",
                unsafe_allow_html=True)
    c2.download_button("Download all (ZIP)", data=lambda: DOC.all_tds_zip(list(prods["code"])),
                       file_name="Prime_TDS_PIS_all.zip", mime="application/zip", type="primary",
                       icon=":material/folder_zip:", key="rc_all_zip", width="stretch")
    if not codes:
        st.info("No products match these filters.")
    cols = st.columns(3)
    for i, code in enumerate(codes):
        p = D.row_dict(prods, "code", code)
        colour = D.text(p.get("colour_hex"), ui.PURPLE)
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='background:linear-gradient(135deg,{colour},{ui.DEEP});border-radius:12px;padding:12px 14px;color:#fff'>"
                    f"<div style='font-size:22px;font-weight:800'>{esc(code)}</div>"
                    f"<div style='font-size:13.5px;opacity:.92'>{esc(D.text(p.get('name')))}</div></div>"
                    f"<p style='font-size:14px;color:{ui.MUTED};margin:8px 0 4px 0'>{esc(D.text(p.get('description')))}</p>",
                    unsafe_allow_html=True)
                chips([chip(esc(D.text(p.get("technology"))), "purple")] +
                      [chip(esc(s), "blue") for s in D.split_pipes(p.get("surfaces"))[:4]])
                b1, b2, b3 = st.columns(3)
                pkey = f"rc_prev_{code}"
                if b1.button("Preview", key=f"rc_pbtn_{code}", icon=":material/visibility:", width="stretch"):
                    ss[pkey] = not ss.get(pkey, False)
                b2.download_button("TDS", data=lambda c=code: tds_bytes(c), file_name=f"TDS_{code}.pdf", mime="application/pdf",
                                   key=f"rc_tds_{code}", icon=":material/download:", width="stretch")
                b3.download_button("PIS", data=lambda c=code: pis_bytes(c), file_name=f"PIS_{code}.pdf", mime="application/pdf",
                                   key=f"rc_pis_{code}", icon=":material/download:", width="stretch")
                if ss.get(pkey):
                    img = tds_preview(code)
                    if img:
                        st.image(img, caption=f"TDS {code} – page 1 (illustrative)")
                    else:
                        st.warning("Preview unavailable – download the PDF instead.")


def tab_projects() -> None:
    df = D.load("sample_projects.csv")
    if df.empty:
        return
    c1, c2 = st.columns(2)
    segs = c1.multiselect("Segment", sorted(df["segment"].dropna().unique()), key="rc_p_seg")
    surfs = c2.multiselect("Surface", sorted(df["surface"].dropna().unique()), key="rc_p_surf")
    if segs:
        df = df[df["segment"].isin(segs)]
    if surfs:
        df = df[df["surface"].isin(surfs)]
    st.markdown(f"**{len(df)} sample reference project(s)** {sample_badge()}", unsafe_allow_html=True)
    if not df.empty:
        mdf = df.copy()
        mdf["lat"] = pd.to_numeric(mdf["lat"], errors="coerce")
        mdf["lon"] = pd.to_numeric(mdf["lon"], errors="coerce")
        mdf["area_sqft"] = pd.to_numeric(mdf["area_sqft"], errors="coerce").fillna(1000)
        fig = px.scatter_geo(mdf.dropna(subset=["lat", "lon"]), lat="lat", lon="lon", color="segment", size="area_sqft",
                             hover_name="project", hover_data={"city": True, "surface": True, "system_id": True,
                                                               "lat": False, "lon": False, "area_sqft": ":,"},
                             color_discrete_map=SEG_COLOURS, size_max=28)
        fig.update_geos(scope="asia", center=dict(lat=22, lon=79), projection_scale=3.2, showcountries=True,
                        countrycolor="#C7C2EA", showland=True, landcolor="#F6F4FF", showocean=True, oceancolor="#EEF4FF",
                        showframe=False)
        fig.update_layout(height=460, title="Sample reference projects across India", margin=dict(l=0, r=0, t=40, b=0),
                          legend=dict(orientation="v", y=0.5, x=1.0))
        ui.plot(fig, key="rc_map")
    sysdf = D.systems()
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        with cols[i % 3]:
            with st.container(border=True):
                col = SEG_COLOURS.get(r["segment"], ui.PURPLE)
                st.markdown(f"<div style='border-left:6px solid {col};padding-left:10px'><b style='font-size:16px;color:{ui.DEEP}'>"
                            f"{esc(r['project'])}</b>{sample_badge()}<br><span style='color:{ui.MUTED};font-size:13.5px'>"
                            f"{esc(r['city'])} · {esc(r['year'])} · {int(D.num(r['area_sqft'])):,} sq ft</span></div>",
                            unsafe_allow_html=True)
                chips([chip(esc(r["surface"]), "purple"), chip(esc(r["segment"]), "grey")])
                layers = sysdf[sysdf["system_id"] == r["system_id"]].sort_values("layer_order")
                with st.expander("View spec", icon=":material/layers:"):
                    if layers.empty:
                        st.caption(f"System `{r['system_id']}` not found in systems.csv")
                    else:
                        st.markdown(f"**{esc(layers['system_name'].iloc[0])}**")
                        for _, l in layers.iterrows():
                            st.markdown(f"- {l['layer_name']} – `{l['product_code_or_generic']}` × {int(D.num(l['coats'], 1))}")
                if st.button("Use this spec", key=f"rc_use_{i}", type="primary", icon=":material/input:", width="stretch"):
                    load_project(r.to_dict())
                    st.switch_page("app_pages/system_builder.py")


def tab_learning() -> None:
    df = D.load("learning_events.csv")
    if df.empty:
        return
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date_dt")
    types = sorted(df["type"].dropna().unique())
    tsel = st.pills("Filter by type", types, selection_mode="multi", key="rc_ev_types")
    if tsel:
        df = df[df["type"].isin(tsel)]
    for month, grp in df.groupby(df["date_dt"].dt.strftime("%B %Y"), sort=False):
        st.markdown(f"#### 📅 {month}")
        for i, (_, e) in enumerate(grp.iterrows()):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 5, 1.4], vertical_alignment="center")
                d = e["date_dt"]
                c1.markdown(f"<div style='background:{ui.LAVENDER};border-radius:12px;text-align:center;padding:6px'>"
                            f"<div style='font-size:24px;font-weight:800;color:{ui.PURPLE}'>{d.day if pd.notna(d) else '–'}</div>"
                            f"<div style='font-size:12px;color:{ui.MUTED}'>{d.strftime('%a') if pd.notna(d) else ''}</div></div>",
                            unsafe_allow_html=True)
                c2.markdown(f"<b style='font-size:16px'>{esc(D.text(e.get('title'), e['type']))}</b><div class='chips'>"
                            f"{chip(esc(e['type']), TYPE_COLOURS.get(e['type'], 'grey'))}{chip('📍 ' + esc(e['city']), 'blue')}"
                            f"{chip('👥 ' + esc(e['audience']), 'grey')}{chip(str(int(D.num(e['seats_left']))) + ' seats left', 'amber')}</div>",
                            unsafe_allow_html=True)
                if c3.button("Register", key=f"rc_reg_{e.name}", type="primary", icon=":material/how_to_reg:", width="stretch"):
                    ev = e.to_dict()
                    ev["date"] = d.strftime("%d %b %Y") if pd.notna(d) else D.text(e["date"])
                    event_dialog(ev)
    st.markdown("### Request an in-house session")
    with st.form("inhouse_form"):
        c1, c2, c3 = st.columns(3)
        org = c1.text_input("Organisation", key="ih_org")
        city = c2.text_input("City", key="ih_city")
        topic = c3.selectbox("Topic", ["Systems-based WP specs (CPD)", "Basement & raft membranes", "Wet areas & tanks",
                                       "Applicator hands-on", "Cool roofs"], key="ih_topic")
        c1, c2 = st.columns(2)
        people = c1.number_input("Expected participants", 5, 500, 20, key="ih_people")
        month = c2.selectbox("Preferred month", ["October 2026", "November 2026", "December 2026", "January 2027"], key="ih_month")
        ok = st.form_submit_button("Request session", type="primary", icon=":material/send:")
    if ok:
        from utils.logic import reference_id
        from utils.state import success_summary

        ref = reference_id()
        st.toast(f"In-house session requested – {ref}", icon="🎓")
        success_summary(ref, {"Organisation": org or "—", "City": city, "Topic": topic, "Participants": people, "Month": month})


def tab_sales() -> None:
    df = D.load("sales_team.csv")
    if df.empty:
        return
    st.caption("Sample contacts for illustration – not real people or numbers.")
    gradients = [(ui.PURPLE, ui.DEEP), (ui.GREEN, "#04795A"), (ui.ORANGE, ui.PINK), (ui.BLUE, ui.PURPLE), (ui.PINK, ui.DEEP)]
    cols = st.columns(len(df) if len(df) <= 5 else 3)
    for i, (_, r) in enumerate(df.iterrows()):
        c1_, c2_ = gradients[i % len(gradients)]
        with cols[i % len(cols)]:
            ui.grad_card(":material/support_agent:", D.text(r["title"]), f"{r['region']} · {r['cities_covered']}", c1_, c2_)
            if st.button("Request callback", key=f"rc_cb_{i}", type="primary", icon=":material/call:", width="stretch"):
                simple_dialog(f"Callback – {r['title']}", "Pick a time slot; the regional expert will call you (simulated).",
                              "Preferred slot", ["Morning (10–12)", "Afternoon (2–4)", "Evening (5–7)"])
            if st.button("Email", key=f"rc_em_{i}", icon=":material/mail:", width="stretch"):
                ss[f"rc_show_email_{i}"] = True
            if ss.get(f"rc_show_email_{i}"):
                st.info(f"📧 {r['email_sample']}\n\n📞 {r['phone_sample']}\n\n(sample contact)")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Not sure which region? Get support", key="rc_support", icon=":material/help:"):
        support_dialog()


def tab_faqs() -> None:
    df = D.load("faqs.csv")
    for i, (_, r) in enumerate(df.iterrows()):
        with st.expander(f"{i + 1}. {r['question']}", icon=":material/help:"):
            st.markdown(D.text(r["answer"]))


# -------------------------------------------------------------------------------------------
ui.hero("Resource Centre", subtitle="Documents, reference projects, learning and expert support")
with st.sidebar:
    st.markdown("<div class='icard lav'><h4>Resource Centre</h4><p style='margin:0;font-size:14px'>Everything a specifier, "
                "builder or applicator needs around a Prime system.</p></div>", unsafe_allow_html=True)
    if st.button("Back to System Builder", key="rc_back", icon=":material/construction:", width="stretch"):
        st.switch_page("app_pages/system_builder.py")
default_tab = ss.get("rc_tab")
tabs = make_tabs(TABS, default_tab)
with tabs[0]:
    tab_library()
with tabs[1]:
    tab_projects()
with tabs[2]:
    tab_learning()
with tabs[3]:
    tab_sales()
with tabs[4]:
    tab_faqs()
