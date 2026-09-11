# Could the Mimir round run as a Databricks Lakeflow pipeline?

*Assessment, 10 September 2026. Written against the pilot as it stands in this
repository — five gates, 38 drivers, a deterministic OLS step, and a run monitor
whose defining feature is that it waits.*

**Short answer: the data layer yes, and it would be better than what the pilot
does today. The gates and the analyst UI no.**

Lakeflow buys governance, lineage and data-quality enforcement. It does not buy
human-in-the-loop workflow — and in this system the waiting is the hard part.
Every difficult thing about a forecast round is a person deciding something and
the machine holding still until they do.

A caveat before the detail: my knowledge runs to roughly May 2026 and Lakeflow's
surface has been moving quickly, particularly the Connect / Declarative
Pipelines / Jobs split and the older Delta Live Tables naming. The
*architectural* points below — sections 1, 2 and 5 especially — I would stand
behind. Anything touching a specific feature should be checked against current
documentation before it is relied on.

---

## What genuinely fits, and improves on the current design

This is not a grudging list. For the data layer, Lakeflow is a better home than
what the pilot has now.

| Piece | Why it is better there than here |
|---|---|
| **Ingestion → claims** | DST, ECB SDMX, OECD, Eurostat and AMECO into bronze tables. Today this is `cli.py` calls writing into SQLite on one laptop |
| **Triangulation** | `w = tier × recency × definition match × independence × skill` is a textbook silver-to-gold transformation, and it is currently a Python function nobody else can see |
| **`efterprøv` V1–V6** | Maps almost directly onto pipeline expectations, including the warn-versus-fail split the chain already draws between `validate` and `guard` |
| **Vintages and `facit`** | Delta time travel gives vintages for free. They are hand-managed today |
| **P3's point-in-time rule** | *A delivery is never newer than the forecast.* An as-of join against a Delta version expresses that properly, instead of the manual cut the pilot does |
| **Licensed bank quotes** | Unity Catalog row and column controls on the `claims` table is a real answer to the thing that has kept the production console undeployed for months |
| **"Which assumptions produced which forecast"** | The brief asks for exactly this audit trail, and UC lineage answers it directly rather than by convention |

If nothing else moved, moving the data layer would still be worth doing.

---

## The problems, worst first

### 1 · A declarative pipeline cannot wait for a human

A pipeline update runs to completion or it fails. There is no way to express
*stop at gate 1 until an analyst has approved 114 driver-years, which may take a
week*.

It can be faked: pipeline A writes proposals, a gate table records approvals,
pipeline B runs only when the gate table says it may. But then the waiting, the
resuming, the timing out and the record of who decided what and when all live
**outside** Lakeflow — in Jobs conditions, in a poller, or in Temporal.

So this does not remove the orchestrator. It fragments it, and a fragmented
orchestrator needs an owner. Temporal is already deployed on CDP and does
precisely this: sleeps at a gate for hours or weeks at no cost, and its history
*is* the audit trail.

### 2 · Expectations are pipeline-granular; the gates are value-granular

This one is subtle and it bites hardest in practice.

A failing expectation aborts the update. But `guard` in this system refuses **one
number** — a negative real mortgage rate — and the round carries on so the
analyst can correct that one cell. Mapping `guard` onto a failing expectation
would abort a whole round because one of 114 cells was wrong.

The consequence is that the real gate logic ends up in Python anyway, and
expectations get used only for warnings. That is still useful, but it is much
less than it first appears.

### 3 · It cannot serve the UI, so one process becomes three

Sliders re-forecast in 6–15 ms because a warm process holds the fitted
coefficients in memory. A pipeline update carries cluster start-up latency;
serverless narrows the gap but not to interactive.

So the analyst app has to be separate whatever else happens — and the estate then
holds a pipeline, an app and a gate store, against today's single process.
For a pilot whose remaining work is mostly interface iteration, more moving parts
is the wrong direction.

### 4 · The compute is tiny and Spark contributes none of it

92 quarters, 15 segments, 3,485 forecast rows, and an ordinary least squares with
six parameters that fits in about 11 ms of pandas. The whole dataset is a few
megabytes.

This is not fatal — run it as a single-node Python task. But it should be said
plainly: **Lakeflow's value here is governance, not throughput.** Nobody should
approve this expecting the forecast to get faster.

### 5 · It threatens the parity property this project actually proved

The chain's central claim about P2 is *same input, same forecast, every time*,
and there is a verified proof of it: 3,485 rows bit-identical between the local
run and the Temporal run, checked cell by cell.

Spark reductions are partition-order dependent in the final floating-point bits,
so a `groupBy().mean()` can differ between runs. For an OLS the difference is
numerically irrelevant — and fatal to a claim of bit-identity.

**Keep P2 as a single-node pandas task even inside Databricks** and the proof
survives. Rewrite it in Spark and it does not.

### 6 · Session state is transactional, not analytic

*The analyst is mid-round and has approved 47 of 107 cells* is a
read-modify-write workload. Delta is append and merge oriented; frequent small
merges bring small-file problems and OPTIMIZE/VACUUM discipline nobody wants to
own during a pilot.

Session state wants Postgres or Lakebase. Delta is the right home for the
**record** of decisions — the append-only journal, which suits it well — not for
the in-flight state.

### 7 · Cadence mismatch

Three forecast rounds a year, with gates that wait weeks. Declarative pipeline
platforms are built for continuous or daily data. Serverless mitigates the cost,
but this is substantial machinery for something that fires quarterly.

### 8 · Two things Lakeflow changes nothing about

* **PDF ingestion.** 150-odd bank reports is not a Lakeflow Connect connector.
  It is a volume plus a Python task — fine, but a task, not a declarative table.
* **WebSearch and WebFetch still have no API path.** P1's research steps 2 and 3
  and P3's cold proof-reader stay blocked exactly as they are now. This is
  platform-independent and it is worth settling before moving anything.

### 9 · The development loop gets much slower

Today: edit a file, reload the browser, 6 ms. There: edit, run a pipeline update,
wait. That is a real tax on a pilot whose open work is mostly interface.

---

## What I would actually do

| Piece | Where | Why |
|---|---|---|
| Ingestion → claims → triangulation → driver panel | **Lakeflow Declarative Pipelines** | The good fit. `efterprøv` as expectations, Delta for vintages |
| The model step | **Lakeflow Jobs, single-node Python — not Spark** | Keeps the bit-identical parity proof |
| The gates | **Temporal** | Lakeflow can be *triggered by* a gate. It cannot *be* one |
| The analyst UI | **A separate app** | Nothing in Lakeflow serves a page |
| Session state | **Postgres or Lakebase** | Transactional, not analytic |
| The decision journal | **Delta** | Append-only suits it, and time travel is a bonus |

Two conditions on the whole thing:

**Unity Catalog only solves the licensing problem if the app queries as the
user**, not through a service principal. Otherwise the access-control problem has
been moved rather than solved, and the reason the production console is still
undeployed remains.

**Settle WebSearch/WebFetch first.** It blocks the agent layer on every platform,
including this one, and it is far cheaper to answer before a migration than
during one.

---

## The one-sentence version for a steering meeting

Lakeflow is the right place for the data and the wrong place for the decisions;
put the claims, the triangulation and the quality checks there, keep the model
single-node so its determinism survives, and leave the waiting to Temporal.
