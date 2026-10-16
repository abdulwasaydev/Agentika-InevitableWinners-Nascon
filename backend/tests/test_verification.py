from uuid import uuid4

import pytest

from app.providers.live import ProviderFailure
from app.schemas import ClaimStatus, ReleaseAction, ReviewDecision
from app.services.assessment import AssessmentDraft, Citation
from app.services.evidence_validation import validate_assessment, validate_evidence
from app.services.extraction import ClaimLimitExceeded, extract_claims
from app.services.policy import PolicyClaim, apply_review, release_action
from app.services.retrieval import seeded_retrieve
from app.services.verification import verify_one_claim


def check(text: str, *, demo: bool = True):
    return verify_one_claim(extract_claims(text)[0], use_demo=demo)


def test_seeded_pipeline_support_and_challenge():
    supported = check("The fictional Aster Archive opened in 2020.")
    disputed = check("The fictional Aster Archive opened in 2018.")
    assert supported.finding.provisional_status == ClaimStatus.supported
    assert supported.evidence[0].validity_status == "valid"
    assert supported.support.citations[0].evidence_id == supported.evidence[0].id
    assert disputed.finding.provisional_status == ClaimStatus.disputed
    assert disputed.challenge.citations[0].evidence_id == disputed.evidence[0].id
    assert release_action("strict", [PolicyClaim(supported.finding.effective_status)]) == ReleaseAction.pass_
    assert release_action("strict", [PolicyClaim(disputed.finding.effective_status)]) == ReleaseAction.hold_for_review


def test_unknown_and_opinion_are_distinct():
    unknown = check("The fictional Aster Archive has 900 rooms.")
    opinion = check("I think the fictional Aster Archive is beautiful.")
    assert unknown.finding.provisional_status == ClaimStatus.insufficient_evidence
    assert unknown.finding.needs_review
    assert opinion.finding.effective_status == ClaimStatus.not_checkable
    assert release_action("strict", [PolicyClaim(opinion.finding.effective_status)]) == ReleaseAction.pass_


def test_invalid_source_and_citation_cannot_support():
    evidence = seeded_retrieve("The fictional Aster Archive opened in 2020.")
    evidence[0].excerpt = "Invented excerpt absent from source"
    assert not validate_evidence(evidence[0])
    invalid_id = AssessmentDraft("support", "supports", "Untrusted", [Citation(uuid4(), "Invented")])
    assert not validate_assessment(invalid_id, evidence)
    invalid_quote = AssessmentDraft("support", "supports", "Untrusted", [Citation(evidence[0].id, "Invented")])
    assert not validate_assessment(invalid_quote, evidence)


def test_provider_failure_fails_closed(monkeypatch):
    def fail(_text):
        raise ProviderFailure("provider unavailable")

    monkeypatch.setattr("app.services.verification.live_retrieve", fail)
    result = check("A test claim happened in 2020.", demo=False)
    assert result.finding.provisional_status == ClaimStatus.insufficient_evidence
    assert "PROVIDER_ERROR" in result.finding.reason_codes
    assert release_action("strict", [PolicyClaim(result.finding.effective_status)]) == ReleaseAction.hold_for_review


def test_review_does_not_upgrade_unsupported_claim():
    for decision in (ReviewDecision.approve, ReviewDecision.dispute, ReviewDecision.insufficient, ReviewDecision.correct):
        effective, needs_review = apply_review(ClaimStatus.insufficient_evidence, decision)
        assert effective != ClaimStatus.supported
        assert release_action("strict", [PolicyClaim(effective)]) == ReleaseAction.hold_for_review
    effective, needs_review = apply_review(ClaimStatus.supported, ReviewDecision.request_more_evidence)
    assert effective == ClaimStatus.pending_review and needs_review


def test_high_risk_and_lineage_hold():
    item = extract_claims("The fictional Aster Archive opened in 2020.")[0]
    result = verify_one_claim(item, use_demo=True, unresolved_parent=True)
    assert result.finding.provisional_status == ClaimStatus.supported
    assert result.finding.effective_status == ClaimStatus.pending_review
    assert "UNRESOLVED_PARENT" in result.finding.reason_codes
    assert release_action("strict", [PolicyClaim(result.finding.effective_status)]) == ReleaseAction.hold_for_review
    risky = check("The medicine prevents every disease.")
    assert risky.finding.effective_status == ClaimStatus.pending_review
    assert "HIGH_RISK_REVIEW" in risky.finding.reason_codes
    assert extract_claims("The best medicine prevents every disease.")[0].checkability == "checkable"
    assert extract_claims("I think the archive opened in 2020.")[0].checkability == "checkable"


def test_extraction_is_bounded_and_has_offsets():
    text = "The fictional Aster Archive opened in 2020. It has 12 rooms."
    claims = extract_claims(text)
    assert [text[c.start_offset:c.end_offset] for c in claims] == [c.text for c in claims]
    with pytest.raises(ClaimLimitExceeded):
        extract_claims("A. B. C. D. E. F.", max_claims=5)


def test_balanced_annotates_ordinary_uncertainty_but_holds_high_risk():
    uncertain = PolicyClaim(ClaimStatus.insufficient_evidence)
    assert release_action("balanced", [uncertain]) == ReleaseAction.annotate
    assert release_action("balanced", [PolicyClaim(ClaimStatus.insufficient_evidence, high_risk=True)]) == ReleaseAction.hold_for_review
