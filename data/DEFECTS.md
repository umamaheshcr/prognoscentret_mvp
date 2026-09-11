# Defects in the frozen snapshot

*Measured 9 September 2026 against `master_exogenous.xlsx` at commit `4c72e0f`,
with `python tools/efterproev.py`. Re-run it after any snapshot refresh — the
numbers below are what the checks said on that file, not a memory.*

**None of these are fixed here, and that is deliberate.** The chain's own rule
is that these are the analyst's call, not the agent's: a driver value may only
change at gate 1, with a reason journalled in the analyst's own words. Silently
rewriting a production number to make a demo tidier would break the one property
the whole system is built to have.

What the pilot does instead is make them impossible to miss. Gate 1 shows each
driver's `efterprøv` findings, **computed from the file** rather than typed — so
a warning cannot outlive the defect it describes, and cannot be forgotten if the
defect is fixed.

---

## 1 · Real mortgage rate — 2027 and 2028 are annual figures, never smoothed

    2026   2.3031 · 2.6623 · 2.5267 · 2.5924     a real quarterly path
    2027   2.7568 · 2.7568 · 2.7568 · 2.7568     one value, four times
    2028   2.4198 · 2.4198 · 2.4198 · 2.4198     one value, four times

The smoothing step — annual estimate into a quarterly path — ran for 2026 and
not beyond. And 2028 falls **33.7 bp** below 2027 with no source behind it: no
institution forecasts the Danish mortgage rate that far, which is why the
production note says *`mortgage_rate` 2028 has no guard; the year is unverified,
not approved.*

**What rests on it.** Held at the 2027 rate instead, apartment starts in 2028
fall from 21,568 to 20,285 — **−5.95 per cent, about 1,284 dwellings** on a
number nobody published. This is the driver both apartment models depend on.

*The analyst's call at gate 1:* accept the unsourced fall, or hold 2028 flat at
2027 and record why.

## 2 · Construction costs — a rule spliced into the fitted sample

    2025Q3   119.1000      1 decimal — an actual
    2025Q4   116.6182      9 decimals — generated
    then     +0.675 % every quarter, exactly (+2.73 %/yr)

Two things, and the second is worse than the first.

**The seam does not connect.** The step from 2025Q3 to 2025Q4 is **−2.084 %**,
against a historical quarterly mean of +0.649 % and sd of 0.821 % — **z = 3.33**.
The worst single quarter in twenty years of Danish data was −0.862 % in 2009Q1,
at the depth of the financial crisis. This is more than twice that fall, with no
event behind it.

**The rule starts *inside* the fitted sample.** History runs to 2025Q4 and the
rule begins at 2025Q4, so the model is estimated on one quarter of synthetic
cost data rather than purely on actuals.

**And it resolves an open question the other way.** `notes/dk_new_residential.md`
records a contradiction: the May text says material prices keep rising, while the
driver path shows only **+0.2 %** for 2026. That +0.2 % is an *artefact of the
−2.08 % seam*, not a forecast — strip the seam and the underlying rule is a flat
+2.7 %/yr throughout:

| | level | growth |
|---|---|---|
| 2024 | 116.650 | +1.52 % |
| 2025 | 118.305 | +1.42 % |
| 2026 | 118.599 | **+0.25 %** ← the artefact |
| 2027 | 121.380 | +2.34 % |
| 2028 | 124.335 | +2.44 % |

So on this evidence **the prose was right and the path is wrong.** That open
question should be closed in favour of the text, and the note updated.

*The analyst's call:* replace the spliced path with the v3 estimate, which the
production note says is ready in `C:\markedsdrivere-data\` — not present in this
repository, so it cannot be applied here.

## 3 · Consumer confidence — a decay rule, not a forecast

    2027Q1 .. 2028Q4   −15.0 % every quarter, exactly

The series is negative and shrinking toward zero by a fixed 15 % a quarter. That
is a mechanical decay, and it is the other half of an open question in the same
notes file: the text says confidence sits at financial-crisis level, the path
"improves steadily" from −16.7 to −2.4. The improvement is a rule.

CCI is not in the pilot's two-driver specification, so it moves no forecast here.
It does enter the production Holiday houses model.

## 4 · V6 identity cannot be closed for any Tobin's Q

Tobin's Q is house prices over construction costs. The snapshot carries the
**ratio** and the **denominator** but not the numerator, so the arithmetic cannot
be checked against its own components — for any of the four series.

This is not a data-entry slip; it is the structural finding of the whole review.
There is no Danish house-price index in the model file. House prices reach the
Danish model only through a ratio nobody can audit, and the same numerator —
defined as **enfamiliehuse**, all 39 claims — feeds detached houses, flats and
holiday homes alike.

*The fix is research, not code:* admit Nykredit and Nordea Kredit through
`optag`, and state plainly that both sit in cluster `dk_private`, so
triangulation independence stays weak even afterwards.

---

## Not reproducible here

The production note names two further defects — `strate` and `ltrate` 2025 being
part-year figures, and `real_interest_rate_st` 2025 disagreeing with its own
components by 0.15 pp. **Neither can be checked or fixed from this repository.**
Those columns belong to `Construction_Market_Drivers.csv`, the CMI cross-country
annual dataset, which is not in any repository here and — per `P1/OVERBLIK.md` —
*is referenced nowhere in the pipeline*. It is not a model input, so those two
defects do not touch the forecast at all, however they are eventually resolved.

## Everything the checks reported

Twelve of twenty-nine Danish drivers report something. Nine are the same species
as the three above — a flat-carried year, a precision jump at 2025Q4, or a
constant growth rate — in `Business cycle Industry`, `Business cycle Services`,
`Exported and import good`, `Hotel stays`, `Office employees total`,
`Retail sales index`, `Share of e-commerce`, `Urban population` and
`Tobins_Q_Office`. Run the tool for the current list.

Indicator series (`Covid_dummy`, `Financial crisis dummy`, `Q2_dummy`,
`Office vacancy`, `Industry Lack of materials`) are exempt from the flat-carry
and constant-growth checks: a dummy is *supposed* to hold one value all year, and
flagging it would bury the findings that matter.
