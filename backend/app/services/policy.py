"""Deterministic claim findings and Guardian release decisions."""

from dataclasses import dataclass

from ..schemas import ClaimStatus, ReleaseAction, ReviewDecision


@dataclass(frozen=True)
class Finding:
    provisional_status: ClaimStatus
    effective_status: ClaimStatus
    needs_review: bool
    reason_codes: list[str]


@dataclass(frozen=True)
class PolicyClaim:
    effective_status: ClaimStatus
    material: bool = True
    high_risk: bool = False


def evaluate_claim(*, checkability: str, support: bool, challenge: bool, evidence_invalid: bool = False,
                   assessment_invalid: bool = False, provider_error: bool = False, high_risk: bool = False,
                   unresolved_parent: bool = False, synthetic: bool = False,
                   weak_source: bool = False) -> Finding:
    if checkability == "not_checkable":
        return Finding(ClaimStatus.not_checkable, ClaimStatus.not_checkable, False, ["NOT_CHECKABLE"])
    if provider_error:
        provisional, reasons = ClaimStatus.insufficient_evidence, ["PROVIDER_ERROR"]
    elif evidence_invalid or assessment_invalid:
        provisional, reasons = ClaimStatus.insufficient_evidence, ["INVALID_CITATION"]
    elif weak_source:
        provisional, reasons = ClaimStatus.insufficient_evidence, ["WEB_SNIPPET_UNVERIFIED"]
    elif challenge:
        provisional, reasons = ClaimStatus.disputed, ["CONTRADICTORY_EVIDENCE"]
    elif support:
        provisional, reasons = ClaimStatus.supported, ["SEEDED_DOCUMENT_SUPPORT" if synthetic else "TRACEABLE_SUPPORT"]
    else:
        provisional, reasons = ClaimStatus.insufficient_evidence, ["NO_VALID_SUPPORT"]
    if unresolved_parent:
        reasons.append("UNRESOLVED_PARENT")
    if high_risk:
        reasons.append("HIGH_RISK_REVIEW")
    needs_review = provisional != ClaimStatus.supported or high_risk or unresolved_parent
    effective = ClaimStatus.pending_review if (high_risk or unresolved_parent) else provisional
    return Finding(provisional, effective, needs_review, reasons)


def apply_review(provisional: ClaimStatus, decision: ReviewDecision) -> tuple[ClaimStatus, bool]:
    if decision == ReviewDecision.approve:
        # Review is provenance, not independent proof; approval cannot upgrade an unsupported finding.
        return provisional, provisional == ClaimStatus.pending_review
    if decision == ReviewDecision.dispute or decision == ReviewDecision.correct:
        return ClaimStatus.disputed, False
    if decision == ReviewDecision.insufficient:
        return ClaimStatus.insufficient_evidence, False
    return ClaimStatus.pending_review, True


def release_action(policy: str, claims: list[PolicyClaim]) -> ReleaseAction:
    material = [c for c in claims if c.material and c.effective_status != ClaimStatus.not_checkable]
    if not material:
        return ReleaseAction.pass_
    if all(c.effective_status == ClaimStatus.supported for c in material):
        return ReleaseAction.pass_
    if policy == "strict" or any(c.high_risk for c in material):
        return ReleaseAction.hold_for_review
    return ReleaseAction.annotate
