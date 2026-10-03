"""Recommendation engine, BOQ maths, crack severity, method statement / spec / application content.

All business content comes from the CSVs in /data; this module only applies rules.
"""
from __future__ import annotations

import math
import zlib
from datetime import date

import pandas as pd

from utils import data as D

TIERS = ["Good", "Better", "Best"]
PREFERENCE_TO_TIER = {"Value": "Good", "Premium": "Better", "Luxury": "Best", "Show me all three": "Better"}
CONDITION_MAP = {"New": "new", "Existing – good": "existing", "Existing – damaged": "existing"}
PRESSURE_MAP = {"None": "none", "Positive side": "positive", "Negative side": "negative"}
REPAIR_LAYER = "Remove loose coating + crack treatment"
CRACK_FILLER = "Polymer crack filler (generic)"
WET_SURFACES = {"Bathroom / toilet", "Other wet areas"}
PONDING_SURFACES = {"Terrace / roof", "Podium / deck", "Bathroom / toilet", "Other wet areas"}


# Crack severity ------------------------------------------------------------------
def crack_severity(width_mm: float) -> dict:
    if width_mm <= 0:
        return {"label": "No crack", "colour": "#06AD80", "band": -1, "note": "No crack treatment needed."}
    if width_mm < 0.3:
        return {"label": "Hairline", "colour": "#06AD80", "band": 0,
                "note": "Hairline (< 0.3 mm): an extra stripe coat of the waterproofing material is enough."}
    if width_mm <= 1:
        return {"label": "Fine", "colour": "#E0A800", "band": 1,
                "note": "Fine (0.3–1 mm): open into a V-groove and fill with polymer crack filler."}
    if width_mm <= 3:
        return {"label": "Medium", "colour": "#F26625", "band": 2,
                "note": "Medium (1–3 mm): V-groove, crack filler + fibre-mesh stripe over the crack."}
    return {"label": "Structural", "colour": "#EF1F51", "band": 3,
            "note": "Structural (> 3 mm): Refer to a structural engineer before waterproofing."}


# Segment modifiers ---------------------------------------------------------------
def segment_info(segment: str | None) -> dict:
    return D.row_dict(D.segments(), "segment", segment) if segment else {}


def modifiers(segment: str | None) -> set[str]:
    return set(D.split_pipes(segment_info(segment).get("modifier_type", "")))


def default_tier(preference: str | None, segment: str | None) -> str:
    tier = PREFERENCE_TO_TIER.get(preference or "", "Better")
    if "upgrade_tier" in modifiers(segment):
        tier = TIERS[min(TIERS.index(tier) + 1, 2)]
    return tier


def effective_area(site: dict, surface: str | None) -> float:
    area = max(D.num(site.get("area"), 0.0), 0.0)
    if surface in WET_SURFACES:
        area *= max(int(D.num(site.get("floors"), 1)), 1)
    return round(area, 1)


# Layer resolution -------------------------------------------------------------------
def _fmt_num(value) -> str:
    """'4.0' -> '4', 0 / blank -> '—'."""
    v = D.num(value, 0.0)
    return f"{v:g}" if v > 0 else "—"


def _resolve_item(ref: str) -> dict:
    """Look up a Prime product code or a generic item name."""
    prod = D.row_dict(D.products(), "code", ref)
    if prod:
        return {
            "is_product": True, "code": ref, "name": D.text(prod.get("name"), ref),
            "technology": D.text(prod.get("technology"), "Other"),
            "description": D.text(prod.get("description")),
            "coverage": D.num(prod.get("coverage_sqft_per_unit"), 1.0) or 1.0,
            "unit": D.text(prod.get("unit"), "unit"), "pack_size": D.num(prod.get("pack_size"), 1.0) or 1.0,
            "price_per_pack": D.num(prod.get("price_per_pack"), 0.0),
            "warranty": D.num(prod.get("warranty_yrs"), 0.0), "elongation": D.num(prod.get("elongation_pct"), 0.0),
            "dry": _fmt_num(prod.get("dry_time_hr")), "recoat": _fmt_num(prod.get("recoat_time_hr")),
            "cure": _fmt_num(prod.get("full_cure_days")), "standards": D.split_pipes(prod.get("standards")),
            "colour": D.text(prod.get("colour_hex"), "#52489E"), "low_odour": D.as_bool(prod.get("low_odour", True)),
            "is_sample": D.as_bool(prod.get("is_sample", True)),
        }
    gen = D.row_dict(D.generic_items(), "item", ref)
    return {
        "is_product": False, "code": "Generic", "name": ref, "technology": D.text(gen.get("technology"), "Generic"),
        "description": D.text(gen.get("description"), "Generic layer item (non-branded)."),
        "coverage": D.num(gen.get("coverage_sqft_per_unit"), 1.0) or 1.0, "unit": D.text(gen.get("unit"), "sq ft"),
        "pack_size": D.num(gen.get("pack_size"), 1.0) or 1.0, "price_per_pack": D.num(gen.get("price_per_pack"), 0.0),
        "warranty": 0.0, "elongation": 0.0, "dry": "—", "recoat": "—", "cure": "—", "standards": [],
        "colour": D.text(gen.get("colour_hex"), "#CBD5E1"), "low_odour": True, "is_sample": True,
    }


