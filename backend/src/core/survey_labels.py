"""Assessment code → human-label maps, ported from frontend/src/lib/surveyOptions.ts.

The frontend file is the source of truth (it renders the questions). This copy
feeds the interviewer's briefing (services/interview_context.py) and the project
data export (services/project_export_service.py).
tests/unit/test_survey_labels_drift.py fails when the two drift apart, so edit
both in the same PR.
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "ATTITUDE",
    "BARRIERS",
    "BREADTH",
    "COMPETENCIES",
    "COMPETENCY_C1",
    "COMPETENCY_C2",
    "COMPETENCY_C3",
    "COMPETENCY_C4",
    "COMPETENCY_C5",
    "COMPETENCY_C6",
    "FREQ",
    "READINESS",
    "SETUP",
    "TOOLS",
    "Competency",
]

FREQ = {
    "NEVER": "Never",
    "MONTHLY": "A few times a month",
    "WEEKLY": "Most weeks",
    "DAILY": "Most days",
    "INTENSIVE": "Every day",
}

BREADTH = {
    "NONE": "None of my work",
    "FEW": "One or two tasks",
    "SEVERAL": "Several areas",
    "MOST": "Across most of my work",
    "ALL": "Across all of my work",
}

TOOLS = {
    "CHATGPT": "ChatGPT",
    "COPILOT": "Microsoft Copilot",
    "CLAUDE": "Claude",
    "GEMINI": "Gemini",
    "OTHER": "Other (incl. tools built into software you use)",
    "NONE_YET": "None yet",
}

ATTITUDE = {
    1: "I'd rather not",
    2: "Cautious",
    3: "Neutral",
    4: "Positive",
    5: "Eager",
}

READINESS = {
    1: "Keep as is",
    2: "Small tweaks",
    3: "Open to change",
    4: "Full rethink",
    5: "Already there",
}

BARRIERS = {
    "NO_ACCESS": "No access to AI tools",
    "NO_TIME": "No time to learn it",
    "DONT_TRUST": "Don't trust the outputs",
    "NOT_SURE_ALLOWED": "Not sure it's allowed",
    "POLICY_RESTRICTS": "Company policy restricts it",
    "DONT_SEE": "Don't see where it'd help",
    "NOTHING": "Nothing, I use it freely",
}

SETUP = {
    "WORKSPACE": "A saved workspace or Project with custom instructions for a recurring context",
    "REUSABLE_INSTR": (
        "A reusable instruction set, Skill, agent or saved prompt template for repeated tasks"
    ),
    "CONNECTION": "A connection linking an AI tool to another app (email, files, spreadsheets)",
    "MULTI_STEP": "A multi-step workflow that chains several steps or tools together",
    "DOCUMENTED": "A workflow documented well enough that someone else could run it",
    "NONE": "None of these yet",
}

COMPETENCY_C1 = {
    "MISSING": "Honestly, I'm not sure how it works.",
    "PARTIAL": "It understands my question and gives back the correct information it has stored.",
    "HAVE": (
        "It predicts likely wording from patterns in its training, so it's often useful "
        "but can be wrong."
    ),
    "ADV_D": (
        "It completes text from patterns rather than looking anything up or reasoning it "
        "out, so what it produces reflects what's statistically likely, not what's true "
        "or grounded."
    ),
    "ADV_E": (
        "I can predict where it will fail. I know which task types produce plausible but "
        "wrong outputs, and I use this to decide when AI is and isn't the right tool."
    ),
}

COMPETENCY_C2 = {
    "MISSING": "I haven't really thought about where it could help me.",
    "PARTIAL": ("I can see it's useful generally, but haven't pinned down where it fits my work."),
    "HAVE": (
        "I've identified specific recurring tasks of mine where it genuinely helps, and use them."
    ),
    "ADV_D": (
        "I spot the less obvious uses, where AI can help in ways most people wouldn't think to try."
    ),
    "ADV_E": (
        "I actively redesign workflows around AI's capabilities, not just applying it to "
        "existing tasks but restructuring how work gets done to make the most of what it "
        "can do."
    ),
}

COMPETENCY_C3 = {
    "MISSING": "Give up and decide it can't do that.",
    "PARTIAL": "Try again, maybe reword it slightly.",
    "HAVE": "Add context or examples, or break it into steps, and iterate until it works.",
    "ADV_D": (
        "I work out why it went wrong, whether it was too vague, missing context, or too "
        "big an ask, and fix that specific thing."
    ),
    "ADV_E": (
        "I work systematically using structured approaches like chain of thought, role "
        "framing, or reusable prompt templates, and I help others get better results, not "
        "just solve my own problems."
    ),
}

COMPETENCY_C4 = {
    "MISSING": "Use it pretty much as is, it reads well.",
    "PARTIAL": "Skim for anything that jumps out as wrong, then use it.",
    "HAVE": (
        "Check the key figures and whether the picture looks balanced, using what I "
        "already know, before using it."
    ),
    "ADV_D": (
        "Verify the claims against an independent source, and look for slants or gaps "
        "that aren't obvious from the text."
    ),
    "ADV_E": (
        "I've built verification into my process. I know which claim types need what "
        "evidence and apply systematic checks rather than treating each output as a "
        "standalone review."
    ),
}

COMPETENCY_C5 = {
    "PUBLIC_PASTE": (
        "Put internal documents or client/customer info into a public tool "
        "(free ChatGPT, Gemini, etc.)"
    ),
    "APPROVED_PASTE": "Put internal documents or client information into a company approved tool",
    "UNSURE": "Wasn't sure whether a tool was approved for that kind of data",
    "KEPT_OUT": "Mostly kept work information out of public tools",
    "NO_USE": "Haven't really used AI for work",
}

COMPETENCY_C6 = {
    "MISSING": "A clear, confident answer with a source is reliable.",
    "PARTIAL": "It can be wrong sometimes, but a source it gives makes it trustworthy.",
    "HAVE": (
        "It can be confidently wrong and can even invent sources that look real, so "
        "neither confidence nor a citation is proof."
    ),
    "ADV_D": (
        "The confident and well sourced answers are the ones I'm least likely to "
        "question, so I scrutinise those hardest."
    ),
    "ADV_E": (
        "I calibrate scrutiny by domain and task type. I know where AI is most unreliable "
        "and apply proportionate verification rather than blanket suspicion, and I help "
        "others develop the same judgement."
    ),
}


class Competency(NamedTuple):
    """One row of the frontend's COMPETENCY_QA."""

    key: str
    label: str
    question: str
    options: dict[str, str]
    multi: bool = False


COMPETENCIES: tuple[Competency, ...] = (
    Competency(
        "c1",
        "Understanding",
        "When a tool like ChatGPT gives you an answer, which is closest to how you'd "
        "describe what it's actually doing?",
        COMPETENCY_C1,
    ),
    Competency(
        "c2",
        "Use case spotting",
        "Thinking about your everyday work, how far have you got with AI?",
        COMPETENCY_C2,
    ),
    Competency(
        "c3",
        "Prompting",
        "When an AI tool gives you a poor or unhelpful answer, what do you usually do?",
        COMPETENCY_C3,
    ),
    Competency(
        "c4",
        "Critical evaluation",
        "You ask an AI tool to draft a market summary for a client. It comes back confident, "
        "polished, with specific figures and a competitor comparison. What do you actually "
        "do with it?",
        COMPETENCY_C4,
    ),
    Competency(
        "c5",
        "Responsible use",
        "In the past month or so, which of these have you done with an AI tool?",
        COMPETENCY_C5,
        multi=True,
    ),
    Competency(
        "c6",
        "Trust calibration",
        "Thinking about how AI assistants actually work, which is closest to your view?",
        COMPETENCY_C6,
    ),
)
