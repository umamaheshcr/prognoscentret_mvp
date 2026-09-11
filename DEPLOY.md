# Putting this on a URL, with a lock on it

*Added 11 September 2026. Nothing in the gates, the model or the data changed —
this is four files and two small patches that let the same app run on a host
instead of only on `127.0.0.1`, and refuse to run there unprotected.*

## Read this part first

`app/main.py` opens by explaining that the pilot is local-only **by decision**:
the driver pages show verbatim quotes from licensed bank research, and that is
the same thing that has kept the production approval console undeployed. A
hosted URL crosses that line. So the deal is:

* **Never deploy this without `MIMIR_BASIC` set.** The app now refuses rather
  than serves if you forget — but the habit matters more than the guard.
* **Never make the repository public**, and don't copy it into a personal
  GitHub account. Fork inside the `asHubexo` org, private.
* **Free hosts are third parties.** Render's free tier is fine for showing
  colleagues a working round; it is not a home for licensed research. If this
  becomes something people rely on, it moves behind the company's own identity
  provider — see *Where this goes next*.

## What changed

| File | What it does |
|---|---|
| `app/auth.py` | **new.** One basic-auth gate in front of every request. Fails *closed*: no credential configured means 503 from anywhere but loopback |
| `app/main.py` | two additions — registers that middleware, and adds `/healthz` for the platform's health check (the one path that skips auth) |
| `app/data.py` | `load()` now prefers a pickled copy of each workbook when one exists, and ignores one older than its workbook |
| `tools/precache.py` | **new.** Writes those pickles and asserts they round-trip equal, dtypes included. Run at build time |
| `render.yaml` | **new.** The blueprint: build command, start command, one worker, health check, Python version |
| `tests/test_deploy_auth.py` | **new.** 12 tests, 23 cases: pins *fails closed*, the static mount being behind the gate, loopback not being an exemption, and the cache not changing a single value |
| `.gitignore` | `data/*.pkl` — generated, never committed |

Run `.venv/Scripts/python -m pytest -q` before you push: the existing 72 tests plus the 23 new cases should all pass, and the two cache tests skip until `python tools/precache.py` has run.

**Running locally is unchanged.** `.\run.ps1` and `./run.sh` still work exactly
as before, with no credential and no environment variable: requests from
loopback pass the gate untouched.

## Deploying to Render

1. **Fork inside the org**, private: `asHubexo/prognoscentret_mvp` → Fork, or
   push this working copy to a new private repo under `asHubexo`. Make sure
   `data/` comes with it — the app needs the two workbooks, and they are
   committed on purpose (see the README's note on why).
2. In Render: **New → Blueprint**, connect that repository, pick the branch.
   Render reads `render.yaml` and proposes one free web service.
3. It will ask for **`MIMIR_BASIC`**. Enter `user:password` as a single string —
   e.g. `mimir:pick-something-long`. The colon separates them; everything after
   the first colon is the password.
4. Apply. First build takes a few minutes (five dependencies plus the precache
   step). Then open the URL, and the browser asks for that user and password.
5. Check `/healthz` — it answers without a login and reports which exogenous
   file loaded. That is the quickest way to tell a cold start from a crash.

Prefer to click through it manually instead of using the blueprint? Same four
answers: runtime **Python 3**, build `pip install -r requirements.txt && python
tools/precache.py`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT
--workers 1`, health check path `/healthz`. Binding `0.0.0.0` and using
`$PORT` are the two that catch everyone — Render routes to the port it hands
you in the environment, not to 8000.

## Two things to tell whoever you share it with

**They share one round.** The state is a single in-memory dict, as the code
says: *one analyst, one round, in memory — a pilot, not a product.* Two people
clicking at the same time approve drivers on top of each other and see each
other's overlays. For a read-through it doesn't matter. For "everyone try it
properly", give each person their own copy instead — a Codespace, or the one
command on their own laptop, which is the repo's supported path anyway.

**The first visit after a quiet spell takes about a minute, and the round
resets.** Free services spin down after 15 minutes idle, and because the round
lives in memory, spinning down discards it — approvals, overlays, the journal's
in-session entries. Warn them, or click the link yourself a minute before a
demo. Paid instances don't sleep; that is most of what the money buys here.

## Where this goes next

Basic auth is one shared password, so the deployment can tell nobody apart —
which is also why the journal still records *what* was decided and not *who*
decided it. Two ways forward, both better than a longer password:

* **Cloudflare Tunnel + Access**, free, no cloud spend, nothing hosted: the app
  keeps running on your machine, and you list who may reach it by work email.
  Good for letting the team check it this week.
* **Azure App Service or Container Apps with Entra ID ("Easy Auth")** — company
  accounts, no auth code at all, and the natural fit for a Microsoft estate.
  This is the real answer once it stops being a demo, and it is what the
  earlier README recommended. It needs a subscription, which is the spend
  approval the project is already waiting on.

When per-user identity does arrive, the interesting follow-on is that the
journal can finally record the name beside the reason — which is the half of
the audit trail that is still missing.

## If it misbehaves

| Symptom | Cause |
|---|---|
| 503 with "MIMIR_BASIC is not configured" | The env var didn't get set, or the service restarted before it was saved. Set it and redeploy |
| Login prompt loops | The value isn't `user:password`, or it has a stray space. It is compared verbatim |
| Build fails on `pandas` | Python version. `PYTHON_VERSION` is pinned to 3.11.9 in the blueprint; older Render defaults can try 3.7 |
| Dies at start-up, exit 137 | Out of memory. Confirm the build log shows `wrote master_*.pkl`; if it still dies, the next lever is a paid instance with 1 GB |
| Numbers differ from your laptop | Check `/healthz` for the exogenous file name — `master_exogenous_fixed.xlsx` is the fixed one, and a deploy missing it silently reverts both fixes in `data/FIXES.md` |
| Health check fails, app looks fine | `/healthz` has to stay out of `OPEN_PATHS`' way in `app/auth.py`. Any auth in front of it will fail the platform's probe |
