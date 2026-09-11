"""English and Swedish for the server-supplied strings.

The interface chrome is translated in `static/i18n.js`. This file covers what
the API sends: driver labels, how each driver reaches the model, the warnings,
and the segment names.

Two things are deliberately NOT translated:

  * source citations — a publication is cited by its own title, in its own
    language. "Økonomisk Redegørelse, august 2026" does not become
    "Ekonomisk redogörelse", because then the reader cannot find it. This is
    style rule 43 applied to the interface.
  * `efterproev` check names — V1 BASIS, V2 DELÅR and the rest are identifiers
    in the production chain, not prose.
"""

LANGS = ("en", "sv")

SEGMENT_LABELS = {
    "Flats": {"en": "Flats · etageboliger", "sv": "Flerbostadshus · etageboliger"},
    "Detached houses": {"en": "Detached houses · enfamiliehuse",
                        "sv": "Småhus · enfamiliehuse"},
    "Row-, chained-, linked houses": {"en": "Row / linked houses · rækkehuse",
                                      "sv": "Rad- och kedjehus · rækkehuse"},
    "Holiday houses": {"en": "Holiday houses · sommerhuse",
                       "sv": "Fritidshus · sommerhuse"},
}

UNITS = {
    "dwellings per quarter": {"en": "dwellings per quarter",
                              "sv": "bostäder per kvartal"},
    "m² per quarter": {"en": "m² per quarter", "sv": "m² per kvartal"},
    "pct": {"en": "pct", "sv": "procent"},
    "pct y/y": {"en": "pct y/y", "sv": "procent å/å"},
    "pct y/y, Q4": {"en": "pct y/y, Q4", "sv": "procent å/å, kv4"},
    "balance": {"en": "balance", "sv": "nettotal"},
}

# Driver strings, keyed by driver → field → language.
DRIVERS = {
    "rate": {
        "label": {"en": "Real mortgage rate", "sv": "Realränta, bolån"},
        "effect": {
            "en": "enters both residential models directly, coefficient b2",
            "sv": "går direkt in i båda bostadsmodellerna, koefficient b2",
        },
        "warning": {
            "en": "No source forecasts the mortgage rate to 2028. That year is "
                  "unverified, not approved — mortgage_rate 2028 has no guard.",
            "sv": "Ingen källa prognostiserar bolåneräntan till 2028. Det året är "
                  "oprövat, inte godkänt — mortgage_rate 2028 saknar värn.",
        },
    },
    "hpi": {
        "label": {"en": "House prices — enfamiliehuse",
                  "sv": "Bostadspriser — enfamiliehuse"},
        "effect": {
            "en": "the only hpi in the model — numerator of Tobin's Q for EVERY "
                  "residential segment, apartments included",
            "sv": "det enda hpi i modellen — täljare i Tobins Q för VARJE "
                  "bostadssegment, lägenheter inräknade",
        },
        "warning": {
            "en": "This is the finding, not a bug in the demo: move this slider and "
                  "apartment starts move, because apartment construction is driven by "
                  "single-family house prices in the current specification.",
            "sv": "Detta är fyndet, inte ett fel i demot: dra i reglaget och "
                  "lägenhetsbyggandet rör sig, eftersom lägenhetsbyggandet drivs av "
                  "småhuspriser i nuvarande specifikation.",
        },
    },
    "cost": {
        "label": {"en": "Construction costs", "sv": "Byggkostnader"},
        "effect": {
            "en": "denominator of Tobin's Q — raising costs lowers profitability of building",
            "sv": "nämnare i Tobins Q — högre kostnader sänker lönsamheten i att bygga",
        },
    },
    "cci": {
        "label": {"en": "Consumer confidence", "sv": "Konsumentförtroende"},
        "effect": {
            "en": "not in the pilot's two-driver specification — it enters the "
                  "production Holiday houses model as an HP deviation",
            "sv": "ingår inte i pilotens tvådrivarspecifikation — den går in i "
                  "produktionsmodellen för fritidshus som en HP-avvikelse",
        },
        "warning": {
            "en": "Open question in notes/dk_new_residential.md: the May text says "
                  "confidence sits at financial-crisis level; the driver path improves "
                  "steadily from −16.7 to −2.4. Unresolved since 8 August.",
            "sv": "Öppen fråga i notes/dk_new_residential.md: majtexten säger att "
                  "förtroendet ligger på finanskrisnivå; drivarbanan förbättras stadigt "
                  "från −16,7 till −2,4. Oavgjort sedan 8 augusti.",
        },
    },
    "hpi_flats": {
        "label": {"en": "House prices — etageboliger",
                  "sv": "Bostadspriser — etageboliger"},
        "effect": {
            "en": "NOT WIRED. There is no apartment hpi driver in master_exogenous.xlsx.",
            "sv": "INTE INKOPPLAD. Det finns ingen hpi-drivare för lägenheter i "
                  "master_exogenous.xlsx.",
        },
        "warning": {
            "en": "Realised apartment growth accelerated five quarters running: "
                  "8.6 · 10.4 · 10.7 · 13.0 · 15.8 (DST EJ56, 2025K1–2026K1). None of "
                  "it reaches the model. Admitting Nykredit and Nordea Kredit through "
                  "`optag` is the fix — both sit in cluster dk_private, so triangulation "
                  "independence stays weak and that has to be said out loud.",
            "sv": "Den realiserade lägenhetsprisökningen accelererade fem kvartal i "
                  "följd: 8,6 · 10,4 · 10,7 · 13,0 · 15,8 (DST EJ56, 2025K1–2026K1). "
                  "Inget av det når modellen. Lösningen är att ta in Nykredit och Nordea "
                  "Kredit genom `optag` — båda ligger i klustret dk_private, så "
                  "trianguleringens oberoende förblir svagt, och det måste sägas rakt ut.",
        },
    },
}

