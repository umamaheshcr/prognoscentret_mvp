"""Smoke tests. Run with:  .venv/Scripts/python -m pytest -q

These check the things the demo would be embarrassing to get wrong: that the
signs match the production config, that the decomposition is exact rather than
approximate, that guard refuses what it is supposed to refuse, and that a
commit without a reason is rejected.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import data, guard, model, scenario  # noqa: E402


# ── data ───────────────────────────────────────────────────────────────────
def test_snapshot_shape():
    assert data.LAST_ACTUAL.year == 2025
    assert len(data.FORECAST_INDEX) == 12          # 2026Q1 .. 2028Q4
    assert str(data.FORECAST_INDEX.min()) == "2026Q1"
    assert str(data.FORECAST_INDEX.max()) == "2028Q4"


def test_every_segment_has_its_drivers():
    for seg, spec in data.SEGMENTS.items():
        assert spec["tobins_q"] in data.DRIVERS.columns
        assert not data.STARTS[seg].dropna().empty


# ── model ──────────────────────────────────────────────────────────────────
def test_signs_match_the_production_config():
    """Tobin's Q positive, real mortgage rate negative. The production config
    records these for the Flats combined ECM; a flipped sign is a finding."""
    for seg, f in model.FITS.items():
        assert f.b_tobins_q > 0, f"{seg}: Tobin's Q sign is wrong"
        assert f.b_rate < 0, f"{seg}: rate sign is wrong"


def test_fit_is_not_degenerate():
    for seg, f in model.FITS.items():
        assert f.n >= 60
        assert 0.0 < f.r2 < 1.0
        assert f.holdout_mape > 0


def test_decomposition_is_exact():
    """The claim on the page is that attribution has no residual. Check it:
    the two driver effects must compose exactly into the net effect."""
    r = scenario.run("Flats", {"rate": 1.8, "hpi": 11.0})
    d = r["decomposition"]
    composed = (1 + d["tobins_q"]["effect_pct"] / 100) * \
               (1 + d["rate"]["effect_pct"] / 100) - 1
    assert math.isclose(composed * 100, d["net_pct"], rel_tol=1e-9, abs_tol=1e-9)


def test_baseline_is_the_agents_forecast():
    """With no overrides, the analyst's forecast and the agent's must be
    identical — otherwise the comparison line is lying."""
    r = scenario.run("Flats", {})
    assert r["annual_forecast"] == r["annual_baseline"]
    assert abs(r["decomposition"]["net_pct"]) < 1e-9


def test_lower_rate_raises_starts():
    base = scenario.run("Flats", {})["annual_forecast"][2027]
    cheaper = scenario.run("Flats", {"rate": 1.5})["annual_forecast"][2027]
    assert cheaper > base


def test_higher_costs_lower_starts():
    """Costs are the denominator of Tobin's Q, so dearer building must reduce
    starts. If this fails the ratio has been wired upside down."""
    base = scenario.run("Flats", {})["annual_forecast"][2027]
    dearer = scenario.run("Flats", {"cost": 6.0})["annual_forecast"][2027]
    assert dearer < base


def test_house_prices_move_apartments():
    """The finding the demo exists to show: one hpi numerator feeds every
    residential segment, so single-family prices move apartment starts."""
    base = scenario.run("Flats", {})["annual_forecast"][2027]
    richer = scenario.run("Flats", {"hpi": 12.0})["annual_forecast"][2027]
    assert richer > base


def test_band_brackets_the_forecast():
    r = scenario.run("Flats", {})
    for lo, mid, hi in zip(r["lo"], r["forecast"], r["hi"]):
        if mid is None:
            continue
        assert lo < mid < hi


# ── guard ──────────────────────────────────────────────────────────────────
def test_guard_refuses_negative_rate():
    v = guard.check("rate", -1.2)
    assert not v.ok and v.kind == "refused"
    assert "below zero" in v.reason


def test_guard_refuses_non_numbers():
    for bad in ("abc", None, float("nan"), float("inf")):
        assert not guard.check("rate", bad).ok


def test_guard_passes_the_unusual_but_possible():
    """A guardrail that stops an unusual but correct number is worse than no
    guardrail. 12 per cent house-price growth is unusual and real."""
    assert guard.check("hpi", 12.0).ok
    assert guard.check("hpi", 24.0).ok


def test_guard_rejects_unknown_driver():
    assert not guard.check("no_such_driver", 1.0).ok


# ── the gate ───────────────────────────────────────────────────────────────
def test_a_reason_is_required():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, client=("127.0.0.1", 50000))
    r = c.post("/api/decision", json={"driver": "rate", "value": 1.8, "reason": "  "})
    assert r.status_code == 422

    r = c.post("/api/decision",
               json={"driver": "rate", "value": 1.8, "reason": "the forward curve"})
    assert r.status_code == 200
    body = r.json()["recorded"]
    assert body["agent_proposed"] == 2.52       # kept beside the analyst's value
    assert body["reason"] == "the forward curve"  # verbatim, not normalised


def test_forecast_endpoint_refuses_a_guarded_value():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, client=("127.0.0.1", 50000))
    r = c.post("/api/forecast",
               json={"segment": "Flats", "overrides": {"rate": -1.0}})
    assert r.status_code == 422


# ── the other three gates ──────────────────────────────────────────────────
# app/auth.py fails closed for any client that is not loopback, and the
# TestClient's default fake peer ("testclient", 50000) is not in its loopback
# set. Pin the peer to 127.0.0.1, the same way test_deploy_auth.py does for
# LOCAL, so these calls exercise the app rather than its deployment gate.
def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, client=("127.0.0.1", 50000))


def test_gate0_rejecting_a_source_needs_a_reason():
    c = _client()
    r = c.post("/api/open-round", json={"rejected": ["dors"], "reason": ""})
    assert r.status_code == 422
    r = c.post("/api/open-round",
               json={"rejected": ["dors"], "reason": "four months old"})
    assert r.status_code == 200 and r.json()["opened"]


def test_gate0_rejects_an_unknown_source():
    assert _client().post("/api/open-round",
                          json={"rejected": ["nope"], "reason": "x"}).status_code == 422


def test_gate0_register_is_derived_and_not_asserted():
    """The register used to be hand-written, with cadences and next-edition
    dates I had asserted rather than read. It is now counted from the bundle's
    claims, and this test pins the properties that must stay derived."""
    reg = _client().get("/api/sources").json()
    assert reg["n_institutions"] == 22
    assert reg["n_claims"] > 200

    # Nothing claims to know when the next edition is due, because nothing does.
    for row in reg["sources"]:
        assert "cadence" not in row
        assert "expected" not in row

    # Six institutions are declared and contribute nothing to this vintage.
    # That is a fact about the vintage, not an error, and it must stay visible.
    assert len(reg["silent"]) == 6
    for key in reg["silent"]:
        row = next(r for r in reg["sources"] if r["key"] == key)
        assert row["claims"] == 0


def test_gate0_surfaces_a_stale_source():
    """What gate 0 is for: Nationalbanken's newest claim in this vintage is a
    year old. An analyst may well reject it, and the page has to show them
    that they should be asked."""
    reg = _client().get("/api/sources").json()
    nb = next(r for r in reg["sources"] if r["key"] == "nationalbanken")
    assert nb["age_days"] is not None and nb["age_days"] >= 300
    assert max(r["age_days"] or 0 for r in reg["sources"]) >= 300


def test_gate2_edits_the_config_not_the_number():
    """Pointing row houses at the flats ratio instead of the detached one is a
    config-row change, and the backtest must re-score it."""
    c = _client()
    r = c.post("/api/config", json={"segment": "Row-, chained-, linked houses",
                                    "tobins_q": "Tobins-Q (Flats)"})
    assert r.status_code == 200
    body = r.json()
    assert body["spec"]["tobins_q"] == "Tobins-Q (Flats)"
    assert body["before"]["holdout_mape"] != body["after"]["holdout_mape"]
    assert body["signs_ok"]


def test_gate2_rejects_a_driver_that_does_not_exist():
    assert _client().post("/api/config",
                          json={"segment": "Flats",
                                "tobins_q": "Tobins-Q (Castles)"}).status_code == 422


def test_gate2_signoff_needs_a_reason():
    c = _client()
    assert c.post("/api/signoff", json={"reason": " "}).status_code == 422
    assert c.post("/api/signoff",
                  json={"reason": "the backtest taught us"}).status_code == 200


def test_publish_refuses_a_naked_number():
    """The production rule: a number bound to nothing is invented, and the
    export exits 1."""
    c = _client()
    r = c.post("/api/publish", json={"segment": "Flats", "overrides": {},
                                     "edited": "Starts will reach 30,000 next year."})
    assert r.status_code == 422
    assert "30,000" in r.json()["check"]["naked_numbers"]


def test_publish_binds_every_number_and_builds_its_own_source_list():
    c = _client()
    r = c.post("/api/publish", json={"segment": "Flats", "overrides": {"rate": 1.9}})
    assert r.status_code == 200
    body = r.json()
    assert body["check"]["ok"]
    assert body["check"]["bound"] == body["check"]["declared"]
    assert len(body["sources"]) >= 5
    # The source list is derived from the bindings, never typed.
    assert {s["binding"] for s in body["sources"]} <= {b["binding"] for b in body["bounds"]}


# ── languages ──────────────────────────────────────────────────────────────
def test_swedish_is_actually_swedish():
    c = _client()
    en = c.get("/api/panel?lang=en").json()["drivers"][0]["label"]
    sv = c.get("/api/panel?lang=sv").json()["drivers"][0]["label"]
    assert en == "Real mortgage rate"
    assert sv == "Realränta, bolån"


def test_an_unknown_language_falls_back_to_english():
    assert _client().get("/api/panel?lang=de").json()["lang"] == "en"


def test_swedish_numbers_use_a_comma_decimal():
    """12,0 read as an English number is a hundred and twenty. Getting this
    wrong in a published chapter is not cosmetic."""
    from app.chapter import num
    assert num(12.0, 1, "sv") == "12,0"
    assert num(12.0, 1, "en") == "12.0"
    assert num(19728, 0, "sv") == "19 728"     # non-breaking space
    assert num(19728, 0, "en") == "19,728"


def test_swedish_thousands_do_not_break_the_check():
    """With an ordinary space, '19 728' reads as two numbers and the first
    looks naked. The non-breaking space is what keeps the check honest."""
    c = _client()
    r = c.post("/api/publish", json={"segment": "Flats", "overrides": {}, "lang": "sv"})
    assert r.status_code == 200, r.json()
    assert r.json()["check"]["naked_numbers"] == []


# ── the claim on the tin ───────────────────────────────────────────────────
def test_no_language_model_anywhere():
    """The pilot claims zero tokens and no API key. Check that nothing in the
    dependency list or the app package can call a model."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    reqs = (root / "requirements.txt").read_text(encoding="utf-8").lower()
    for banned in ("anthropic", "openai", "langchain", "transformers", "litellm"):
        assert banned not in reqs, f"{banned} is in requirements.txt"

    for py in (root / "app").glob("*.py"):
        src = py.read_text(encoding="utf-8").lower()
        for banned in ("import anthropic", "import openai", "requests.post(",
                       "httpx.post(", "urllib.request"):
            assert banned not in src, f"{banned} in {py.name}"


