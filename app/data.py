"""Loads the frozen September 2026 snapshot.

Column contract taken from the production `model_runner.py`: both master files
are long format and are pivoted here the same way.

    master_endogenous.xlsx   YearQuarter | Country | Buildingtype | Value
    master_exogenous.xlsx    YearQuarter | Country | Marketdriver | Value

Read once at import. The pilot never writes to either file.
"""

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
COUNTRY = "DK"

# Segment name in the endogenous file → its Tobin's Q driver in the exogenous
# file. Every residential segment shares one hpi numerator; the Q series differ
# by their segment-specific cost base, not by their price source.
SEGMENTS = {
    "Flats": {
        "label": "Flats · etageboliger",
        "tobins_q": "Tobins-Q (Flats)",
        "unit": "dwellings per quarter",
        "production": "5-model ensemble (SeasonalNaive · AR4 · COMBINED_ECM · "
                      "SARIMA · Hubexo pipeline) — OOS MAPE h1 23.7 / h4 32.4 / h8 43.9",
    },
    "Detached houses": {
        "label": "Detached houses · enfamiliehuse",
        "tobins_q": "Tobins-Q (Detached houses)",
        "unit": "dwellings per quarter",
        "production": "PRA, single model — OOS MAPE 10.1, walk-forward validated "
                      "(strongest residential model)",
    },
    "Row-, chained-, linked houses": {
        "label": "Row / linked houses · rækkehuse",
        "tobins_q": "Tobins-Q (Detached houses)",
        "unit": "dwellings per quarter",
        "production": "SARIMAX on HP-deviation Tobin's Q — OOS MAPE 14.2, "
                      "walk-forward validated",
    },
    "Holiday houses": {
        "label": "Holiday houses · sommerhuse",
        "tobins_q": "Tobins-Q (Holiday homes)",
        "unit": "m² per quarter",
        "production": "SARIMAX — OOS MAPE 8.9, best performing residential model",
    },
}

RATE = "Real Interest rate (Mortgage)"
COST = "Construction costs"


def _quarters(series):
    return pd.PeriodIndex(series.astype(str), freq="Q")


# The pilot prefers the fixed exogenous file when it is present, and says which
# one it loaded. The upstream snapshot is never modified — `tools/fix_master.py`
# writes a separate file, so deleting it reverts every fix. See data/FIXES.md.
EXO_UPSTREAM = DATA / "master_exogenous.xlsx"
EXO_FIXED = DATA / "master_exogenous_fixed.xlsx"
EXO_FILE = EXO_FIXED if EXO_FIXED.exists() else EXO_UPSTREAM
EXO_IS_FIXED = EXO_FILE is EXO_FIXED


# A 512 MB host parses these workbooks with openpyxl at start-up, which is the
# single largest memory spike in the process. `tools/precache.py` writes a
# pickled DataFrame beside each workbook and verifies it round-trips equal, so
# dtypes are preserved exactly and the forecast is unchanged. Delete the .pkl
# files and this reverts to reading the workbooks. Nothing else changes.
def _read(path: Path) -> pd.DataFrame:
    cached = path.with_suffix(".pkl")
    if cached.exists() and cached.stat().st_mtime >= path.stat().st_mtime:
        return pd.read_pickle(cached)
    return pd.read_excel(path)


def load():
    endo = _read(DATA / "master_endogenous.xlsx")
    exo = _read(EXO_FILE)

    endo = endo[endo["Country"] == COUNTRY].copy()
    exo = exo[exo["Country"] == COUNTRY].copy()
    endo["p"] = _quarters(endo["YearQuarter"])
    exo["p"] = _quarters(exo["YearQuarter"])

    starts = {
        seg: (endo[endo["Buildingtype"] == seg]
              .set_index("p")["Value"].astype(float).sort_index())
        for seg in SEGMENTS
    }
    drivers = (exo.pivot_table(index="p", columns="Marketdriver",
                               values="Value", aggfunc="first")
               .sort_index())
    drivers.index = pd.PeriodIndex(drivers.index, freq="Q")
    return starts, drivers


STARTS, DRIVERS = load()

# The forecast period is where drivers exist and starts do not.
LAST_ACTUAL = max(s.index.max() for s in STARTS.values())
FORECAST_INDEX = DRIVERS.index[DRIVERS.index > LAST_ACTUAL]
FORECAST_FROM = FORECAST_INDEX.min()


def meta(lang: str = "en"):
    from . import i18n
    lang = i18n.norm(lang)
    return {
        "country": COUNTRY,
        "exogenous_file": EXO_FILE.name,
        "exogenous_fixed": EXO_IS_FIXED,
        "actuals": f"{min(s.index.min() for s in STARTS.values())} .. {LAST_ACTUAL}",
        "forecast": f"{FORECAST_INDEX.min()} .. {FORECAST_INDEX.max()}",
        "n_forecast_quarters": len(FORECAST_INDEX),
        "segments": {k: i18n.pick(i18n.SEGMENT_LABELS, k, "", lang, v["label"])
                     for k, v in SEGMENTS.items()},
    }
