"""The exit barrier.

Four things stop a number and no more:

  1. it is not a number
  2. it is negative on a series that has never been below zero
  3. it is under a `hard_lo` DECLARED in config
  4. it is over a `hard_hi` DECLARED in config

Everything else warns. A guardrail that stops an unusual but *correct* number
is worse than no guardrail: 2022 gave 65 per cent material shortage and a
51-index-point jump in retail confidence, and a limit derived from history
would have made the agent lie about reality.

Hence the rule that what cannot be derived must be declared. Bounds live in
`panel.py`, next to the driver, not inferred from the sample.
"""

from dataclasses import dataclass

from . import i18n
from .panel import BY_KEY


@dataclass
class Verdict:
    ok: bool
    reason: str = ""
    kind: str = "pass"      # pass | refused | warned


def _msg(key: str, lang: str, **kw) -> str:
    return i18n.GUARD[key].get(lang, i18n.GUARD[key]["en"]).format(**kw)


def check(key: str, value, lang: str = "en") -> Verdict:
    lang = i18n.norm(lang)
    d = BY_KEY.get(key)
    if d is None:
        return Verdict(False, _msg("unknown", lang, k=key), "refused")

    label = i18n.pick(i18n.DRIVERS, key, "label", lang, d.label)
    unit = i18n.pick(i18n.UNITS, d.unit, "", lang, d.unit)

    try:
        v = float(value)
    except (TypeError, ValueError):
        return Verdict(False, _msg("not_a_number", lang, v=value), "refused")
    if v != v or v in (float("inf"), float("-inf")):
        return Verdict(False, _msg("not_a_number", lang, v=value), "refused")

    if d.never_negative and v < 0:
        return Verdict(False, _msg("never_negative", lang, label=label), "refused")
    if d.hard_lo is not None and v < d.hard_lo:
        return Verdict(False, _msg("hard_lo", lang, b=d.hard_lo, u=unit), "refused")
    if d.hard_hi is not None and v > d.hard_hi:
        return Verdict(False, _msg("hard_hi", lang, b=d.hard_hi, u=unit), "refused")

    # Warnings never stop anything. They are for the analyst's eyes.
    if v < d.lo or v > d.hi:
        return Verdict(True, _msg("outside_slider", lang, lo=d.lo, hi=d.hi), "warned")
    return Verdict(True, _msg("pass", lang), "pass")
