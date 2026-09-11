"""efterprøv — does a number mean what it claims to mean?

The production chain runs V1–V6 against the claims database. This is the same
idea applied to the frozen driver snapshot: not *is the value plausible*, but
*is it measured as it claims to be*.

What each check is actually looking for:

    FLAT-CARRY     identical values across all four quarters of a year — an
                   annual estimate the smoothing step never turned into a
                   quarterly path.
    PRECISION      decimal places jumping mid-series. Actuals arrive rounded;
                   rule-generated values carry the arithmetic's full precision.
                   Where the precision changes, the source changed.
    CONSTANT-Δ     the same quarter-on-quarter growth rate, to six decimals,
                   several quarters running. Real series do not do this.
    SPLICE         a step at the actual/rule seam that the series' own history
                   rejects.
    V3 CONTINUITY  a move inside the forecast window beyond 2.5 sd of the
                   history it continues.
    V5 SCALE       a forecast value off its own order of magnitude — 250 where
                   2.50 belongs.
    V6 IDENTITY    a derived column against its own components.

Two deliberate restraints, because a check that cries wolf is a check nobody
reads:

  * **Indicators are exempt from FLAT-CARRY and CONSTANT-Δ.** `Covid_dummy` is
    supposed to hold one value all year. Flagging it would bury the findings
    that matter.
  * **CONTINUITY is not applied to history.** Danish construction really did
    move beyond 2.5 sd in 2008 and 2022. What matters is whether the *forecast*
    behaves like the series it continues.

This reports; it stops nothing. That is the production distinction: `validate`
points, `guard` refuses, `efterprøv` explains — and the analyst decides.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

try:                        # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from .data import DRIVERS, FORECAST_FROM

SD_LIMIT = 2.5


def _decimals(v: float) -> int:
    s = f"{v:.10f}".rstrip("0")
    return len(s.split(".")[1]) if "." in s else 0


def is_indicator(name: str, s: pd.Series) -> bool:
    """Dummies and switches are SUPPOSED to be flat within a year."""
    if any(w in name.lower() for w in ("dummy", "vacancy", "lack of")):
        return True
    return set(s.dropna().unique()) <= {0.0, 1.0}


def flat_carry(s: pd.Series) -> list:
    out = []
    for year, grp in s.groupby(s.index.year):
        vals = grp.dropna()
        if len(vals) >= 4 and vals.nunique() == 1:
            out.append({"year": int(year), "value": round(float(vals.iloc[0]), 6),
                        "quarters": int(len(vals))})
    return out


def precision_shift(s: pd.Series) -> dict | None:
    dec = s.dropna().map(_decimals)
    if dec.empty:
        return None
    for i in range(1, len(dec)):
        before, after = dec.iloc[:i], dec.iloc[i:]
        if before.max() <= 2 and after.min() >= before.max() + 2:
            return {"at": str(dec.index[i]),
                    "decimals_before": int(before.max()),
                    "decimals_after": int(after.min())}
    return None


def constant_growth(s: pd.Series, boundary) -> dict | None:
    """The longest CONTIGUOUS run of one growth rate inside the forecast window.

    Contiguity matters: a rate that recurs in 2026Q2 and again in 2028Q3 is a
    coincidence, and reporting it as a run from 2026 to 2028 would be a lie
    dressed as a finding.
    """
    v = s.dropna()
    g = v.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    g = g[g.index >= boundary]
    if len(g) < 4:
        return None
    r = g.round(6)

    best = (0, None, None, None)
    start, length = 0, 1
    for i in range(1, len(r) + 1):
        if i < len(r) and r.iloc[i] == r.iloc[start]:
            length += 1
            continue
        if length > best[0] and abs(float(r.iloc[start])) > 1e-9:
            best = (length, float(r.iloc[start]), r.index[start], r.index[i - 1])
        start, length = i, 1

    n, top, a, b = best
    if n < 4 or top is None:
        return None
    return {"qoq_pct": round(top * 100, 4), "quarters": n,
            "from": str(a), "to": str(b),
            "annualised_pct": round(((1 + top) ** 4 - 1) * 100, 3)}


def splice(s: pd.Series, boundary) -> dict | None:
    v = s.dropna()
    hist = v[v.index < boundary]
    if len(hist) < 12 or boundary not in v.index:
        return None
    d = hist.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 8:
        return None
    sd, mu = float(d.std()), float(d.mean())
    if not np.isfinite(sd) or sd == 0:
        return None
    prev = float(hist.iloc[-1])
    if not np.isfinite(prev) or prev == 0:
        return None
    step = float(v[boundary]) / prev - 1.0
    if not np.isfinite(step):
        return None
    z = abs(step - mu) / sd
    if z > SD_LIMIT:
        return {"at": str(boundary), "step_pct": round(step * 100, 3),
                "z": round(z, 2), "hist_sd_pct": round(sd * 100, 3)}
    return None


def continuity(s: pd.Series, boundary) -> list:
    v = s.dropna()
    d = v.diff().dropna()
    hist, fwd = d[d.index < boundary], d[d.index >= boundary]
    if len(hist) < 12 or fwd.empty:
        return []
    sd, mu = float(hist.std()), float(hist.mean())
    if not np.isfinite(sd) or sd == 0:
        return []
    z = (fwd - mu).abs() / sd
    return [{"at": str(i), "change": round(float(fwd[i]), 4), "z": round(float(z[i]), 2)}
            for i in z[z > SD_LIMIT].index]


def scale(s: pd.Series, boundary) -> list:
    v = s.dropna()
    hist, fwd = v[v.index < boundary], v[v.index >= boundary]
    if len(hist) < 12 or fwd.empty:
        return []
    med = float(hist.abs().median())
    if med == 0 or not np.isfinite(med):
        return []
    bad = fwd[(fwd.abs() > med * 20) | ((fwd.abs() < med / 20) & (fwd.abs() > 0))]
    return [{"at": str(i), "value": round(float(bad[i]), 4), "median": round(med, 4)}
            for i in bad.index]


def identity(d: pd.DataFrame) -> list:
    """V6 — derived columns against their own components.

    Tobin's Q is house prices over construction costs. The snapshot carries the
    ratio and the denominator but NOT the numerator, so the identity cannot be
    closed. That absence is the finding, and it is reported rather than skipped:
    there is no Danish house-price index in the model file, so house prices
    reach the model only through a ratio nobody can audit.
    """
    have = set(d.columns)
    return [{
        "derived": q,
        "needs": ["a Danish house-price index (numerator)", "Construction costs"],
        "present": ["Construction costs"] if "Construction costs" in have else [],
        "verdict": "CANNOT CLOSE — the numerator is not in the file, so the "
                   "identity is unverifiable by construction.",
    } for q in sorted(c for c in have if c.lower().startswith("tobins"))]


def run(drivers: pd.DataFrame = DRIVERS, boundary=FORECAST_FROM) -> dict:
    findings = []
    for name in sorted(drivers.columns):
        s = drivers[name].dropna()
        if s.empty:
            continue
        indicator = is_indicator(name, s)
        f = {}
        if not indicator:
            if (v := flat_carry(s)):
                f["flat_carry"] = v
            if (v := constant_growth(s, boundary)):
                f["constant_growth"] = v
        if (v := precision_shift(s)):
            f["precision_shift"] = v
        if (v := splice(s, boundary)):
            f["splice_at_boundary"] = v
        if (v := continuity(s, boundary)):
            f["continuity"] = v[:4]
        if (v := scale(s, boundary)):
            f["scale"] = v[:4]
        if f:
            findings.append({"driver": name,
                             "span": f"{s.index.min()} .. {s.index.max()}",
                             "n": int(len(s)), "indicator": indicator,
                             "findings": f})
    return {"boundary": str(boundary),
            "drivers_checked": int(len(drivers.columns)),
            "drivers_with_findings": len(findings),
            "findings": findings,
            "identity": identity(drivers)}


# ── what gate 1 shows ──────────────────────────────────────────────────────
_BY_DRIVER: dict | None = None


def for_driver(name: str) -> list:
    """The findings for one driver, as sentences a gate page can show.
    Computed from the data, so it cannot drift out of agreement with the file
    the way a hand-written warning eventually does."""
    global _BY_DRIVER
    if _BY_DRIVER is None:
        _BY_DRIVER = {i["driver"]: i for i in run()["findings"]}
    item = _BY_DRIVER.get(name)
    if not item:
        return []

    out, f = [], item["findings"]
    if "flat_carry" in f:
        yrs = ", ".join(str(x["year"]) for x in f["flat_carry"])
        out.append(f"FLAT-CARRY — {yrs} hold one value across all four quarters: "
                   "an annual estimate the smoothing step never turned into a "
                   "quarterly path.")
    if "precision_shift" in f:
        p = f["precision_shift"]
        out.append(f"PRECISION — decimals go {p['decimals_before']} → "
                   f"{p['decimals_after']} at {p['at']}. Actuals arrive rounded; "
                   "the numbers from here are generated.")
    if "constant_growth" in f:
        c = f["constant_growth"]
        out.append(f"CONSTANT-Δ — {c['qoq_pct']}% every quarter from {c['from']} "
                   f"to {c['to']} ({c['annualised_pct']}%/yr). A rule, not an estimate.")
    if "splice_at_boundary" in f:
        sp = f["splice_at_boundary"]
        out.append(f"SPLICE — a {sp['step_pct']}% step at {sp['at']}, z={sp['z']} "
                   "against the series' own history.")
    if "continuity" in f:
        w = max(f["continuity"], key=lambda x: x["z"])
        out.append(f"V3 CONTINUITY — {w['change']:+g} at {w['at']} (z={w['z']}) "
                   "is a move the history does not support.")
    return out


def report(res: dict) -> None:
    print(f"efterprøv · frozen snapshot · forecast begins {res['boundary']}")
    print(f"{res['drivers_with_findings']} of {res['drivers_checked']} "
          f"drivers report something\n")
    for item in res["findings"]:
        print(f"-- {item['driver']}   ({item['span']}, n={item['n']})")
        for line in for_driver(item["driver"]):
            print(f"   {line}")
        print()
    print("-- V6 IDENTITY")
    for i in res["identity"]:
        print(f"   {i['derived']}: {i['verdict']}")
