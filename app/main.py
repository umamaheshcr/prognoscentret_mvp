"""Mimir MVP — the gate-1 console.

Local only, by decision. The pilot displays verbatim quotes from licensed bank
research, which is the same thing that has kept the production approval console
undeployed. Running on 127.0.0.1 means that question never has to be answered
to get a demo, and no licensed material leaves the machine.

    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

from pathlib import Path
import hashlib
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import (auth, bundle, chapter, data, guard, i18n, journal, model, orchestrator,
               overlay, scenario, sources, verify)
from .panel import panel

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Mimir MVP · the four gates", docs_url="/api/docs")

# Every request passes the gate first, including the static mount below: an
# app-level dependency would not cover a mounted sub-application. Unset
# MIMIR_BASIC keeps localhost working and refuses everything else. See auth.py.
app.add_middleware(auth.BasicAuth)


@app.get("/healthz")
def healthz():
    """Exempt from auth — a platform health check cannot log in."""
    return {"ok": True, "gates": 5, "exogenous_file": data.EXO_FILE.name}


# Session state. One analyst, one round, in memory — a pilot, not a product.
STATE = {
    "round_opened": False,
    "overlay": overlay.Overlay(),   # gate 1b — analyst levels, per segment/year
    "verify": verify.Verification(),  # gate 1 — driver approvals, per year
    "run": orchestrator.Run(),        # the orchestrator's own state
    "role": "analyst",                # analyst | orchestrator
    "specs": {},                 # segment → model.Spec, set at gate 2
    "signed_off": False,
    "published": None,
}


class ForecastRequest(BaseModel):
    segment: str = "Flats"
    overrides: dict = Field(default_factory=dict)
    lang: str = "en"


class OpenRoundRequest(BaseModel):
    rejected: list = Field(default_factory=list)   # source keys judged too old/thin
    reason: str = ""


class ConfigRequest(BaseModel):
    segment: str
    tobins_q: str | None = None
    use_rate: bool | None = None
    seasonals: bool | None = None
    tq_transform: str | None = None


class SignOffRequest(BaseModel):
    reason: str = ""


class OverlayRequest(BaseModel):
    segment: str = "Flats"
    year: int
    value: float
    reason: str = ""
    overrides: dict = Field(default_factory=dict)


class ClearOverlayRequest(BaseModel):
    segment: str = "Flats"
    year: int | None = None


class ApproveRequest(BaseModel):
    driver_id: str
    year: int
    value: float | None = None     # omit to accept the agent's own estimate
    reason: str = ""


class ApproveAllRequest(BaseModel):
    only_unmoved: bool = True      # accept the agent's estimate where untouched


class StepRequest(BaseModel):
    step_id: str
    note: str = ""


class RoleRequest(BaseModel):
    role: str = "analyst"


class PublishRequest(BaseModel):
    segment: str = "Flats"
    overrides: dict = Field(default_factory=dict)
    edited: str | None = None
    lang: str = "en"


class DecisionRequest(BaseModel):
    gate: str = "1"
    driver: str
    value: float
    reason: str = ""
    lang: str = "en"


class EditRequest(BaseModel):
    section: str = "house_prices"
    original: str = ""
    edited: str = ""
    reason: str = ""


@app.get("/")
def index():
    """Serve the page with every asset URL stamped by its file hash.

    Without this a `git pull` can leave a browser running yesterday's app.js
    against today's API — the network log shows a fresh 200 while the page is
    still executing the cached script, which is a genuinely confusing failure
    to debug. The stamp changes only when a file changes, so caching still
    works; it just cannot go stale.
    """
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("style.css", "i18n.js", "app.js", "verify.js"):
        f = STATIC / name
        if not f.exists():
            continue
        stamp = hashlib.sha1(f.read_bytes()).hexdigest()[:10]
        html = html.replace(f'/static/{name}"', f'/static/{name}?v={stamp}"')
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.get("/api/panel")
def get_panel(lang: str = "en"):
    lang = i18n.norm(lang)
    p = panel(lang)
    p["meta"] = data.meta(lang)
    p["diagnostics"] = model.diagnostics(STATE["specs"])
    p["journal"] = journal.count_by_gate()
    p["state"] = {"round_opened": STATE["round_opened"],
                  "signed_off": STATE["signed_off"],
                  "published": STATE["published"] is not None}
    p["tq_choices"] = model.TQ_CHOICES
    p["lang"] = lang
    return p


# ── gate 0 · fresh? ─────────────────────────────────────────────────────────
@app.get("/api/sources")
def get_sources():
    return sources.register(STATE["round_opened"])


@app.post("/api/open-round")
def post_open_round(req: OpenRoundRequest):
    """The round starts because the analyst says so, not because a date
    arrived. A rejected source is journalled — gate 0 had no recorded history
    in production, and this is where that starts."""
    known = sources.by_key()
    unknown = [k for k in req.rejected if k not in known]
    if unknown:
        return JSONResponse({"error": f"unknown source(s): {unknown}"}, 422)
    if req.rejected and not req.reason.strip():
        return JSONResponse(
            {"error": "a reason is required",
             "reason": "Rejecting a source is a decision. Unrecorded, it is gone, "
                       "and gate 0's history stays empty — which is the hole this closes."},
            422)
    STATE["round_opened"] = True
    entry = journal.record("0", "open_round", {
        "rejected": req.rejected,
        "rejected_names": [known[k]["name"] for k in req.rejected],
        "reason": req.reason.strip(),
        "sources_held": len(known) - len(req.rejected),
    })
    return {"recorded": entry, "opened": True}


@app.post("/api/forecast")
def post_forecast(req: ForecastRequest):
    """Called live as the analyst drags a slider. Coefficients are fitted once
    at start-up, so this is a matrix multiply — the timing is returned so the
    interface can show that it is honest about being live."""
    t0 = time.perf_counter()
    if req.segment not in data.SEGMENTS:
        return JSONResponse({"error": f"unknown segment '{req.segment}'"}, 400)

    clean, warnings = {}, []
    for key, value in (req.overrides or {}).items():
        v = guard.check(key, value, req.lang)
        if not v.ok:
            return JSONResponse(
                {"error": "guard refused", "driver": key, "reason": v.reason,
                 "kind": v.kind}, 422)
        if v.kind == "warned":
            warnings.append({"driver": key, "reason": v.reason})
        clean[key] = float(value)

    out = scenario.run(req.segment, clean, STATE["specs"].get(req.segment),
                       i18n.norm(req.lang), STATE["overlay"])
    out["warnings"] = warnings
    out["overrides"] = clean
    out["compute_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return out


# ── gate 2 · sign-off ───────────────────────────────────────────────────────
@app.post("/api/config")
def post_config(req: ConfigRequest):
    """Gate 2 edits the CONFIG ROW, never a number. A hand-edited value is
    untraceable; a weight is not. Changing a row refits the model and the
    backtest re-scores it — the backtest is the referee."""
    if req.segment not in data.SEGMENTS:
        return JSONResponse({"error": f"unknown segment '{req.segment}'"}, 400)
    cur = STATE["specs"].get(req.segment) or model.DEFAULT_SPECS[req.segment]
    tq = req.tobins_q or cur.tobins_q
    if tq not in data.DRIVERS.columns:
        return JSONResponse({"error": f"no such driver '{tq}'"}, 422)

    new = model.Spec(
        tobins_q=tq,
        use_rate=cur.use_rate if req.use_rate is None else req.use_rate,
        seasonals=cur.seasonals if req.seasonals is None else req.seasonals,
        tq_transform=req.tq_transform or cur.tq_transform,
        holdout=cur.holdout,
    )
    before = model.get_fit(req.segment, cur)
    after = model.get_fit(req.segment, new)
    STATE["specs"][req.segment] = new

    journal.record("2", "config_row", {
        "segment": req.segment,
        "before": cur.as_dict(),
        "after": new.as_dict(),
        "holdout_mape_before": round(before.holdout_mape, 1),
        "holdout_mape_after": round(after.holdout_mape, 1),
        "verdict": "improved" if after.holdout_mape < before.holdout_mape else "worse",
    })
    return {
        "segment": req.segment,
        "spec": new.as_dict(),
        "before": {"holdout_mape": round(before.holdout_mape, 1),
                   "r2": round(before.r2, 3),
                   "b_tobins_q": round(before.b_tobins_q, 4),
                   "b_rate": round(before.b_rate, 4)},
        "after": {"holdout_mape": round(after.holdout_mape, 1),
                  "r2": round(after.r2, 3),
                  "b_tobins_q": round(after.b_tobins_q, 4),
                  "b_rate": round(after.b_rate, 4)},
        "signs_ok": after.b_tobins_q > 0 and (not new.use_rate or after.b_rate < 0),
        "diagnostics": model.diagnostics(STATE["specs"]),
    }


@app.post("/api/signoff")
def post_signoff(req: SignOffRequest):
    """What the backtest taught is journalled and routed to research: a missing
    driver is research, not code."""
    if not req.reason.strip():
        return JSONResponse(
            {"error": "a reason is required",
             "reason": "Gate 2 had no recorded history in production. What the "
                       "backtest taught is exactly what the next round needs."}, 422)
    STATE["signed_off"] = True
    entry = journal.record("2", "signoff", {
        "reason": req.reason.strip(),
        "specs": {s: (STATE["specs"].get(s) or model.DEFAULT_SPECS[s]).as_dict()
                  for s in data.SEGMENTS},
        "accuracy": {d["segment"]: d["holdout_mape"]
                     for d in model.diagnostics(STATE["specs"])},
    })
    return {"recorded": entry, "signed_off": True}


# ── gate 3 · red pen, and publish ───────────────────────────────────────────
@app.post("/api/chapter")
def post_chapter(req: PublishRequest):
    clean = {k: float(v) for k, v in (req.overrides or {}).items()}
    result = scenario.run(req.segment, clean, STATE["specs"].get(req.segment),
                          i18n.norm(req.lang), STATE["overlay"])
    ch = chapter.build(result, clean, i18n.norm(req.lang))
    ch["check"] = chapter.check(ch, req.edited)
    ch["sources"] = chapter.source_list(ch)
    return ch


@app.post("/api/publish")
def post_publish(req: PublishRequest):
    """The check binds every number to a source, or the publish does not
    happen. In production this exits 1."""
    clean = {k: float(v) for k, v in (req.overrides or {}).items()}
    result = scenario.run(req.segment, clean, STATE["specs"].get(req.segment),
                          i18n.norm(req.lang), STATE["overlay"])
    ch = chapter.build(result, clean, i18n.norm(req.lang))
    chk = chapter.check(ch, req.edited)
    if not chk["ok"]:
        return JSONResponse({"error": "check failed", "check": chk}, 422)

    ch["check"] = chk
    ch["sources"] = chapter.source_list(ch)
    ch["published_text"] = req.edited or " ".join(ch["paragraphs"])
    STATE["published"] = ch
    journal.record("pub", "publish", {
        "section": ch["section"],
        "segment": req.segment,
        "numbers_bound": chk["bound"],
        "sources": len(ch["sources"]),
        "overrides": clean,
    })
    return ch


@app.post("/api/guard")
def post_guard(driver: str, value: float, lang: str = "en"):
    v = guard.check(driver, value, lang)
    return {"ok": v.ok, "kind": v.kind, "reason": v.reason}


@app.post("/api/decision")
def post_decision(req: DecisionRequest):
    """Commit an override. A reason is required — that is the whole point.
    The agent's proposal is kept beside the analyst's value."""
    v = guard.check(req.driver, req.value, req.lang)
    if not v.ok:
        return JSONResponse({"error": "guard refused", "reason": v.reason}, 422)
    if not req.reason.strip():
        lang = i18n.norm(req.lang)
        return JSONResponse(
            {"error": "a reason is required",
             "reason": i18n.GUARD["reason_required"][lang]}, 422)

    from .panel import BY_KEY
    d = BY_KEY[req.driver]
    entry = journal.record("1", "override", {
        "driver": req.driver,
        "label": d.label,
        "year": d.year,
        "agent_proposed": d.agent,
        "analyst_value": req.value,
        "reason": req.reason.strip(),      # verbatim, never normalised
        "guard": v.kind,
        "source": d.source,
    })
    return {"recorded": entry, "guard": v.kind,
            "repeated": journal.repeated_corrections()}


# ── gate 1b · the analyst overlay ───────────────────────────────────────────
@app.get("/api/overlay")
def get_overlay(segment: str = "Flats", lang: str = "en"):
    """What the model says per year, and what the analyst has put beside it."""
    if segment not in data.SEGMENTS:
        return JSONResponse({"error": f"unknown segment '{segment}'"}, 400)
    return {
        "segment": segment,
        "unit": data.SEGMENTS[segment]["unit"],
        "model": scenario.model_annual(segment, {}, STATE["specs"].get(segment)),
        "adjustments": STATE["overlay"].as_list(segment),
    }


@app.post("/api/overlay")
def post_overlay(req: OverlayRequest):
    """Set the forecast level for one year by hand.

    The model's own value is stored beside the analyst's, the reason is kept
    verbatim, and the two lines stay separate everywhere they are drawn. This
    is the only place in the pilot where a number does not come from the model,
    so it is also the only place that records who decided it.
    """
    if req.segment not in data.SEGMENTS:
        return JSONResponse({"error": f"unknown segment '{req.segment}'"}, 400)

    clean = {k: float(v) for k, v in (req.overrides or {}).items()}
    model_annual = scenario.model_annual(req.segment, clean,
                                         STATE["specs"].get(req.segment))
    if req.year not in model_annual:
        return JSONResponse(
            {"error": f"{req.year} is not a forecast year",
             "reason": f"the forecast covers {sorted(model_annual)}"}, 422)

    mv = model_annual[req.year]
    ok, why = overlay.guard(req.value, mv, data.SEGMENTS[req.segment]["unit"])
    if not ok:
        return JSONResponse({"error": "guard refused", "reason": why}, 422)
    if not req.reason.strip():
        return JSONResponse(
            {"error": "a reason is required",
             "reason": "An overlay is the one number with no model behind it, so "
                       "it is the one number that cannot exist without a stated "
                       "judgement. Without it, `p3 check` has nothing to bind to."},
            422)

    a = STATE["overlay"].set(req.segment, req.year, mv, req.value, req.reason)
    entry = journal.record("1b", "overlay", {
        "segment": req.segment,
        "year": req.year,
        "model_value": mv,
        "analyst_value": float(req.value),
        "delta_pct": round(a.delta_pct, 3),
        "reason": req.reason.strip(),      # verbatim
        "attributable_to_a_driver": False,
    })
    return {"recorded": entry, "adjustment": a.to_dict(), "guard": why,
            "adjustments": STATE["overlay"].as_list(req.segment)}


@app.delete("/api/overlay")
def delete_overlay(req: ClearOverlayRequest):
    STATE["overlay"].clear(req.segment, req.year)
    journal.record("1b", "overlay_cleared",
                   {"segment": req.segment, "year": req.year})
    return {"adjustments": STATE["overlay"].as_list(req.segment)}



# ── roles ───────────────────────────────────────────────────────────────────
# The brief asks for multiple roles later. Two are enough to prove the shape:
# the analyst decides at the gates, the orchestrator runs and watches the round.
# Nothing here is authentication — it is a role switch, and it says so.
ROLES = {
    "analyst": {
        "label": {"en": "Analyst", "sv": "Analytiker"},
        "may": ["verify", "overlay", "signoff", "red_pen", "publish"],
        # `verify` is gate 1 now. `1` is the forecast page — kept separate,
        # because the forecast must not sit on the verification page.
        "pages": ["0", "verify", "1", "1b", "2", "3", "pub"],
    },
    "orchestrator": {
        "label": {"en": "Orchestrator", "sv": "Orkestrerare"},
        "may": ["run_step", "retry", "reset", "trigger"],
        "pages": ["run"],
    },
}


@app.get("/api/roles")
def get_roles(lang: str = "en"):
    lang = i18n.norm(lang)
    return {
        "current": STATE["role"],
        "roles": [{"id": k, "label": v["label"].get(lang, v["label"]["en"]),
                   "may": v["may"], "pages": v["pages"]} for k, v in ROLES.items()],
        "note": "A role switch, not authentication. Real access control belongs "
                "with the company login, wherever this is eventually hosted.",
    }


@app.post("/api/role")
def post_role(req: RoleRequest):
    if req.role not in ROLES:
        return JSONResponse({"error": f"unknown role '{req.role}'"}, 422)
    STATE["role"] = req.role
    journal.record("role", "switch", {"role": req.role})
    return {"current": req.role, "pages": ROLES[req.role]["pages"]}


# ── gate 1 · driver verification (research bundle) ──────────────────────────
@app.get("/api/research")
def get_research(lang: str = "en"):
    """The driver index. No forecast numbers here, by request — verification
    and forecasting are separate steps."""
    if not bundle.available():
        return JSONResponse({"error": "the research bundle is not present"}, 503)
    ix = bundle.index(i18n.norm(lang))
    v = STATE["verify"]
    ix["progress"] = v.progress()
    for row in ix["drivers"]:
        row["state"] = v.driver_state(row["id"])
    return ix


@app.get("/api/research/driver")
def get_research_driver(driver_id: str, lang: str = "en"):
    c = verify.card(driver_id, STATE["verify"])
    if not c:
        return JSONResponse({"error": f"unknown driver '{driver_id}'"}, 404)
    return c


@app.post("/api/research/approve")
def post_approve(req: ApproveRequest):
    """Approve one driver for one year. A reason is required only when the
    analyst moves the number — accepting the agent's own estimate is not a
    correction and does not need explaining."""
    card = bundle.driver_card(req.driver_id)
    if not card:
        return JSONResponse({"error": f"unknown driver '{req.driver_id}'"}, 404)
    y = next((x for x in card["years"] if x["year"] == req.year), None)
    if y is None:
        return JSONResponse(
            {"error": f"{req.year} is not a forecast year",
             "reason": f"this driver covers {[x['year'] for x in card['years']]}"},
            422)

    if y["central"] is None and req.value is None:
        return JSONResponse(
            {"error": "no estimate to approve",
             "reason": f"{card['label']} has no estimate for {req.year}: "
                       f"coverage is '{y.get('coverage')}' and no institution "
                       "publishes the number. Set a value by hand if you are "
                       "willing to carry it, or leave the cell empty."}, 422)

    agent_value = y["central"]
    value = agent_value if req.value is None else float(req.value)
    if agent_value is None:
        agent_value = value
    moved = abs(value - agent_value) > 1e-9
    if moved and not req.reason.strip():
        return JSONResponse(
            {"error": "a reason is required",
             "reason": "Moving a driver away from the triangulated estimate is a "
                       "correction, and the agent reads it before the next round. "
                       "Accepting the estimate needs no reason; changing it does."},
            422)

    a = STATE["verify"].approve(req.driver_id, req.year, agent_value, value,
                               req.reason)
    journal.record("1", "driver_approved", {
        "driver": req.driver_id,
        "label": card["label"],
        "year": req.year,
        "agent_proposed": agent_value,
        "analyst_value": value,
        "moved": moved,
        "reason": req.reason.strip(),
        "n_sources": y["n_sources"],
        "quality": y["quality_grade"],
        "engine_id": card.get("engine_id"),
    })
    return {"approval": a.to_dict(), "progress": STATE["verify"].progress(),
            "state": STATE["verify"].driver_state(req.driver_id)}


@app.post("/api/research/approve-all")
def post_approve_all(req: ApproveAllRequest):
    """Carl's 'Approve all unchanged'. Accepts the agent's estimate everywhere
    the analyst has not already decided — and only there."""
    v = STATE["verify"]
    n, skipped = 0, []
    for d in bundle.drivers():
        card = bundle.driver_card(d["id"])
        for y in card["years"]:
            if y["central"] is None:
                skipped.append({"driver": d["id"], "year": y["year"]})
                continue
            if req.only_unmoved and v.get(d["id"], y["year"]) is not None:
                continue
            v.approve(d["id"], y["year"], y["central"], y["central"], "")
            n += 1
    journal.record("1", "approve_all_unchanged",
                   {"cells": n, "skipped_no_estimate": len(skipped)})
    return {"approved": n, "skipped_no_estimate": skipped,
            "progress": v.progress()}


@app.delete("/api/research/approve")
def delete_approve(driver_id: str, year: int | None = None):
    STATE["verify"].clear(driver_id, year)
    return {"progress": STATE["verify"].progress(),
            "state": STATE["verify"].driver_state(driver_id)}


@app.get("/api/research/engine-overrides")
def get_engine_overrides():
    """What crosses from research into the model: approved values only, in the
    engine's own units. Ten of the 38 drivers can reach it at all."""
    ov = STATE["verify"].engine_overrides()
    return {
        "overrides": ov,
        "engine_drivers": {k: bundle.engine_column(k)
                           for k in bundle.engine_drivers()},
        "units": bundle.ENGINE_UNITS,
        "note": "A year-on-year fraction from the bundle is compounded onto the "
                "engine's own last actual level. Feeding the fraction straight in "
                "would not error — it would be wrong by two orders of magnitude.",
    }