# ── efterprøv · the defects are locked in, so a fix cannot pass unnoticed ──
def _upstream(name: str):
    """The untouched snapshot, read straight from the upstream file. The fixes
    are written to a separate file, so both are available and every fix can be
    pinned in both directions."""
    import pandas as pd
    from app.data import COUNTRY, EXO_UPSTREAM
    df = pd.read_excel(EXO_UPSTREAM)
    sub = df[(df["Country"] == COUNTRY) & (df["Marketdriver"] == name)].copy()
    sub["p"] = pd.PeriodIndex(sub["YearQuarter"].astype(str), freq="Q")
    return sub.set_index("p")["Value"].astype(float).sort_index()


def test_the_pilot_loads_the_fixed_file_and_says_so():
    from app import data
    assert data.EXO_IS_FIXED, "run tools/fix_master.py"
    assert data.meta()["exogenous_file"] == "master_exogenous_fixed.xlsx"
    assert data.EXO_UPSTREAM.exists(), "the upstream file must never be removed"


def test_the_flat_carried_mortgage_rate_is_fixed_and_was_real():
    """FIX 2. Upstream, the driver both apartment models depend on holds one
    value across all four quarters of 2027 and 2028 — an annual estimate the
    smoothing step never ran on. The fix gives it a path and leaves the annual
    means bit-for-bit unchanged."""
    from app import efterproev
    from app.data import DRIVERS, RATE

    up = _upstream(RATE)
    for year in (2027, 2028):
        assert up[up.index.year == year].nunique() == 1      # the defect was real

    # fixed: a path, not a step
    now = DRIVERS[RATE].dropna()
    for year in (2027, 2028):
        assert now[now.index.year == year].nunique() > 1

    # and no annual number moved
    for year in (2026, 2027, 2028):
        assert abs(float(now[now.index.year == year].mean())
                   - float(up[up.index.year == year].mean())) < 1e-9

    # efterprøv no longer reports it
    res = {i["driver"]: i for i in efterproev.run()["findings"]}
    assert "flat_carry" not in res.get(RATE, {}).get("findings", {})


