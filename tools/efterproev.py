"""CLI for the efterprøv checks. The checks themselves live in
`app/efterproev.py`, because gate 1 derives its warnings from them — a warning
that is computed cannot go stale the way a typed one can.

    python tools/efterproev.py
    python tools/efterproev.py --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.efterproev import report, run  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = run()
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        report(res)