def _layer(order: float, layer_name: str, ref: str, thickness: float, coats: float) -> dict:
    item = _resolve_item(ref)
    item.update({"order": order, "layer_name": layer_name, "ref": ref,
                 "thickness": thickness, "coats": max(int(coats), 1)})
    return item


# Recommendation engine -----------------------------------------------------------------
def _score_system(rows: pd.DataFrame, cond: str, press: str, exposures: list[str], mods: set[str]) -> float | None:
    first = rows.iloc[0]
    s_cond = D.text(first.get("condition"), "any").lower()
    s_press = D.text(first.get("pressure"), "any").lower()
    if s_cond not in ("any", cond):
        return None
    if s_press not in ("any", press):
        return None
    score = 0.0
    score += 2 if s_cond == cond else 0
    score += 5 if s_press == press else 0  # explicit water-pressure match outranks condition
    pref = D.text(first.get("exposure_pref", ""))
    if pref:
        score += 3 if pref in exposures else -4
    refs = [D.text(r) for r in rows["product_code_or_generic"]]
    if "prefer_hdpe" in mods and any(r.startswith("HS") for r in refs):
        score += 1
    if "low_odour" in mods:
        for r in refs:
            prod = D.row_dict(D.products(), "code", r)
            if prod and not D.as_bool(prod.get("low_odour", True)):
                score -= 1
    return score


def pick_system_id(surface: str, tier: str, site: dict, segment: str | None) -> str | None:
    sysdf = D.systems()
    if sysdf.empty:
        return None
    cand = sysdf[sysdf["surface"] == surface]
    if cand.empty:
        return None
    cond = CONDITION_MAP.get(site.get("condition", "New"), "new")
    press = PRESSURE_MAP.get(site.get("pressure", "None"), "none")
    exposures = list(site.get("exposure", []) or [])
    mods = modifiers(segment)
    # Try requested tier first, then nearest tiers.
    order = [tier] + sorted([t for t in TIERS if t != tier], key=lambda t: abs(TIERS.index(t) - TIERS.index(tier)))
    for t in order:
        best_id, best_score = None, None
        for sid, rows in cand[cand["tier"] == t].groupby("system_id", sort=False):
            sc = _score_system(rows, cond, press, exposures, mods)
            if sc is not None and (best_score is None or sc > best_score):
                best_id, best_score = sid, sc
        if best_id:
            return best_id
    return cand["system_id"].iloc[0]


