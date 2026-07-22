"""Add the review's quiz verdicts to each fresh per-module file.

The apply agents work from fresh content but need the review's quiz judgement
(which quiz to shuffle/trim/fix and why). Matches phase2 review entries to
per-module files by filename basename.
"""

import json
import os
from pathlib import Path

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
PM = WORK / "per_module"
phase2 = json.loads((WORK / "phase2_findings_review.json").read_text(encoding="utf-8"))

by_base = {}
for entry in phase2:
    base = os.path.basename(entry["module_path"].replace("\\", "/"))
    by_base[base] = entry

n = 0
for f in PM.glob("*.json"):
    mod = json.loads(f.read_text(encoding="utf-8"))
    review = by_base.get(f.name, {})
    mod["quiz_verdicts"] = review.get("quiz", [])
    mod["editorial_copy_notes"] = review.get("copy_layout", [])
    f.write_text(json.dumps(mod, ensure_ascii=False, indent=2), encoding="utf-8")
    n += 1
print(f"enriched {n} per-module files with quiz_verdicts + editorial notes")
