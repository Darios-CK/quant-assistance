"""Daily routine: run every analysis listed in routine.json into reports/auto/ and write an index.

One failing job (source down, missing key) is recorded in the index; the others still run.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone

from qa.cache import ROOT

INDEX = ROOT / "reports" / "auto" / "README.md"


def run_all(path=ROOT / "routine.json") -> int:
    from qa.__main__ import _save, run

    jobs = json.loads(path.read_text(encoding="utf-8"))
    rows, failed = [], 0
    for job in jobs:
        started = datetime.now(timezone.utc)
        try:
            text, per_event, _ = run(job["args"])
            _save(job["name"], text, per_event, fixed=job["name"])
            status = "ok"
        except (Exception, SystemExit) as exc:   # SystemExit: e.g. FRED key missing
            failed += 1
            status = f"fehlgeschlagen: {str(exc).splitlines()[0][:160] if str(exc) else type(exc).__name__}"
            traceback.print_exc(file=sys.stderr)
        rows.append((job, status, (datetime.now(timezone.utc) - started).total_seconds()))
        print(f"{job['name']}: {status}", file=sys.stderr)

    lines = ["# Automatische Berichte", "",
             f"Stand: {datetime.now(timezone.utc):%d.%m.%Y %H:%M} UTC · neu berechnet an jedem Werktag", "",
             "| Bericht | Status | Dauer |", "|---|---|---:|"]
    for job, status, secs in rows:
        link = f"[{job['titel']}]({job['name']}.md)" if status == "ok" else job["titel"]
        lines.append(f"| {link} | {status} | {secs:.0f} s |")
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return failed
