"""Validate source provenance and every assessment citation before policy use."""

from .assessment import AssessmentDraft
from .retrieval import EvidenceCandidate


def validate_evidence(item: EvidenceCandidate) -> bool:
    valid = bool(
        (item.url or item.document_id)
        and item.excerpt.strip()
        and item.source_text.strip()
        and item.excerpt in item.source_text
        and item.stance in {"support", "challenge", "context"}
    )
    item.validity_status = "valid" if valid else "invalid"
    return valid


def validate_assessment(draft: AssessmentDraft, evidence: list[EvidenceCandidate]) -> bool:
    by_id = {item.id: item for item in evidence}
    for citation in draft.citations:
        item = by_id.get(citation.evidence_id)
        if item is None or item.validity_status != "valid" or not citation.quote.strip() or citation.quote not in item.source_text:
            return False
        if draft.role == "support" and item.stance not in {"support", "context"}:
            return False
        if draft.role == "challenge" and item.stance not in {"challenge", "context"}:
            return False
    if draft.position in {"supports", "challenges"} and not draft.citations:
        return False
    return True
