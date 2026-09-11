"""Gate 1b — the analyst overlay.

The forecast level, set by hand, where no driver can carry the judgement.

This is the one place in the pilot where a number is not produced by the model,
so it is worth being exact about what keeps it honest.

**Why it exists.** The chain already admits the case: sometimes no source can be
connected and the analyst has to set the assumption themselves — a political
change with no published calculation of its effects, a scheme whose start date
slipped, a segment where the driver set demonstrably does not reach the cause.
Refusing to represent that does not make it go away; it pushes it into a
spreadsheet nobody audits.

**What keeps it traceable.** Four things, and none is optional:

  1. **It is a layer, never a blend.** The model line and the overlay line are
     both kept and both drawn. You can always see what the model said.
  2. **The analyst is the source.** The number binds to `analytikerskøn` with a
     name and a date, so `p3 check` still binds every figure — the rule was
     never "a number must come from a document", it was "a number must have a
     source you can name".
  3. **It is not attributable to a driver, and says so.** The decomposition
     carries the overlay as its own row, labelled as judgement rather than
     cause. An overlay that quietly appeared inside the Tobin's Q contribution
     would be the actual dishonesty.
  4. **Annual level only, and the model keeps the shape.** You set the year;
     the within-year quarterly profile stays the model's. Setting 48 quarterly
     numbers by hand is not judgement, it is a different forecast.

**What it costs, stated plainly.** The backtest cannot validate an overlay — it
scores the model, and the overlay is by construction outside it. So an overlay
is measurable against the outcome but not against the method, and a round in
which overlays carry most of the movement is a round in which the model has
stopped being the thing that produces the forecast. The loop can count them;
that is the point of recording them.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import pandas as pd


@dataclass
class Adjustment:
    segment: str
    year: int
    model_value: float        # what the model said, kept beside the analyst's
    analyst_value: float
    reason: str               # verbatim, never normalised
    ts: str

    @property
    def factor(self) -> float:
        return (self.analyst_value / self.model_value) if self.model_value else 1.0

    @property
    def delta_pct(self) -> float:
        return (self.factor - 1.0) * 100.0

    def to_dict(self):
        d = asdict(self)
        d["factor"] = round(self.factor, 6)
        d["delta_pct"] = round(self.delta_pct, 3)
        return d


class Overlay:
    """Per segment, per year. Held in memory for the session and journalled."""

    def __init__(self):
        self._by_segment: dict[str, dict[int, Adjustment]] = {}

    # ── reading ────────────────────────────────────────────────────────────
    def for_segment(self, segment: str) -> dict[int, Adjustment]:
        return self._by_segment.get(segment, {})

    def factors(self, segment: str) -> dict[int, float]:
        return {y: a.factor for y, a in self.for_segment(segment).items()}

    def as_list(self, segment: str | None = None) -> list:
        segs = [segment] if segment else list(self._by_segment)
        return [a.to_dict() for s in segs
                for a in sorted(self.for_segment(s).values(), key=lambda x: x.year)]

    def any_set(self, segment: str) -> bool:
        return bool(self.for_segment(segment))

    # ── writing ────────────────────────────────────────────────────────────
    def set(self, segment: str, year: int, model_value: float,
            analyst_value: float, reason: str) -> Adjustment:
        a = Adjustment(segment=segment, year=int(year),
                       model_value=float(model_value),
                       analyst_value=float(analyst_value),
                       reason=reason.strip(),
                       ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self._by_segment.setdefault(segment, {})[int(year)] = a
        return a

    def clear(self, segment: str, year: int | None = None) -> None:
        if year is None:
            self._by_segment.pop(segment, None)
        else:
            self._by_segment.get(segment, {}).pop(int(year), None)


def apply(path: pd.DataFrame, factors: dict[int, float]) -> pd.DataFrame:
    """Scale a quarterly forecast to hit the analyst's annual level.

    The factor is applied to every quarter of the year, so the annual total
    lands where the analyst put it and the within-year profile stays the
    model's. The band scales with the level — an overlay expresses a different
    view of where the series sits, not more confidence about it.
    """
    if not factors:
        return path
    out = path.copy()
    years = out.index.year
    for year, f in factors.items():
        mask = years == int(year)
        if mask.any():
            out.loc[mask, ["level", "lo", "hi"]] *= f
    return out


def guard(analyst_value: float, model_value: float, unit: str) -> tuple[bool, str]:
    """The same four questions guard asks of a driver, asked of a level.

    Deliberately permissive about size: an analyst who knows a scheme has been
    cancelled may legitimately halve a segment. What is refused is what cannot
    be true — a negative number of dwellings — and what is almost certainly a
    typo rather than a judgement.
    """
    try:
        v = float(analyst_value)
    except (TypeError, ValueError):
        return False, f"'{analyst_value}' is not a number"
    if v != v or v in (float("inf"), float("-inf")):
        return False, f"'{analyst_value}' is not a number"
    if v < 0:
        return False, (f"{unit} cannot be negative. A segment can go to zero; "
                       "it cannot go below it.")
    if model_value and v > model_value * 10:
        return False, (f"{v:,.0f} is more than ten times the model's "
                       f"{model_value:,.0f}. Refused as a typo rather than a "
                       "judgement — if it is a judgement, say so in the reason "
                       "and set it in two steps.")
    if model_value and v > 0 and v < model_value / 10:
        return False, (f"{v:,.0f} is less than a tenth of the model's "
                       f"{model_value:,.0f}. Refused as a typo rather than a "
                       "judgement.")
    return True, "inside what a level can be"