def build_system(system_id: str, site: dict, surface: str, segment: str | None) -> dict:
    sysdf = D.systems()
    rows = sysdf[sysdf["system_id"] == system_id].sort_values("layer_order")
    if rows.empty:
        return {}
    first = rows.iloc[0]
    layers = [_layer(D.num(r["layer_order"]), D.text(r["layer_name"]), D.text(r["product_code_or_generic"]),
                     D.num(r["thickness_mm"]), D.num(r["coats"], 1)) for _, r in rows.iterrows()]
    mods = modifiers(segment)
    notes: list[str] = []
    refs = [l["ref"] for l in layers]
    # Repair / CHS segments (or damaged substrate): add removal + crack treatment prep layer.
    if ("repair_prep" in mods or site.get("condition") == "Existing – damaged") and REPAIR_LAYER not in refs:
        layers.insert(1 if layers and layers[0]["ref"] == "Surface preparation" else 0,
                      _layer(0.5, REPAIR_LAYER, REPAIR_LAYER, 0.0, 1))
        notes.append("Repair modifier: 'Remove loose coating + crack treatment' prep layer added.")
    # Cracks ≥ 0.3 mm on crack-check surfaces: make sure a crack filler layer exists.
    surf = D.row_dict(D.surfaces(), "surface", surface)
    width = D.num(site.get("crack_w"), 0.0)
    if D.as_bool(surf.get("needs_crack_check", False)) and width >= 0.3 and CRACK_FILLER not in [l["ref"] for l in layers]:
        pos = next((i + 1 for i, l in enumerate(layers) if not l["is_product"] and "prep" in l["technology"].lower()), 0)
        layers.insert(pos, _layer(0.6, "Crack filling", CRACK_FILLER, 1.0, 1))
        notes.append(f"Crack check ({width:.1f} mm): polymer crack filler layer added.")
    if "low_odour" in mods:
        notes.append("Low-odour, water-based products highlighted; phase work zone-by-zone for minimal downtime.")
    if "prefer_hdpe" in mods and surface in ("Basement", "Foundation / raft"):
        notes.append("New construction: pre-applied HDPE (HS series) is the default for below-grade works.")

    products = [l for l in layers if l["is_product"]]
    area = effective_area(site, surface)
    warranty = max([l["warranty"] for l in products] or [0])
    standards: list[str] = []
    for l in products:
        for s in l["standards"]:
            if s not in standards:
                standards.append(s)
    if "cpwd_spec" in mods:
        standards.append("CPWD Specs (WP section)")
    base_days = D.num(first.get("app_days"), 3)
    days = int(base_days + max(0, math.ceil(area / 2500) - 1)) if area else int(base_days)
    return {
        "system_id": system_id, "system_name": D.text(first.get("system_name"), system_id),
        "tier": D.text(first.get("tier")), "layers": layers,
        "whys": [D.text(first.get(c)) for c in ("why_1", "why_2", "why_3") if D.text(first.get(c))],
        "warranty": warranty, "standards": standards, "app_days": days, "area": area,
        "total_coats": int(sum(l["coats"] for l in products)), "n_layers": len(layers), "notes": notes,
        "elongation": max([l["elongation"] for l in products] or [0]),
        "technologies": sorted({l["technology"] for l in products}),
        "is_sample": True,
    }


def recommend(surface: str, tier: str, site: dict, segment: str | None) -> dict:
    sid = pick_system_id(surface, tier, site, segment)
    if not sid:
        return {}
    system = build_system(sid, site, surface, segment)
    if system and system["tier"] != tier:
        system["notes"].append(f"No {tier} variant configured for this surface – showing the nearest tier ({system['tier']}).")
    system["why_tailored"] = tailored_whys(system, surface, segment, site)
    return system


def tailored_whys(system: dict, surface: str, segment: str | None, site: dict) -> list[str]:
    whys = list(system.get("whys", []))[:3]
    exposures = site.get("exposure", []) or []
    extra = []
    if "Direct sun/UV" in exposures and any(l["code"] == "B90" for l in system["layers"]):
        extra.append("Strong sun on site – B90's cool-roof finish cuts surface heat and thermal cracking.")
    if "Ponding water" in exposures and surface in PONDING_SURFACES:
        extra.append("Ponding water expected – the system is verified with a 48-hour ponding test before handover.")
    if "Vehicle traffic" in exposures:
        extra.append("Vehicle traffic – a protection screed / wearing course is essential over the waterproofing.")
    mods = modifiers(segment)
    if "low_odour" in mods:
        extra.append("Low-odour, water-based choice suits occupied hospitals and schools.")
    if "repair_prep" in mods:
        extra.append("Old failed layers are removed first so the new system bonds to sound substrate.")
    # Replace the last generic reason(s) with tailored ones, keep 3 bullets.
    out = whys[: max(3 - len(extra), 1)] + extra
    return out[:3]


def tier_comparison(surface: str, site: dict, segment: str | None) -> pd.DataFrame:
    rows = []
    for t in TIERS:
        s = recommend(surface, t, site, segment)
        if not s:
            continue
        boq = boq_table(s, s["area"] or 1000, 10)
        tot = totals(boq, 0, s["area"] or 1000)
        rows.append({"Tier": t, "System": s["system_name"], "Warranty (yrs)": int(s["warranty"]),
                     "₹/sq ft (sample)": round(tot["per_sqft"], 1),
                     "Max elongation %": int(s["elongation"]) if s["elongation"] else "—",
                     "Best for": s["whys"][0] if s["whys"] else ""})
    return pd.DataFrame(rows)


