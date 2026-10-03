"""Page 3 – Project Insights: the research behind Prime System Builder."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import data as D
from utils import ui
from utils.state import init_state
from utils.ui import chip, chips, esc, sample_badge

init_state()

BRAND_COLOURS = {"Birla Opus Prime": ui.PURPLE, "Opus Prime – today": ui.PURPLE, "Opus Prime – target": ui.PURPLE,
                 "Dr. Fixit": ui.ORANGE, "Asian Paints SmartCare": ui.PINK, "Fosroc": ui.BLUE, "Sika": ui.AMBER,
                 "Local": "#9CA3AF", "Local brands": "#9CA3AF"}
STATUS_COLOURS = {"Done": ui.GREEN, "In progress": ui.AMBER, "Planned": ui.BLUE, "Delayed": ui.PINK}
DELIV_COLOURS = {"Delivered": "green", "Handed over": "blue", "In use": "purple", "Pending": "amber"}


def mv(metric: str, default: float = 0.0) -> float:
    return D.market_value(metric, default)


# -------------------------------------------------------------------------------------------
def tab_market() -> None:
    kpis = [(f"₹{mv('india_wp_market_2025', 10170):,.0f} Cr", "India WP market (2025)", ui.PURPLE, True),
            (f"~{mv('cagr_to_2035', 8.1):g}%", "CAGR to 2035", ui.GREEN, True),
            (f"₹{mv('prime_addressable_fy26', 668):,.0f} → ₹{mv('prime_addressable_fy27', 1158):,.0f} Cr",
             "Prime addressable market FY26 → FY27", ui.PINK, True),
            (f"{mv('touchpoints', 22):.0f}", "Stakeholder touchpoints", ui.ORANGE, False),
            (f"{mv('products_benchmarked', 28):.0f}", "Products benchmarked", ui.BLUE, False),
            (f"{mv('priority_skus', 10):.0f}", "Priority SKUs", ui.DEEP, False)]
    for row in (kpis[:3], kpis[3:]):
        cols = st.columns(3)
        for col, (v, l, c, s) in zip(cols, row):
            with col:
                ui.kpi(v, l, c, s)
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Funnel(
            y=["TAM – India WP market", "SAM – Prime addressable (FY27)", "SOM – FY27 plan"],
            x=[mv("tam", 10170), mv("sam", 1158), mv("som", 60)], textinfo="value+percent initial",
            texttemplate="₹%{value:,.0f} Cr<br>%{percentInitial:.1%}",
            marker=dict(color=[ui.PURPLE, ui.PINK, ui.GREEN]), connector=dict(line=dict(color="#E7E2FF"))))
        fig.update_layout(title="TAM → SAM → SOM (sample)", height=380, margin=dict(l=210, r=20, t=50, b=20))
        ui.plot(fig, key="pi_funnel")
    with c2:
        seg = D.load("segments_market.csv")
        if not seg.empty:
            seg["value_cr"] = pd.to_numeric(seg["value_cr"], errors="coerce").fillna(0)
            fig = px.treemap(seg, path=["parent", "segment"], values="value_cr", color="segment",
                             color_discrete_sequence=ui.PALETTE)
            fig.update_traces(texttemplate="<b>%{label}</b><br>₹%{value:,.0f} Cr", root_color="#F6F4FF")
            fig.update_layout(title="WP sub-segments (₹ Cr, sample)", height=380, margin=dict(l=4, r=4, t=50, b=4))
            ui.plot(fig, key="pi_treemap")

    st.markdown("### Growth scenario " + sample_badge(), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    cagr = c1.slider("Addressable-market CAGR after FY27 (%)", 2.0, 20.0, float(mv("cagr_to_2035", 8.1)), 0.1, key="pi_cagr")
    share = c2.slider("Prime share of addressable market (%)", 1.0, 20.0, 5.0, 0.5, key="pi_share")
    years = ["FY26", "FY27", "FY28", "FY29", "FY30"]
    market = [mv("prime_addressable_fy26", 668), mv("prime_addressable_fy27", 1158)]
    for _ in range(3):
        market.append(market[-1] * (1 + cagr / 100))
    revenue = [m * share / 100 for m in market]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=revenue, mode="lines+markers+text", name="Prime WP revenue (₹ Cr)",
                             line=dict(color=ui.PURPLE, width=4), marker=dict(size=10),
                             text=[f"₹{v:,.0f}" for v in revenue], textposition="top center"))
    fig.add_hline(y=mv("fy27_plan", 60), line_dash="dash", line_color=ui.PINK,
                  annotation_text=f"FY27 plan ₹{mv('fy27_plan', 60):.0f} Cr", annotation_position="bottom right")
    fig.update_layout(title="Prime WP revenue scenario to FY30", height=380, yaxis_title="₹ Cr", showlegend=False)
    ui.plot(fig, key="pi_growth")
    gap = revenue[1] - mv("fy27_plan", 60)
    st.markdown(f"<div class='icard {'mint' if gap >= 0 else 'pinkish'}'><b>FY27 at {share:g}% share: ₹{revenue[1]:,.0f} Cr</b> – "
                f"{'ahead of' if gap >= 0 else 'behind'} the ₹{mv('fy27_plan', 60):.0f} Cr plan by ₹{abs(gap):,.0f} Cr.</div>",
                unsafe_allow_html=True)
    st.info("Waterproofing is a **part of construction chemicals** – its value sits inside the construction-chemicals "
            "market and is never added on top of it.", icon=":material/info:")


def tab_competitors() -> None:
    brands = D.load("brands.csv")
    if not brands.empty:
        for c in ("reach", "credibility", "size"):
            brands[c] = pd.to_numeric(brands[c], errors="coerce").fillna(5)
        fig = go.Figure()
        for q in [(0, 5, 0, 5, "#FAFAFC"), (5, 10, 5, 10, "#F6F4FF")]:
            fig.add_shape(type="rect", x0=q[0], x1=q[1], y0=q[2], y1=q[3], fillcolor=q[4], line_width=0, layer="below")
        fig.add_vline(x=5, line_color="#D9D4F5", line_width=2)
        fig.add_hline(y=5, line_color="#D9D4F5", line_width=2)
        for x, y, t in [(2.5, 9.6, "Engineer-led"), (7.5, 9.6, "White space: engineer-grade + mass reach"),
                        (2.5, 0.4, "Low reach, low credibility"), (7.5, 0.4, "Retail-led")]:
            fig.add_annotation(x=x, y=y, text=f"<b>{t}</b>", showarrow=False, font=dict(color=ui.MUTED, size=12))
        for _, b in brands.iterrows():
            col = BRAND_COLOURS.get(b["brand"], ui.BLUE)
            fig.add_trace(go.Scatter(x=[b["reach"]], y=[b["credibility"]], mode="markers+text", name=b["brand"],
                                     text=[b["brand"]], textposition="top center",
                                     marker=dict(size=b["size"], color=col, opacity=0.35 if "today" in b["brand"] else 0.85,
                                                 line=dict(color="#fff", width=2))))
        t = brands[brands["brand"].str.contains("today")]
        g = brands[brands["brand"].str.contains("target")]
        if not t.empty and not g.empty:
            fig.add_annotation(x=g["reach"].iloc[0], y=g["credibility"].iloc[0], ax=t["reach"].iloc[0], ay=t["credibility"].iloc[0],
                               xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.6,
                               arrowwidth=3, arrowcolor=ui.PURPLE)
        fig.update_layout(title="White-space map: reach vs technical credibility (sample)", height=520, showlegend=False,
                          xaxis=dict(title="Reach / familiarity →", range=[0, 10], showgrid=False),
                          yaxis=dict(title="Technical credibility →", range=[0, 10], showgrid=False))
        ui.plot(fig, key="pi_bubble")
    comp = D.load("competitor_products.csv")
    if comp.empty:
        return
    st.markdown(f"### Benchmark – {len(comp)} products across {comp['brand'].nunique()} players {sample_badge()}",
                unsafe_allow_html=True)
    brands_sel = st.pills("Players", sorted(comp["brand"].unique()), selection_mode="multi", key="pi_brands")
    view = comp[comp["brand"].isin(brands_sel)] if brands_sel else comp
    st.dataframe(view.drop(columns=["is_sample"]).assign(sample="Sample"), hide_index=True, width="stretch",
                 column_config={"price_sqft": st.column_config.NumberColumn("₹/sq ft", format="₹%d"),
                                "elongation_pct": "Elongation %", "warranty_yrs": "Warranty (yrs)"})
    sc = comp.copy()
    sc["price_sqft"] = pd.to_numeric(sc["price_sqft"], errors="coerce")
    sc["elongation_pct"] = pd.to_numeric(sc["elongation_pct"], errors="coerce")
    sc["warranty_yrs"] = pd.to_numeric(sc["warranty_yrs"], errors="coerce").fillna(1)
    sc = sc.dropna(subset=["price_sqft", "elongation_pct"])
    fig = px.scatter(sc, x="price_sqft", y="elongation_pct", color="brand", size="warranty_yrs", hover_name="product",
                     color_discrete_map=BRAND_COLOURS, size_max=26, symbol="technology")
    fig.update_layout(title="Price vs performance (sample)", height=460, xaxis_title="₹ per sq ft (sample)",
                      yaxis_title="Elongation % (sample)")
    ui.plot(fig, key="pi_scatter")


def tab_field() -> None:
    tp = D.load("touchpoints.csv")
    c1, c2 = st.columns([1, 1])
    with c1:
        if not tp.empty:
            tp["lat"] = pd.to_numeric(tp["lat"], errors="coerce")
            tp["lon"] = pd.to_numeric(tp["lon"], errors="coerce")
            pts = tp.dropna(subset=["lat", "lon"])
            kwargs = dict(lat="lat", lon="lon", color="stakeholder_type", hover_name="name",
                          hover_data={"city": True, "key_insight": True, "lat": False, "lon": False},
                          color_discrete_sequence=ui.PALETTE, zoom=5.4, center=dict(lat=21.1, lon=72.9), height=520)
            map_fn = getattr(px, "scatter_map", None)
            if map_fn is not None:
                fig = map_fn(pts, map_style="carto-positron", **kwargs)
            else:  # older plotly
                fig = px.scatter_mapbox(pts, mapbox_style="carto-positron", **kwargs)
            fig.update_traces(marker=dict(size=14))
            fig.update_layout(title=f"{len(tp)} stakeholder touchpoints – Mumbai/Thane, Ahmedabad, Gandhinagar",
                              margin=dict(l=0, r=0, t=50, b=0), legend=dict(orientation="h", y=-0.02, title=""))
            ui.plot(fig, key="pi_tp_map")
            counts = tp.groupby(["city", "stakeholder_type"]).size().reset_index(name="count")
            st.dataframe(counts.pivot(index="stakeholder_type", columns="city", values="count").fillna(0).astype(int),
                         width="stretch")
    with c2:
        links = D.load("insight_links.csv")
        if not links.empty:
            links["value"] = pd.to_numeric(links["value"], errors="coerce").fillna(1)
            nodes = list(dict.fromkeys(list(links["source"]) + list(links["target"])))
            idx = {n: i for i, n in enumerate(nodes)}
            ncol = [ui.PALETTE[i % len(ui.PALETTE)] for i in range(len(nodes))]
            fig = go.Figure(go.Sankey(
                node=dict(label=nodes, pad=28, thickness=16, color=ncol, line=dict(color="#fff", width=1)),
                link=dict(source=[idx[s] for s in links["source"]], target=[idx[t] for t in links["target"]],
                          value=links["value"], color="rgba(82,72,158,0.18)")))
            fig.update_layout(title="Stakeholder → insight → recommendation", height=620, font=dict(size=12))
            ui.plot(fig, key="pi_sankey")
    st.markdown("### The three key insights")
    cols = st.columns(3)
    insights = [("🏗️", "Cat-A contractors unlock the market", "They decide the brand on most project sites – win them and specs follow.", ui.PURPLE, ui.DEEP),
                ("🎨", "Cat-B/C paint contractors are already in our system", "Opus paint applicators can be trained into WP applicators (T3 model).", ui.GREEN, "#04795A"),
                ("🧩", "Buyers buy systems, not products", "Specs, BOQs and warranties are written for complete systems.", ui.PINK, ui.ORANGE)]
    for col, (ic, t, b, c1_, c2_) in zip(cols, insights):
        with col:
            ui.grad_card(ic, t, b, c1_, c2_)
    st.markdown("### Voices from the field")
    quotes = D.load("quotes.csv")
    cols = st.columns(3)
    for i, (_, q) in enumerate(quotes.iterrows()):
        cols[i % 3].markdown(f"<div class='quote'>“{esc(q['quote'])}”<div class='who'>— {esc(q['stakeholder'])}, {esc(q['city'])}</div></div>",
                             unsafe_allow_html=True)


def tab_priority() -> None:
    df = D.load("priority_products.csv")
    if df.empty:
        return
    crit = [("market_size", "Market size"), ("growth", "Growth"), ("gap_vs_drfixit", "Gap vs Dr. Fixit"),
            ("rd_feasibility", "R&D feasibility"), ("margin", "Margin"), ("brand_fit", "Brand fit")]
    defaults = [25, 20, 15, 15, 15, 10]
    st.markdown("#### Weights – drag to re-rank")
    cols = st.columns(6)
    weights = {}
    for col, (c, label), d in zip(cols, crit, defaults):
        weights[c] = col.slider(label, 0, 50, d, 5, key=f"pi_w_{c}")
    total_w = sum(weights.values()) or 1
    for c, _ in crit:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    contrib = pd.DataFrame({label: df[c] * weights[c] / total_w for c, label in crit})
    df["Score"] = contrib.sum(axis=1).round(2)
    df = pd.concat([df, contrib], axis=1).sort_values("Score", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    df["vendors_qualified"] = pd.to_numeric(df["vendors_qualified"], errors="coerce").fillna(0).astype(int)
    df["Vendors ≥ 5"] = df["vendors_qualified"].apply(lambda v: "✅" if v >= 5 else "⚠️")
    st.dataframe(df[["Rank", "product", "code", "Score", "make_or_buy", "vendors_qualified", "Vendors ≥ 5", "launch_quarter", "status"]],
                 hide_index=True, width="stretch",
                 column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=10, format="%.2f"),
                                "product": "Product", "code": "Code", "make_or_buy": "Make / Buy",
                                "vendors_qualified": "Vendors qualified", "launch_quarter": "Launch", "status": "Status"})
    long = df.melt(id_vars=["product", "code"], value_vars=[l for _, l in crit], var_name="Criterion", value_name="Contribution")
    long["label"] = long["code"] + " – " + long["product"]
    fig = px.bar(long, y="label", x="Contribution", color="Criterion", orientation="h",
                 color_discrete_sequence=[ui.PURPLE, ui.GREEN, ui.PINK, ui.AMBER, ui.ORANGE, ui.BLUE],
                 category_orders={"label": list(df["code"] + " – " + df["product"])})
    fig.update_layout(title="Score contributions by criterion", height=480, yaxis_title="", xaxis_title="Weighted score")
    ui.plot(fig, key="pi_priority_bar")
    mb = df["make_or_buy"].value_counts()
    chips([chip(f"🏭 Make (in-house): {mb.get('Make', 0)}", "purple"), chip(f"🤝 Buy (bought-out): {mb.get('Buy', 0)}", "orange"),
           chip(f"Vendor target ≥ 5 met: {(df['vendors_qualified'] >= 5).sum()}/{len(df)}", "green")])


def tab_gtm() -> None:
    st.markdown("<div class='hero' style='padding:22px 28px'><div class='wordmark'>Positioning</div>"
                "<h1 style='font-size:1.6rem'>“The only engineer-grade waterproofing expert with mass reach.”</h1></div>",
                unsafe_allow_html=True)
    levers = [(":material/architecture:", "1. Specifier pull", "CPD, spec text and BOQs that drop straight into tenders.", ui.PURPLE, ui.DEEP),
              (":material/handshake:", "2. Contractor & owner pull", "Cat-A contractor programmes + system warranty for owners.", ui.GREEN, "#04795A"),
              (":material/groups:", "3. T3 model", "Train Cat-B/C paint contractors; WhatsApp tech community.", ui.ORANGE, ui.PINK),
              (":material/category:", "4. Segment positioning", "Distinct stories for CHS, hospitals, government, C&I.", ui.BLUE, ui.PURPLE),
              (":material/science:", "5. Tier 1.5/2 cities first", "Pilot + A/B tests before scaling regionally.", ui.PINK, ui.DEEP)]
    cols = st.columns(5)
    for col, (ic, t, b, c1_, c2_) in zip(cols, levers):
        with col:
            ui.grad_card(ic, t, b, c1_, c2_)
    rm = D.load("roadmap.csv")
    if not rm.empty:
        rm["start"] = pd.to_datetime(rm["start"], errors="coerce")
        rm["end"] = pd.to_datetime(rm["end"], errors="coerce")
        rm = rm.dropna(subset=["start", "end"])
        fig = px.timeline(rm, x_start="start", x_end="end", y="task", color="status", color_discrete_map=STATUS_COLOURS,
                          hover_data={"workstream": True})
        fig.update_yaxes(autorange="reversed", title="")
        today = pd.Timestamp(date.today())
        fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper", line=dict(color=ui.PINK, width=2, dash="dash"))
        fig.add_annotation(x=today, y=1.02, yref="paper", text="Today", showarrow=False, font=dict(color=ui.PINK))
        fig.update_layout(title="12-month roadmap", height=480, xaxis=dict(showgrid=True, gridcolor="#F3F4F6"))
        ui.plot(fig, key="pi_gantt")
    sp = D.load("scale_paths.csv")
    if not sp.empty:
        st.markdown("### Scale path for each innovation")
        st.dataframe(sp.rename(columns={"innovation": "Innovation", "pilot": "① Pilot", "region": "② Region",
                                        "pan_india": "③ Pan-India", "owner": "Owner", "metric": "Success metric"}),
                     hide_index=True, width="stretch")


def tab_deliverables() -> None:
    dl = D.load("deliverables.csv")
    if dl.empty:
        return
    closed = dl["status"].isin(["Delivered", "Handed over", "In use"]).sum()
    pct = closed / len(dl) * 100
    c1, c2 = st.columns([2, 1])
    with c1:
        rows = "".join(
            f"<tr><td style='padding:8px 6px'><b>{esc(r['deliverable'])}</b></td>"
            f"<td>{chip(esc(r['status']), DELIV_COLOURS.get(r['status'], 'grey'))}</td>"
            f"<td style='color:{ui.MUTED}'>{esc(r['owner_after_handover'])}</td>"
            f"<td style='color:{ui.MUTED}'>{esc(D.text(r.get('date')))}</td></tr>" for _, r in dl.iterrows())
        st.markdown(f"<div class='icard'><table style='width:100%;border-collapse:collapse'><tr style='text-align:left;color:{ui.PURPLE}'>"
                    f"<th>Deliverable</th><th>Status</th><th>Owner after handover</th><th>Date</th></tr>{rows}</table></div>",
                    unsafe_allow_html=True)
    with c2:
        fig = go.Figure(go.Pie(values=[closed, len(dl) - closed], labels=["Closed", "Open"], hole=0.74, sort=False,
                               marker=dict(colors=[ui.GREEN, "#EEEAFB"]), textinfo="none"))
        fig.update_layout(title="Deliverables closed", height=320, showlegend=False,
                          annotations=[dict(text=f"<b>{pct:.0f}%</b><br>{closed}/{len(dl)} closed", showarrow=False,
                                            font=dict(size=20, color=ui.DEEP))])
        ui.plot(fig, key="pi_ring")
    sh = D.load("stakeholders.csv")
    if not sh.empty:
        st.markdown("### Stakeholder alignment")
        cols = st.columns(3)
        for i, (_, r) in enumerate(sh.iterrows()):
            cols[i % 3].markdown(f"<div class='icard mint'><h4>✅ {esc(r['stakeholder'])}</h4><p style='margin:0;color:{ui.MUTED};font-size:13px'>"
                                 f"{esc(r['role'])}</p><p style='margin:6px 0 0 0'>{esc(r['agreed_to'])}</p></div>",
                                 unsafe_allow_html=True)


# -------------------------------------------------------------------------------------------
ui.hero("Project Insights", title="The research behind Prime System Builder",
        subtitle="Market, competitors, field insights, product priorities and roadmap")
with st.sidebar:
    st.markdown("<div class='icard lav'><h4>Project Insights</h4><p style='margin:0;font-size:14px'>Values come from CSV files "
                "in /data. Items marked <span class='sample'>SAMPLE</span> are illustrative.</p></div>", unsafe_allow_html=True)
    if st.button("Back to System Builder", key="pi_back", icon=":material/construction:", width="stretch"):
        st.switch_page("app_pages/system_builder.py")
t = st.tabs(["📈 Market", "🥊 Competitors", "🗣️ Field Insights", "🎯 Product Priority", "🚀 GTM & Roadmap", "✅ Deliverables & Closure"])
with t[0]:
    tab_market()
with t[1]:
    tab_competitors()
with t[2]:
    tab_field()
with t[3]:
    tab_priority()
with t[4]:
    tab_gtm()
with t[5]:
    tab_deliverables()
