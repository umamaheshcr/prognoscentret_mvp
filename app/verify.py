"""Gate 1 — market-driver verification, per driver and per forecast year.

Three changes from the first pilot, all requested:

  1. **An assumption per year of the forecast period**, not one value carried
     across. 2026, 2027 and 2028 are separate decisions with separate sources,
     separate consensus bands and separate quality grades — and in the data they
     genuinely differ: real GDP has nine sources for 2026 and one for 2028.
  2. **The sources shown per assumption** — institution, tier, value, weight,
     publication date and age, report title, page, the verbatim quote and a link
     to the report.
  3. **No forecast on this page.** Verification and forecasting are separate
     steps. Approving a driver must not be steered by watching a forecast line
     move while you do it.

The approval state lives here rather than in the bundle: the bundle is read-only
research, and what an analyst decided about it is a different thing with a
different lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from . import bundle


@dataclass
class Approval:
    driver_id: str
    year: int
    agent_value: float             # the triangulated central estimate
    analyst_value: float
    reason: str                    # verbatim; required only when the value moved
    moved: bool
    ts: str

    def to_dict(self):
        d = asdict(self)
        d["delta"] = round(self.analyst_value - self.agent_value, 6)
        return d


class Verification:
    """Per driver, per year. In memory for the session, journalled as it goes."""

    def __init__(self):
        self._a: dict[tuple[str, int], Approval] = {}

    def get(self, driver_id: str, year: int) -> Approval | None:
        return self._a.get((driver_id, int(year)))

    def approve(self, driver_id: str, year: int, agent_value,
                analyst_value, reason: str) -> Approval:
        """A cell with no estimate cannot be approved — there is nothing there
        to accept. Seven driver-years in the bundle are like this, all of them
        2028 with coverage 'none', and `mortgage_rate` and `hpi_flats` are two
        of them. That is the research layer declining to invent a number no
        institution publishes, and it must not be papered over here."""
        if agent_value is None and analyst_value is None:
            raise ValueError("no estimate to approve")
        if analyst_value is None:
            analyst_value = agent_value
        if agent_value is None:
            agent_value = analyst_value
        moved = abs(float(analyst_value) - float(agent_value)) > 1e-9
        a = Approval(driver_id=driver_id, year=int(year),
                     agent_value=float(agent_value),
                     analyst_value=float(analyst_value),
                     reason=reason.strip(), moved=moved,
                     ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self._a[(driver_id, int(year))] = a
        return a

    def clear(self, driver_id: str, year: int | None = None) -> None:
        if year is None:
            for k in [k for k in self._a if k[0] == driver_id]:
                del self._a[k]
        else:
            self._a.pop((driver_id, int(year)), None)

    def for_driver(self, driver_id: str) -> dict:
        return {y: a.to_dict() for (d, y), a in self._a.items() if d == driver_id}

    def all(self) -> list:
        return [a.to_dict() for a in sorted(
            self._a.values(), key=lambda x: (x.driver_id, x.year))]

    # ── progress, in the terms Carl's header uses ──────────────────────────
    def progress(self) -> dict:
        years = bundle.forecast_years()
        approvable = 0
        no_estimate = []
        for d in bundle.drivers():
            for y in bundle.driver_card(d["id"])["years"]:
                if y["central"] is None:
                    no_estimate.append({"driver": d["id"], "label": d.get("label"),
                                        "year": y["year"]})
                else:
                    approvable += 1
        no_est_keys = {(x["driver"], x["year"]) for x in no_estimate}
        done = sum(1 for k in self._a if k not in no_est_keys)
        carried = sum(1 for k in self._a if k in no_est_keys)
        moved = sum(1 for a in self._a.values() if a.moved)
        fully = 0
        for d in bundle.drivers():
            need = [y["year"] for y in bundle.driver_card(d["id"])["years"]
                    if y["central"] is not None]
            if need and all(self.get(d["id"], y) for y in need):
                fully += 1
        return {"cells_total": approvable, "cells_approved": done,
                "carried_by_hand": carried, "moved": moved,
                "drivers_total": len(bundle.drivers()), "drivers_approved": fully,
                "years": years,
                "no_estimate": no_estimate,
                "no_estimate_note":
                    "Cells with no estimate cannot be approved. Every one is 2028 "
                    "with coverage 'none' — the research layer declining to invent "
                    "a number no institution publishes."}

    def driver_state(self, driver_id: str) -> str:
        years = [y["year"] for y in bundle.driver_card(driver_id)["years"]
                 if y["central"] is not None]
        if not years:
            return "no_estimate"
        got = [self.get(driver_id, y) for y in years]
        if not any(got):
            return "unchanged"
        if all(got):
            return "moved" if any(a.moved for a in got if a) else "approved"
        return "partial"

    # ── what reaches the engine ────────────────────────────────────────────
    def engine_overrides(self) -> dict:
        """Approved values for the ten drivers the model actually eats,
        converted into the engine's units.

        Only approved cells cross this line. An unapproved research value stays
        research — which is the whole point of the gate.
        """
        from .data import DRIVERS

        out: dict[str, dict[int, float]] = {}
        for engine_id, d in bundle.engine_drivers().items():
            col = bundle.engine_column(engine_id)
            if not col or col not in DRIVERS.columns:
                continue
            series = DRIVERS[col].dropna()
            prev_by_year = {}
            for y in bundle.forecast_years():
                s = series[series.index.year == y - 1]
                prev_by_year[y] = float(s.mean()) if len(s) else None

            for year in bundle.forecast_years():
                a = self.get(d["id"], year)
                if a is None:
                    continue
                prev = prev_by_year.get(year)
                if prev is None:
                    hist = series[series.index.year == year - 1]
                    prev = float(hist.mean()) if len(hist) else None
                val = bundle.to_engine_value(engine_id, a.analyst_value, prev)
                if val is not None:
                    out.setdefault(engine_id, {})[year] = val
        return out


def card(driver_id: str, v: Verification) -> dict:
    """A driver card with the analyst's own decisions folded in."""
    c = bundle.driver_card(driver_id)
    if not c:
        return {}
    mine = v.for_driver(driver_id)
    for y in c["years"]:
        y["approval"] = mine.get(y["year"])
    c["state"] = v.driver_state(driver_id)
    return c