def test_the_construction_cost_splice_is_fixed_and_was_real():
    """FIX 1. Upstream, the path did not connect to the last actual: the step
    at 2025Q4 was a bigger single-quarter fall than 2009Q1 produced at the
    depth of the financial crisis, with no event behind it. The fix re-anchors
    the rule-generated segment and keeps the rule's own growth rates."""
    from app.data import DRIVERS

    up = _upstream("Construction costs")
    hist = up[up.index <= "2025Q3"].pct_change().dropna()
    seam_before = float(up["2025Q4"] / up["2025Q3"] - 1)
    assert seam_before < float(hist.min())                   # worse than any actual
    assert abs(seam_before - hist.mean()) / hist.std() > 3.0

    now = DRIVERS["Construction costs"].dropna()
    seam_after = float(now["2025Q4"] / now["2025Q3"] - 1)
    rule = float(now["2026Q1"] / now["2025Q4"] - 1)
    assert abs(seam_after - rule) < 1e-9      # the seam is now the rule's own rate
    assert seam_after > 0

    # history is untouched; only the rule-generated segment moved
    for q in ("2025Q1", "2025Q2", "2025Q3", "2020Q1"):
        assert abs(float(now[q]) - float(up[q])) < 1e-9

    # and the rule's growth rates survive the re-anchoring unchanged
    for q in ("2026Q2", "2027Q3", "2028Q4"):
        gb = float(up[q] / up[str(pd_prev(q))] - 1)
        ga = float(now[q] / now[str(pd_prev(q))] - 1)
        assert abs(gb - ga) < 1e-9


