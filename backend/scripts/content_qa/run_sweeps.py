"""Run deterministic checks over the snapshot; emit findings + per-module files."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from content_qa.checks import (
    check_quiz_conformance, find_americanisms, find_banned_punctuation, quiz_stats,
)

OUT_DIR = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def main() -> None:
    lessons = json.loads((OUT_DIR / "lessons_snapshot.json").read_text(encoding="utf-8"))
    findings: dict[str, dict] = {}
    modules: dict[str, dict] = {}

    for les in lessons:
        blocks = les["content_blocks"]
        det = {
            "track": les["track"], "module_title": les["module_title"],
            "lesson_title": les["lesson_title"],
            "punctuation": find_banned_punctuation(blocks),
            "americanisms": find_americanisms(blocks),
            "quiz_conformance": check_quiz_conformance(blocks),
            "quiz_stats": quiz_stats(blocks),
        }
        findings[les["lesson_id"]] = det

        key = f"{les['module_order']:02d}__{les['track']}__{les['module_title']}"
        mod = modules.setdefault(key, {"track": les["track"],
                                       "module_title": les["module_title"], "lessons": []})
        mod["lessons"].append({
            "lesson_id": les["lesson_id"], "lesson_title": les["lesson_title"],
            "content_blocks": blocks, "deterministic": det,
        })

    (OUT_DIR / "deterministic_findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")

    per_module_dir = OUT_DIR / "per_module"
    per_module_dir.mkdir(exist_ok=True)
    for key, mod in modules.items():
        (per_module_dir / f"{slug(key)}.json").write_text(
            json.dumps(mod, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary roll-up
    punct = sum(len(f["punctuation"]) for f in findings.values())
    amer = sum(len(f["americanisms"]) for f in findings.values())
    conf: Counter = Counter()
    for f in findings.values():
        for c in f["quiz_conformance"]:
            conf[c["kind"]] += 1
    per_quiz_qcount: Counter = Counter()
    for f in findings.values():
        by_quiz: Counter = Counter(q["quiz_index"] for q in f["quiz_stats"]["questions"])
        for cnt in by_quiz.values():
            per_quiz_qcount[cnt] += 1

    lines = [
        "# Deterministic sweep summary - admin content QA 2026-07-20", "",
        f"- Lessons scanned: {len(findings)}",
        f"- Banned-punctuation hits: {punct}",
        f"- Americanism hits: {amer}",
        f"- Quizzes total: {sum(f['quiz_stats']['num_quizzes'] for f in findings.values())}",
        f"- Modules: {len(modules)}", "",
        "## Quiz conformance findings", "",
        *[f"- {k}: {v}" for k, v in sorted(conf.items())], "",
        "## Questions-per-quiz distribution", "",
        *[f"- {k} questions: {v} quizzes" for k, v in sorted(per_quiz_qcount.items())],
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Findings for {len(findings)} lessons; {len(modules)} per-module files; summary.md written.")


main()
