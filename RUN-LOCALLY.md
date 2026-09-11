# Running Mimir on your own machine

*For anyone with read access to `asHubexo/prognoscentret_mvp`. Everyone runs it
the same way on their own machine — clone, one command, browser. Nothing else:
**no Docker, no container, no Databricks, no cloud host, no database, no API
key.** About five minutes, most of it waiting for `pip`.*

---

## What you install yourself, once

Two things, on your own machine. Nobody sets these up for you and nothing in
the repository installs them.

| | | |
|---|---|---|
| **Git** | `git --version` should answer | `winget install Git.Git` · `brew install git` · `apt install git` |
| **Python 3.11 or newer** | `python --version` should answer | `winget install Python.Python.3.13` · `brew install python@3.13` · `apt install python3 python3-venv` |

On Windows, **open a new terminal after installing** — PATH is only picked up by
new shells.

**Node.js is not needed.** The page is plain JavaScript with no build step, so
there is nothing to `npm install` and nothing to compile. If you have Node
already it is simply unused.

The launcher then creates a `.venv` inside the clone and installs five Python
packages into it — FastAPI, uvicorn, pandas, numpy and openpyxl. Nothing is
installed globally and nothing touches your system Python.

Nothing runs on the network except the clone and that one `pip install`. After
that the app works with the network off.

---

## Windows · PowerShell

```powershell
git clone https://github.com/asHubexo/prognoscentret_mvp
cd prognoscentret_mvp
.\run.ps1
```

Then open **http://127.0.0.1:8000**.

If PowerShell refuses to run the script, it is the execution policy, not the
script:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## macOS · Linux

```bash
git clone https://github.com/asHubexo/prognoscentret_mvp
cd prognoscentret_mvp
./run.sh
```

## By hand, if you would rather see each step

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # .venv/bin/python on mac and linux
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first run creates `.venv` and installs five packages — FastAPI, uvicorn,
pandas, numpy and openpyxl. That takes about a minute. Every run after that
starts in a second or two.

Stop the server with **Ctrl+C**.

---

## What you should see

The header carries five gates plus a **Forecast** page, a role switch and an
**EN / SV** language toggle. Everything is in both languages, including the
numbers — Swedish writes `22 287` and `12,0` where English writes `22,287` and
`12.0`.

| Page | What it is |
|---|---|
| **Gate 0 · fresh?** | 22 institutions, 223 claims. Tier, cluster, how many claims each contributes, latest publication and its age. Reject one as too old — Nationalbanken's newest claim here is a year old — and the reason is journalled |
| **Gate 1 · drivers** | 38 market drivers in five groups. One assumption **per forecast year**, with the consensus band, and every source behind it: institution, tier, value, weight, publication date, report link, page and the verbatim quote. **No forecast on this page** |
| **Forecast** | The model. Sliders redraw it live, server-side, in about 6–15 ms |
| **Gate 1b · overlay** | Set a forecast level by hand where no driver carries the judgement. Kept as a separate layer, never blended |
| **Gate 2 · sign-off** | Config rows — which Tobin's Q series a segment uses, its transform, its terms. The model refits and the backtest re-scores it |
| **Gate 3 · red pen** | The chapter, every figure superscripted to its binding |
| **Publish** | The check binds every number to a source, or the publish fails |
| **Run** (Orchestrator role) | The round as workflow state: 14 steps with status, logs, timing, retry |

### Four things worth trying on purpose

1. **On Forecast, set the mortgage rate below zero.** `guard` refuses and names
   the bound that stopped it. A control nobody has watched refuse is a claim,
   not a control.
2. **On Gate 1, open *Huspriser* and look at 2028.** Nine sources price 2026 and
   one prices 2028. Then open `mortgage_rate` 2028 — it has *no* estimate at
   all, because no institution publishes one. It cannot be approved blindly.
3. **On Gate 2, point *row houses* at the Flats Tobin's Q** instead of the
   detached one. Hold-out error falls from about 58 per cent to about 16. That
   is a live finding about the production specification, not a scripted trick.
4. **Switch the role to Orchestrator.** The navigation collapses to the run
   monitor — the analyst's gates are not on it, and it is not on theirs.

---

## Keeping up to date

```bash
git pull
```

If `requirements.txt` changed, re-run the launcher; it reinstalls only when
needed. If you have edited files locally and `git pull` complains, `git stash`
first.

---

## When something goes wrong

| Symptom | Cause and cure |
|---|---|
| `python` not recognised (Windows) | The Store alias is not on PATH. `winget install Python.Python.3.13`, then open a **new** terminal |
| `[Errno 10048] error while attempting to bind` | Port 8000 is already taken, usually by an older copy of this app. Close it, or run on another port: `--port 8010` |
| `ModuleNotFoundError: fastapi` | The venv exists but is empty — the first install was interrupted. Delete `.venv` and run the launcher again |
| Page loads but stays empty | Hard-reload the browser (Ctrl+Shift+R). The page is plain JavaScript with no build step, so a stale cache is the usual culprit |
| `pip` fails behind the company proxy | `pip install --proxy http://your.proxy:port -r requirements.txt` |
| Excel says the data files are locked | Close them in Excel. OneDrive can also hold a lock mid-sync; wait for it to finish |

---

## Access

The repository is **private** under the `asHubexo` organisation. An org owner
adds people on `github.com/asHubexo/prognoscentret_mvp` → *Settings* →
*Collaborators and teams*, with **Read**. Read is enough — nobody needs write
access to run it.

**Do not make the repository public, and do not host the app on a URL.** `data/`
carries Hubexo's own forecast input, and the driver pages show verbatim quotes
from licensed bank research. That is precisely why the production approval
console has never been deployed. Run it locally and the question never arises.

---

## What it deliberately does not do

* **No language model runs anywhere in it.** Zero tokens, no API key, no network
  call. The research is a frozen snapshot and the chapter is assembled by a
  template, not written by P3. `test_no_language_model_anywhere` asserts it.
* **No Postgres, no Temporal, no model gateway, no container.** Not needed to
  show a decision. The run monitor has Temporal's shape so the move later is a
  port, but its state lives in memory — kill the process and the round is gone.
* **The forecast is a demo model**, and every page that shows it says so:
  ordinary least squares on two drivers, chosen so slider response is smooth and
  attribution exact. It is less accurate than the production ensemble, and the
  figure beside each segment says by how much.

## Where to read next

| | |
|---|---|
| `README.md` | What the app is, the model, and the finding it is built around |
| `data/FIXES.md` | The two fixes applied to the exogenous master file, and what was deliberately left alone |
| `data/DEFECTS.md` | What `efterprøv` measures in the snapshot, with the evidence |
| `docs/Mimir-forecast-chain.md` | Lasse's description of the **full chain** — three agents, four gates, the learning loop. What the pilot is a slice of |
| `docs/Mimir-MVP-scope.md` | Scope: nodes live, frozen and cut, plus the entry criteria |
| `docs/Databricks-Lakeflow-assessment.md` | Whether this could run as a Lakeflow pipeline, and the nine problems if it did |
| `python tools/efterproev.py` | Run the data checks yourself |
| `.venv/Scripts/python -m pytest -q` | 72 tests |