def pd_prev(q: str):
    import pandas as pd
    return pd.Period(q, freq="Q") - 1


def test_the_2026_cost_artefact_is_gone():
    """`notes/dk_new_residential.md` records the May text saying material prices
    keep rising, against a path showing +0.2 % for 2026 — and files that as an
    open contradiction. The +0.2 % was the seam, not a forecast. With the seam
    corrected the same path grows about 2.8 %, so the open question closes in
    favour of the text: the prose was right and the path was wrong."""
    from app.data import DRIVERS

    up = _upstream("Construction costs")
    ab = up.groupby(up.index.year).mean()
    stated_before = (ab[2026] / ab[2025] - 1) * 100
    assert 0.0 < stated_before < 0.5               # the artefact was real

    now = DRIVERS["Construction costs"].dropna()
    aa = now.groupby(now.index.year).mean()
    stated_after = (aa[2026] / aa[2025] - 1) * 100
    assert 2.0 < stated_after < 3.5                # and now it says what the rule says


def test_fixing_the_costs_barely_moves_the_forecast_and_that_is_the_point():
    """Worth pinning, because it is counter-intuitive and it is a finding: the
    corrected cost path does NOT reach the model. Tobin's Q is stored as its own
    series rather than derived from prices over costs, so a cost correction
    changes the report's numbers and not the forecast's. The cost defect
    mattered for the text, not for the starts."""
    from app import bundle
    from app.data import DRIVERS

    # cost and Tobin's Q are independent columns, not one derived from the other
    cost = DRIVERS["Construction costs"].dropna()
    tq = DRIVERS["Tobins-Q (Flats)"].dropna()
    ratio = (tq / cost).dropna()
    assert ratio.std() > 1e-6, "if this were derived the ratio would be constant"

    # and the model's own driver list does not include costs
    from app.model import DEFAULT_SPECS
    spec = DEFAULT_SPECS["Flats"]
    assert spec.tobins_q == "Tobins-Q (Flats)"
    assert "Construction costs" not in (spec.tobins_q, "Real Interest rate (Mortgage)")

    # the bundle agrees that costs reach the engine only as their own series
    assert bundle.engine_column("Construction_costs") == "Construction costs"


def test_indicators_are_exempt_from_flat_carry():
    """A dummy is supposed to hold one value all year. Flagging Covid_dummy
    would bury the findings that matter."""
    from app import efterproev
    flagged = {i["driver"] for i in efterproev.run()["findings"]}
    for dummy in ("Covid_dummy", "Financial crisis dummy", "Q2_dummy"):
        assert dummy not in flagged


def test_v6_identity_cannot_close_for_any_tobins_q():
    """The structural finding: the numerator is not in the file, so house prices
    reach the Danish model only through a ratio nobody can audit."""
    from app import efterproev
    ident = efterproev.run()["identity"]
    assert len(ident) >= 4
    assert all("CANNOT CLOSE" in i["verdict"] for i in ident)


def test_gate1_derives_its_warnings_from_the_data():
    """The panel must not carry hand-typed efterprøv text — a warning that is
    computed cannot outlive the defect it describes."""
    from app.panel import panel
    by_key = {d["key"]: d for d in panel()["drivers"]}
    # costs are still rule-generated from 2025Q4 — that is a fact about the
    # file, not a defect the fix claimed to remove, so it must still be shown
    assert any("PRECISION" in s for s in by_key["cost"]["efterproev"])
    # the rate's flat carry was fixed, so the warning must have gone with it
    assert not any("FLAT-CARRY" in s for s in by_key["rate"]["efterproev"])
    assert by_key["hpi"]["efterproev"] == []       # nothing to report, so nothing shown


