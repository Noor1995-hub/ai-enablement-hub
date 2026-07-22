"""Build + validate the rewritten 'You're ready' lesson draft. Does NOT touch the DB."""

import json
import os
import re
import uuid


def _id() -> str:
    return str(uuid.uuid4())


def heading(text: str, level: int = 2) -> dict:
    return {"id": _id(), "type": "heading", "level": level, "text": text}


def para(text: str) -> dict:
    return {"id": _id(), "type": "paragraph", "text": text}


def kicker(text: str) -> dict:
    return {"id": _id(), "type": "kicker", "text": text}


def callout(text: str) -> dict:
    return {"id": _id(), "type": "callout", "text": text}


def whitespace(size: str = "md") -> dict:
    return {"id": _id(), "type": "whitespace", "size": size}


def card(title: str, body: str) -> dict:
    return {"id": _id(), "title": title, "body": body}


def card_group(cards: list[dict]) -> dict:
    return {"id": _id(), "type": "card_group", "cards": cards}


def image(alt: str, caption: str, width: int | None = None) -> dict:
    b = {"id": _id(), "type": "image", "blob_path": "", "alt": alt, "caption": caption}
    if width is not None:
        b["width"] = width
    return b


def quiz(questions: list[dict]) -> dict:
    out_q = []
    for q in questions:
        out_q.append(
            {
                "id": _id(),
                "q": q["q"],
                "options": q["options"],
                "correct": q["correct"],
                "explanation": q["explanation"],
            }
        )
    return {"id": _id(), "type": "quiz", "questions": out_q}


blocks = [
    kicker(
        "You started this track knowing how to use AI. You're finishing it knowing how to "
        "direct it: what to hand over, what to check, and when to keep your hands on the work "
        "yourself."
    ),
    para(
        "That shift is what carries. The mechanics of any single tool will change within a "
        "year. The judgement you have built will not."
    ),
    heading("What you now know"),
    para(
        "Seven things, each building on the last:\n\n"
        "- **What generative AI really is**: a model that predicts text, not a system that "
        "looks up facts, though many tools now pair it with search or connectors that add "
        "current information on top.\n"
        "- **Enough of how it works to have good instincts**: tokens and context, why the same "
        "prompt gives different answers, why it can hand you a fluent but confidently wrong "
        "answer.\n"
        "- **How to write a prompt** that gets a usable result.\n"
        "- **How to supply the context** the model cannot see on its own.\n"
        "- **The instruct-review-refine loop**, instead of taking the first draft as final.\n"
        "- **Where it fails and what those failures cost**: bias, stale information, gaps in "
        "reasoning, the tasks that are simply off-limits.\n"
        "- **How to verify before you forward or decide**: what should never be pasted into a "
        "tool, and that whatever goes out is yours to stand behind.\n\n"
        "And the move under all of it: from doing the work to **directing** it, choosing what "
        "to hand off and what needs your own hand."
    ),
    callout(
        "The core skill is **a way of thinking, not a tool.** You start from a plain question, "
        "what is this task really asking for, then choose the method to fit, including the "
        "choice to use no AI at all."
    ),
    heading("What comes next"),
    para(
        "From here the path turns to specific tools. One lens is worth keeping: most AI tools "
        "fall into three broad kinds."
    ),
    card_group(
        [
            card(
                "Conversational tools",
                "The chat-style tools you already know. Draft a reply to a complaint, turn "
                "messy notes into a task list, put a dense clause into plain language. Broad, "
                "flexible, and the default for most knowledge work.",
            ),
            card(
                "Agentic and connected tools",
                "Tools that take several steps on their own and reach into your files, inbox "
                "or systems through connectors. More capable, and more to keep an eye on, "
                "because they act rather than only answer.",
            ),
            card(
                "Specialist tools",
                "Built for one kind of work: writing code, automating a process without code, "
                "running a personal knowledge base. Deeper in their lane, weaker outside it.",
            ),
        ]
    ),
    para(
        "The tracks ahead aren't organised around these three. Each goes deep on one product "
        "(Copilot, Claude, and so on), and a single product often spans more than one kind. "
        "The lens still earns its keep: it tells you what a feature is actually doing, even as "
        "products get renamed and replaced. You will judge a new tool by **what it does and "
        "where it breaks**, not by how it is sold."
    ),
    heading("Where to point it first"),
    para(
        "You have already done this once, on the task you worked through a couple of lessons "
        "back. The same move is your parting advice: pick one **recurring task you already "
        "own**, then refine your approach over a few real repetitions. Something like:\n\n"
        "- the weekly report you always rewrite\n"
        "- the inbox thread that eats an hour\n"
        "- the write-up nobody enjoys drafting\n\n"
        "Calibration comes from reps on work you can already judge. Experiments on unfamiliar, "
        "high-stakes work teach you far less."
    ),
    image(
        alt=(
            "From foundation to tools: the foundation you built (judgement, the loop, "
            "verifying), the three kinds of tool (conversational, agentic and connected, "
            "specialist), and the one recurring task to point it at first"
        ),
        caption="From foundation to tools",
        width=90,
    ),
    whitespace("md"),
    heading("Check your understanding"),
    quiz(
        [
            {
                "q": "Why does this foundation teach categories of AI tools rather than specific products?",
                "correct": 0,
                "options": [
                    "Products change fast, while the categories and the judgement for choosing between them stay put",
                    "Specific products are far too expensive and change too fast to be worth covering in a course",
                    "There is really only one worthwhile tool inside each of these three categories anyway",
                    "Category names happen to be a little easier for most people to memorise than product names",
                ],
                "explanation": "Individual products come and go. The kinds of work they support, and the skill of matching a task to the right approach, carry forward. That judgement is what the foundation was built for.",
            },
            {
                "q": "What does this foundation call the core skill for working with AI?",
                "correct": 2,
                "options": [
                    "Memorising the individual strengths and weaknesses of every major AI product on the market today",
                    "Writing the longest, most exhaustively detailed prompt that you can possibly manage every single time",
                    "Starting from what the task really needs, then choosing the method, including no AI at all",
                    "Always reaching straight for the most powerful, most agentic tool that you happen to have to hand",
                ],
                "explanation": "The judgement is task-first, not tool-first. Sometimes the right call is a simple method or no AI at all. Choosing well beats grabbing the flashiest option.",
            },
            {
                "q": "What is the best way to build real skill with a new tool from here?",
                "correct": 3,
                "options": [
                    "Experiment first on unfamiliar, high-stakes work so that you learn quickly under genuine pressure",
                    "Read carefully through every product review you can find before you ever actually touch the tool",
                    "Skip verifying the output altogether, so that you are able to move through the work much faster",
                    "Point it at a recurring task you already own, then refine over a few repetitions",
                ],
                "explanation": "Calibration comes from repetitions on work you can already evaluate. That is what lets you tell when the output is right or wrong and adjust your direction accordingly.",
            },
        ]
    ),
]

