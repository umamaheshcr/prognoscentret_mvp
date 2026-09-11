# Frozen snapshot

Copied 9 September 2026 from `LasseLundqvist/forecasting-models` at commit
`4c72e0f` ("Exog-masterfilen som den staar 9. september, og Temporal-pilotens
paritetsbevis").

| File | Contents |
|---|---|
| `master_endogenous.xlsx` | DK building starts, 15 segments, 2006Q1–2025Q4 |
| `master_exogenous.xlsx` | 29 DK market drivers, 2006Q1–**2028Q4** (12 forecast quarters) |

The pilot never writes to these. Gate 1 overrides are held in memory for the
session and journalled to `journal/decisions.jsonl`.

The upstream repository is read-only for this project.