# ── the orchestrator ────────────────────────────────────────────────────────
@app.get("/api/run")
def get_run():
    return STATE["run"].state()


@app.post("/api/run/step")
def post_run_step(req: StepRequest):
    """Run one step, or pass a gate. The work each code step does here is the
    real thing where the pilot has it, and a recorded no-op where the pilot
    deliberately does not — a step that pretends to do research would make the
    monitor a lie."""
    run = STATE["run"]
    step = run.step(req.step_id)
    if step is None:
        return JSONResponse({"error": f"unknown step '{req.step_id}'"}, 404)

    if step.kind == "gate":
        return run.complete_gate(req.step_id, req.note) if req.note == "__pass__" \
            else run.run_step(req.step_id)

    def work():
        if req.step_id == "ingest":
            n = len(bundle.drivers())
            return f"read {n} drivers from the research bundle · frozen 2026-08-15"
        if req.step_id == "triangulate":
            cells = sum(len(bundle.driver_card(d["id"])["years"])
                        for d in bundle.drivers())
            return f"{cells} driver-years already triangulated in the bundle"
        if req.step_id == "validate":
            thin = [d["id"] for d in bundle.drivers()
                    for y in bundle.driver_card(d["id"])["years"]
                    if (y.get("n_sources") or 0) < 3]
            return f"{len(thin)} driver-years rest on fewer than 3 sources"
        if req.step_id == "forecast":
            out = scenario.run("Flats", {}, STATE["specs"].get("Flats"), "en",
                               STATE["overlay"])
            return f"Flats 2026 = {out['annual_forecast'][2026]:,.0f} dwellings"
        if req.step_id == "brief":
            return "brief assembled from the forecast and the approved drivers"
        if req.step_id == "draft":
            return "chapter assembled by template — not P3's language model"
        if req.step_id == "check":
            res = scenario.run("Flats", {}, STATE["specs"].get("Flats"), "en",
                               STATE["overlay"])
            ch = chapter.build(res, {}, "en")
            c = chapter.check(ch)
            if not c["ok"]:
                raise ValueError(c["verdict"])
            return c["verdict"]
        if req.step_id == "publish":
            return "published to the page"
        if req.step_id == "source_watch":
            reg = sources.register()
            return (f"{reg['n_institutions']} institutions hold "
                    f"{reg['n_claims']} claims; {len(reg['silent'])} declared "
                    "sources contributed nothing to this vintage")
        return "no work defined for this step in the pilot"

    return run.run_step(req.step_id, work)


@app.post("/api/run/reset")
def post_run_reset(req: StepRequest):
    STATE["run"].reset(req.step_id or None)
    return STATE["run"].state()


@app.post("/api/run/new")
def post_run_new():
    STATE["run"] = orchestrator.Run()
    return STATE["run"].state()


@app.post("/api/edit")
def post_edit(req: EditRequest):
    """Gate 3. A correction that returns becomes a numbered style rule; the
    pilot records and counts, it does not yet inject."""
    if not req.reason.strip():
        return JSONResponse({"error": "a reason is required"}, 422)
    entry = journal.record("3", "red_pen", {
        "section": req.section,
        "original": req.original,
        "edited": req.edited,
        "reason": req.reason.strip(),
    })
    return {"recorded": entry, "next_style_rule": 44}


@app.get("/api/journal")
def get_journal():
    return {"entries": journal.read_all(),
            "by_gate": journal.count_by_gate(),
            "repeated": journal.repeated_corrections()}


app.mount("/static", StaticFiles(directory=STATIC), name="static")
