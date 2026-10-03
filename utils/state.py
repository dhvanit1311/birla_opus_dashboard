"""Shared session state helpers and pop-up dialogs (simulated – nothing is sent externally)."""
from __future__ import annotations

import io

import streamlit as st

from utils import data as D
from utils import logic
from utils.ui import chip, chips, esc, sample_badge

SITE_DEFAULTS = {
    "area_mode": "Enter sq ft", "area": 1000.0, "length": 40.0, "width": 25.0, "floors": 1,
    "condition": "New", "substrate": "RCC", "crack_w": 0.0, "crack_d": 0.0, "crack_done": False,
    "exposure": ["Direct sun/UV"], "pressure": "None", "city": "Mumbai", "climate": "Coastal humid",
    "preference": "Premium",
}
WIZARD_KEYS = ["step", "persona", "segment", "surface", "site", "tier", "selected_layer", "active_panel"]


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("step", 1)
    ss.setdefault("persona", None)
    ss.setdefault("segment", None)
    ss.setdefault("surface", None)
    ss.setdefault("site", dict(SITE_DEFAULTS))
    ss.setdefault("tier", None)
    ss.setdefault("selected_layer", None)
    ss.setdefault("active_panel", None)
    ss.setdefault("pack_downloads", 0)


def reset_wizard() -> None:
    for k in WIZARD_KEYS:
        st.session_state.pop(k, None)
    for k in [k for k in st.session_state.keys() if str(k).startswith(("site_", "boq_", "tier_ctl", "layer_pill", "prev_"))]:
        st.session_state.pop(k, None)
    init_state()


def load_project(row: dict) -> None:
    """Load a sample project's persona/segment/surface/tier into the wizard and jump to results."""
    init_state()
    sysdf = D.systems()
    srow = sysdf[sysdf["system_id"] == row.get("system_id")]
    tier = D.text(srow["tier"].iloc[0]) if not srow.empty else "Better"
    cond = D.text(srow["condition"].iloc[0], "any") if not srow.empty else "any"
    press = D.text(srow["pressure"].iloc[0], "any") if not srow.empty else "any"
    segment = D.text(row.get("segment"))
    site = dict(SITE_DEFAULTS)
    site.update({
        "area": D.num(row.get("area_sqft"), 1000), "area_mode": "Enter sq ft", "city": D.text(row.get("city"), "Mumbai"),
        "condition": "New" if cond == "new" or "New construction" in segment else "Existing – good",
        "pressure": {"negative": "Negative side", "positive": "Positive side"}.get(press, "None"),
        "crack_done": True,
    })
    for k in [k for k in st.session_state.keys() if str(k).startswith(("site_", "boq_", "tier_ctl", "layer_pill"))]:
        st.session_state.pop(k, None)
    st.session_state.update({
        "persona": D.text(row.get("persona")) or st.session_state.get("persona") or "Builder / Developer",
        "segment": segment, "surface": D.text(row.get("surface")), "site": site, "tier": tier,
        "step": 5, "selected_layer": None, "active_panel": None,
    })


def success_summary(ref: str, fields: dict, note: str = "") -> None:
    st.success(f"Request received – reference **{ref}**", icon=":material/check_circle:")
    rows = "".join(f"<tr><td style='color:#6B7280;padding:3px 10px 3px 0'>{esc(k)}</td><td><b>{esc(v)}</b></td></tr>"
                   for k, v in fields.items() if v not in (None, "", []))
    st.markdown(f"<div class='icard mint'><h4>Summary</h4><table>{rows}</table>"
                f"<p style='color:#6B7280;font-size:13px;margin-top:8px'>{esc(note or 'Prototype – nothing was sent. The sales team would contact you within 1 working day.')}</p></div>",
                unsafe_allow_html=True)


def _qr_png(text: str) -> bytes | None:
    try:
        import qrcode

        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


