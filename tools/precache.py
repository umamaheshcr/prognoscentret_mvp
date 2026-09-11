"""Pickle each master workbook beside itself, and prove it round-trips equal.

Why this exists: on a 512 MB host, parsing the workbooks with openpyxl at
start-up is the largest memory spike in the process, and it happens before the
app can serve anything. A pickled DataFrame loads with a fraction of that peak
and in a fraction of the time.

Why pickle rather than CSV or parquet: this project's central claim about the
model step is *same input, same forecast, every time*. CSV would re-infer
dtypes on the way back in, and parquet would add pyarrow to a deliberately
five-dependency build. Pickle is pandas-native, adds nothing, and preserves
dtypes exactly — and this script asserts that rather than assuming it.

    python tools/precache.py            # write the caches
    python tools/precache.py --check    # verify only, write nothing
    python tools/precache.py --clear    # delete them; the app reverts to xlsx

The caches are generated, never committed: see .gitignore. `app/data.py`
ignores a cache older than its workbook, so a refreshed snapshot cannot be
served from a stale pickle.
"""

from pathlib import Path
import sys

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
WORKBOOKS = [
    "master_endogenous.xlsx",
    "master_exogenous.xlsx",
    "master_exogenous_fixed.xlsx",
]


def _mib(path: Path) -> str:
    return f"{path.stat().st_size / 1048576:.2f} MiB"


def main(argv: list) -> int:
    check = "--check" in argv
    clear = "--clear" in argv
    failures = 0

    for name in WORKBOOKS:
        book = DATA / name
        cache = book.with_suffix(".pkl")

        if not book.exists():
            print(f"skip   {name} — not present")
            continue

        if clear:
            if cache.exists():
                cache.unlink()
                print(f"remove {cache.name}")
            else:
                print(f"skip   {cache.name} — not present")
            continue

        frame = pd.read_excel(book)

        if check:
            if not cache.exists():
                print(f"MISSING {cache.name}")
                failures += 1
                continue
            reloaded = pd.read_pickle(cache)
        else:
            frame.to_pickle(cache)
            reloaded = pd.read_pickle(cache)

        if frame.equals(reloaded) and list(frame.dtypes) == list(reloaded.dtypes):
            verb = "verified" if check else "wrote   "
            print(f"{verb} {cache.name}  {_mib(cache)}  "
                  f"({len(frame):,} rows, identical to {name})")
        else:
            print(f"MISMATCH {cache.name} — does not round-trip equal to {name}")
            if cache.exists() and not check:
                cache.unlink()
            failures += 1

    if failures:
        print(f"\n{failures} problem(s). The app will read the workbooks directly.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