lesson = {
    "id": "a4e1e842-6bf1-4225-a1eb-e3782193b2e0",
    "title": "You're ready",
    "sort_order": 1,
    "content_blocks": blocks,
}

# ---- validation ----
errors = []
warnings = []
FORBIDDEN = {"em dash": "—", "en dash": "–", "ellipsis": "…"}


def walk_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)
    elif isinstance(obj, str):
        yield obj


for s in walk_strings(blocks):
    for name, ch in FORBIDDEN.items():
        if ch in s:
            errors.append(f"{name} found in: {s[:60]!r}")

# duplicate ids
ids = []


def collect_ids(obj):
    if isinstance(obj, dict):
        if "id" in obj:
            ids.append(obj["id"])
        for v in obj.values():
            collect_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            collect_ids(v)


collect_ids(blocks)
dupes = {i for i in ids if ids.count(i) > 1}
if dupes:
    errors.append(f"duplicate ids: {dupes}")

# image sanity: never persist a url; blob_path present
for b in blocks:
    if b["type"] == "image":
        if "url" in b:
            errors.append("image block has a stray 'url' key")
        if "blob_path" not in b:
            errors.append("image block missing 'blob_path'")

# quiz balance
for b in blocks:
    if b["type"] == "quiz":
        for qi, q in enumerate(b["questions"]):
            opts = q["options"]
            lengths = [len(o.split()) for o in opts]
            correct = q["correct"]
            maxlen = max(lengths)
            if lengths[correct] == maxlen and lengths.count(maxlen) == 1:
                errors.append(f"Q{qi + 1}: correct answer is the UNIQUE longest option")
        positions = [q["correct"] for q in b["questions"]]
        if len(set(positions)) == 1:
            warnings.append(f"quiz correct positions do not vary: {positions}")
        print(f"quiz correct positions: {positions}")

# bold count per text field
for s in walk_strings(blocks):
    n = s.count("**") // 2
    # bulleted lead-ins allowed to exceed; only warn on non-bullet blocks
    if n > 2 and "\n- " not in s and not s.strip().startswith("- "):
        warnings.append(f"{n} bold spans in: {s[:50]!r}")

# US spelling scan
us = re.findall(
    r"\b(organiz\w*|recogniz\w*|memoriz\w*|summariz\w*|behavior|color|judgment)\b",
    json.dumps(lesson),
    re.I,
)
if us:
    warnings.append(f"US spellings: {us}")

print(f"\nblocks: {len(blocks)}")
print(f"types: {[b['type'] for b in blocks]}")
print(f"ERRORS: {errors if errors else 'none'}")
print(f"WARNINGS: {warnings if warnings else 'none'}")

out_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "scratch_review",
    "claude_cowork",
    "drafts",
    "foundation_to_tools_REWRITE.json",
)
out_path = os.path.abspath(out_path)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump([lesson], f, ensure_ascii=False, indent=2)
print(f"\nwrote draft -> {out_path}")
