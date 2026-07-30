from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.db.models import User
    from src.services.learning_service import LearningService
    from src.services.maturity_service import MaturityService
    from src.services.survey_service import SurveyService

__all__ = ["InterviewContextService"]

# ── Code → human-label maps, ported from frontend/src/lib/surveyOptions.ts
# (source of truth — keep in sync with it). ──────────────────────────────────

FREQ = {
    "NEVER": "Never",
    "MONTHLY": "A few times a month",
    "WEEKLY": "Most weeks",
    "DAILY": "Most days",
    "INTENSIVE": "Every day",
}

TOOLS = {
    "CHATGPT": "ChatGPT",
    "COPILOT": "Microsoft Copilot",
    "CLAUDE": "Claude",
    "GEMINI": "Gemini",
    "OTHER": "Other (incl. tools built into software you use)",
    "NONE_YET": "None yet",
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


def _labels(codes: list[str] | None, mapping: dict[str, str]) -> str:
    """Comma-joined human labels for a list of codes; falls back to the raw
    code if unmapped, "—" if empty/None."""
    if not codes:
        return "—"
    return ", ".join(mapping.get(code, code) for code in codes)


def _label(code: str | None, mapping: dict[str, str]) -> str:
    """Human label for a single code; falls back to the raw code if
    unmapped, "—" if empty/None."""
    if not code:
        return "—"
    return mapping.get(code, code)


class InterviewContextService:
    """Composes a caller's completed assessment + effective maturity +
    learning status into interview-facing text. Strictly token-scoped:
    everything derives from the `User` passed in, never a request-supplied
    user_id."""

    def __init__(
        self,
        surveys: SurveyService,
        maturity: MaturityService,
        learning: LearningService,
    ) -> None:
        self._surveys = surveys
        self._maturity = maturity
        self._learning = learning

    async def build_briefing(self, user: User) -> str:
        """The 'What you already know' block appended to the interview
        system prompt."""
        survey = await self._surveys.get_own(user.id)
        level = await self._maturity.effective_level(user)
        learning = await self._learning.learning_status(user.id)
        name = f"{user.first_name} {user.last_name}"
        header = (
            "## What you already know about the person (from their assessment — a "
            "briefing, not the truth; never make them repeat it)"
        )

        if survey is None:
            return (
                f"{header}\n"
                f"- Name: {name}\n"
                "- No completed assessment on file; explore their role and work from scratch."
            )

        return (
            f"{header}\n"
            f"- Name: {name}\n"
            f"- Role / function: {survey.job_title or '—'}, in {survey.department or '—'}\n"
            f"- Self-reported AI maturity: {level or '—'} — uses AI {_label(survey.b_freq, FREQ)}\n"
            f"- Tools they report using: {_labels(survey.b_tools, TOOLS)}\n"
            f"- Things they've set up: {_labels(survey.b_setup, SETUP)}\n"
            f"- Barriers they reported: {_labels(survey.b_barriers, BARRIERS)}\n"
            f'- In their words — biggest time-sink: "{survey.q_timesink or "—"}"; '
            f'most excited about: "{survey.q_excitement or "—"}"\n'
            f"- Learning-path progress: {learning}"
        )

    async def build_assessment_context(self, user: User) -> str:
        """A fuller structured dump of the assessment for the wrap-up
        generation prompt (destined for an `<assessment_record>` block)."""
        survey = await self._surveys.get_own(user.id)
        level = await self._maturity.effective_level(user)
        learning = await self._learning.learning_status(user.id)
        name = f"{user.first_name} {user.last_name}"

        if survey is None:
            return (
                f"Name: {name}\n"
                f"Effective maturity: {level or '—'}\n"
                "No completed assessment on file.\n"
                f"Learning-path progress: {learning}"
            )

        lines = [
            f"Name: {name}",
            f"Role / function: {survey.job_title or '—'}, in {survey.department or '—'}",
            f"Effective maturity: {level or '—'}",
            f"Scored level: {survey.score_level or '—'}",
            f"Usage band: {survey.usage_band or '—'}",
            f"Frequency of AI use: {_label(survey.b_freq, FREQ)}",
            f"Tools used: {_labels(survey.b_tools, TOOLS)}",
            f"Setups in place: {_labels(survey.b_setup, SETUP)}",
            f"Barriers reported: {_labels(survey.b_barriers, BARRIERS)}",
            f'Biggest time-sink: "{survey.q_timesink or "—"}"',
            f'Most excited about: "{survey.q_excitement or "—"}"',
            f"Understanding of how AI works (C1): {_label(survey.c1_code, COMPETENCY_C1)}",
            f"Use-case spotting (C2): {_label(survey.c2_code, COMPETENCY_C2)}",
            f"Prompting approach (C3): {_label(survey.c3_code, COMPETENCY_C3)}",
            f"Critical evaluation (C4): {_label(survey.c4_code, COMPETENCY_C4)}",
            f"Responsible use (C5): {_labels(survey.c5_codes, COMPETENCY_C5)}",
            f"Trust calibration (C6): {_label(survey.c6_code, COMPETENCY_C6)}",
            f"Learning-path progress: {learning}",
        ]
        return "\n".join(lines)