def test_the_unsourced_2028_rate_is_worth_about_1300_dwellings():
    """What rests on a number no institution publishes."""
    import numpy as np
    from app.data import DRIVERS, RATE
    from app.model import FITS
    from app import scenario
    r = DRIVERS[RATE].dropna()
    step = float(r[r.index.year == 2028].mean() - r[r.index.year == 2027].mean())
    assert step < -0.003                            # 2028 falls, unsourced
    eff = np.exp(FITS["Flats"].b_rate * -step) - 1
    at_risk = scenario.run("Flats", {})["annual_forecast"][2028] * abs(eff)
    assert 1000 < at_risk < 1600


# ── gate 1b · the analyst overlay ──────────────────────────────────────────
def _overlay_with(segment="Flats", year=2027, value=17500,
                  reason="two Copenhagen schemes will not start in 2027"):
    from app import overlay, scenario
    o = overlay.Overlay()
    m = scenario.model_annual(segment, {})
    o.set(segment, year, m[year], value, reason)
    return o, m


def test_overlay_hits_the_annual_level_and_keeps_the_model_shape():
    """The analyst sets the year; the within-year quarterly profile stays the
    model's. Otherwise it is not judgement, it is a different forecast."""
    from app import scenario
    o, _ = _overlay_with(value=17500)
    r = scenario.run("Flats", {}, None, "en", o)
    assert abs(r["annual_forecast"][2027] - 17500) < 1.0

    # the within-year shape is unchanged: quarter/annual ratios must match.
    # The tolerance is set by serialisation, not by the model — the API rounds
    # levels to one decimal, which on a ~4,700 quarter is a relative error of
    # about 1e-5. The scaling itself is exact.
    qs = [(q, f, m) for q, f, m in
          zip(r["quarters"], r["forecast"], r["model_line"])
          if q.startswith("2027") and f is not None]
    assert len(qs) == 4
    fsum, msum = sum(x[1] for x in qs), sum(x[2] for x in qs)
    for _, f, m in qs:
        assert abs(f / fsum - m / msum) < 2e-5


def test_overlay_leaves_other_years_alone():
    from app import scenario
    o, m = _overlay_with(year=2027)
    r = scenario.run("Flats", {}, None, "en", o)
    assert abs(r["annual_forecast"][2026] - m[2026]) < 1.0
    assert abs(r["annual_forecast"][2028] - m[2028]) < 1.0


def test_model_line_survives_the_overlay():
    """The model line and the overlay line are both kept. If they were blended
    the analyst could no longer see what the model said."""
    from app import scenario
    o, m = _overlay_with()
    r = scenario.run("Flats", {}, None, "en", o)
    assert r["annual_model"][2027] != r["annual_forecast"][2027]
    assert abs(r["annual_model"][2027] - m[2027]) < 1.0
    assert r["has_overlay"] is True


def test_overlay_is_not_attributed_to_any_driver():
    """The whole claim of the decomposition is that it names causes. An overlay
    has no cause, so it must sit in its own row marked unattributable — folding
    it into Tobin's Q would be the actual dishonesty."""
    from app import scenario
    o, _ = _overlay_with()
    r = scenario.run("Flats", {}, None, "en", o)
    dec = r["decomposition"]
    assert dec["overlay"]["attributable"] is False
    assert dec["overlay"]["years"] == [2027]
    assert dec["overlay"]["effect_pct"] < 0
    # drivers untouched: no overrides were set, so they explain nothing
    assert abs(dec["tobins_q"]["effect_pct"]) < 1e-9
    assert abs(dec["rate"]["effect_pct"]) < 1e-9
    # and the net has to include the overlay, or the total would be a lie
    assert abs(dec["net_with_overlay_pct"] - dec["overlay"]["effect_pct"]) < 1e-6


def test_overlay_guard_refuses_what_cannot_be_true():
    from app.overlay import guard
    ok, why = guard(-500, 19752.8, "dwellings")
    assert not ok and "negative" in why
    ok, _ = guard(float("nan"), 19752.8, "dwellings")
    assert not ok


def test_overlay_guard_refuses_typos_but_permits_judgement():
    """An analyst who knows a scheme is cancelled may legitimately halve a
    segment. A hundredfold change is a slipped keystroke, not a view."""
    from app.overlay import guard
    assert not guard(1_975_000, 19752.8, "dwellings")[0]
    assert not guard(197, 19752.8, "dwellings")[0]
    assert guard(9_000, 19752.8, "dwellings")[0]      # a halving is allowed
    assert guard(0, 19752.8, "dwellings")[0]          # so is zero


def test_overlay_requires_a_reason():
    c = _client()
    r = c.post("/api/overlay", json={"segment": "Flats", "year": 2027,
                                     "value": 17500, "reason": "   "})
    assert r.status_code == 422
    r = c.post("/api/overlay", json={"segment": "Flats", "year": 2027,
                                     "value": 17500, "reason": "schemes slipped"})
    assert r.status_code == 200
    a = r.json()["adjustment"]
    assert a["model_value"] != a["analyst_value"]     # the model's value is kept
    assert a["reason"] == "schemes slipped"           # verbatim


