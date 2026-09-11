"""Turning slider positions into a driver path, and the analyst's overlay into
a level.

Tobin's Q is a ratio — house prices over construction costs. The pilot uses
that definition directly, which is what lets a house-price slider and a cost
slider both move the model:

    Q_new = Q_base × (price level factor) ÷ (cost level factor)

A slider sets the value for 2026. Changing a growth rate in 2026 shifts the
price or cost LEVEL from 2026Q1 onward by a constant proportion, and that shift
carries through 2027 and 2028 — so the delta is applied to every forecast
quarter, not just to 2026. That is stated in the interface rather than left for
the analyst to infer.

The mortgage rate enters the model directly, so its slider is a level shift on
the rate path itself.

Three lines come out of here, and they are kept apart on purpose:

    baseline    the agent's own proposal, untouched
    model       the model under the analyst's approved drivers (gate 1)
    forecast    the model with the analyst's overlay applied (gate 1b)

Where no overlay is set, `model` and `forecast` are identical. Where one is,
the difference between them is exactly the analyst's judgement — which is why
they are never collapsed into one series.

History is never touched. The analyst is adjusting the forecast.
"""

import pandas as pd

from .data import DRIVERS, FORECAST_FROM, RATE
from .model import decompose, get_fit, predict
from .panel import BY_KEY
from . import overlay as ov


def agents() -> dict:
    return {k: d.agent for k, d in BY_KEY.items()}


def _factors(overrides: dict):
    """Price and cost level factors relative to the agent's path."""
    a = agents()
    hpi = overrides.get("hpi", a["hpi"])
    cost = overrides.get("cost", a["cost"])
    price_factor = (1.0 + hpi / 100.0) / (1.0 + a["hpi"] / 100.0)
    cost_factor = (1.0 + cost / 100.0) / (1.0 + a["cost"] / 100.0)
    return price_factor, cost_factor


def driver_paths(segment: str, overrides: dict, spec=None):
    """Baseline and adjusted (Tobin's Q, rate) over the whole sample."""
    f = get_fit(segment, spec)
    tq_base = DRIVERS[f.tobins_q_name].dropna()
    rate_base = DRIVERS[RATE].dropna()

    a = agents()
    price_factor, cost_factor = _factors(overrides)
    rate_delta = overrides.get("rate", a["rate"]) - a["rate"]

    fwd = tq_base.index >= FORECAST_FROM
    tq_new = tq_base.copy()
    tq_new[fwd] = tq_base[fwd] * price_factor / cost_factor

    fwd_r = rate_base.index >= FORECAST_FROM
    rate_new = rate_base.copy()
    rate_new[fwd_r] = rate_base[fwd_r] + rate_delta

    idx = tq_base.index.intersection(rate_base.index)
    return (tq_base.loc[idx], rate_base.loc[idx],
            tq_new.loc[idx], rate_new.loc[idx])


def model_annual(segment: str, overrides: dict, spec=None) -> dict:
    """The model's annual levels under the approved drivers, with no overlay.
    Gate 1b needs these to show what it is departing from — and to store the
    model's value beside the analyst's."""
    from .data import LAST_ACTUAL

    f = get_fit(segment, spec)
    _, _, tq_n, rate_n = driver_paths(segment, overrides, spec)
    fwd = tq_n.index > LAST_ACTUAL
    p = predict(f, tq_n[fwd], rate_n[fwd])["level"]
    g = p.groupby(p.index.year).sum()
    return {int(y): round(float(v), 1) for y, v in g.items()}


def run(segment: str, overrides: dict, spec=None, lang: str = "en",
        overlay: "ov.Overlay | None" = None) -> dict:
    from .data import LAST_ACTUAL, SEGMENTS, STARTS
    from . import i18n

    lang = i18n.norm(lang)
    f = get_fit(segment, spec)
    tq_b, rate_b, tq_n, rate_n = driver_paths(segment, overrides, spec)
    fwd = tq_n.index > LAST_ACTUAL

    base = predict(f, tq_b[fwd], rate_b[fwd])          # the agent's proposal
    model = predict(f, tq_n[fwd], rate_n[fwd])         # gate 1
    factors = overlay.factors(segment) if overlay else {}
    final = ov.apply(model, factors)                   # gate 1b
    fitted = predict(f, tq_n[~fwd], rate_n[~fwd])

    actual = STARTS[segment]
    dec = decompose(f, tq_b[fwd], rate_b[fwd], tq_n[fwd], rate_n[fwd])

    def annual(s):
        g = s.groupby(s.index.year).sum()
        return {int(y): round(float(v), 1) for y, v in g.items()}

    ann_model, ann_final = annual(model["level"]), annual(final["level"])
    ann_base = annual(base["level"])

    # The overlay's effect on the whole forecast horizon, as its own row. It is
    # judgement, not cause, and the decomposition says so rather than folding
    # it into a driver's contribution.
    tot_m = sum(ann_model.values()) or 1.0
    tot_f = sum(ann_final.values())
    dec["overlay"] = {
        "effect_pct": round((tot_f / tot_m - 1.0) * 100.0, 3),
        "attributable": False,
        "years": sorted(factors),
        "note": "analyst judgement · not attributable to any driver",
    }
    dec["net_with_overlay_pct"] = round(
        ((1 + dec["net_pct"] / 100.0) * (tot_f / tot_m) - 1.0) * 100.0, 3)

    n_hist = int((~fwd).sum())
    pad = [None] * n_hist

    return {
        "segment": segment,
        "label": i18n.pick(i18n.SEGMENT_LABELS, segment, "", lang,
                           SEGMENTS[segment]["label"]),
        "unit": i18n.pick(i18n.UNITS, SEGMENTS[segment]["unit"], "", lang,
                          SEGMENTS[segment]["unit"]),
        "production": i18n.pick(i18n.PRODUCTION, segment, "", lang,
                                SEGMENTS[segment]["production"]),
        "spec": f.spec.as_dict(),
        "quarters": [str(p) for p in tq_n.index],
        "actual": [None if p not in actual.index else round(float(actual[p]), 1)
                   for p in tq_n.index],
        "fitted": [round(float(v), 1) for v in fitted["level"]] + [None] * int(fwd.sum()),
        "forecast": pad + [round(float(v), 1) for v in final["level"]],
        "model_line": pad + [round(float(v), 1) for v in model["level"]],
        "lo": pad + [round(float(v), 1) for v in final["lo"]],
        "hi": pad + [round(float(v), 1) for v in final["hi"]],
        "baseline": pad + [round(float(v), 1) for v in base["level"]],
        "annual_forecast": ann_final,
        "annual_model": ann_model,
        "annual_baseline": ann_base,
        "overlay": overlay.as_list(segment) if overlay else [],
        "has_overlay": bool(factors),
        "decomposition": dec,
        "tobins_q_2026": round(float(tq_n[tq_n.index.year == 2026].mean()), 4),
        "tobins_q_2026_agent": round(float(tq_b[tq_b.index.year == 2026].mean()), 4),
        "fit": {
            "r2": round(f.r2, 3),
            "n": f.n,
            "holdout_mape": round(f.holdout_mape, 1),
            "b_tobins_q": round(f.b_tobins_q, 4),
            "b_rate": round(f.b_rate, 4),
            "tobins_q_driver": f.tobins_q_name,
        },
    }
