"""The gate-1 driver panel.

One entry per driver the analyst approves. The values here are the September
2026 round as it stands in the sources named — the agent's proposal, the
institutions' figures beside it, and the verbatim-quote slot.

House rule kept: no number without its source. Where a quote has not been
lifted from the source document into this file, `quote` is None and the panel
says so rather than inventing one.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

from . import bundle, efterproev, i18n


@dataclass
class Institution:
    name: str
    value: Optional[float]
    published: str
    note: str = ""


@dataclass
class Driver:
    key: str
    label: str
    unit: str
    year: int
    agent: float                  # the agent's triangulated proposal
    lo: float                     # slider floor
    hi: float                     # slider ceiling
    step: float
    source: str                   # where the agent's number comes from
    in_model: bool                # does the forecast actually eat this?
    effect: str = ""              # how it reaches the model, in one line
    hard_lo: Optional[float] = None   # guard: declared in config, not derived
    hard_hi: Optional[float] = None
    never_negative: bool = False
    quote: Optional[str] = None
    institutions: list = field(default_factory=list)
    warning: Optional[str] = None
    series: Optional[str] = None   # its column in master_exogenous, for efterprøv
    bundle_id: Optional[str] = None   # the research driver whose range this uses
    range_basis: Optional[str] = None  # filled from the bundle, never typed
    efterproev: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["institutions"] = [asdict(i) for i in self.institutions]
        return d


# ── The September 2026 round ────────────────────────────────────────────────
#
# hpi is defined as enfamiliehuse — all 39 claims — and the same numerator
# feeds Tobin's Q for Detached houses, Flats AND Holiday homes. That is why
# the single house-price slider moves every residential segment, and why the
# etageboliger path below is present but inert.

DRIVERS = [
    Driver(
        key="rate",
        label="Real mortgage rate",
        unit="pct",
        year=2026,
        agent=2.52,
        lo=0.0, hi=6.0, step=0.01,
        source="master_exogenous.xlsx · Real Interest rate (Mortgage) · 2026 annual mean",
        in_model=True,
        effect="enters both residential models directly, coefficient b2",
        hard_lo=0.0,
        never_negative=True,
        quote=None,
        series="Real Interest rate (Mortgage)",
        bundle_id="exo:Real interest rate (Mortgage)",
        institutions=[
            Institution("DØR", None, "2026-05-01",
                        "Dansk Økonomi, forår 2026 — forecasts the long rate, not the mortgage real rate"),
            Institution("ØM", None, "2026-08-27",
                        "Økonomisk Redegørelse, august 2026"),
        ],
        warning="No source forecasts the mortgage rate to 2028. That year is "
                "unverified, not approved — mortgage_rate 2028 has no guard.",
    ),
    Driver(
        key="hpi",
        label="House prices — enfamiliehuse",
        unit="pct y/y, Q4",
        year=2026,
        agent=6.0,
        lo=-10.0, hi=25.0, step=0.1,
        source="Prognosecenteret · Tobins Q - autoudtræk.xlsx ('Til manuel figur'); "
               "history DST EJ56 · EJENDOMSKATE 0111 · TAL 310",
        bundle_id="hpi",
        in_model=True,
        effect="the only hpi in the model — numerator of Tobin's Q for EVERY "
               "residential segment, apartments included",
        quote=None,
        institutions=[
            Institution("House path", 6.0, "2026-08-28",
                        "boligprisbane_enfamiliehuse — 2025 realised 7.2, then 6.0 · 2.5 · 2.5"),
        ],
        warning="This is the finding, not a bug in the demo: move this slider and "
                "apartment starts move, because apartment construction is driven by "
                "single-family house prices in the current specification.",
    ),
    Driver(
        key="cost",
        label="Construction costs",
        unit="pct y/y",
        year=2026,
        agent=0.2,
        lo=-4.0, hi=10.0, step=0.1,
        source="master_exogenous.xlsx · Construction costs · index 118.6 in 2026 "
               "(118.3 in 2025, 121.4 in 2027, 124.3 in 2028)",
        in_model=True,
        effect="denominator of Tobin's Q — raising costs lowers profitability of building",
        quote=None,
        series="Construction costs",
        bundle_id="exo:Construction costs",
        institutions=[],
    ),
    Driver(
        key="cci",
        label="Consumer confidence",
        unit="balance",
        year=2026,
        agent=-9.9,
        lo=-25.0, hi=5.0, step=0.1,
        source="master_exogenous.xlsx · Consumer confidence indicator (CCI) · "
               "2026 annual mean (−16.7 in 2025, −4.6 in 2027, −2.4 in 2028)",
        in_model=False,
        effect="not in the pilot's two-driver specification — it enters the "
               "production Holiday houses model as an HP deviation",
        quote=None,
        series="Consumer confidence indicator (CCI)",
        bundle_id="exo:Consumer confidence indicator (CCI)",
        institutions=[],
        warning="Open question in notes/dk_new_residential.md: the May text says "
                "confidence sits at financial-crisis level; the driver path improves "
                "steadily from −16.7 to −2.4. Unresolved since 8 August.",
    ),
]


# Present but deliberately inert: the apartment price path the model cannot use.
INERT = [
    Driver(
        key="hpi_flats",
        label="House prices — etageboliger",
        unit="pct y/y, Q4",
        year=2026,
        agent=12.0,
        lo=-10.0, hi=25.0, step=0.1,
        source="Prognosecenteret · Tobins Q - autoudtræk.xlsx; "
               "history DST EJ56 · EJENDOMSKATE 2103 · TAL 310",
        bundle_id="hpi_flats",
        in_model=False,
        effect="NOT WIRED. There is no apartment hpi driver in master_exogenous.xlsx.",
        quote=None,
        institutions=[
            Institution("House path", 12.0, "2026-08-28",
                        "boligprisbane_etageboliger — 2025 realised 13.0, then 12.0 · 2.5 · 2.0"),
            Institution("Nykredit", 15.0, "2026-07-02",
                        "Boligprisprognose Danmark — one of only two Danish institutions "
                        "that publish an apartment number"),
            Institution("Nordea Kredit", None, "2026-01",
                        "Ny boligprisprognose — the other one"),
        ],
        warning="Realised apartment growth accelerated five quarters running: "
                "8.6 · 10.4 · 10.7 · 13.0 · 15.8 (DST EJ56, 2025K1–2026K1). None of "
                "it reaches the model. Admitting Nykredit and Nordea Kredit through "
                "`optag` is the fix — both sit in cluster dk_private, so triangulation "
                "independence stays weak and that has to be said out loud.",
    ),
]


def _bundle_range(d):
    """Slider bounds come from the research bundle, which states them per year
    with a declared basis — institutional spread, a single source with air
    around it, or the series' own history.

    They used to be hand-set here. That was the one invented number left in this
    file: a bound nobody measured, presented next to values that were all read
    from somewhere. Where the bundle has a range, it wins; where it does not,
    the fallback is marked so it cannot be mistaken for a measurement.
    """
    if not d.bundle_id:
        return None
    try:
        card = bundle.driver_card(d.bundle_id)
    except Exception:
        return None
    if not card:
        return None
    lows, highs, bases = [], [], []
    for y in card["years"]:
        sl = y.get("slider") or {}
        if sl.get("min") is not None and sl.get("max") is not None:
            lows.append(float(sl["min"]))
            highs.append(float(sl["max"]))
            if sl.get("basis"):
                bases.append(sl["basis"])
    if not lows:
        return None
    # The pilot's slider is one control for the whole horizon, so it must span
    # every year's range rather than any single year's.
    return min(lows), max(highs), "+".join(sorted(set(bases)))


def _localise(d, lang):
    out = d.to_dict()
    rng = _bundle_range(d)
    if rng:
        lo, hi, basis = rng
        # The bundle states costs and Tobin's Q as y/y fractions; this panel's
        # cost slider is in per cent, so a fraction range converts.
        if d.key == "cost":
            lo, hi = lo * 100.0, hi * 100.0
        # A declared hard bound beats a derived range. The bundle pads its
        # history-based range outward, which for the real mortgage rate crosses
        # zero — and that rate has never been below zero in 92 quarters
        # (minimum 0.0418 in 2022Q3). Offering a range guard will refuse is a
        # worse interface than a narrower honest one.
        clamped = []
        if d.hard_lo is not None and lo < d.hard_lo:
            lo = d.hard_lo
            clamped.append("hard_lo")
        if d.hard_hi is not None and hi > d.hard_hi:
            hi = d.hard_hi
            clamped.append("hard_hi")
        if d.never_negative and lo < 0:
            lo = 0.0
            clamped.append("never_negative")
        out["lo"], out["hi"] = round(lo, 4), round(hi, 4)
        out["range_basis"] = basis + (
            " · clamped to " + "+".join(clamped) if clamped else "")
    else:
        out["range_basis"] = "fallback · not measured"
    # Derived, not typed: the gate shows what the checks find in the file it is
    # actually using, so the warning cannot outlive the defect.
    if d.series:
        out["efterproev"] = efterproev.for_driver(d.series)
    out["label"] = i18n.pick(i18n.DRIVERS, d.key, "label", lang, d.label)
    out["unit"] = i18n.pick(i18n.UNITS, d.unit, "", lang, d.unit)
    out["effect"] = i18n.pick(i18n.DRIVERS, d.key, "effect", lang, d.effect)
    if d.warning:
        out["warning"] = i18n.pick(i18n.DRIVERS, d.key, "warning", lang, d.warning)
    return out


def panel(lang: str = "en"):
    lang = i18n.norm(lang)
    return {
        "round": "Denmark · September 2026",
        "sources_as_of": "1 September 2026",
        "drivers": [_localise(d, lang) for d in DRIVERS],
        "inert": [_localise(d, lang) for d in INERT],
    }


BY_KEY = {d.key: d for d in DRIVERS}
