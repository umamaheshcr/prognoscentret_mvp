"""One append-only journal for every gate.

The analyst's own words are kept verbatim. A paraphrase is already an
interpretation, and the words are the signal — so nothing here summarises,
normalises or trims a reason.

The agent's proposal is stored beside the analyst's value, which is what lets
a later round measure which of the two was closer. That measurement is out of
scope for the pilot: at three forecast rounds a year it cannot be
demonstrated. Recording is in scope, and it is the part that has to be right
from the first round, because a decision not recorded is gone.

Format matches the production loop's `haendelser.jsonl` closely enough to be
imported: one JSON object per line, never rewritten.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import threading

JOURNAL = Path(__file__).resolve().parent.parent / "journal" / "decisions.jsonl"
_lock = threading.Lock()


def record(gate: str, event: str, payload: dict) -> dict:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gate": gate,
        "event": event,
        **payload,
    }
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with JOURNAL.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    return entry


def read_all() -> list:
    if not JOURNAL.exists():
        return []
    out = []
    with JOURNAL.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def count_by_gate() -> dict:
    counts = {}
    for e in read_all():
        counts[e.get("gate", "?")] = counts.get(e.get("gate", "?"), 0) + 1
    return counts


def repeated_corrections() -> list:
    """A correction that comes back twice is a systematic fault in the agent.
    Once is a special case. The pilot only counts; acting on the count is the
    learning loop's job and out of scope here."""
    seen = {}
    for e in read_all():
        if e.get("event") != "override":
            continue
        key = (e.get("driver"), (e.get("reason") or "").strip().lower())
        seen[key] = seen.get(key, 0) + 1
    return [{"driver": k[0], "times": n} for k, n in seen.items() if n >= 2]
