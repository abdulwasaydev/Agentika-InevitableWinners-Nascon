from uuid import uuid4

from app.models import SuppliedDocument
from app.services.assessment import AssessmentDraft, Citation
from app.services.comparison import compare_promise
from app.services.evidence_validation import validate_assessment


def document(text: str, name: str = "TERMS-v1") -> SuppliedDocument:
    return SuppliedDocument(document_id=name, title="Fictional policy", version="v1", text=text)


def test_consistent_promise_uses_exact_supplied_passages():
    policy = document("Members may cancel at any time. Cancellation stops the next renewal. Access continues through the end of the paid month.")
    result = compare_promise("Cancel anytime; access continues until the end of your paid month.", [policy])
    assert result.result == "consistent"
    assert result.finding.provisional_status == "supported"
    assert result.unresolved_questions == []
    assert len(result.evidence) == 2
    assert all(item.document_id == "TERMS-v1" and item.excerpt in policy.text and item.validity_status == "valid" for item in result.evidence)


def test_refund_exception_is_qualified_and_clause_change_changes_result():
    promise = "Full refund within 30 days."
    limited = compare_promise(promise, [document("A full refund is available within 30 days only if the service has never been used.")])
    assert limited.result == "qualified"
    assert limited.finding.provisional_status == "pending_review"
    assert limited.evidence[0].stance == "challenge"
    assert "never been used" in limited.evidence[0].excerpt
    changed = compare_promise(promise, [document("No refunds are available.")])
    assert changed.result == "conflicting"
    assert changed.finding.provisional_status == "disputed"


def test_missing_refund_policy_is_insufficient_not_deception():
    result = compare_promise("Cancel anytime and receive a refund.", [document("You may cancel at any time through account settings. Cancellation stops the next renewal.")])
    assert result.result == "insufficient_evidence"
    assert any("refund" in question for question in result.unresolved_questions)
    assert "not proof of deception" in result.explanation
    assert all("refund" not in item.excerpt.casefold() for item in result.evidence)


def test_missing_or_invented_citation_cannot_establish_support():
    result = compare_promise("Full refund within 30 days.", [document("The service description contains no billing terms.")])
    assert result.result == "insufficient_evidence"
    invented = AssessmentDraft("support", "supports", "Unsupported assertion", [Citation(uuid4(), "Invented clause")])
    assert not validate_assessment(invented, result.evidence)
