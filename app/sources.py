"""Gate 0 — fresh?

The round starts because the analyst says so, not because a date arrived.

**Every number on this page is counted from the research bundle.** Tier, cluster
and consensus membership come from the bundle's institution records; claim
counts, driver coverage, latest publication date, age in days, report links and
extraction method are aggregated from the claims themselves.

An earlier version of this file carried a hand-written register with cadences
and next-edition dates I had asserted rather than read. Those are gone. Nothing
in the data says when an institution's next edition is due, so the page does not
say it either — a plausible date is worse than a blank, because a blank prompts
a question and a plausible date ends one.

The few qualitative notes that remain are quoted from P1's own source dossier
and attributed to it, so it is visible which statements are measured and which
are inherited.

Gate 0 had **no recorded history** in the production chain — nothing was ever
journalled there. That is the hole the learning loop closes, and it is why this
gate is in the pilot at all: it starts empty on purpose.
"""

from __future__ import annotations

import collections
from functools import lru_cache

from . import bundle

# Statements taken from P1's dossier (`hpi-boligtyper-kilder.md`, 22 August
# 2026) rather than from the bundle. Attributed, because they are inherited
# rather than measured here.
DOSSIER_NOTES = {
    "nykredit_bolig": "One of only two Danish institutions that print an apartment "
                      "number. Machine-readable table at a fixed URL. "
                      "(P1 dossier, 22 Aug 2026)",
    "nordea": "The other institution that prints an apartment number. Same "
              "cluster as Nykredit, so admitting both does not buy two "
              "independent signals. (P1 dossier, 22 Aug 2026)",
    "nationalbanken": "Forecasts enfamiliehuse only; Copenhagen apartments are "
                      "discussed qualitatively, with no number. "
                      "(P1 dossier, 22 Aug 2026)",
    "dors": "Forecasts 'kontantpris på boliger' — enfamiliehuse. Apartments only "
            "as a Copenhagen analysis. (P1 dossier, 22 Aug 2026)",
    "dst": "The facit series. EJENDOMSKATE 2103 = etageboliger, 0111 = "
           "enfamiliehuse, 0801 = sommerhuse. (P1 dossier, 22 Aug 2026)",
}

# Source ids the bundle uses for values that are not an outside institution.
INTERNAL = {"agent_nowcast", "agent_project", "knime_2026v3"}


@lru_cache(maxsize=1)
def _aggregate() -> dict:
    """Count what each source actually contributes. Nothing is asserted here."""
    agg: dict[str, dict] = {}
    for d in bundle.drivers():
        card = bundle.driver_card(d["id"])
        for y in card["years"]:
            for c in y["claims"]:
                sid = c.get("source_id")
                if not sid:
                    continue
                a = agg.setdefault(sid, {
                    "claims": 0, "drivers": set(), "published": set(),
                    "ages": [], "urls": set(), "titles": set(),
                    "extraction": collections.Counter(), "excluded": 0,
                })
                a["claims"] += 1
                a["drivers"].add(d["id"])
                if c.get("published_at"):
                    a["published"].add(c["published_at"])
                if c.get("age_days") is not None:
                    a["ages"].append(c["age_days"])
                if c.get("report_url"):
                    a["urls"].add(c["report_url"])
                if c.get("report_title"):
                    a["titles"].add(c["report_title"])
                a["extraction"][c.get("extraction")] += 1
                if c.get("excluded"):
                    a["excluded"] += 1
    return agg


def register(round_opened: bool = False) -> dict:
    inst = bundle.institutions()
    agg = _aggregate()
    m = bundle.manifest()

    rows = []
    for sid, meta in inst.items():
        a = agg.get(sid, {})
        pub = sorted(a.get("published", []))
        rows.append({
            "key": sid,
            "name": meta.get("name") or sid,
            "short_name": meta.get("short_name"),
            "tier": meta.get("tier"),
            "cluster": meta.get("cluster"),
            "in_consensus": meta.get("in_consensus"),
            # counted, not asserted
            "claims": a.get("claims", 0),
            "drivers_covered": len(a.get("drivers", ())),
            "latest_published": pub[-1] if pub else None,
            "age_days": min(a["ages"]) if a.get("ages") else None,
            "reports": sorted(a.get("titles", []))[:3],
            "has_link": bool(a.get("urls")),
            "extraction": dict(a.get("extraction", {})),
            "excluded_claims": a.get("excluded", 0),
            "note": DOSSIER_NOTES.get(sid),
        })

    # No claims at all is a fact worth surfacing: the source is declared in the
    # catalogue and contributes nothing to this vintage.
    silent = [r["key"] for r in rows if r["claims"] == 0]
    rows.sort(key=lambda r: (-r["claims"], r["name"]))

    internal = []
    for sid in sorted(INTERNAL & set(agg)):
        a = agg[sid]
        internal.append({"key": sid, "claims": a["claims"],
                         "drivers_covered": len(a["drivers"]),
                         "extraction": dict(a["extraction"])})

    return {
        "round": f"{m.get('country')} · bundle generated {str(m.get('generated_at'))[:10]}",
        "as_of": str(m.get("generated_at"))[:10],
        "history_last": m.get("history_last"),
        "forecast_from": m.get("forecast_from"),
        "opened": round_opened,
        "sources": rows,
        "internal": internal,
        "n_institutions": len(rows),
        "n_claims": sum(r["claims"] for r in rows),
        "silent": silent,
        "silent_note": "Declared in the catalogue and contributing no claims to "
                       "this vintage. Not an error — a source that was admitted "
                       "and has not published into it.",
        "no_cadence_note": "The bundle records when each report was published, "
                           "not when the next is due, so no next-edition date is "
                           "shown. Gate 0 asks whether what we hold is fresh "
                           "enough, which is a judgement, not a schedule.",
        "history": "Gate 0 has no recorded history in the production chain — "
                   "nothing was ever journalled here. It starts empty on purpose.",
    }


BY_KEY_NOTE = ("Kept as a function rather than a dict so it cannot drift from "
               "the bundle.")


def by_key() -> dict:
    return {r["key"]: r for r in register()["sources"]}
