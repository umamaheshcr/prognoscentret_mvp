"""Carl's research bundle — 38 market drivers with their sources.

Extracted from `Mimir-demo.html` (generated 2026-08-15) into `data/bundle/`.
This is the substrate the driver-verification page runs on, and it is a far
richer thing than the four hand-written drivers the pilot started with:

    38 drivers in five groups · 22 institutions
    per driver, per forecast year: a central estimate, a p10–p90 consensus
    band, a slider range, a quality grade, and every claim behind it
    per claim: institution, tier, value, weight, publication date and age,
    report title, report URL, page, table reference, and the verbatim quote

**The unit trap, and why it matters.** The research layer and the forecast
engine do not speak the same units. Carl's bundle states Tobin's Q, construction
costs, office employment and trade volume as **year-on-year fractions** — Tobin's
Q for flats in 2026 is `0.114341`, meaning +11.4 per cent. The engine's
`master_exogenous.xlsx` holds the same series as **levels** — 1.1916. Feeding a
fraction where a level belongs would not error; it would silently produce a
forecast off by two orders of magnitude. So the conversion is explicit here,
declared per driver, and tested.

**Two vintages, deliberately kept apart.** The bundle was generated 15 August
2026; the engine snapshot is 9 September. They disagree, and the disagreement is
informative rather than a defect — the unsourced 2028 mortgage-rate fall this
project flagged earlier appeared *between* the two: August has 2.526, September
has 2.420. The bundle is never silently substituted for the snapshot; a driver
value reaches the engine only when an analyst approves it at the gate.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent / "data" / "bundle"

# Group ids in the bundle are Danish. Presentation order follows Carl's design.
GROUPS = [
    ("makro", {"en": "Macro", "sv": "Makro"}),
    ("renter", {"en": "Interest rates", "sv": "Räntor"}),
    ("boligmarked", {"en": "Housing market", "sv": "Bostadsmarknad"}),
    ("byggeomkostninger", {"en": "Construction costs", "sv": "Byggkostnader"}),
    ("erhverv", {"en": "Business", "sv": "Näringsliv"}),
]

# engine_id → the column it is actually called in master_exogenous.xlsx.
#
# The bundle writes `Tobins_Q_Flats`; the spreadsheet writes `Tobins-Q (Flats)`.
# Neither is wrong and no rule converts one into the other — underscores against
# spaces, a hyphen against parentheses, `Trade_volume` against `Exported and
# import good (volume)`. This is the naming trap the earlier review flagged, in
# its concrete form, and the only safe response is to write the mapping out and
# assert it at import.
ENGINE_COLUMN = {
    "Real_Interest_rate_Mortgage": "Real Interest rate (Mortgage)",
    "Tobins_Q_Detached_houses": "Tobins-Q (Detached houses)",
    "Tobins_Q_Flats": "Tobins-Q (Flats)",
    "Tobins_Q_Holiday_homes": "Tobins-Q (Holiday homes)",
    "Construction_costs": "Construction costs",
    "Business_cycle_Industry_survey": "Business cycle Industry (survey)",
    "Consumer_confidence_indicator_CCI": "Consumer confidence indicator (CCI)",
    "Retail_sales_index_volume": "Retail sales index (volume)",
    "Kontorbeskaeftigelse": "Kontorbeskaeftigelse",
    "Trade_volume": "Exported and import good (volume)",
}

# How a research driver's value converts to the engine's units.
#   "level"   the bundle already states what the engine wants
#   "yoy"     the bundle states a year-on-year fraction; compound it onto the
#             last actual level from the engine's own history
ENGINE_UNITS = {
    "Real_Interest_rate_Mortgage": "level",
    "Consumer_confidence_indicator_CCI": "level",
    "Business_cycle_Industry_survey": "level",
    "Retail_sales_index_volume": "level",
    "Tobins_Q_Flats": "yoy",
    "Tobins_Q_Detached_houses": "yoy",
    "Tobins_Q_Holiday_homes": "yoy",
    "Construction_costs": "yoy",
    "Kontorbeskaeftigelse": "yoy",
    "Trade_volume": "yoy",
}


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    return json.loads((BUNDLE / name).read_text(encoding="utf-8"))


def available() -> bool:
    return (BUNDLE / "research.json").exists()


@lru_cache(maxsize=1)
def manifest() -> dict:
    return _load("manifest.json")


def _rows(container):
    return list(container.values()) if isinstance(container, dict) else list(container)


@lru_cache(maxsize=1)
def drivers() -> list:
    """All 38, ordered by group then by the bundle's own `order`."""
    rows = _rows(_load("research.json")["drivers"])
    gi = {g: i for i, (g, _) in enumerate(GROUPS)}
    rows.sort(key=lambda d: (gi.get(d.get("group"), 99), d.get("order") or 0))
    return rows


@lru_cache(maxsize=1)
def by_id() -> dict:
    return {d["id"]: d for d in drivers()}


@lru_cache(maxsize=1)
def institutions() -> dict:
    rows = _rows(_load("research.json")["institutions"])
    out = {}
    for i in rows:
        key = i.get("id") or i.get("source_id") or i.get("name")
        if key:
            out[key] = i
    return out


def years_of(d: dict) -> list:
    ys = d.get("years") or {}
    rows = _rows(ys)
    rows.sort(key=lambda y: y.get("year", 0))
    return rows


def forecast_years() -> list:
    for d in drivers():
        ys = [y["year"] for y in years_of(d)]
        if ys:
            return ys
    return []


def engine_drivers() -> dict:
    """engine_id → the research driver that carries it. Ten of the 38."""
    return {d["engine_id"]: d for d in drivers() if d.get("engine_id")}


