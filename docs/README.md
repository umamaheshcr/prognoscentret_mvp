# docs

Two documents kept with the code, for provenance rather than for reading order.

| File | What it is |
|---|---|
| `Mimir-forecast-chain.md` | **Lasse's description of the full chain**, and the document this pilot implements a subset of: the three agents, the four human gates, the three controls (`validate` points, `guard` refuses, `efterprøv` explains), and the learning loop. Read this first to understand what the pilot is a slice of |
| `Databricks-Lakeflow-assessment.md` | Whether the round could run as a Lakeflow pipeline. Short answer: the data layer yes, the gates and the UI no. Nine problems, worst first, and what to put where |
| `Mimir-MVP-scope.md` | The pilot's scope: which nodes of the chain are live, which are frozen, which are cut, plus the wireframes and the entry criteria. Written before the app; updated as gates were built out |
| `Mimir-demo.html` | **Carl's design demo, and the origin of `data/bundle/`.** The bundle's ten JSON files were extracted from the `window.__MIMIR_BUNDLE__` literal in this file — 38 drivers, 22 institutions, 223 claims, generated 2026-08-15. Kept so the data's provenance is checkable from inside the repo instead of resting on a commit message |

All three are copies; the originals stay in the Prognos working folder next to
the use-case brief and the workshop deck, which do not belong here.

`Mimir-forecast-chain.md` is **not this project's document** — it describes the
production chain, and the pilot is one slice of it. It is included because the
pilot's design decisions only make sense against it: why gate 2 edits config
rows and never numbers, why `efterprøv` reports rather than refuses, why the
overlay at gate 1b had to be built as a layer.

## Not here, on purpose

* **`AI workshop stockholm.pptx`** — 144 MB. GitHub warns above 50 MB and blocks
  at 100, so it cannot be committed even if it should be.
* **`repos-backup/`** — local clones of `P1`, `P3` and `forecasting-models`.
  Committing them would duplicate three separate private repositories into this
  one and lose the provenance that makes them read-only here.
* **A Dockerfile and a devcontainer.** Both existed and were deleted on purpose.
  Everyone runs the app the same way on their own machine, with plain Python, so
  there is exactly one way to start it and nothing to choose between.