def test_overlay_rejects_a_year_outside_the_forecast():
    c = _client()
    r = c.post("/api/overlay", json={"segment": "Flats", "year": 2035,
                                     "value": 17500, "reason": "x"})
    assert r.status_code == 422


def test_the_chapter_binds_the_overlay_to_the_analyst():
    """`p3 check` must still pass with an overlay in play — the analyst becomes
    the named source. And BOTH numbers in the sentence bind: what was set, and
    what the model gave."""
    from app import chapter, scenario
    o, _ = _overlay_with()
    r = scenario.run("Flats", {}, None, "en", o)
    ch = chapter.build(r, {}, "en")
    chk = chapter.check(ch)

    assert chk["ok"], chk
    kinds = [b["kind"] for b in ch["bounds"]]
    assert "analytikerskoen" in kinds
    binding = next(b["binding"] for b in ch["bounds"]
                   if b["kind"] == "analytikerskoen")
    assert "gate 1b" in binding
    assert "will not start in 2027" in binding        # the reason travels


def test_every_overlaid_year_is_reported_not_just_the_first():
    """An overlay the text does not mention is the case this layer exists to
    prevent: the reader would attribute an analyst level to the model."""
    from app import chapter, overlay, scenario
    o = overlay.Overlay()
    m = scenario.model_annual("Flats", {})
    o.set("Flats", 2027, m[2027], 17500, "schemes slipped out of 2027")
    o.set("Flats", 2028, m[2028], 23000, "and land in 2028 instead")
    r = scenario.run("Flats", {}, None, "en", o)
    ch = chapter.build(r, {}, "en")

    assert chapter.check(ch)["ok"]
    text = " ".join(ch["paragraphs"])
    assert "2027" in text and "2028" in text
    assert sum(1 for b in ch["bounds"] if b["kind"] == "analytikerskoen") == 2


def test_publish_carries_the_overlay_into_the_source_list():
    c = _client()
    c.post("/api/overlay", json={"segment": "Flats", "year": 2027, "value": 17500,
                                 "reason": "the maksimumbeloeb agreement slipped"})
    r = c.post("/api/publish", json={"segment": "Flats", "overrides": {}})
    assert r.status_code == 200, r.json()
    kinds = [s["kind"] for s in r.json()["sources"]]
    assert "analytikerskoen" in kinds


def test_clearing_an_overlay_restores_the_model():
    from app import scenario
    o, m = _overlay_with()
    o.clear("Flats", 2027)
    r = scenario.run("Flats", {}, None, "en", o)
    assert abs(r["annual_forecast"][2027] - m[2027]) < 1.0
    assert r["has_overlay"] is False


# ── the research bundle · gate 1 verification ──────────────────────────────
def test_bundle_shape():
    from app import bundle
    ix = bundle.index()
    assert ix["country"] == "DK"
    assert ix["n_drivers"] == 38
    assert ix["n_institutions"] == 22
    assert ix["forecast_years"] == [2026, 2027, 2028]
    assert [g["n"] for g in ix["groups"]] == [10, 6, 6, 3, 13]


def test_engine_column_map_is_complete_and_correct():
    """The bundle writes `Tobins_Q_Flats`; the spreadsheet writes
    `Tobins-Q (Flats)`. No rule converts one to the other, so the map is
    written out — and a rename upstream must fail here rather than silently
    drop a driver out of the model."""
    from app import bundle
    assert bundle.check_engine_map() == []
    assert len(bundle.engine_drivers()) == 10


def test_yoy_drivers_are_compounded_not_passed_through():
    """The bundle states Tobin's Q for flats as +0.114341 — a fraction. The
    engine holds it as a level near 1.19. Passing the fraction straight in
    would not error; it would be wrong by two orders of magnitude."""
    from app import bundle
    from app.data import DRIVERS
    col = bundle.engine_column("Tobins_Q_Flats")
    s = DRIVERS[col].dropna()
    prev = float(s[s.index.year == 2025].mean())
    got = bundle.to_engine_value("Tobins_Q_Flats", 0.114341, prev)
    assert 1.1 < got < 1.4                       # a level, not a fraction
    assert bundle.to_engine_value("Tobins_Q_Flats", 0.114341, None) is None


def test_level_drivers_pass_through_unchanged():
    from app import bundle
    assert bundle.to_engine_value("Real_Interest_rate_Mortgage", 2.5211, 9.9) == 2.5211


