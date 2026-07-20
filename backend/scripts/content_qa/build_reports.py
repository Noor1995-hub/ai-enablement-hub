"""Merge deterministic + editorial findings into the two review reports.

Editorial (Phase 2) findings are joined to modules by the ASCII per-module file
path the agent echoed back (module titles contain em-dashes and are not trusted
from agent echo); the authoritative track/module_title come from that file.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
OUT = Path(__file__).resolve().parents[2].parent / "scratch_review"
PER_MODULE = WORK / "per_module"

# terms where the American form may be a legitimate product name, not an error
PRODUCT_NAME_TERMS = {"artifact", "artifacts"}


def load(name):
    return json.loads((WORK / name).read_text(encoding="utf-8"))


def module_meta(module_path: str) -> tuple[str, str]:
    """Resolve (track, module_title) from the per-module file, by basename."""
    base = module_path.replace("\\", "/").rsplit("/", 1)[-1]
    d = json.loads((PER_MODULE / base).read_text(encoding="utf-8"))
    return d["track"], d["module_title"]


def main() -> None:
    snapshot = load("lessons_snapshot.json")
    det = load("deterministic_findings.json")
    phase2 = load("phase2_findings.json")

    # (track, module_title) -> (track_order, module_order) for stable ordering
    order = {}
    for les in snapshot:
        order[(les["track"], les["module_title"])] = (les["track_order"], les["module_order"])

    # editorial findings keyed by (track, module_title)
    ed_copy = defaultdict(list)
    ed_quiz = defaultdict(list)
    for entry in phase2:
        track, mtitle = module_meta(entry["module_path"])
        ed_copy[(track, mtitle)].extend(entry.get("copy_layout", []))
        ed_quiz[(track, mtitle)].extend(entry.get("quiz", []))

    # ---- Copy/layout report, grouped track > module > lesson ----
    cl = [
        "# Copy & layout review - admin-assigned content (2026-07-20)", "",
        "Report-only. Standard: `scratch_review/claude_cowork/authoring_guide.md`.",
        "Deterministic findings (punctuation, en-GB, spacing) are exhaustive for their patterns; "
        "editorial findings are judgement.", "",
        "> **Caveat on `artifact`/`artifacts`:** house spelling is *Artefact*, but *Artifacts* is "
        "also Anthropic's real product-feature name. En-GB findings on these terms are correct "
        "only where the text is prose, not naming the Claude product - verify before applying.", "",
    ]
    # Group lessons by module first. Two Claude modules share sort_order, so
    # their lessons interleave in the flat snapshot; grouping by module_title
    # keeps each module in one section and prevents double-printed editorials.
    mod_groups: dict = {}
    for les in snapshot:
        key = (les["track_order"], les["module_order"], les["track"], les["module_title"])
        mod_groups.setdefault(key, []).append(les)

    cur_t = None
    for (t_ord, m_ord, track, mtitle), mod_lessons in sorted(mod_groups.items()):
        if track != cur_t:
            cur_t = track; cl.append(f"\n## {track}")
        cl.append(f"\n### {mtitle}")
        for les in mod_lessons:
            d = det[les["lesson_id"]]
            if not (d["punctuation"] or d["americanisms"] or d["quiz_conformance"]):
                continue
            cl.append(f"\n**{les['lesson_title']}**")
            for f in d["punctuation"]:
                cl.append(f"- [punctuation/{f['char']}] `{f['path']}` - {f['snippet']}")
            for f in d["americanisms"]:
                note = " (verify: product name?)" if f["term"].lower() in PRODUCT_NAME_TERMS else ""
                cl.append(f"- [en-GB] `{f['term']}` -> `{f['suggestion']}`{note} at `{f['path']}` - {f['snippet']}")
            for f in d["quiz_conformance"]:
                cl.append(f"- [spacing/{f['kind']}] block {f['block_index']}: {f['detail']}")
        _flush_editorial(cl, ed_copy, track, mtitle)
    (OUT / "copy_layout_review_2026-07-20.md").write_text("\n".join(cl), encoding="utf-8")

    # ---- Quiz report ----
    qz = [
        "# Quiz review - admin-assigned content (2026-07-20)", "",
        "Report-only. Standard: `scratch_review/claude_cowork/authoring_guide.md`.",
        "Answer-length bias is already fixed and not reported.", "",
    ]
    verdicts = Counter()
    for key in sorted(ed_quiz, key=lambda k: order.get(k, (99, 99))):
        entries = [q for q in ed_quiz[key] if q.get("verdict") != "no-quiz-ok"]
        if not entries:
            continue
        qz.append(f"\n## {key[0]} - {key[1]}")
        for q in entries:
            verdicts[q["verdict"]] += 1
            bits = [f"**{q['lesson_title']}** - _{q['verdict']}_", q["rationale"]]
            if q.get("suggested_question_count") is not None:
                bits.append(f"suggested questions: {q['suggested_question_count']}")
            mode = q.get("suggested_interactive_mode")
            if mode and mode != "none":
                bits.append(f"convert to: {mode}")
            if q.get("variety_note"):
                bits.append(f"variety: {q['variety_note']}")
            if q.get("quality_flags"):
                bits.append("flags: " + ", ".join(q["quality_flags"]))
            qz.append("- " + " | ".join(bits))

    # hub-wide stats from deterministic data
    per_quiz_qcount = Counter()
    positions = Counter()
    for d in det.values():
        by_quiz = defaultdict(list)
        for q in d["quiz_stats"]["questions"]:
            by_quiz[q["quiz_index"]].append(q)
            positions[q["correct_index"]] += 1
        for qs in by_quiz.values():
            per_quiz_qcount[len(qs)] += 1
    qz += [
        "\n## Hub-wide stats", "",
        "Verdicts: " + ", ".join(f"{k}={v}" for k, v in verdicts.most_common()),
        "Questions per quiz: " + ", ".join(f"{k}q={v}" for k, v in sorted(per_quiz_qcount.items())),
        "Correct-option position counts: " + ", ".join(f"idx{k}={v}" for k, v in sorted(positions.items())),
    ]
    (OUT / "quiz_review_2026-07-20.md").write_text("\n".join(qz), encoding="utf-8")
    print("Wrote copy_layout_review_2026-07-20.md and quiz_review_2026-07-20.md")


def _flush_editorial(cl: list, ed_copy: dict, track, module_title) -> None:
    if track is None or module_title is None:
        return
    items = ed_copy.get((track, module_title))
    if not items:
        return
    cl.append("\n_Editorial (judgement) findings:_")
    for f in items:
        sev = f.get("severity", "")
        tag = f["issue_type"] + (f"/{sev}" if sev else "")
        cl.append(f"- [{tag}] **{f['lesson_title']}**: \"{f['quote']}\" -> {f['suggestion']}")


main()
