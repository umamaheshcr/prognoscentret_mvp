# Prognosecenteret · Mimir MVP

*Five gates. An analyst opens the round, adjusts a driver and watches the
forecast move live, sets a level by hand where no driver carries the judgement,
records why at every step, signs off the config, takes a red pen to the chapter,
and publishes it with every number bound to a source. Denmark, September 2026 —
in English and Swedish.*

One command and a browser. No language model, no API key, no network call.

**New here? Read [RUN-LOCALLY.md](RUN-LOCALLY.md)** — prerequisites, the one
command, what to click, and what to do when it does not start.

---

## Run it

You need **Python 3.11 or newer** and read access to this repository. Nothing
else — no Docker, no database, no cloud account, no API key.

### Windows (PowerShell)

```powershell
git clone https://github.com/asHubexo/prognoscentret_mvp
cd prognoscentret_mvp
.\run.ps1
```

`run.ps1` creates a virtual environment on first run, installs the five
dependencies, and starts the server. It takes about a minute the first time and
a second after that. Then open **http://127.0.0.1:8000**.

### macOS / Linux

```bash
git clone https://github.com/asHubexo/prognoscentret_mvp
cd prognoscentret_mvp
./run.sh
```

### By hand, if you prefer

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # .venv/bin/python on mac/linux
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**If `python` is not found on Windows:** the Microsoft Store build works fine —
`winget install Python.Python.3.13`, then reopen the terminal.

---

## Who can run it, and how

The repository is **private** under the `asHubexo` organisation. An org owner
adds people on `github.com/asHubexo/prognoscentret_mvp` → *Settings* →
*Collaborators and teams* with **Read**. Read is enough — nobody needs write
access to run it.

Everyone runs it **the same way, on their own machine**: clone, one command,
browser. That is the only supported path. There is no Docker image, no
container, no Codespace, no cloud host and no database — those were removed on
purpose so nobody has to decide between two ways of starting it. See
[RUN-LOCALLY.md](RUN-LOCALLY.md), and
[docs/Mimir-forecast-chain.md](docs/Mimir-forecast-chain.md) for the full
chain this pilot is a slice of.

**Do not make the repository public.** `data/` carries Hubexo's own forecast
input, and the driver pages show verbatim quotes from licensed bank research.
Run locally and that question never arises.

## What you are looking at

All five gates work, in **English and Swedish** (the toggle is top right, and
it is remembered).

| | |
|---|---|
| **Gate 0 · fresh?** | The source register — tier, cluster, cadence, edition held, and whether the source watch could fetch it or needs an upload. Reject one as too old and the reason is journalled. **The round starts because you say so, not because a date arrived** |
| **Gate 1 · review** | Four drivers. Drag a slider and the forecast redraws live — server-side, typically 5–15 ms. Nothing is committed until you give a reason |
| **Gate 1b · overlay** | Set the forecast level **by hand**, where no driver carries the judgement. You set the year; the model keeps the within-year shape. The model line stays on the chart, the decomposition shows the overlay as judgement rather than cause, and the published chapter names you as its source |
| **Gate 2 · sign-off** | The config rows. Change which Tobin's Q series a segment uses, its transform, whether the rate is in, whether the seasonals are — the model refits and the backtest re-scores it. **You adjust the config, never the number** |
| **Gate 3 · red pen** | The chapter, every figure carrying a superscript to its binding. Edit a sentence, give a reason, and it is journalled; a correction that returns becomes a numbered style rule |
| **Publish** | The check binds every number to a source or the publish does not happen, then the source list is built from the bindings — derived, not typed |
| **Charts** | Quarterly starts with a ±1 se band, the agent's forecast as a dashed line beside yours, KPI cards per forecast year, and annual bars comparing the two |
| **What moved it** | Exact attribution per driver. In logs the model is additive, so each effect is its coefficient times its change — no residual |
| **guard** | Try setting the mortgage rate below zero. It refuses, and says which declared bound stopped it |
| **The reason field** | Required at every gate. Kept verbatim. The agent's value is stored beside yours so a later round can measure which was closer |
| **Not wired** | The apartment price path is shown and deliberately inert — see below |

