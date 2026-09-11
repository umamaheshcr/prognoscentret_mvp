"""Apply the declared fixes to the pilot's copy of the exogenous master file.

    python tools/fix_master.py            write data/master_exogenous_fixed.xlsx
    python tools/fix_master.py --report   say what would change, write nothing

**The upstream file is never modified.** `data/master_exogenous.xlsx` stays
exactly as it came from `forecasting-models@4c72e0f`; the fixes are written to a
separate file, and `app/data.py` reports which of the two it loaded. So the fix
is reproducible, auditable and reversible by deleting one file.

Two fixes, and only two. Both correct a *construction* — a value produced by a
rule rather than measured — and neither invents a level:

**FIX 1 · re-anchor the construction-cost path to the last actual.**
History carries one decimal to 2025Q3 (119.1); from 2025Q4 the series carries
nine and is rule-generated. The seam drops **−2.084 %**, against a historical
quarterly mean of +0.649 % and sd of 0.821 % — z = 3.33, and a bigger single
quarter fall than 2009Q1 produced at the depth of the financial crisis, with no
event behind it. The rule's own growth rates are fine and are kept untouched
(+0.675 %/qtr in 2026, +0.650 in 2027, +0.525 in 2028); only the level it starts
from is wrong. So the whole rule-generated segment is multiplied by one factor
that makes 2025Q4 continue from 2025Q3 at the rule's own first rate. One
parameter, no new growth assumption.

**FIX 2 · smooth the flat-carried mortgage rate into a quarterly path.**
2027 and 2028 hold a single value across all four quarters: an annual estimate
the smoothing step never ran on, while 2026 has a real quarterly path. The fix
interpolates between annual anchors and then rescales each year so its mean is
*exactly* what it was. No annual number changes — only the within-year
distribution, from a step function to a path.

That distinction matters and is the reason this fix is allowed at all: the flat
carry is not a measurement of a flat quarter, it is the absence of a within-year
estimate. Replacing one construction with a better-behaved construction of the
same annual content adds no information and removes a false step.

**What is NOT fixed, deliberately.**

* The 2028 mortgage-rate *level* — 33.7 bp below 2027 with no source behind it.
  There is no correct value to write: no institution forecasts the Danish
  mortgage rate that far, which is why Carl's research bundle records
  `mortgage_rate` 2028 as coverage `none` rather than filling it. Changing the
  level would be inventing the number the research layer declined to invent.
  The pilot surfaces it at gate 1 instead, where an analyst can carry it.
* Consumer confidence, which decays at a flat −15 %/quarter through 2027–28.
  It is a rule, and there is no better source here to replace it with.
* Every other driver flagged by `efterprøv`. Same reason: the check reports;
  replacing a rule needs a source, not an opinion.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
UPSTREAM = DATA / "master_exogenous.xlsx"
FIXED = DATA / "master_exogenous_fixed.xlsx"

COUNTRY = "DK"
COST = "Construction costs"
RATE = "Real Interest rate (Mortgage)"
LAST_ACTUAL_COST = "2025Q3"       # history carries 1 decimal to here
FLAT_YEARS = (2027, 2028)         # the rate years that were never smoothed


def _load() -> pd.DataFrame:
    return pd.read_excel(UPSTREAM)


def _series(df: pd.DataFrame, name: str) -> pd.Series:
    sub = df[(df["Country"] == COUNTRY) & (df["Marketdriver"] == name)].copy()
    sub["p"] = pd.PeriodIndex(sub["YearQuarter"].astype(str), freq="Q")
    return sub.set_index("p")["Value"].astype(float).sort_index()


# ── fix 1 ──────────────────────────────────────────────────────────────────
def cost_reanchor(s: pd.Series) -> tuple[pd.Series, dict]:
    anchor = pd.Period(LAST_ACTUAL_COST, freq="Q")
    first_rule = anchor + 1
    if first_rule not in s.index:
        raise ValueError("the rule-generated segment does not start where expected")

    # The rule's own first growth rate, taken from the rule itself.
    rule_g = float(s[first_rule + 1] / s[first_rule] - 1)
    want = float(s[anchor]) * (1.0 + rule_g)
    have = float(s[first_rule])
    factor = want / have

    out = s.copy()
    mask = out.index >= first_rule
    out[mask] = out[mask] * factor

    hist = s[s.index <= anchor].pct_change().dropna()
    return out, {
        "anchor": str(anchor),
        "anchor_value": round(float(s[anchor]), 4),
        "rule_growth_qoq_pct": round(rule_g * 100, 4),
        "was": round(have, 4),
        "now": round(want, 4),
        "factor": round(factor, 6),
        "seam_step_pct_before": round((have / float(s[anchor]) - 1) * 100, 3),
        "seam_step_pct_after": round(rule_g * 100, 3),
        "hist_qoq_mean_pct": round(float(hist.mean()) * 100, 3),
        "hist_qoq_sd_pct": round(float(hist.std()) * 100, 3),
        "z_before": round(abs((have / float(s[anchor]) - 1) - hist.mean())
                          / float(hist.std()), 2),
    }


# ── fix 2 ──────────────────────────────────────────────────────────────────
def rate_smooth(s: pd.Series, years=FLAT_YEARS) -> tuple[pd.Series, dict]:
    """Interpolate between annual anchors, then rescale each year to its own
    original mean. The annual content is preserved exactly; only the shape
    inside the year changes."""
    out = s.copy()
    means_before = {y: float(s[s.index.year == y].mean()) for y in years}

    # Anchor every year of the forecast at its mean, positioned at the year's
    # midpoint, and read the interpolation off at quarter midpoints.
    fc_years = sorted({p.year for p in s.index if p.year >= 2026})
    anchors_x = np.array([y + 0.5 for y in fc_years], dtype=float)
    anchors_y = np.array([float(s[s.index.year == y].mean()) for y in fc_years])

    for y in years:
        qs = [p for p in s.index if p.year == y]
        if len(qs) != 4:
            continue
        xs = np.array([y + (q.quarter - 0.5) / 4.0 for q in qs])
        vals = np.interp(xs, anchors_x, anchors_y)
        # Rescale so the year's mean is bit-for-bit what it was.
        vals = vals + (means_before[y] - vals.mean())
        for q, v in zip(qs, vals):
            out[q] = float(v)

    info = {"years": list(years),
            "means_before": {y: round(v, 5) for y, v in means_before.items()},
            "means_after": {y: round(float(out[out.index.year == y].mean()), 5)
                            for y in years},
            "path_before": {y: [round(float(v), 5) for v in s[s.index.year == y]]
                            for y in years},
            "path_after": {y: [round(float(v), 5) for v in out[out.index.year == y]]
                           for y in years}}
    return out, info


# ── writing ────────────────────────────────────────────────────────────────
def _write(df: pd.DataFrame, updates: dict[str, pd.Series]) -> None:
    out = df.copy()
    key = out["YearQuarter"].astype(str)
    for name, series in updates.items():
        sel = (out["Country"] == COUNTRY) & (out["Marketdriver"] == name)
        for p, v in series.items():
            out.loc[sel & (key == str(p)), "Value"] = v
    out.to_excel(FIXED, index=False)


def main(report_only: bool = False) -> int:
    if not UPSTREAM.exists():
        print(f"missing {UPSTREAM}", file=sys.stderr)
        return 1
    df = _load()

    cost_before = _series(df, COST)
    rate_before = _series(df, RATE)
    cost_after, c_info = cost_reanchor(cost_before)
    rate_after, r_info = rate_smooth(rate_before)

    print(f"source  {UPSTREAM.name}")
    print(f"target  {FIXED.name}{'  (report only — nothing written)' if report_only else ''}")
    print()
    print("FIX 1 · construction costs re-anchored to the last actual")
    print(f"  last actual {c_info['anchor']} = {c_info['anchor_value']}")
    print(f"  seam was {c_info['seam_step_pct_before']:+.3f}% "
          f"(z={c_info['z_before']} against history: mean "
          f"{c_info['hist_qoq_mean_pct']:+.3f}%, sd {c_info['hist_qoq_sd_pct']:.3f}%)")
    print(f"  seam now {c_info['seam_step_pct_after']:+.3f}% — the rule's own rate")
    print(f"  {c_info['anchor']}+1: {c_info['was']} -> {c_info['now']} "
          f"(x{c_info['factor']} applied to the whole rule segment)")
    ab = cost_before.groupby(cost_before.index.year).mean()
    aa = cost_after.groupby(cost_after.index.year).mean()
    for y in (2026, 2027, 2028):
        print(f"    {y} annual mean {ab[y]:8.3f} -> {aa[y]:8.3f} "
              f"({(aa[y]/ab[y]-1)*100:+.2f}%)")

    print()
    print("FIX 2 · mortgage rate smoothed into a quarterly path")
    for y in r_info["years"]:
        print(f"  {y} before {r_info['path_before'][y]}")
        print(f"       after {r_info['path_after'][y]}")
        print(f"       annual mean {r_info['means_before'][y]} -> "
              f"{r_info['means_after'][y]}"
              f"{'  UNCHANGED' if abs(r_info['means_before'][y] - r_info['means_after'][y]) < 1e-9 else '  CHANGED — BUG'}")

    if report_only:
        return 0
    _write(df, {COST: cost_after, RATE: rate_after})
    print()
    print(f"wrote {FIXED}")
    print("the upstream file is untouched; delete the fixed file to revert")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="say what would change and write nothing")
    a = ap.parse_args()
    raise SystemExit(main(a.report))
