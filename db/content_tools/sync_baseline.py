"""Re-apply an edits module (same format as apply_content_edits.py) directly
onto db/baseline/data/lessons.json, so the local snapshot matches what was
just written live -- WITHOUT reformatting the rest of the 90+ untouched
lessons in the file.

IMPORTANT gotcha (hit and fixed once already this project): do NOT
json.dumps(..., sort_keys=True) or otherwise rebuild the whole file from a
freshly-serialized structure. The original file's per-object key order is
NOT alphabetical (it's whatever order the original export used, e.g.
id/text/type/level for headings) and reformatting it produces a spurious
diff across every lesson in the file, not just the ones you touched. This
script avoids that by only ever mutating VALUES of keys that already exist
on the loaded objects (Python dicts preserve their original key-insertion
order when you reassign an existing key) -- never rebuilding a block dict
from scratch except for genuinely new blocks/steps you're adding.

Usage:
    python db/content_tools/sync_baseline.py titles.json edits.py
    (no DB connection needed -- this only touches the local file)
"""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _edit_engine import apply_one  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "db" / "baseline" / "data" / "lessons.json"


def main() -> None:
    edits_module_path = Path(sys.argv[1])

    spec = importlib.util.spec_from_file_location("edits_module", edits_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    EDITS = mod.EDITS

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    by_title = {l["title"]: l for l in baseline}

    touched = 0
    for title, ledits in EDITS.items():
        if title not in by_title:
            raise SystemExit(f"lesson not in baseline: {title}")
        blocks = by_title[title]["content_blocks"]
        for e in ledits:
            apply_one(blocks, e)
        touched += 1

    print(f"patched {touched} lessons in baseline")

    text = json.dumps(baseline, indent=2) + "\n"
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")  # match the file's existing CRLF convention
    BASELINE.write_bytes(text.encode("utf-8"))
    print(f"wrote {BASELINE}")
    print("\nNow verify scope with git:")
    print('  git diff --stat -- db/baseline/data/lessons.json')
    print("  (should show only the lessons you actually touched, not the whole file --")
    print("   if it's huge, something reformatted an untouched lesson; investigate before committing)")


if __name__ == "__main__":
    main()
