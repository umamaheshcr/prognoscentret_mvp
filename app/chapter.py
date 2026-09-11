"""Gate 3 and publish — the chapter, and the check that binds every number.

**This is not P3's writer.** P3 drafts with a language model from a brief; this
is a deterministic sentence assembler, and it is labelled as such everywhere it
appears. It exists so the pilot can demonstrate the *control* rather than the
prose: every figure in the text carries a binding, and `check()` fails the
publish if any figure cannot be traced to the forecast, a driver, or a source.

That is the production rule kept intact: a number must be bound to a source, or
the export exits 1. A figure that binds to none of them is invented.

Two house rules from `style/dk.md` are honoured because breaking them would
misrepresent the system:

  * **Tobin's Q is never named in the text.** The reader cannot verify an
    index; 1.19 says nothing without the fraction. The text talks about prices
    against costs instead.
  * **A source estimate carries its date** and its publication by title, so the
    reader can see whether it is still current.
"""

from dataclasses import dataclass
import re


@dataclass
class Bound:
    """A number in the text and where it comes from."""
    marker: str          # [1], [2] …
    value: str
    binding: str         # human-readable source
    kind: str            # forecast | driver | source | husberegning | analytikerskoen


NBSP = " "


def num(v: float, dec: int, lang: str) -> str:
    """Swedish and Danish write 19 728 and 12,0; English writes 19,728 and 12.0.
    Getting this wrong in a published chapter is not cosmetic — 12,0 read as an
    English number is a hundred and twenty.

    Thousands use a NON-BREAKING space. That is typographically correct, and it
    also keeps `check()` unambiguous: with an ordinary space "19 728" reads as
    two numbers, and the first of them looks naked.
    """
    s = f"{v:,.{dec}f}"
    if lang == "sv":
        s = s.replace(",", NBSP).replace(".", ",")
    return s


def build(result: dict, overrides: dict, lang: str = "en") -> dict:
    """Assemble the chapter from the forecast that was just signed off."""
    ann = result["annual_forecast"]
    base = result["annual_baseline"]
    years = sorted(ann)
    y0, yl = years[0], years[-1]
    seg = result["label"]
    unit = result["unit"].split(" per ")[0]
    dec = result["decomposition"]

    revised = abs(ann[y0] / base[y0] - 1) > 0.0005
    dirn = ("higher" if ann[y0] > base[y0] else "lower") if revised else "unchanged"

    bounds = [
        Bound("[1]", num(ann[y0], 0, lang), "P2 forecast · this round", "forecast"),
        Bound("[2]", num(ann[yl], 0, lang), "P2 forecast · this round", "forecast"),
        Bound("[3]", num(result["tobins_q_2026"], 2, lang),
              "master_exogenous.xlsx · Tobins-Q · 2026 annual mean", "driver"),
        Bound("[4]", num(12.0, 1, lang),
              "Prognosecenteret · Tobins Q - autoudtræk.xlsx · "
              "boligprisbane_etageboliger, read 28 August 2026", "husberegning"),
        Bound("[5]", num(15.0, 1, lang),
              "Nykredit · Boligprisprognose Danmark · 2 July 2026", "source"),
        Bound("[6]", num(15.8, 1, lang),
              "DST EJ56 · OMRÅDE 000 · EJENDOMSKATE 2103 · TAL 310 · 2026K1", "source"),
    ]
    if revised:
        bounds.append(Bound("[7]", num(abs(ann[y0] / base[y0] - 1) * 100, 1, lang),
                            "gate 1 · analyst override, journalled with its reason",
                            "forecast"))

    # Gate 1b. An overlay has no model behind it, so the analyst IS the source
    # — named, dated, and carrying the reason they gave. The rule was never
    # "a number must come from a document"; it was "a number must have a source
    # you can name".
    #
    # EVERY overlaid year is reported, not just the first. An overlay the text
    # does not mention is the dishonest case this whole layer exists to avoid:
    # the reader would see a level and attribute it to the model.
    # Each overlay contributes TWO bindings, because the sentence states two
    # numbers: what the analyst set, and what the model gave. Quoting the
    # model's figure without binding it is the naked-number case the check
    # exists to catch — and it caught it.
    overlays = sorted(result.get("overlay", []), key=lambda a: a["year"])
    for adj in overlays:
        adj["_marker"] = f"[{len(bounds) + 1}]"
        bounds.append(Bound(
            adj["_marker"], num(adj["analyst_value"], 0, lang),
            f"analytikerskøn · gate 1b, {adj['ts'][:10]} — set by hand for "
            f"{adj['year']} because: {adj['reason']}",
            "analytikerskoen"))
        adj["_marker_model"] = f"[{len(bounds) + 1}]"
        bounds.append(Bound(
            adj["_marker_model"], num(adj["model_value"], 0, lang),
            f"P2 forecast · {adj['year']}, before the gate-1b overlay",
            "forecast"))

    if lang == "sv":
        body = [
            f"Nybyggandet av {seg.lower()} beräknas till "
            f"{num(ann[y0], 0, lang)}[1] {unit} {y0} och {num(ann[yl], 0, lang)}[2] {yl}.",
            "Lönsamheten i att bygga bestäms av bostadspriserna mot "
            "byggkostnaderna, och avståndet mellan dem är poängen — inte nivån "
            f"i sig. Förhållandet ligger på {num(result['tobins_q_2026'], 2, lang)}[3] {y0}.",
            "Priserna på etageboliger stiger men decelererar: husets bana visar "
            f"{num(12.0, 1, lang)}[4] procent för {y0}, medan Nykredit i sin prognos "
            f"från juli 2026 väntar {num(15.0, 1, lang)}[5] procent. Den realiserade "
            f"tillväxten var {num(15.8, 1, lang)}[6] procent i första kvartalet 2026, "
            "femte kvartalet i följd med acceleration.",
        ]
        if revised:
            body.append(
                f"Prognosen är reviderad {num(abs(ann[y0] / base[y0] - 1) * 100, 1, lang)}[7] "
                f"procent {'upp' if ann[y0] > base[y0] else 'ned'} mot agentens "
                "förslag efter analytikerns beslut i grind 1."
            )
        for ol in overlays:
            body.append(
                f"Nivån för {ol['year']} är satt av analytikern till "
                f"{num(ol['analyst_value'], 0, lang)}{ol['_marker']} {unit} — "
                f"modellen gav {num(ol['model_value'], 0, lang)}"
                f"{ol['_marker_model']}. Det är ett "
                "skön, inte en drivare, och det bärs av analytikern."
            )
    else:
        body = [
            f"New construction of {seg.lower()} is estimated at "
            f"{num(ann[y0], 0, lang)}[1] {unit} in {y0} and {num(ann[yl], 0, lang)}[2] in {yl}.",
            "The profitability of building is set by house prices against "
            "construction costs, and the distance between them is the point — not "
            f"the level itself. The ratio stands at {num(result['tobins_q_2026'], 2, lang)}[3] "
            f"in {y0}.",
            "Apartment prices are still rising but decelerating: the house path "
            f"shows {num(12.0, 1, lang)}[4] per cent for {y0}, while Nykredit's "
            f"July 2026 forecast expects {num(15.0, 1, lang)}[5] per cent. Realised "
            f"growth was {num(15.8, 1, lang)}[6] per cent in the first quarter of "
            "2026, the fifth consecutive quarter of acceleration.",
        ]
        if revised:
            body.append(
                f"The forecast is revised {num(abs(ann[y0] / base[y0] - 1) * 100, 1, lang)}[7] "
                f"per cent {dirn} against the agent's proposal, following the "
                "analyst's decision at gate 1."
            )
        for ol in overlays:
            body.append(
                f"The level for {ol['year']} is set by the analyst at "
                f"{num(ol['analyst_value'], 0, lang)}{ol['_marker']} {unit} — the "
                f"model gave {num(ol['model_value'], 0, lang)}"
                f"{ol['_marker_model']}. That is a "
                "judgement, not a driver, and it is carried by the analyst."
            )

    return {
        "section": "house_prices",
        "title": "Huspriser" if lang == "sv" else "House prices",
        "paragraphs": body,
        "bounds": [b.__dict__ for b in bounds],
        "assembled_by": "deterministic template — NOT P3's language model",
        "style_notes": [
            "Tobin's Q is not named in the text: a reader cannot verify an index.",
            "Every source estimate carries its publication and date (style rule 43).",
            "Apartment growth is quoted quarter against the same quarter a year "
            "earlier, never as an annual average.",
            "An overlaid level is reported as the analyst's judgement and never "
            "attributed to the model.",
        ],
    }