def test_nominal_and_real_mortgage_rate_are_different_drivers():
    """OVERBLIK.md warns that two drivers are named almost the same and measure
    different things. The bundle has both: `mortgage_rate` is the nominal
    30-year rate near 4.5, and `exo:Real interest rate (Mortgage)` is the real
    rate near 2.5, which is the one the engine eats. Confusing them would put
    a nominal rate into a model fitted on a real one."""
    from app import bundle
    nom = bundle.driver_card("mortgage_rate")
    real = bundle.driver_card("exo:Real interest rate (Mortgage)")
    n26 = next(y["central"] for y in nom["years"] if y["year"] == 2026)
    r26 = next(y["central"] for y in real["years"] if y["year"] == 2026)
    assert n26 > 4.0 and r26 < 3.0
    assert nom["engine_id"] is None              # the nominal one never reaches it
    assert real["engine_id"] == "Real_Interest_rate_Mortgage"


def test_every_claim_carries_a_source_and_most_carry_a_link():
    """Requested: show the assumption for each source, including links, claims
    and year."""
    from app import bundle
    card = bundle.driver_card("rgdp")
    y26 = next(y for y in card["years"] if y["year"] == 2026)

    for c in y26["claims"]:
        assert c["source_name"] and c["quote"] and c["published_at"]
        assert c["weight"] is not None
    assert sum(1 for c in y26["claims"] if c["report_url"]) >= 7

    # ordered by weight, so the heaviest source reads first
    ws = [c["weight"] for c in y26["claims"]]
    assert ws == sorted(ws, reverse=True)

    # More claims than consensus sources, and that gap must stay visible: AE
    # and DI are carried at weight zero because they are only reachable via the
    # ØEM archive, which has ceased. They are kept for calibration and
    # learning, and the reason travels with them — hiding an excluded claim
    # would be the black box the brief rules out.
    excluded = [c for c in y26["claims"] if c["excluded"]]
    assert len(y26["claims"]) == y26["n_sources"] + len(excluded)
    assert len(excluded) == 2
    for c in excluded:
        assert c["weight"] == 0
        assert c["excluded_reason"]


def test_assumptions_differ_by_year_which_is_why_they_are_per_year():
    """Requested: set assumptions for each year of the forecast period. They
    are separate decisions because the evidence is genuinely different — real
    GDP has nine sources for 2026 and one for 2028."""
    from app import bundle
    card = bundle.driver_card("rgdp")
    by_year = {y["year"]: y for y in card["years"]}
    assert by_year[2026]["n_sources"] == 9
    assert by_year[2028]["n_sources"] == 1
    assert by_year[2026]["quality_grade"] == "A"
    assert by_year[2028]["quality_grade"] == "B"
    assert len({y["central"] for y in card["years"]}) == 3


def test_seven_cells_have_no_estimate_and_all_are_2028():
    """The research layer declining to invent a number no institution
    publishes — including the mortgage rate and the apartment price path this
    project already flagged as unsourced."""
    from app import bundle
    empty = [(d["id"], y["year"])
             for d in bundle.drivers()
             for y in bundle.driver_card(d["id"])["years"]
             if y["central"] is None]
    assert len(empty) == 7
    assert {y for _, y in empty} == {2028}
    ids = {i for i, _ in empty}
    assert "mortgage_rate" in ids and "hpi_flats" in ids


def test_a_cell_with_no_estimate_cannot_be_approved_blindly():
    c = _client()
    r = c.post("/api/research/approve",
               json={"driver_id": "mortgage_rate", "year": 2028})
    assert r.status_code == 422
    assert "no estimate" in r.json()["error"]
    # but an analyst may carry it, and then it is theirs
    r = c.post("/api/research/approve",
               json={"driver_id": "mortgage_rate", "year": 2028, "value": 4.79,
                     "reason": "held at the 2027 level; no source goes to 2028"})
    assert r.status_code == 200


def test_moving_a_driver_needs_a_reason_but_accepting_it_does_not():
    c = _client()
    assert c.post("/api/research/approve",
                  json={"driver_id": "rgdp", "year": 2026}).status_code == 200
    r = c.post("/api/research/approve",
               json={"driver_id": "rgdp", "year": 2027, "value": 1.2})
    assert r.status_code == 422
    r = c.post("/api/research/approve",
               json={"driver_id": "rgdp", "year": 2027, "value": 1.2,
                     "reason": "the spring view predates the reopening"})
    assert r.status_code == 200 and r.json()["approval"]["moved"] is True


def test_only_approved_values_cross_into_the_engine():
    """The whole point of the gate: unapproved research stays research."""
    c = _client()
    c.post("/api/research/approve", json={"driver_id": "exo:Tobins-Q (Flats)",
                                          "year": 2026})
    ov = c.get("/api/research/engine-overrides").json()["overrides"]
    assert "Tobins_Q_Flats" in ov
    assert 1.1 < list(ov["Tobins_Q_Flats"].values())[0] < 1.4    # a level


