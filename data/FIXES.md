# Fixes applied to the pilot's copy of the exogenous master file

*Applied 10 September 2026 with `python tools/fix_master.py`. Re-run it after any
snapshot refresh; run it with `--report` to see what it would change and write
nothing.*

**The upstream file is never modified.** `data/master_exogenous.xlsx` is exactly
what came from `forecasting-models@4c72e0f`. The fixes are written to
`data/master_exogenous_fixed.xlsx`, and `app/data.py` prefers that file when it
exists and reports which one it loaded. **Delete the fixed file and every fix
reverts.** Both files ship, so each fix is pinned by tests in both
directions — the defect present upstream, absent after.

Two fixes, and only two. Both correct a *construction* — a value produced by a
rule rather than measured — and neither invents a level.

---

## Fix 1 · construction costs re-anchored to the last actual

**The defect.** History carries one decimal to 2025Q3 (119.1); from 2025Q4 the
series carries nine and is rule-generated. The step at the seam was **−2.084 %**,
against a historical quarterly mean of +0.649 % and a standard deviation of
0.821 % — **z = 3.33**. The worst single quarter in twenty years of Danish data
was −0.862 % in 2009Q1, at the depth of the financial crisis. This was more than
twice that fall, with no event behind it. And the rule began *inside* the fitted
sample, so the model was estimated on one quarter of synthetic cost data.

**The fix.** The rule's own growth rates were never the problem and are kept
untouched: +0.675 %/qtr in 2026, +0.650 in 2027, +0.525 in 2028. Only the level
it started from was wrong. So the whole rule-generated segment is multiplied by
**one factor, ×1.028175**, which makes 2025Q4 continue from 2025Q3 at the rule's
own first rate.

| | before | after |
|---|---|---|
| seam at 2025Q4 | **−2.084 %** (z = 3.33) | **+0.675 %** — the rule's own rate |
| 2025Q4 level | 116.6182 | 119.9039 |
| 2026 annual mean | 118.599 | 121.941 (+2.82 %) |
| 2027 annual mean | 121.380 | 124.799 (+2.82 %) |
| 2028 annual mean | 124.335 | 127.839 (+2.82 %) |

History is untouched; every quarter to 2025Q3 is bit-for-bit unchanged, and
every one of the rule's growth rates survives the re-anchoring exactly.

**It closes an open question in P3's notes.** `notes/dk_new_residential.md`
records the May text saying material prices keep rising, against a driver path
showing only **+0.2 %** for 2026, and files the two as a contradiction awaiting
a decision. That +0.2 % was the seam, not a forecast. Corrected, the same path
grows **+2.8 %** — so the question closes in favour of the text: **the prose was
right and the path was wrong.**

**What it does not do — and this is the more useful finding.** The corrected cost
path barely moves the forecast: apartment starts change by less than 0.05 % in
every year. Costs do not reach the model, because **Tobin's Q is stored as its
own series rather than derived from prices over costs.** A cost correction
therefore changes what the report says and not what the model produces. The cost
defect mattered for the text, not for the starts — and a system where fixing the
denominator of a ratio does not change the ratio is worth knowing about on its
own. `test_fixing_the_costs_barely_moves_the_forecast_and_that_is_the_point`
pins it.

---

## Fix 2 · the mortgage rate smoothed into a quarterly path

**The defect.** 2027 and 2028 each held a single value across all four quarters,
while 2026 had a real quarterly path — an annual estimate the smoothing step
never ran on. This is the driver both apartment models depend on.

**The fix.** Interpolate between annual anchors, then rescale each year so its
mean is *exactly* what it was.

| year | before | after | annual mean |
|---|---|---|---|
| 2027 | 2.75677 × 4 | 2.73998 · 2.79889 · 2.78623 · 2.70197 | **2.75677 → 2.75677** |
| 2028 | 2.41977 × 4 | 2.50402 · 2.41977 · 2.37764 · 2.37764 | **2.41977 → 2.41977** |

**No annual number changes.** Only the within-year distribution does, from a step
function to a path — and that is the reason this fix is allowed at all. A flat
carry is not a measurement of four identical quarters; it is the *absence* of a
within-year estimate. Replacing one construction with a better-behaved
construction of the same annual content adds no information and removes a false
step.

2028Q3 and Q4 remain equal, because `np.interp` has no anchor beyond 2028 to
interpolate toward. That is deliberate: past the last anchor there is no
information, so the path flattens rather than extrapolating a trend nobody
stated.

---

## What is deliberately not fixed

**The 2028 mortgage-rate level.** It sits 33.7 bp below 2027 with no source
behind it, and about 1,284 apartment dwellings in 2028 rest on it. There is no
correct value to write: no institution forecasts the Danish mortgage rate that
far, which is exactly why Carl's research bundle records `mortgage_rate` 2028 as
coverage **`none`** rather than filling it in. Changing the level would be
inventing the number the research layer declined to invent. The pilot surfaces it
at gate 1 instead, where an analyst can carry it by hand — and then it is
theirs, with their reason attached.

**Consumer confidence**, which decays at a flat −15 %/quarter through 2027–28.
It is a rule, and there is no better source here to replace it with.

**The other nine drivers `efterprøv` flags** — a flat-carried year, a precision
jump at 2025Q4, or a constant growth rate, in `Business cycle Industry`,
`Business cycle Services`, `Exported and import good`, `Hotel stays`,
`Office employees total`, `Retail sales index`, `Share of e-commerce`,
`Urban population` and `Tobins_Q_Office`. Same reason: the check reports, and
replacing a rule needs a source rather than an opinion.

**V6 identity for Tobin's Q**, which cannot be closed because the numerator is
not in the file. That is research, not a data fix: admit Nykredit and Nordea
Kredit through `optag`, and say plainly that both sit in cluster `dk_private`, so
triangulation independence stays weak even afterwards.

`efterprøv` now reports **11 of 29** drivers rather than 12, and the two entries
that changed are the two fixed above. Run `python tools/efterproev.py` for the
current list.
