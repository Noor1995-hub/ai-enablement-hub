from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

__all__ = [
    "Blockers",
    "DiagnosedBlocker",
    "DoThisToday",
    "EngagementNotes",
    "InputQuality",
    "Maturity",
    "NextMove",
    "Pain",
    "Person",
    "PlaybookExtraction",
    "PlaybookInternal",
    "PlaybookShared",
    "Reframe",
    "SystemEntry",
    "UseCase",
]

Difficulty = Literal["Quick Win", "Worth a Session", "Bigger Build"]


# --- shared (learner-facing playbook) ---------------------------------------


class UseCase(BaseModel):
    rank: int
    start_here: bool
    name: str
    pain_it_kills: str
    in_practice: str
    before: str
    after: str
    impact: str
    difficulty: Difficulty
    systems_involved: list[str]
    assumption_to_check: str | None
    cross_functional: bool


class NextMove(BaseModel):
    order: int
    move: str
    why_now: str
    linked_use_case: int


class Reframe(BaseModel):
    their_hesitation: str
    the_concern: str
    reframe: str
    first_proof: str


class DoThisToday(BaseModel):
    action: str
    time_required: str
    why_this_one: str


class PlaybookShared(BaseModel):
    where_you_are_today: str
    use_cases: list[UseCase]
    next_moves: list[NextMove]
    reframes: list[Reframe]
    do_this_today: DoThisToday


# --- internal (delaware-only analysis) --------------------------------------


class InputQuality(BaseModel):
    tier: Literal["RICH", "PARTIAL", "THIN"]
    evidence: str
    what_to_probe_next: list[str]


class Person(BaseModel):
    role_reality: str
    influence: str
    decision_rights: str
    champion_potential: str
    confidence: str


class Pain(BaseModel):
    pain: str
    evidence: str
    frequency: str
    est_time_cost: str
    basis: Literal["stated", "inferred"]
    confidence: str


class DiagnosedBlocker(BaseModel):
    type: str
    reasoning: str
    basis: str
    confidence: str


class Blockers(BaseModel):
    stated: list[str]
    diagnosed: list[DiagnosedBlocker]


class Maturity(BaseModel):
    placement: str
    behavioural_evidence: str
    vs_self_reported: str
    trajectory: str


class SystemEntry(BaseModel):
    system: str
    how_used: str
    implication: str


class EngagementNotes(BaseModel):
    opportunities: list[str]
    risks: list[str]
    follow_up_questions: list[str]


class PlaybookInternal(BaseModel):
    input_quality: InputQuality
    person: Person
    pains: list[Pain]
    blockers: Blockers
    maturity: Maturity
    systems_landscape: list[SystemEntry]
    company_context: str
    engagement_notes: EngagementNotes


class PlaybookExtraction(BaseModel):
    internal: PlaybookInternal
    shared: PlaybookShared