def to_engine_value(engine_id: str, research_value: float,
                    prev_level: float | None) -> float | None:
    """Convert a research value into the engine's units.

    A year-on-year fraction needs the previous level to compound onto, so this
    returns None rather than guessing when that is missing — a silently wrong
    level is worse than a visibly absent one.
    """
    kind = ENGINE_UNITS.get(engine_id, "level")
    if kind == "level":
        return float(research_value)
    if prev_level is None:
        return None
    return float(prev_level) * (1.0 + float(research_value))


# ── what the verification page needs ───────────────────────────────────────
def group_summary(lang: str = "en") -> list:
    out = []
    for gid, names in GROUPS:
        members = [d for d in drivers() if d.get("group") == gid]
        out.append({"id": gid, "label": names.get(lang, names["en"]),
                    "n": len(members),
                    "driver_ids": [d["id"] for d in members]})
    return out


def provenance(d: dict) -> str:
    """What stands behind the driver, in Carl's terms: how many sources, or
    that it is derived from other drivers, or that only the agent estimated it."""
    if d.get("derived_from"):
        return "derived"
    ys = years_of(d)
    counts = [y.get("n_sources") or 0 for y in ys]
    n = max(counts) if counts else 0
    if n == 0:
        return "agent"
    return f"{n} source" + ("s" if n != 1 else "")


def driver_card(driver_id: str) -> dict:
    """One driver, everything the verification page shows — and nothing about
    the forecast. The forecast lives on its own step, by request."""
    d = by_id().get(driver_id)
    if d is None:
        return {}
    inst = institutions()

    years = []
    for y in years_of(d):
        claims = []
        for c in y.get("claims") or []:
            meta = inst.get(c.get("source_id"), {})
            claims.append({
                "source_id": c.get("source_id"),
                "source_name": c.get("source_name") or meta.get("name"),
                "tier": c.get("tier"),
                "value": c.get("value"),
                "weight": c.get("weight"),
                "published_at": c.get("published_at"),
                "age_days": c.get("age_days"),
                "report_title": c.get("report_title"),
                "report_url": c.get("report_url") or None,
                "page": c.get("page"),
                "table_ref": c.get("table_ref"),
                "quote": c.get("quote"),
                "extraction": c.get("extraction"),
                "printed": c.get("printed"),
                "definition_src": c.get("definition_src"),
                "excluded": c.get("excluded"),
                "excluded_reason": c.get("excluded_reason"),
                "dissent": c.get("dissent"),
            })
        claims.sort(key=lambda c: -(c.get("weight") or 0))
        years.append({
            "year": y.get("year"),
            "central": y.get("central"),
            "p10": y.get("p10"),
            "p90": y.get("p90"),
            "low": y.get("low"),
            "high": y.get("high"),
            "slider": y.get("slider") or {},
            "n_sources": y.get("n_sources"),
            "coverage": y.get("coverage"),
            "coverage_note": y.get("coverage_note"),
            "quality_grade": y.get("quality_grade"),
            "quality_label": y.get("quality_label"),
            "quality_reason": y.get("quality_reason"),
            "method": y.get("method"),
            "method_note": y.get("method_note"),
            "dispersion": y.get("dispersion"),
            "claims": claims,
        })

    return {
        "id": d["id"],
        "label": d.get("label"),
        "unit": d.get("unit"),
        "unit_kind": d.get("unit_kind"),
        "definition": d.get("definition"),
        "layer": d.get("layer"),
        "group": d.get("group"),
        "engine_id": d.get("engine_id"),
        "engine_units": ENGINE_UNITS.get(d.get("engine_id") or "", None),
        "engine_column": ENGINE_COLUMN.get(d.get("engine_id") or ""),
        "in_model": bool(d.get("engine_id")),
        "last_actual": d.get("last_actual") or {},
        "derived_from": d.get("derived_from") or [],
        "used_by_segments": d.get("used_by_segments") or [],
        "cited_in_sections": d.get("cited_in_sections") or [],
        "provenance": provenance(d),
        "years": years,
    }


def index(lang: str = "en") -> dict:
    """The left-hand list: every driver with just enough to render a row."""
    return {
        "country": manifest().get("country"),
        "generated_at": manifest().get("generated_at"),
        "history_last": manifest().get("history_last"),
        "forecast_from": manifest().get("forecast_from"),
        "forecast_years": forecast_years(),
        "n_drivers": len(drivers()),
        "n_institutions": len(institutions()),
        "groups": group_summary(lang),
        "drivers": [{
            "id": d["id"],
            "label": d.get("label"),
            "unit": d.get("unit"),
            "group": d.get("group"),
            "layer": d.get("layer"),
            "provenance": provenance(d),
            "in_model": bool(d.get("engine_id")),
            "engine_id": d.get("engine_id"),
            "engine_column": ENGINE_COLUMN.get(d.get("engine_id") or ""),
        } for d in drivers()],
    }


def engine_column(engine_id: str) -> str | None:
    return ENGINE_COLUMN.get(engine_id)


def check_engine_map() -> list:
    """Every mapped column must exist in the snapshot, and every engine driver
    must be mapped. Called by the tests; a rename upstream should fail loudly
    rather than quietly drop a driver out of the model."""
    from .data import DRIVERS
    problems = []
    for eid in engine_drivers():
        col = ENGINE_COLUMN.get(eid)
        if col is None:
            problems.append(f"{eid}: no column mapped")
        elif col not in DRIVERS.columns:
            problems.append(f"{eid}: mapped to '{col}', which is not in the snapshot")
        if eid not in ENGINE_UNITS:
            problems.append(f"{eid}: no unit kind declared")
    return problems
