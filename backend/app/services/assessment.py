"""Independent support and challenge role assessments for seeded mode."""

from dataclasses import dataclass
from uuid import UUID

from .retrieval import EvidenceCandidate


@dataclass(frozen=True)
class Citation:
    evidence_id: UUID
    quote: str


@dataclass(frozen=True)
class AssessmentDraft:
    role: str
    position: str
    reasoning_summary: str
    citations: list[Citation]
    limitations: str | None = None


def support_assess(claim_text: str, evidence: list[EvidenceCandidate]) -> AssessmentDraft:
    sources = [item for item in evidence if item.stance == "support"]
    if not sources:
        return AssessmentDraft("support", "no_support", "No supporting source passage was retrieved.", [], "Seeded corpus has limited coverage.")
    return AssessmentDraft("support", "supports", "The cited source passage states the claim.", [Citation(e.id, e.excerpt) for e in sources])


def challenge_assess(claim_text: str, evidence: list[EvidenceCandidate]) -> AssessmentDraft:
    sources = [item for item in evidence if item.stance == "challenge"]
    if not sources:
        return AssessmentDraft("challenge", "no_challenge", "No contradictory source passage was retrieved.", [], "Absence of challenge is not proof.")
    return AssessmentDraft("challenge", "challenges", "The cited source passage gives a conflicting value.", [Citation(e.id, e.excerpt) for e in sources])
