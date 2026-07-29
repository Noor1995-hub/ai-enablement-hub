from __future__ import annotations

import json

from src.schemas.interview import PlaybookExtraction
from src.services.interview_schema import PLAYBOOK_SCHEMA


def test_schema_top_level_is_two_boxes() -> None:
    properties = PLAYBOOK_SCHEMA.input_schema["properties"]
    assert set(properties.keys()) == {"internal", "shared"}


def test_difficulty_enum_labels() -> None:
    schema_text = json.dumps(PLAYBOOK_SCHEMA.input_schema)
    for label in ("Quick Win", "Worth a Session", "Bigger Build"):
        assert label in schema_text


def test_extraction_roundtrips() -> None:
    payload = {
        "internal": {
            "input_quality": {
                "tier": "RICH",
                "evidence": "Gave concrete examples with time estimates.",
                "what_to_probe_next": ["Who owns the approval step?"],
            },
            "person": {
                "role_reality": "Ops lead who runs the weekly reconciliation.",
                "influence": "Can pilot changes within their team.",
                "decision_rights": "No budget authority.",
                "champion_potential": "High — already evangelizes small automations.",
                "confidence": "high",
            },
            "pains": [
                {
                    "pain": "Manual reconciliation of vendor invoices.",
                    "evidence": "Described re-keying data every Friday.",
                    "frequency": "weekly",
                    "est_time_cost": "3 hours/week",
                    "basis": "stated",
                    "confidence": "high",
                }
            ],
            "blockers": {
                "stated": ["No IT budget this quarter."],
                "diagnosed": [
                    {
                        "type": "governance",
                        "reasoning": "Repeated references to needing sign-off from finance.",
                        "basis": "Mentioned finance twice unprompted.",
                        "confidence": "medium",
                    }
                ],
            },
            "maturity": {
                "placement": "Practitioner",
                "behavioural_evidence": "Already uses templated prompts for email drafts.",
                "vs_self_reported": "Self-reported as beginner but behaviour suggests higher.",
                "trajectory": "Trending toward Integrator within two quarters.",
            },
            "systems_landscape": [
                {
                    "system": "SAP",
                    "how_used": "Source of vendor invoice data.",
                    "implication": "Any automation needs read access to SAP exports.",
                }
            ],
            "company_context": "Mid-size manufacturer, finance shared services team.",
            "engagement_notes": {
                "opportunities": ["Quick win on invoice reconciliation."],
                "risks": ["Limited budget could stall bigger builds."],
                "follow_up_questions": ["What's the current approval SLA?"],
            },
        },
        "shared": {
            "where_you_are_today": "You're already comfortable with basic AI-assisted drafting.",
            "use_cases": [
                {
                    "rank": 1,
                    "start_here": True,
                    "name": "Automate invoice reconciliation",
                    "pain_it_kills": "Manual re-keying of vendor invoices every week.",
                    "in_practice": "Feed the export into an AI-assisted matcher.",
                    "before": "3 hours of manual matching every Friday.",
                    "after": "20 minutes reviewing exceptions.",
                    "impact": "Frees up most of a workday each week.",
                    "difficulty": "Quick Win",
                    "systems_involved": ["SAP"],
                    "assumption_to_check": "Confirm export format is consistent week to week.",
                    "cross_functional": False,
                }
            ],
            "next_moves": [
                {
                    "order": 1,
                    "move": "Pilot the reconciliation matcher on one vendor.",
                    "why_now": "Low risk, fast feedback loop.",
                    "linked_use_case": 1,
                }
            ],
            "reframes": [
                {
                    "their_hesitation": "Worried AI will make mistakes finance won't catch.",
                    "the_concern": "Trust in automated output.",
                    "reframe": "Start with AI-assisted review, not full automation.",
                    "first_proof": "Run it alongside the manual process for two weeks.",
                }
            ],
            "do_this_today": {
                "action": "List every field you re-key from the vendor invoice export.",
                "time_required": "15 minutes",
                "why_this_one": "Gives the pilot a concrete starting checklist.",
            },
        },
    }

    extraction = PlaybookExtraction.model_validate(payload)

    assert extraction.shared.use_cases[0].difficulty == "Quick Win"
    assert extraction.internal.input_quality.tier == "RICH"