**Three things worth doing on purpose in a demo.** Set the mortgage rate below
zero, so `guard` is seen refusing — a control nobody has watched refuse is a
claim, not a control. At gate 2, point *row houses* at the **Flats** Tobin's Q
instead of the detached one: hold-out error falls from about 58 per cent to
about 16, which is a live finding about the production specification, not a
scripted trick. And at gate 1b, overlay a year and then publish: the chapter
names you as the source of that number, in the machine-built source list.

### Gate 1b, and why it is built the way it is

Gate 1b is the one place in the pilot where a number does not come from the
model, so it is worth being exact about what keeps it honest. **The design rule
everywhere else is that the analyst adjusts inputs, never outputs** — gate 2
exists to enforce precisely that, because *a hand-edited value is untraceable
and a weight is not.* An output override was therefore a deliberate exception,
and it is built as a separate layer rather than as an edit:

| | |
|---|---|
| **It is a layer, never a blend** | The model line and the overlay line are both kept and both drawn. You can always see what the model said |
| **The analyst is the source** | The number binds to `analytikerskøn` with a date and your reason, so `p3 check` still binds every figure. The rule was never "a number must come from a document" — it was "a number must have a source you can name" |
| **Not attributable to a driver** | The decomposition carries the overlay in its own row, marked as judgement. An overlay folded into Tobin's Q would be the actual dishonesty |
| **Annual level only** | You set the year; the model keeps the within-year profile. Setting forty-eight quarterly numbers by hand is not judgement, it is a different forecast |
| **Every overlaid year is reported** | Not just the first. An overlay the text does not mention is exactly the case this layer exists to prevent |

`guard` still applies, and it is deliberately permissive about size: an analyst
who knows a scheme has been cancelled may legitimately halve a segment, or take
it to zero. What is refused is what cannot be true — a negative number of
dwellings — and what is almost certainly a slipped keystroke rather than a view,
a hundredfold change either way.

**What it costs, stated plainly.** The backtest cannot validate an overlay: it
scores the model, and the overlay is by construction outside it. So an overlay
is measurable against the outcome but not against the method, and a round in
which overlays carry most of the movement is a round in which the model has
stopped being the thing that produces the forecast. The journal counts them,
which is the point of recording them.

### The finding the demo is built to show

Move the **house prices** slider and apartment starts move. That is not a bug
in the demo. `hpi` is defined as **enfamiliehuse** — all 39 claims — and the
same numerator feeds Tobin's Q for detached houses, flats *and* holiday homes.
So in the current specification, Danish apartment construction is driven by
single-family house prices.

The apartment price path exists and is inert: the house's own path is 12.0 per
cent for 2026, Nykredit says 15.0, and realised growth accelerated five
quarters running — 8.6 · 10.4 · 10.7 · 13.0 · 15.8 (DST EJ56, 2025K1–2026K1).
None of it reaches the model. Only two Danish institutions publish an apartment
forecast at all, Nykredit and Nordea Kredit, and both sit in cluster
`dk_private`, so triangulation independence stays weak even after they are
admitted. That has to be said out loud rather than averaged away.

---

## The model

```
log(starts) = a + b1·TobinsQ + b2·RealMortgageRate + quarterly dummies
```

Fitted at start-up on 2006Q1–2025Q4; drivers run to 2028Q4, which is the
forecast. `LRA` is already a model type in the production `model_library.py`
— Office, Education, Other buildings and Transport all use it, and the Office
model is a log-log OLS — so this is an in-house method, not a shortcut around
the method.

**Why OLS and not the production ensemble.** Under a moving slider, an ensemble
containing a seasonal-naive member and a pipeline overlay capped at four
quarters responds discontinuously, and the analyst sees movement they cannot
attribute. OLS responds smoothly and monotonically, and its decomposition is
exact. That is what lets the interface *name a cause*.

