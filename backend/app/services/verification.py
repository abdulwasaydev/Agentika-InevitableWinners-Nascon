"""Claim-level pipeline shared by the worker and deterministic tests."""

from dataclasses import dataclass

from ..providers.live import ProviderFailure, live_assess, live_retrieve
from .assessment import AssessmentDraft, challenge_assess, support_assess
from .evidence_validation import validate_assessment, validate_evidence
from .extraction import ExtractedClaim
from .policy import Finding, evaluate_claim
from .retrieval import EvidenceCandidate, seeded_retrieve


@dataclass
class ClaimVerification:
    evidence: list[EvidenceCandidate]
    support: AssessmentDraft
    challenge: AssessmentDraft
    finding: Finding


def verify_one_claim(item: ExtractedClaim, *, use_demo: bool, unresolved_parent: bool = False,
                     document_mode: bool = False) -> ClaimVerification:
    provider_error = False
    if item.checkability == "not_checkable" or document_mode:
        candidates = []
    else:
        try:
            candidates = seeded_retrieve(item.text) if use_demo else live_retrieve(item.text)
        except ProviderFailure:
            candidates = []
            provider_error = True

    evidence_invalid = not all([validate_evidence(e) for e in candidates])
    if use_demo or not candidates or document_mode:
        support = support_assess(item.text, candidates)
        challenge = challenge_assess(item.text, candidates)
    else:
        try:
            support = live_assess("support", item.text, candidates)
            challenge = live_assess("challenge", item.text, candidates)
        except ProviderFailure:
            support = support_assess(item.text, [])
            challenge = challenge_assess(item.text, [])
            provider_error = True

    support_valid = validate_assessment(support, candidates)
    challenge_valid = validate_assessment(challenge, candidates)
    finding = evaluate_claim(
        checkability=item.checkability,
        support=support.position == "supports" and support_valid,
        challenge=challenge.position == "challenges" and challenge_valid,
        evidence_invalid=evidence_invalid,
        assessment_invalid=not (support_valid and challenge_valid),
        provider_error=provider_error,
        high_risk=item.high_risk,
        unresolved_parent=unresolved_parent,
        synthetic=use_demo,
        weak_source=bool(candidates) and all(e.source_type == "web_search_snippet" for e in candidates),
    )
    return ClaimVerification(candidates, support, challenge, finding)