@st.dialog("Get support from Prime experts", width="large", icon=":material/support_agent:")
def support_dialog(prefill_message: str = "", request_type: str = "Technical consultation") -> None:
    persona = st.session_state.get("persona") or "PMC / Specifier"
    types = ["Site visit", "Technical consultation", "Sample request", "Training"]
    with st.form("support_form", border=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name", key="sup_name")
        company = c2.text_input("Company", key="sup_company")
        role = c1.text_input("Role", value=persona, key="sup_role")
        city = c2.text_input("City", value=st.session_state.get("site", {}).get("city", ""), key="sup_city")
        phone = c1.text_input("Phone", key="sup_phone")
        email = c2.text_input("Email", key="sup_email")
        stage = c1.selectbox("Project stage", ["Design / specification", "Tendering", "Under construction", "Repair / maintenance"], key="sup_stage")
        rtype = c2.radio("I need", types, index=types.index(request_type) if request_type in types else 1, key="sup_type", horizontal=True)
        msg = st.text_area("Message", value=prefill_message, key="sup_msg")
        sent = st.form_submit_button("Submit request", type="primary", icon=":material/send:")
    if sent:
        ref = logic.reference_id()
        st.toast(f"Support request logged – {ref}", icon="✅")
        success_summary(ref, {"Name": name or "—", "Company": company, "Role": role, "City": city, "Phone": phone,
                              "Email": email, "Stage": stage, "Request": rtype, "Message": msg,
                              "System": st.session_state.get("current_system_name", "")})
    st.divider()
    if st.button("Join Prime WhatsApp Tech Community", icon=":material/forum:", key="wa_join"):
        st.session_state["show_wa_qr"] = True
    if st.session_state.get("show_wa_qr"):
        c1, c2 = st.columns([1, 2])
        png = _qr_png("Prime WhatsApp Tech Community – prototype placeholder")
        if png:
            c1.image(png, width=150)
        c2.info("Prototype – link will be shared by sales team.", icon=":material/qr_code_2:")


@st.dialog("Confirm your interest", icon=":material/event_available:")
def simple_dialog(title: str, intro: str, extra_field: str = "", options: list[str] | None = None) -> None:
    st.markdown(f"#### {esc(title)}")
    st.caption(intro)
    with st.form(f"simple_form_{abs(hash(title)) % 10_000}", border=False):
        name = st.text_input("Name", key="sd_name")
        org = st.text_input("Company / organisation", key="sd_org")
        phone = st.text_input("Phone", key="sd_phone")
        extra = st.selectbox(extra_field, options, key="sd_extra") if extra_field and options else None
        ok = st.form_submit_button("Confirm", type="primary", icon=":material/check:")
    if ok:
        ref = logic.reference_id()
        st.toast(f"{title} – {ref}", icon="🎉")
        fields = {"Request": title, "Name": name or "—", "Organisation": org, "Phone": phone}
        if extra_field:
            fields[extra_field] = extra
        success_summary(ref, fields)


@st.dialog("Register for event", icon=":material/how_to_reg:")
def event_dialog(event: dict) -> None:
    st.markdown(f"#### {esc(event.get('title') or event.get('type'))}")
    chips([chip(esc(event.get("type", "")), "purple"), chip("📅 " + esc(event.get("date", "")), "blue"),
           chip("📍 " + esc(event.get("city", "")), "green"), chip(f"{esc(event.get('seats_left', ''))} seats left", "amber")])
    with st.form("event_form", border=False):
        name = st.text_input("Name", key="ev_name")
        org = st.text_input("Company", key="ev_org")
        seats = st.number_input("Seats", 1, 10, 1, key="ev_seats")
        ok = st.form_submit_button("Register", type="primary", icon=":material/how_to_reg:")
    if ok:
        ref = logic.reference_id()
        st.toast(f"Registered – {ref}", icon="🎟️")
        success_summary(ref, {"Event": event.get("title") or event.get("type"), "Date": event.get("date"),
                              "City": event.get("city"), "Name": name or "—", "Company": org, "Seats": seats},
                        "Prototype – a calendar invite would be emailed by the learning team.")


@st.dialog("Layer detail", width="large", icon=":material/layers:")
def layer_dialog(layer: dict) -> None:
    from utils import documents

    code = layer["code"] if layer["is_product"] else "Generic item"
    st.markdown(f"### {esc(layer['layer_name'])}")
    st.markdown(f"<div class='chips'>{chip(esc(code), 'purple')}{chip(esc(layer['name']), 'blue')}"
                f"{chip(esc(layer['technology']), 'green')}{sample_badge()}</div>", unsafe_allow_html=True)
    st.markdown(f"**What it does:** {layer['description']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Coverage / coat", f"{layer['coverage']:g} sq ft/{layer['unit']}")
    c2.metric("Coats", layer["coats"])
    c3.metric("Thickness", f"{layer['thickness']:g} mm" if layer["thickness"] else "—")
    if layer["is_product"]:
        c1, c2, c3 = st.columns(3)
        unit = lambda v, u: f"{v} {u}" if v != "—" else "— (n/a)"  # noqa: E731
        c1.metric("Dry time", unit(layer["dry"], "h"))
        c2.metric("Recoat time", unit(layer["recoat"], "h"))
        c3.metric("Full cure", unit(layer["cure"], "days"))
        st.download_button("Download TDS (illustrative PDF)", data=lambda: documents.tds_pdf(layer["code"]),
                           file_name=f"TDS_{layer['code']}.pdf", mime="application/pdf", type="primary",
                           icon=":material/description:", key=f"dlg_tds_{layer['code']}")
    else:
        st.info("Generic, non-branded layer item – no Prime TDS. Use as per method statement.", icon=":material/info:")