GUARD = {
    "not_a_number": {"en": "'{v}' is not a number", "sv": "'{v}' är inte ett tal"},
    "never_negative": {
        "en": "{label} has never been below zero in the sample, so it may not go "
              "below zero here. Change the value, or change the config row at gate 2.",
        "sv": "{label} har aldrig varit under noll i urvalet och får därför inte gå "
              "under noll här. Ändra värdet, eller ändra konfigurationsraden i grind 2.",
    },
    "hard_lo": {"en": "below hard_lo ({b:g} {u}), declared in config",
                "sv": "under hard_lo ({b:g} {u}), deklarerat i konfigurationen"},
    "hard_hi": {"en": "above hard_hi ({b:g} {u}), declared in config",
                "sv": "över hard_hi ({b:g} {u}), deklarerat i konfigurationen"},
    "outside_slider": {
        "en": "outside the slider range [{lo:g}, {hi:g}] but inside the declared "
              "hard bounds — allowed, and worth a sentence in the reason",
        "sv": "utanför reglagets intervall [{lo:g}, {hi:g}] men inom de deklarerade "
              "hårda gränserna — tillåtet, och värt en mening i skälet",
    },
    "pass": {"en": "inside the declared hard_lo / hard_hi",
             "sv": "inom deklarerade hard_lo / hard_hi"},
    "unknown": {"en": "unknown driver '{k}'", "sv": "okänd drivare '{k}'"},
    "reason_required": {
        "en": "The loop cannot learn from a value with no reason, and the number "
              "would be untraceable. This is not a form validation — it is the design.",
        "sv": "Slingan kan inte lära av ett värde utan skäl, och talet skulle bli "
              "ospårbart. Detta är ingen formulärvalidering — det är designen.",
    },
}

PRODUCTION = {
    "Flats": {
        "en": "5-model ensemble (SeasonalNaive · AR4 · COMBINED_ECM · SARIMA · "
              "Hubexo pipeline) — OOS MAPE h1 23.7 / h4 32.4 / h8 43.9",
        "sv": "ensemble av 5 modeller (SeasonalNaive · AR4 · COMBINED_ECM · SARIMA · "
              "Hubexo-pipeline) — OOS MAPE h1 23,7 / h4 32,4 / h8 43,9",
    },
    "Detached houses": {
        "en": "PRA, single model — OOS MAPE 10.1, walk-forward validated "
              "(strongest residential model)",
        "sv": "PRA, enskild modell — OOS MAPE 10,1, walk-forward-validerad "
              "(starkaste bostadsmodellen)",
    },
    "Row-, chained-, linked houses": {
        "en": "SARIMAX on HP-deviation Tobin's Q — OOS MAPE 14.2, walk-forward validated",
        "sv": "SARIMAX på HP-avvikelse i Tobins Q — OOS MAPE 14,2, walk-forward-validerad",
    },
    "Holiday houses": {
        "en": "SARIMAX — OOS MAPE 8.9, best performing residential model",
        "sv": "SARIMAX — OOS MAPE 8,9, bäst presterande bostadsmodell",
    },
}


def pick(table: dict, key: str, field: str, lang: str, fallback: str = "") -> str:
    """Look a string up, falling back to English then to what the caller had."""
    entry = table.get(key, {})
    if field:
        entry = entry.get(field, {})
    if not isinstance(entry, dict):
        return fallback
    return entry.get(lang) or entry.get("en") or fallback


def norm(lang: str) -> str:
    lang = (lang or "en").lower()[:2]
    return lang if lang in LANGS else "en"
