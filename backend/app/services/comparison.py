"""Conservative, deterministic comparison against user-supplied policy passages.

This bounded adapter is a demo aid, not model inference or a legal conclusion.
It only cites exact substrings of the supplied documents and fails closed when
its narrow phrasing rules cannot establish a promised component.
"""

import re
from dataclasses import dataclass
from uuid import uuid4

from ..models import SuppliedDocument
from ..schemas import ClaimStatus
from .assessment import AssessmentDraft, Citation
from .evidence_validation import validate_assessment, validate_evidence
from .policy import Finding
from .retrieval import EvidenceCandidate


@dataclass(frozen=True)
class Comparison:
    result: str
    explanation: str
    unresolved_questions: list[str]
    evidence: list[EvidenceCandidate]
    support: AssessmentDraft
    challenge: AssessmentDraft
    finding: Finding


def _clauses(text: str) -> list[str]:
    return [match.group().strip() for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", text) if match.group().strip()]


def _topics(text: str) -> set[str]:
    lowered = text.casefold()
    return {topic for topic, pattern in {
        "cancellation": r"\bcancel(?:lation)?\b",
        "access": r"\baccess\b",
        "refund": r"\brefunds?\b",
    }.items() if re.search(pattern, lowered)}


def _supports(topic: str, promise: str, clause: str) -> bool:
    c = clause.casefold()
    p = promise.casefold()
    if topic == "cancellation":
        return bool(re.search(r"\bcancel(?:lation)?\b", c)) and (
            not re.search(r"\bany\s*time\b|\banytime\b", p)
            or bool(re.search(r"\bany\s*time\b|\banytime\b", c))
        )
    if topic == "access":
        return "access" in c and bool(re.search(r"\b(?:through|until|continues|remains)\b", c)) and bool(
            re.search(r"\b(?:paid month|paid period|billing period|current period)\b", c)
        )
    if topic == "refund":
        if not re.search(r"\brefunds?\b", c):
            return False
        if re.search(r"\bfull refund\b", p) and not re.search(r"\bfull refund\b", c):
            return False
        if re.search(r"\b30\s*days\b|\bthirty\s*days\b", p) and not re.search(r"\b30\s*days\b|\bthirty\s*days\b", c):
            return False
        return True
    return False


def _conflicts(topic: str, promise: str, clause: str) -> bool:
    c = clause.casefold()
    p = promise.casefold()
    if topic == "cancellation":
        return bool(re.search(r"\b(?:cannot cancel|no cancellations|cancellation is not permitted)\b", c))
    if topic == "access":
        return "access" in c and bool(re.search(r"\b(?:ends immediately|stops immediately|ends upon cancellation)\b", c))
    if topic == "refund":
        if re.search(r"\b(?:no refunds?|non.refundable|refunds? (?:are )?not available)\b", c):
            return True
        if "full refund" in p and "partial refund" in c:
            return True
        if re.search(r"\b30\s*days\b", p) and re.search(r"\b(?:7|14)\s*days\b", c) and "refund" in c:
            return True
    return False


def _qualifies(topic: str, clause: str) -> bool:
    if topic != "refund":
        return False
    return bool(re.search(r"\b(?:only if|only when|provided that|unless|unused|never used|not used)\b", clause, re.I))


def compare_promise(promise: str, documents: list[SuppliedDocument]) -> Comparison:
    topics = _topics(promise)
    supported: set[str] = set()
    qualified: set[str] = set()
    contradicted: set[str] = set()
    evidence: list[EvidenceCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    for document in documents:
        for clause in _clauses(document.text):
            for topic in topics:
                stance = None
                if _conflicts(topic, promise, clause):
                    stance = "challenge"
                    contradicted.add(topic)
                elif _supports(topic, promise, clause):
                    stance = "challenge" if _qualifies(topic, clause) else "support"
                    supported.add(topic)
                    if stance == "challenge":
                        qualified.add(topic)
                elif topic == "refund" and _qualifies(topic, clause) and re.search(r"\b(?:refund|unused|never used)\b", clause, re.I):
                    stance = "challenge"
                    qualified.add(topic)
                if not stance or (document.document_id, clause, stance) in seen:
                    continue
                seen.add((document.document_id, clause, stance))
                candidate = EvidenceCandidate(
                    id=uuid4(), stance=stance, source_type="supplied_document",
                    provenance="user_supplied", url=None,
                    document_id=document.document_id,
                    title=f"{document.title} · {document.version}" if document.version else document.title,
                    excerpt=clause, source_text=document.text,
                )
                validate_evidence(candidate)
                evidence.append(candidate)

    supporting = [item for item in evidence if item.stance == "support"]
    challenging = [item for item in evidence if item.stance == "challenge"]
    support = AssessmentDraft(
        "support", "supports" if supporting else "no_support",
        "The cited supplied-policy passages address parts of the promise." if supporting else "No unqualified supporting passage was identified.",
        [Citation(item.id, item.excerpt) for item in supporting],
        "Deterministic wording rules; limited to supplied documents.",
    )
    challenge = AssessmentDraft(
        "challenge", "challenges" if challenging else "no_challenge",
        "The cited passages contain a material exception or conflict." if challenging else "No material exception or conflict was identified in the supplied passages.",
        [Citation(item.id, item.excerpt) for item in challenging],
        "Absence of a challenge is not proof that other policies agree.",
    )
    valid = all(item.validity_status == "valid" for item in evidence) and validate_assessment(support, evidence) and validate_assessment(challenge, evidence)
    missing = topics - supported - contradicted
    if not valid or not topics:
        result, status, reason = "insufficient_evidence", ClaimStatus.insufficient_evidence, "INVALID_OR_UNRECOGNIZED_POLICY_EVIDENCE"
    elif contradicted:
        result, status, reason = "conflicting", ClaimStatus.disputed, "SUPPLIED_POLICY_CONFLICT"
    elif missing:
        result, status, reason = "insufficient_evidence", ClaimStatus.insufficient_evidence, "MISSING_POLICY_COVERAGE"
    elif qualified:
        result, status, reason = "qualified", ClaimStatus.pending_review, "MATERIAL_POLICY_EXCEPTION"
    else:
        result, status, reason = "consistent", ClaimStatus.supported, "SUPPLIED_POLICY_CONSISTENT"

    questions = [f"What does the supplied policy say about {topic}?" for topic in sorted(missing)]
    if qualified:
        questions.append("Does the advertised promise disclose the policy condition?")
    if result == "consistent":
        explanation = "The supplied passages support each recognized part of this promise, within these documents only."
    elif result == "qualified":
        explanation = "The policy contains a material condition that narrows the advertised promise."
    elif result == "conflicting":
        explanation = "A supplied passage explicitly conflicts with the advertised promise."
    else:
        explanation = "The supplied passages do not establish every material part of this promise. Missing evidence is not proof of deception."
    finding = Finding(status, status, result != "consistent", [reason, "DETERMINISTIC_SUPPLIED_DOCUMENT_CHECK"])
    return Comparison(result, explanation, questions, evidence, support, challenge, finding)