# BOQ ------------------------------------------------------------------------------
BOQ_COLUMNS = ["Item", "Product code", "Coverage (sq ft/unit)", "Unit", "Coats", "Area (sq ft)", "Wastage %",
               "Quantity", "Pack size", "Packs needed", "Rate per pack (₹)", "Amount (₹)"]


def boq_table(system: dict, area: float, wastage: float = 10.0) -> pd.DataFrame:
    rows = []
    for l in system.get("layers", []):
        rows.append({
            "Item": l["layer_name"] + ("" if l["is_product"] else " (generic)"),
            "Product code": l["code"] if l["is_product"] else "Generic",
            "Coverage (sq ft/unit)": float(l["coverage"]), "Unit": l["unit"], "Coats": int(l["coats"]),
            "Area (sq ft)": float(area), "Wastage %": float(wastage), "Quantity": 0.0,
            "Pack size": float(l["pack_size"]), "Packs needed": 0, "Rate per pack (₹)": float(l["price_per_pack"]),
            "Amount (₹)": 0.0,
        })
    return recompute_boq(pd.DataFrame(rows, columns=BOQ_COLUMNS))


def recompute_boq(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    for c in ["Coverage (sq ft/unit)", "Coats", "Area (sq ft)", "Wastage %", "Pack size", "Rate per pack (₹)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    cov = df["Coverage (sq ft/unit)"].where(df["Coverage (sq ft/unit)"] > 0, 1)
    pack = df["Pack size"].where(df["Pack size"] > 0, 1)
    df["Quantity"] = (df["Area (sq ft)"] * df["Coats"] / cov * (1 + df["Wastage %"] / 100)).round(2)
    df["Packs needed"] = [int(math.ceil(q / p - 1e-9)) if q > 0 else 0 for q, p in zip(df["Quantity"], pack)]
    df["Amount (₹)"] = (df["Packs needed"] * df["Rate per pack (₹)"]).round(0)
    return df


def totals(df: pd.DataFrame, labour_rate: float, area: float) -> dict:
    material = float(df["Amount (₹)"].sum()) if not df.empty else 0.0
    labour = float(labour_rate) * float(area)
    grand = material + labour
    return {"material": material, "labour": labour, "grand": grand, "per_sqft": grand / area if area else 0.0}


def inr(x: float) -> str:
    """Indian-style grouping: 12,34,567."""
    x = round(float(x))
    neg, s = x < 0, str(abs(int(x)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + s


# Method statement ---------------------------------------------------------------------
def _stage_rows(steps: pd.DataFrame, stage: str, surface: str, techs: set[str]) -> list[dict]:
    if steps.empty:
        return []
    s = steps[steps["stage"] == stage]
    s = s[s["technology"].isin(techs | {"All"})]
    general = s[s["surface"] == "All"]
    specific = s[s["surface"] == surface] if surface != "All" else s.iloc[0:0]
    # Surface-specific rows replace generic rows of the same stage (e.g. Testing); otherwise add to them.
    if stage == "Testing":
        chosen = specific if not specific.empty else general
    else:
        chosen = pd.concat([general, specific])
    chosen = chosen.sort_values("step_no", kind="stable")
    return [{"text": D.text(r["instruction"]), "hold": D.text(r["hold_time"]), "qa": D.text(r["qa_check"])}
            for _, r in chosen.iterrows()]


def method_statement(system: dict, ctx: dict) -> list[dict]:
    """Return ordered sections: {title, items:[{text, hold, qa}]}."""
    steps = D.load("method_steps.csv")
    surface = ctx.get("surface", "")
    site = ctx.get("site", {})
    techs = set(system.get("technologies", []))
    layers = system.get("layers", [])
    sections: list[dict] = []

    def add(title, items):
        if items:
            sections.append({"title": title, "items": items})

    add("Scope", [{"text": f"Waterproofing of {surface.lower()} – {system['system_name']} for a "
                           f"{ctx.get('segment', 'project')} project, approx. {system['area']:,.0f} sq ft "
                           f"on {site.get('substrate', 'RCC')} substrate ({site.get('condition', 'New')}).", "hold": "", "qa": ""},
                  {"text": f"City: {site.get('city') or '—'} · Climate: {site.get('climate', '—')} · "
                           f"Exposure: {', '.join(site.get('exposure', []) or ['—'])}.", "hold": "", "qa": ""}])
    add("Materials", [{"text": f"{l['layer_name']}: {l['name']}" + (f" ({l['code']})" if l["is_product"] else "")
                               + f" – {l['coats']} coat(s)" + (" [SAMPLE data]" if l["is_product"] else ""),
                       "hold": "", "qa": ""} for l in layers])
    add("Tools & equipment", _stage_rows(steps, "Tools & equipment", surface, techs))
    add("Safety & PPE", _stage_rows(steps, "Safety & PPE", surface, techs))
    add("Surface preparation", _stage_rows(steps, "Surface preparation", surface, techs))
    has_crack = any(l["ref"] in (CRACK_FILLER, REPAIR_LAYER) for l in layers) or D.num(site.get("crack_w")) > 0
    if has_crack:
        sev = crack_severity(D.num(site.get("crack_w")))
        items = _stage_rows(steps, "Crack treatment", surface, techs)
        items.insert(0, {"text": f"Site crack check: {D.num(site.get('crack_w')):.1f} mm wide, "
                                 f"{D.num(site.get('crack_d')):.0f} mm deep – {sev['label']}. {sev['note']}",
                         "hold": "", "qa": "Crack severity recorded"})
        add("Crack treatment", items)
    add("Primer", [i for i in _stage_rows(steps, "Primer", surface, techs) if not i["text"].startswith("No ")]
        or [{"text": "No separate primer required for this system.", "hold": "", "qa": ""}])
    app_items = _stage_rows(steps, "Application", surface, techs)
    for l in layers:
        if not l["is_product"]:
            continue
        cov = f"{l['coverage']:g} sq ft/{l['unit']} per coat"
        for c in range(1, l["coats"] + 1):
            app_items.append({"text": f"{l['layer_name']} – {l['code']} coat {c}: apply at ~{cov} (sample).",
                              "hold": f"Recoat {l['recoat']} h" if l["recoat"] != "—" else "",
                              "qa": f"{l['code']} coat {c} complete, uniform, no pinholes"})
    add("Application", app_items)
    add("Detailing – corners, upstands & drains", _stage_rows(steps, "Detailing", surface, techs))
    add("Curing", _stage_rows(steps, "Curing", surface, techs))
    add("Testing", _stage_rows(steps, "Testing", surface, techs))
    protections = [l for l in layers if l["technology"] in ("Protection", "Finish")]
    if protections:
        items = _stage_rows(steps, "Protection", surface, techs)
        items += [{"text": f"{p['layer_name']}: {p['description']}", "hold": "", "qa": ""} for p in protections]
        add("Protection layer", items)
    qa = [{"text": i["qa"], "hold": "", "qa": i["qa"]} for s in sections for i in s["items"] if i.get("qa")]
    seen, qa_unique = set(), []
    for q in qa:
        if q["text"] not in seen:
            seen.add(q["text"])
            qa_unique.append(q)
    add("QA checklist", qa_unique)
    add("Handover", _stage_rows(steps, "Handover", surface, techs))
    return sections


# Spec / tender text ----------------------------------------------------------------------
def spec_text(system: dict, ctx: dict) -> str:
    tpl = D.load("spec_templates.csv")
    mods = modifiers(ctx.get("segment"))
    surface = ctx.get("surface", "")
    layers = system.get("layers", [])
    layer_lines = "\n".join(
        f"  {i}. {l['layer_name']} – {l['name']}" + (f" ({l['code']}), {l['coats']} coat(s) @ ~{l['coverage']:g} sq ft/{l['unit']}/coat"
                                                        if l["is_product"] else " (generic)")
        for i, l in enumerate(layers, 1))
    inline = "; ".join(f"{l['layer_name'].lower()} ({l['code']})" if l["is_product"] else l["layer_name"].lower() for l in layers)
    coverage = "; ".join(f"{l['code']}: ~{l['coverage']:g} sq ft/{l['unit']}/coat × {l['coats']}" for l in layers if l["is_product"])
    testing = ("48-hour flood / ponding test, signed by the Engineer-in-Charge." if surface in PONDING_SURFACES
               else "Visual inspection and adhesion check; water test where applicable.")
    values = {
        "surface": surface, "surface_upper": surface.upper(), "system_name": system.get("system_name", ""),
        "segment": ctx.get("segment", ""), "area": f"{system.get('area', 0):,.0f}",
        "area_sqm": f"{system.get('area', 0) * 0.092903:,.0f}", "layers": layer_lines, "layers_inline": inline,
        "coverage": coverage + " (sample values)", "standards": ", ".join(system.get("standards", [])) or "—",
        "warranty": f"{system.get('warranty', 0):g}", "testing": testing, "tier": system.get("tier", ""),
        "item_no": f"{zlib.crc32(system.get('system_id', '').encode()) % 900 + 100}",
    }

    def fill(kind: str) -> str:
        row = tpl[tpl["template_type"] == kind] if not tpl.empty else tpl
        if row is None or row.empty:
            return ""
        raw = D.text(row["text_with_placeholders"].iloc[0])
        try:
            return raw.format(**values)
        except (KeyError, IndexError, ValueError):
            return raw

    out = fill("standard")
    if "cpwd_spec" in mods:
        out += "\n\n" + "=" * 60 + "\n\n" + fill("cpwd")
    out += f"\n\n[Prototype – illustrative specification generated {date.today():%d %b %Y}. Values are SAMPLE.]"
    return out


# Application steps (contractor) -------------------------------------------------------------
def application_steps(system: dict, ctx: dict) -> list[dict]:
    surface = ctx.get("surface", "")
    layers = system.get("layers", [])
    steps = [{"icon": "🧹", "title": "Prepare the surface", "line": "Clean, grind loose material, form coving at corners."}]
    if any(l["ref"] == REPAIR_LAYER for l in layers):
        steps.append({"icon": "🪓", "title": "Remove old coating", "line": "Scrape off failed layers back to sound substrate."})
    if any(l["ref"] == CRACK_FILLER for l in layers):
        steps.append({"icon": "🩹", "title": "Treat cracks", "line": "V-groove and fill cracks; stripe-coat hairlines."})
    for l in layers:
        if l["is_product"] and l["code"] == "APS1":
            steps.append({"icon": "🖌️", "title": "Prime", "line": "Roll APS1 primer; wait till touch-dry (1–2 h)."})
    if any(l["ref"] == "Fibre mesh (generic)" for l in layers):
        steps.append({"icon": "🧵", "title": "Detail junctions", "line": "Embed fibre mesh at corners, upstands and outlets."})
    seen = set()
    for l in layers:
        if l["is_product"] and l["code"] not in ("APS1",) and l["code"] not in seen:
            seen.add(l["code"])
            total = sum(x["coats"] for x in layers if x["code"] == l["code"])
            verb = "Lay" if l["unit"] == "roll" else "Apply"
            steps.append({"icon": "🧴" if l["unit"] != "roll" else "📜", "title": f"{verb} {l['code']}",
                          "line": f"{total} coat(s)/layer @ ~{l['coverage']:g} sq ft/{l['unit']}"
                                  + (f"; recoat {l['recoat']} h." if l["recoat"] != "—" else ".")})
    steps.append({"icon": "💧", "title": "Cure", "line": "Follow curing time – protect from rain and traffic."})
    if surface in PONDING_SURFACES:
        steps.append({"icon": "🧪", "title": "Ponding test", "line": "Hold water 48 h; check below for damp."})
    else:
        steps.append({"icon": "🔍", "title": "Inspect", "line": "Check laps, adhesion and terminations; take photos."})
    if any(l["technology"] in ("Protection", "Finish") for l in layers):
        steps.append({"icon": "🛡️", "title": "Protect & finish", "line": "Place screed / board / tiles without puncturing."})
    return steps[:8]


def tools_list(system: dict) -> list[str]:
    steps = D.load("method_steps.csv")
    techs = set(system.get("technologies", []))
    return [r["text"] for r in _stage_rows(steps, "Tools & equipment", "All", techs)]


def dos_donts(system: dict) -> tuple[list[str], list[str]]:
    df = D.load("dos_donts.csv")
    if df.empty:
        return [], []
    techs = set(system.get("technologies", [])) | {"All"}
    df = df[df["technology"].isin(techs)]
    return list(df[df["type"] == "Do"]["text"]), list(df[df["type"] == "Don't"]["text"])


def reference_id() -> str:
    import random
    return f"PRM-{date.today().year}-{random.randint(10000, 99999):05d}"