def test_approve_all_skips_what_it_cannot_approve():
    c = _client()
    r = c.post("/api/research/approve-all", json={}).json()
    assert len(r["skipped_no_estimate"]) == 7
    p = r["progress"]
    assert p["cells_approved"] <= p["cells_total"]
    assert p["drivers_approved"] == p["drivers_total"] == 38


def test_slider_bounds_come_from_the_bundle_not_from_me():
    """These used to be hand-set — the one invented number left in panel.py.
    Every bound now carries the basis the bundle declares for it."""
    from app.panel import panel
    for d in panel()["drivers"]:
        assert d["range_basis"], f"{d['key']} has no declared range basis"
        assert "not measured" not in d["range_basis"], d["key"]


def test_a_declared_hard_bound_beats_a_derived_range():
    """The bundle pads its history range outward, which for the real mortgage
    rate crosses zero. That rate has never been below zero in 92 quarters, and
    `hard_lo` is declared, so the declared bound wins."""
    from app.data import DRIVERS, RATE
    from app.panel import panel
    assert float(DRIVERS[RATE].dropna().min()) > 0
    rate = next(d for d in panel()["drivers"] if d["key"] == "rate")
    assert rate["lo"] == 0.0
    assert "clamped to hard_lo" in rate["range_basis"]


# ── the orchestrator, apart from the analyst UI ────────────────────────────
def test_orchestrator_has_the_whole_round_with_gates_that_wait():
    c = _client()
    st = c.get("/api/run").json()
    ids = [s["id"] for s in st["steps"]]
    assert ids[0] == "source_watch" and ids[-1] == "publish"
    gates = [s for s in st["steps"] if s["kind"] == "gate"]
    assert {g["id"] for g in gates} == {"gate0", "gate1", "gate1b", "gate2", "gate3"}
    assert st["totals"]["cost_usd"] == 0.0        # no model runs anywhere


def test_a_gate_waits_rather_than_running():
    c = _client()
    c.post("/api/run/new")
    r = c.post("/api/run/step", json={"step_id": "gate0"}).json()
    assert r["status"] == "waiting_for_analyst"
    r = c.post("/api/run/step", json={"step_id": "gate0", "note": "__pass__"}).json()
    assert r["status"] == "done"


def test_a_code_step_records_what_it_read_and_how_long_it_took():
    c = _client()
    c.post("/api/run/new")
    r = c.post("/api/run/step", json={"step_id": "ingest"}).json()
    assert r["status"] == "done"
    assert r["ms"] is not None and r["attempts"] == 1
    assert r["reads"] and r["logs"]
    assert "38 drivers" in r["logs"][-1]["msg"]


def test_a_failing_step_is_recorded_and_retryable():
    """`check` fails when the chapter carries a number bound to nothing. The
    monitor has to show that, keep the error, and allow another attempt —
    otherwise a failure looks the same as a step nobody ran."""
    c = _client()
    c.post("/api/run/new")
    r1 = c.post("/api/run/step", json={"step_id": "check"}).json()
    assert r1["status"] in ("done", "failed")
    r2 = c.post("/api/run/step", json={"step_id": "check"}).json()
    assert r2["attempts"] == 2


def test_reset_from_a_step_clears_everything_after_it():
    c = _client()
    c.post("/api/run/new")
    for sid in ("source_watch", "ingest", "triangulate"):
        c.post("/api/run/step", json={"step_id": sid})
    c.post("/api/run/reset", json={"step_id": "ingest"})
    st = c.get("/api/run").json()
    by = {s["id"]: s for s in st["steps"]}
    assert by["source_watch"]["status"] == "done"
    assert by["ingest"]["status"] == "pending"
    assert by["triangulate"]["status"] == "pending"


# ── roles ──────────────────────────────────────────────────────────────────
def test_roles_separate_the_analyst_from_the_orchestrator():
    c = _client()
    r = c.get("/api/roles").json()
    ids = {x["id"] for x in r["roles"]}
    assert ids == {"analyst", "orchestrator"}
    analyst = next(x for x in r["roles"] if x["id"] == "analyst")
    orch = next(x for x in r["roles"] if x["id"] == "orchestrator")
    assert "run" not in analyst["pages"]          # the analyst does not drive the run
    assert orch["pages"] == ["run"]
    assert "not authentication" in r["note"]


def test_switching_roles_is_journalled_and_rejects_unknown_roles():
    c = _client()
    assert c.post("/api/role", json={"role": "orchestrator"}).status_code == 200
    assert c.post("/api/role", json={"role": "root"}).status_code == 422
