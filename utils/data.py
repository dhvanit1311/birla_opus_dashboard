"""Cached CSV loaders with schema validation.

Every loader returns a DataFrame (possibly empty) and never raises. If a file is
missing or a required column is absent, a st.warning names the file and the
expected columns, and the app keeps running.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Required columns per file. Extra columns are allowed.
SCHEMAS: dict[str, list[str]] = {
    "personas.csv": ["persona", "icon", "description", "priority_sections", "default_tab", "welcome_line"],
    "segments.csv": ["segment", "icon", "description", "modifier_type", "modifier_notes"],
    "surfaces.csv": ["surface", "icon", "description", "needs_pressure", "needs_crack_check"],
    "products.csv": ["code", "name", "technology", "description", "surfaces", "coverage_sqft_per_unit", "unit",
                     "pack_size", "coats", "price_per_pack", "warranty_yrs", "elongation_pct", "dry_time_hr",
                     "recoat_time_hr", "full_cure_days", "standards", "colour_hex", "is_sample"],
    "generic_items.csv": ["item", "description", "unit", "coverage_sqft_per_unit", "pack_size", "price_per_pack",
                          "colour_hex", "is_sample"],
    "systems.csv": ["system_id", "surface", "tier", "condition", "pressure", "system_name", "layer_order",
                    "layer_name", "product_code_or_generic", "thickness_mm", "coats", "why_1", "why_2", "why_3",
                    "app_days", "is_sample"],
    "method_steps.csv": ["surface", "technology", "step_no", "stage", "instruction", "hold_time", "qa_check"],
    "dos_donts.csv": ["technology", "type", "text"],
    "spec_templates.csv": ["template_type", "text_with_placeholders"],
    "sample_projects.csv": ["project", "city", "lat", "lon", "segment", "surface", "system_id", "area_sqft",
                            "year", "is_sample"],
    "learning_events.csv": ["date", "city", "type", "audience", "seats_left"],
    "sales_team.csv": ["region", "title", "cities_covered", "phone_sample", "email_sample"],
    "faqs.csv": ["question", "answer"],
    "market.csv": ["metric", "value", "unit", "label", "is_sample"],
    "segments_market.csv": ["parent", "segment", "value_cr", "is_sample"],
    "brands.csv": ["brand", "reach", "credibility", "group", "size", "is_sample"],
    "competitor_products.csv": ["brand", "product", "technology", "application", "elongation_pct", "warranty_yrs",
                                "price_sqft", "standards", "is_sample"],
    "touchpoints.csv": ["stakeholder_type", "name", "city", "lat", "lon", "key_insight"],
    "insight_links.csv": ["source", "target", "value"],
    "quotes.csv": ["quote", "stakeholder", "city"],
    "priority_products.csv": ["product", "code", "market_size", "growth", "gap_vs_drfixit", "rd_feasibility",
                              "margin", "brand_fit", "make_or_buy", "vendors_qualified", "launch_quarter", "status"],
    "roadmap.csv": ["task", "workstream", "start", "end", "status"],
    "scale_paths.csv": ["innovation", "pilot", "region", "pan_india", "owner", "metric"],
    "deliverables.csv": ["deliverable", "status", "owner_after_handover"],
    "stakeholders.csv": ["stakeholder", "role", "agreed_to"],
}


@st.cache_data(show_spinner=False)
def _read_csv(name: str, mtime: float = 0.0) -> tuple[pd.DataFrame, str | None]:
    """Read a CSV; return (df, problem message or None). Cached per file modification time."""
    path = DATA_DIR / name
    expected = SCHEMAS.get(name, [])
    if not path.exists():
        return pd.DataFrame(columns=expected), f"Data file `data/{name}` is missing. Expected columns: {', '.join(expected)}"
    try:
        df = pd.read_csv(path, encoding="utf-8", keep_default_na=True)
    except Exception as exc:  # noqa: BLE001 – never crash on bad data
        return pd.DataFrame(columns=expected), f"Could not read `data/{name}` ({exc}). Expected columns: {', '.join(expected)}"
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        for c in missing:
            df[c] = pd.NA
        return df, (f"`data/{name}` is missing column(s): {', '.join(missing)}. "
                    f"Expected columns: {', '.join(expected)}")
    return df, None


def load(name: str) -> pd.DataFrame:
    """Public loader: returns a copy and shows a warning if the file has problems."""
    path = DATA_DIR / name
    mtime = path.stat().st_mtime if path.exists() else -1.0
    df, problem = _read_csv(name, mtime)
    if problem:
        shown = st.session_state.setdefault("_data_warnings_shown", set())
        if name not in shown:  # one warning per file per run (reset in app.py)
            shown.add(name)
            st.warning(problem, icon=":material/warning:")
    return df.copy()


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value, default: float = 0.0) -> float:
    try:
        f = float(value)
        if pd.isna(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def text(value, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return s if s else default


def split_pipes(value) -> list[str]:
    return [p.strip() for p in text(value).split("|") if p.strip()]


# Convenience accessors -------------------------------------------------------

def personas() -> pd.DataFrame:
    return load("personas.csv")


def segments() -> pd.DataFrame:
    return load("segments.csv")


def surfaces() -> pd.DataFrame:
    return load("surfaces.csv")


def products() -> pd.DataFrame:
    return load("products.csv")


def generic_items() -> pd.DataFrame:
    return load("generic_items.csv")


def systems() -> pd.DataFrame:
    df = load("systems.csv")
    if not df.empty:
        df["layer_order"] = pd.to_numeric(df["layer_order"], errors="coerce").fillna(0)
    return df


def market_value(metric: str, default: float = 0.0) -> float:
    df = load("market.csv")
    row = df[df["metric"] == metric]
    return num(row["value"].iloc[0], default) if not row.empty else default


def row_dict(df: pd.DataFrame, column: str, value) -> dict:
    """First row where column == value, as a dict ({} if none)."""
    if df.empty or column not in df.columns:
        return {}
    hit = df[df[column] == value]
    return hit.iloc[0].to_dict() if not hit.empty else {}
