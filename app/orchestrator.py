"""The orchestrator — a place to run and watch the round, apart from the
analyst's own pages.

The brief asks for observability and control that is *not* the analyst UI:
step status, logs, token and cost per run, failure alerts, trigger per country,
pause and retry, and a review gate the workflow waits at. It also asks for "no
black box": the UI must read directly from workflow state rather than from a
summary someone wrote by hand.

So this is a small durable state machine, and the page over it is a monitor
rather than a control panel with its own memory. Every step records what it
read, what it wrote, how long it took and what it cost — and a step that waits
for a human says so and stays waiting.

**What this is not.** It is not Temporal. Temporal is what the brief names, it
is already deployed on CDP, and it is the right answer for a round whose gates
wait for weeks. This has the same shape — named steps, explicit state,
durable-looking transitions, retry — so the mapping later is a port rather than
a redesign, and it needs nothing but Python to run on a laptop today.

The honest difference: this state lives in memory for the session. Kill the
process and the round is gone. Temporal is what fixes that, not more code here.
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

STATUSES = ("pending", "running", "waiting_for_analyst", "done", "failed", "skipped")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Step:
    id: str
    title: str
    kind: str                 # code | llm | gate
    owner: str                # which agent or gate it belongs to
    status: str = "pending"
    started_at: str | None = None
    ended_at: str | None = None
    ms: float | None = None
    tokens: int = 0
    cost_usd: float = 0.0
    reads: list = field(default_factory=list)
    writes: list = field(default_factory=list)
    logs: list = field(default_factory=list)
    error: str | None = None
    attempts: int = 0

    def log(self, msg: str) -> None:
        self.logs.append({"ts": _now(), "msg": msg})

    def to_dict(self):
        return asdict(self)


# The round, as the chain defines it. `gate` steps stop and wait; `code` steps
# run deterministically; `llm` steps would cost tokens — and in this pilot there
# are none, which is why every cost below is zero and the page says so.
def _fresh_steps() -> list:
    return [
        Step("source_watch", "Source watch · check every source for a new edition",
             "code", "P1", reads=["source register"], writes=["editions held"]),
        Step("gate0", "GATE 0 · fresh? — the analyst opens the round",
             "gate", "analyst"),
        Step("ingest", "Ingest · parse the reports we hold into claims",
             "code", "P1", reads=["research bundle"], writes=["claims"]),
        Step("triangulate", "Triangulate · weight the claims into one path per driver",
             "code", "P1", reads=["claims"], writes=["central estimates"]),
        Step("validate", "Validate · flag what needs human eyes (never stops a number)",
             "code", "P1", reads=["central estimates"], writes=["needs_human flags"]),
        Step("gate1", "GATE 1 · review — every driver, every forecast year",
             "gate", "analyst"),
        Step("gate1b", "GATE 1b · overlay — levels set by hand, where a driver cannot carry it",
             "gate", "analyst"),
        Step("forecast", "P2 · run the model — deterministic, zero LLM",
             "code", "P2", reads=["approved drivers", "starts history"],
             writes=["forecast by segment"]),
        Step("gate2", "GATE 2 · sign-off — config rows, never numbers",
             "gate", "analyst"),
        Step("brief", "P3 · build the chapter brief",
             "code", "P3", reads=["forecast", "drivers", "style rules"],
             writes=["brief"]),
        Step("draft", "P3 · assemble the chapter",
             "code", "P3", reads=["brief"], writes=["draft"]),
        Step("check", "p3 check · bind every number to a source, or fail",
             "code", "P3", reads=["draft"], writes=["check result"]),
        Step("gate3", "GATE 3 · red pen — the analyst edits the text",
             "gate", "analyst"),
        Step("publish", "Publish · chapter + machine-built source list",
             "code", "P3", reads=["draft"], writes=["published page"]),
    ]


class Run:
    def __init__(self, country: str = "DK", label: str = "September 2026"):
        self.id = f"{country.lower()}-{int(time.time())}"
        self.country = country
        self.label = label
        self.created_at = _now()
        self.steps = _fresh_steps()
        self.events: list = []

    # ── lookups ────────────────────────────────────────────────────────────
    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)

    @property
    def current(self) -> Step | None:
        """The first step not finished — what the round is waiting on."""
        return next((s for s in self.steps
                     if s.status in ("pending", "running", "waiting_for_analyst",
                                     "failed")), None)

    def event(self, msg: str, **kw) -> None:
        self.events.append({"ts": _now(), "msg": msg, **kw})

    # ── transitions ────────────────────────────────────────────────────────
    def run_step(self, step_id: str, fn=None) -> dict:
        """Run one step. A gate does not execute — it announces that it is
        waiting, which is the whole reason the workflow exists."""
        s = self.step(step_id)
        if s is None:
            return {"error": f"unknown step '{step_id}'"}

        if s.kind == "gate":
            s.status = "waiting_for_analyst"
            s.started_at = s.started_at or _now()
            s.log("waiting for a decision — the workflow sleeps here")
            self.event(f"{s.id}: waiting for the analyst", step=s.id)
            return s.to_dict()

        s.attempts += 1
        s.status = "running"
        s.started_at = _now()
        s.error = None
        s.log(f"attempt {s.attempts}")
        t0 = time.perf_counter()
        try:
            if fn is not None:
                note = fn()
                if note:
                    s.log(str(note))
            s.status = "done"
        except Exception as exc:                       # noqa: BLE001
            s.status = "failed"
            s.error = f"{type(exc).__name__}: {exc}"
            s.log(s.error)
            s.logs.append({"ts": _now(), "msg": traceback.format_exc(limit=3)})
            self.event(f"{s.id}: FAILED — {s.error}", step=s.id, level="error")
        finally:
            s.ms = round((time.perf_counter() - t0) * 1000, 2)
            s.ended_at = _now()
        if s.status == "done":
            self.event(f"{s.id}: done in {s.ms} ms", step=s.id)
        return s.to_dict()

    def complete_gate(self, step_id: str, note: str = "") -> dict:
        s = self.step(step_id)
        if s is None or s.kind != "gate":
            return {"error": f"'{step_id}' is not a gate"}
        s.status = "done"
        s.ended_at = _now()
        if note:
            s.log(note)
        self.event(f"{s.id}: passed", step=s.id)
        return s.to_dict()

    def reset(self, step_id: str | None = None) -> None:
        if step_id is None:
            self.steps = _fresh_steps()
            self.event("run reset")
            return
        i = next((k for k, s in enumerate(self.steps) if s.id == step_id), None)
        if i is None:
            return
        fresh = _fresh_steps()
        for k in range(i, len(self.steps)):
            self.steps[k] = fresh[k]
        self.event(f"reset from {step_id}", step=step_id)

    # ── what the monitor page shows ────────────────────────────────────────
    def state(self) -> dict:
        done = [s for s in self.steps if s.status == "done"]
        return {
            "id": self.id,
            "country": self.country,
            "label": self.label,
            "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
            "current": (self.current.id if self.current else None),
            "counts": {st: sum(1 for s in self.steps if s.status == st)
                       for st in STATUSES},
            "totals": {
                "steps": len(self.steps),
                "done": len(done),
                "elapsed_ms": round(sum(s.ms or 0 for s in self.steps), 2),
                "tokens": sum(s.tokens for s in self.steps),
                "cost_usd": round(sum(s.cost_usd for s in self.steps), 4),
            },
            "cost_note": "Zero, and not rounded to zero: no language model runs "
                         "in this pilot. The column exists because the brief asks "
                         "for cost per step, and it is what a company API key "
                         "would populate.",
            "events": self.events[-40:],
            "durability": "In memory for this session. Temporal is what makes a "
                          "round survive the process — this has the same shape so "
                          "the move is a port, not a redesign.",
        }