MARKER = re.compile(r"\[\d+\]")
# A number is a run of digits with optional thousands/decimal separators —
# including the non-breaking space Swedish uses for thousands. The pattern
# starts at a digit preceded by neither a digit, a separator, nor an opening
# bracket, so it can never begin part-way through a longer number, and never
# matches the digit inside a [1] marker.
NUMBER = re.compile(r"(?<![\d.,\[ ])\d+(?:[., ]\d+)*")
BOUND_AFTER = re.compile(r"^\s*\[\d+\]")


def check(chapter: dict, edited: str | None = None) -> dict:
    """The deterministic check. Every number in the text must be followed by a
    marker, and every marker must have a binding. Exits with ok=False
    otherwise — the production equivalent exits 1 and the export does not
    happen.

    The dangerous case is a *naked* number: a figure in the prose that claims
    nothing. Years and small ordinals are not claims, and are excused by name
    rather than by a loose pattern.
    """
    text = edited if edited is not None else " ".join(chapter["paragraphs"])
    used = set(MARKER.findall(text))
    declared = {b["marker"] for b in chapter["bounds"]}

    unbound = sorted(used - declared)      # a marker citing a binding that does not exist
    unused = sorted(declared - used)       # a binding nothing cites

    naked = []
    for m in NUMBER.finditer(text):
        tok = m.group(0)
        rest = text[m.end():]
        if BOUND_AFTER.match(rest):        # the number carries its binding
            continue
        if re.fullmatch(r"(19|20)\d\d", tok):   # a year is not a claim
            continue
        if tok in {"1", "2", "3", "4", "5"}:    # ordinals in prose (gate 1, kv4)
            continue
        naked.append(tok)

    ok = not unbound and not naked
    return {
        "ok": ok,
        "bound": len(used & declared),
        "declared": len(declared),
        "unbound_markers": unbound,
        "unused_bindings": unused,
        "naked_numbers": naked,
        "verdict": (
            f"{len(used & declared)} of {len(declared)} numbers bound to a source"
            if ok else
            "REFUSED — a number in the text binds to nothing. In production this "
            "exits 1 and the export does not happen."
        ),
    }


def source_list(chapter: dict) -> list:
    """The machine-built source list. Not typed — derived from the bindings,
    which is the whole reason it can be trusted."""
    seen, out = set(), []
    for b in chapter["bounds"]:
        if b["binding"] in seen:
            continue
        seen.add(b["binding"])
        out.append({"binding": b["binding"], "kind": b["kind"]})
    return out
