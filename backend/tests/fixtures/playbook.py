"""One complete, fictional playbook extraction for the tagged-document tests (#149). Two use
cases and two next moves, so the derived fields (rank, start_here, order) are exercised."""

from __future__ import annotations

from typing import Any

__all__ = ["EXTRACTION"]

EXTRACTION: dict[str, Any] = {
    "internal": {
        "input_quality": {
            "tier": "RICH",
            "evidence": "Gave concrete examples with time estimates.",
            "what_to_probe_next": ["Who owns the approval step?", "How often does it slip?"],
        },
        "person": {
            "role_reality": "Ops lead who runs the weekly reconciliation.",
            "influence": "Can pilot changes within the team.",
            "decision_rights": "No budget authority.",
            "champion_potential": "High, already shares small automations.",
            "confidence": "high",
        },
        "pains": [
            {
                "pain": "Manual reconciliation of vendor invoices.",
                "evidence": 'Said "I re-key the same numbers every Friday".',
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
                    "reasoning": "Mentioned sign-off from finance twice.",
                    "basis": "Unprompted, twice.",
                    "confidence": "medium",
                }
            ],
        },
        "maturity": {
            "placement": "Practitioner",
            "behavioural_evidence": "Uses templated prompts for email drafts.",
            "vs_self_reported": "Self-reported beginner, behaves higher.",
            "trajectory": "Towards Integrator within two quarters.",
        },
        "systems_landscape": [
            {
                "system": "SAP",
                "how_used": "Source of vendor invoice data.",
                "implication": "Automation needs read access to SAP exports.",
            }
        ],
        "company_context": "Mid-size manufacturer, finance shared services.",
        "engagement_notes": {
            "opportunities": ["Quick win on invoice reconciliation."],
            "risks": ["Limited budget could stall bigger builds."],
            "follow_up_questions": ["What is the current approval SLA?"],
        },
    },
    "shared": {
        "where_you_are_today": (
            "You already draft emails with AI and know where it helps.\n"
            "- You keep a clear weekly rhythm.\n"
            "- You know exactly which numbers matter."
        ),
        "use_cases": [
            {
                "rank": 1,
                "start_here": True,
                "name": "Match invoices to the SAP export",
                "pain_it_kills": "Re-keying vendor invoices every Friday.",
                "in_practice": "Feed the export and the invoices to an AI matcher.",
                "before": "3 hours of matching.",
                "after": "20 minutes reviewing exceptions.",
                "impact": "Most of a Friday back.",
                "difficulty": "Quick Win",
                "systems_involved": ["SAP", "Excel"],
                "assumption_to_check": "The export format stays the same each week.",
                "cross_functional": False,
            },
            {
                "rank": 2,
                "start_here": False,
                "name": "Draft the monthly close summary",
                "pain_it_kills": "Writing the same commentary each month.",
                "in_practice": "Let AI draft from last month's notes.",
                "before": "Half a day of writing.",
                "after": "An hour of editing.",
                "impact": "Faster close reporting.",
                "difficulty": "Worth a Session",
                "systems_involved": [],
                "assumption_to_check": None,
                "cross_functional": True,
            },
        ],
        "next_moves": [
            {
                "order": 1,
                "move": "Pilot the matcher on one vendor.",
                "why_now": "Low risk, fast feedback.",
                "linked_use_case": 1,
            },
            {
                "order": 2,
                "move": "Show the controller the close draft.",
                "why_now": "Brings a colleague in early.",
                "linked_use_case": 2,
            },
        ],
        "reframes": [
            {
                "their_hesitation": "Worried AI makes mistakes finance won't catch.",
                "the_concern": "Trust in automated output.",
                "reframe": "Start with AI-assisted review, not full automation.",
                "first_proof": "Run it next to the manual process for two weeks.",
            }
        ],
        "do_this_today": {
            "action": "List every field you re-key from the invoice export.",
            "time_required": "15 minutes",
            "why_this_one": "Gives the pilot a concrete checklist.",
        },
    },
}