**Signs are a test, not a formality.** The production config records the correct
long-run signs — Tobin's Q positive, rate negative. All four segments reproduce
them, and the diagnostics table on the page says so per segment. If a sign
flipped, that would be a finding to report, not a fit to adjust until it agrees.

### This is a demo model

| Segment | OLS hold-out MAPE | Production |
|---|---|---|
| Flats · etageboliger | ~48 % | 5-model ensemble — OOS h4 **32.4 %** |
| Detached houses | ~21 % | PRA — OOS **10.1 %**, walk-forward validated |
| Row / linked houses | ~58 % | SARIMAX — OOS **14.2 %** |
| Holiday houses | ~21 % | SARIMAX — OOS **8.9 %** |

The pilot forecast is **not** the house forecast, and the page says so in three
places. The production weights were set by hold-out backtest for exactly this
reason. Phase 2 puts the ensemble back behind the same API and the interface
does not change.

---

## What it does not do

- **No language model runs anywhere in this pilot.** Zero tokens, no API key,
  no network call at all. P1's research is a frozen snapshot, P2 has no model in
  it by design in production too, and the chapter is assembled by a
  deterministic template rather than P3's writer. `test_no_language_model_anywhere`
  asserts it, so the claim cannot rot quietly.
- **No sentiment analysis.** In the full chain sentiment is P1 research step 3,
  and it carries **no value column by design** — it may flag a divergence at the
  review gate, and may never become a claim or move a number. So adding it would
  change no forecast. It also needs WebSearch/WebFetch, which has no API path,
  and freezing it is how the pilot sidesteps that blocker entirely.
- **No live research.** P1's output is the frozen gate-approved snapshot.
- **No orchestration, no Postgres, no model gateway.** Not needed to show a
  decision. Gates earn durable waits when they wait for weeks, and a demo does
  not wait.
- **The chapter is not P3's prose.** It is a template that inserts the
  forecast's own numbers with their bindings. It demonstrates the *control*, not
  the writing, and it says so on the page.
- **The learning loop only records.** Measure and inject are phase 2 — at three
  forecast rounds a year they cannot be demonstrated anyway.

See `../Mimir-MVP-scope.md` for the full scope, what is deliberately cut, and
the entry criteria.

---

## Layout

```
app/
  data.py       loads the frozen snapshot; column contract from model_runner.py
  model.py      OLS — fit, predict, exact decomposition, hold-out error
  scenario.py   slider positions → driver paths (Tobin's Q is price ÷ cost)
  panel.py      gate 1 — drivers, sources, institutions, declared bounds
  overlay.py    gate 1b — analyst levels, their guard, and what they cost
  sources.py    gate 0 — the source register and what can be fetched
  chapter.py    gate 3 + publish — assembly, the check, the source list
  guard.py      the four hard stops, and nothing more
  journal.py    append-only decisions, reasons kept verbatim
  i18n.py       English and Swedish for everything the API sends
  main.py       FastAPI
static/         one page, vanilla JS, hand-rolled SVG charts — no CDN, works offline
  i18n.js       interface chrome, English and Swedish
data/           frozen September 2026 snapshot (see data/SNAPSHOT.md)
                master_exogenous.xlsx        upstream, never modified
                master_exogenous_fixed.xlsx  two declared fixes (data/FIXES.md)
                bundle/                      Carl's research: 38 drivers, 223 claims
journal/        decisions.jsonl, written at runtime, gitignored
```

The page holds no model. It never computes a forecast itself, so there is
nothing in the browser that can drift out of parity with the round — which is
the trap the existing console fell into by reimplementing the ensemble in
JavaScript.

## Upstream

Reads a frozen copy of data from `LasseLundqvist/forecasting-models` at commit
`4c72e0f`. That repository, and `P1` and `P3`, are **read-only** for this
project and are never written to.
