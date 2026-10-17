"""The real-policy path must use exact policy quotes and fail closed."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from app.main import app
from app.models import Base
from app.schemas import VerificationRequest
from app.providers.live import ProviderFailure
from app.services import official_policy
from app.services.pipeline import process_job


QUOTE = "We use Personal Data to develop and improve our products, including training models."
POLICY = "# GitHub General Privacy Statement\n\n## Product Development\n\n" + QUOTE + "\n\n" + (
    "## Other processing\n\nGitHub describes additional processing purposes.\n\n" * 150
)


def _snapshot():
    return official_policy.PolicySnapshot(POLICY, "a" * 64, datetime.now(timezone.utc))


def test_two_roles_cite_exact_policy_and_keep_release_pending(monkeypatch):
    monkeypatch.setattr(official_policy, "load_policy", _snapshot)
    calls = []

    def fake_chat(instruction, payload, **_kwargs):
        calls.append(instruction)
        if "support analyst" in instruction:
            return {"position": "no_support", "reasoning_summary": "No direct support.", "citations": [], "limitations": "Only ranked passages were read."}
        passage = next(item for item in payload["passages"] if QUOTE in item["text"])
        return {"position": "challenges", "reasoning_summary": "The policy permits model training.",
                "citations": [{"passage_id": passage["id"], "quote": QUOTE}], "limitations": "Policy text does not prove actual practice."}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    result = official_policy.compare_official_policy("GitHub never uses personal data to train AI models.")
    assert len(calls) == 2
    assert result.result == "conflicting"
    assert result.finding.effective_status == "pending_review"
    assert result.finding.needs_review is True
    assert result.challenge.position == "challenges"
    assert len(result.evidence) == 1
    assert result.evidence[0].excerpt == QUOTE
    assert result.evidence[0].validity_status == "valid"
    assert result.evidence[0].url == official_policy.POLICY_PAGE


def test_invalid_model_quote_cannot_become_evidence(monkeypatch):
    monkeypatch.setattr(official_policy, "load_policy", _snapshot)

    def fake_chat(instruction, payload, **_kwargs):
        if "support analyst" in instruction:
            return {"position": "supports", "reasoning_summary": "Unsupported assertion.",
                    "citations": [{"passage_id": payload["passages"][0]["id"], "quote": "This quote was invented by the model."}]}
        return {"position": "no_challenge", "reasoning_summary": "No passage.", "citations": []}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    with pytest.raises(ProviderFailure, match="did not match"):
        official_policy.compare_official_policy("GitHub never uses personal data to train AI models.")


def test_uncited_assertion_is_downgraded_to_insufficient(monkeypatch):
    monkeypatch.setattr(official_policy, "load_policy", _snapshot)

    def fake_chat(instruction, payload, **_kwargs):
        return {"position": "supports" if "support analyst" in instruction else "no_challenge",
                "reasoning_summary": "Model-only assertion.", "citations": []}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    result = official_policy.compare_official_policy("GitHub may use personal data to train AI models.")
    assert result.result == "insufficient_evidence"
    assert result.support.position == "no_support"
    assert result.evidence == []
    assert result.finding.effective_status == "pending_review"


def test_citations_for_declined_position_are_discarded(monkeypatch):
    monkeypatch.setattr(official_policy, "load_policy", _snapshot)

    def fake_chat(instruction, payload, **_kwargs):
        if "support analyst" in instruction:
            passage = next(item for item in payload["passages"] if QUOTE in item["text"])
            return {"position": "no_support", "reasoning_summary": "Inconsistent model response.",
                    "citations": [{"passage_id": passage["id"], "quote": QUOTE}]}
        return {"position": "no_challenge", "reasoning_summary": "No passage.", "citations": []}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    result = official_policy.compare_official_policy("GitHub may use personal data to train AI models.")
    assert result.result == "insufficient_evidence"
    assert result.evidence == []


def test_snapshot_hash_mismatch_is_rejected(monkeypatch):
    metadata = '{"source_url":"' + official_policy.POLICY_PAGE + '","sha256":"wrong","retrieved_at":"2026-10-17T00:00:00+00:00"}'
    monkeypatch.setattr(official_policy, "POLICY_FILE", SimpleNamespace(read_text=lambda **_kwargs: POLICY))
    monkeypatch.setattr(official_policy, "POLICY_META", SimpleNamespace(read_text=lambda **_kwargs: metadata))
    with pytest.raises(official_policy.PolicySourceUnavailable):
        official_policy.load_policy()


def test_pasted_policy_requires_full_text_and_source_selection():
    with pytest.raises(ValidationError):
        VerificationRequest(text="A claim.", policy_source="github_privacy", policy_text="short")
    with pytest.raises(ValidationError):
        VerificationRequest(text="A claim.", policy_text=POLICY)


def test_pasted_policy_uses_saved_full_text_and_unverified_provenance(monkeypatch):
    assert len(POLICY) > 10000
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "local-test-only")
    monkeypatch.setenv("LLM_MODEL", "mock")
    monkeypatch.setattr("app.main.load_policy", lambda: (_ for _ in ()).throw(AssertionError("Downloaded source must not be loaded")))

    def fake_chat(instruction, payload, **_kwargs):
        if "support analyst" in instruction:
            passage = next(item for item in payload["passages"] if QUOTE in item["text"])
            return {"position": "supports", "reasoning_summary": "The pasted policy lists model training.",
                    "citations": [{"passage_id": passage["id"], "quote": QUOTE}]}
        return {"position": "no_challenge", "reasoning_summary": "No contrary passage.", "citations": []}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={
            "text": "GitHub may use personal data to train models.",
            "policy_source": "github_privacy", "policy_text": POLICY,
        })
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "completed"
        assert job["origin"] == "user_pasted_github_policy"
        assert job["documents"][0]["text"] == POLICY
        assert job["overall_action"] == "hold_for_review"
        detail = client.get(f"/api/v1/claims/{job['claims'][0]['id']}").json()
        assert detail["evidence"][0]["source_type"] == "user_supplied_privacy_policy"
        assert detail["evidence"][0]["provenance"] == "user_pasted_unverified"
        assert detail["evidence"][0]["url"] is None
        assert detail["evidence"][0]["excerpt"] == QUOTE
    engine.dispose()


def test_official_policy_api_review_and_guardian_gate(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LLM_API_URL", "https://unit-test.invalid/chat")
    monkeypatch.setenv("LLM_API_KEY", "local-test-only")
    monkeypatch.setenv("LLM_MODEL", "mock")
    monkeypatch.setattr(official_policy, "load_policy", _snapshot)
    monkeypatch.setattr("app.main.load_policy", _snapshot)

    def fake_chat(instruction, payload, **_kwargs):
        if "support analyst" in instruction:
            passage = next(item for item in payload["passages"] if QUOTE in item["text"])
            return {"position": "supports", "reasoning_summary": "The source says model training is a purpose.",
                    "citations": [{"passage_id": passage["id"], "quote": QUOTE}], "limitations": "Written policy only."}
        return {"position": "no_challenge", "reasoning_summary": "No contrary passage in the ranked selection.",
                "citations": [], "limitations": "Retrieval can miss passages."}

    monkeypatch.setattr(official_policy, "_chat_json", fake_chat)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={
            "text": "GitHub may use personal data to train AI models.",
            "policy_source": "github_privacy", "policy": "strict",
        })
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "completed"
        assert job["overall_action"] == "hold_for_review"
        assert job["origin"] == "official_github_policy"
        claim_id = job["claims"][0]["id"]
        detail = client.get(f"/api/v1/claims/{claim_id}").json()
        assert detail["evidence"][0]["excerpt"] == QUOTE
        assert {item["role"] for item in detail["assessments"]} == {"support", "challenge"}
        approved = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "approve", "reviewer_id": "test-reviewer", "rationale": "The exact passage supports the written-policy claim.",
        })
        assert approved.status_code == 200
        assert approved.json()["overall_action"] == "pass"
    engine.dispose()
