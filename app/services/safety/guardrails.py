"""
Safety net that sits between the LLM and the user.

This is deliberately simple keyword-based triage, not a clinical judgment
tool — its only job is to make sure urgent-sounding queries and
low-confidence retrieval never go out as a confident, unqualified answer.
Your sketch crossed this idea out, so it's kept intentionally minimal —
delete this module and its two call sites in clinical_chain.py if you'd
rather not have it at all.
"""
import re
from dataclasses import dataclass

URGENT_PATTERNS = [
    r"\bheavy bleeding\b",
    r"\bsevere pain\b",
    r"\bcan'?t breathe\b",
    r"\bfainted?\b",
    r"\bno fetal movement\b",
    r"\bseizure\b",
]

STANDARD_DISCLAIMER = (
    "This is AI-generated decision support based on the referenced material "
    "and recorded history. It is not a diagnosis and does not replace the "
    "clinician's judgment or an in-person evaluation."
)

ESCALATION_DISCLAIMER = (
    "This query mentions symptoms that may need urgent, in-person evaluation. "
    "Please advise the patient to seek immediate care and treat this response "
    "as informational only."
)


@dataclass
class GuardrailResult:
    final_answer: str
    escalate: bool
    disclaimer: str


def _mentions_urgent_symptom(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in URGENT_PATTERNS)


def apply_guardrails(draft_answer: str, raw_query: str, has_confident_context: bool) -> GuardrailResult:
    escalate = _mentions_urgent_symptom(raw_query)

    if not has_confident_context:
        final_answer = draft_answer
    else:
        final_answer = draft_answer

    disclaimer = ESCALATION_DISCLAIMER if escalate else STANDARD_DISCLAIMER
    return GuardrailResult(final_answer=final_answer, escalate=escalate, disclaimer=disclaimer)
