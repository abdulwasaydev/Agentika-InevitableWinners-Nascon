import json

import httpx
import pytest

from app.providers.live import ProviderFailure, live_assess, live_extract, live_retrieve
from app.schemas import ClaimStatus
from app.services.assessment import AssessmentDraft, Citation
from app.services.extraction import extract_claims
from app.services.retrieval import EvidenceCandidate
from app.services.verification import verify_one_claim


def _llm_response(payload):
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})


def test_live_extraction_checks_exact_source_and_coverage(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "https://example.test/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    text = "The test archive opened in 2020."
    with httpx.Client(transport=httpx.MockTransport(lambda request: _llm_response({"claims": [{"text": text}]}))) as client:
        claims = live_extract(text, client=client)
    assert claims[0].start_offset == 0
    with httpx.Client(transport=httpx.MockTransport(lambda request: _llm_response({"claims": []}))) as client:
        with pytest.raises(ProviderFailure):
            live_extract(text, client=client)


def test_brave_result_is_labeled_unverified_snippet(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    def response(request):
        assert request.headers["X-Subscription-Token"] == "test-key"
        return httpx.Response(200, json={"web": {"results": [{
            "title": "Example source", "url": "https://example.test/source",
            "description": "The test archive opened in 2020.",
        }]}})
    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        evidence = live_retrieve("The test archive opened in 2020.", client=client)
    assert evidence[0].source_type == "web_search_snippet"
    assert evidence[0].provenance == "live_search_snippet_unverified_page"


def test_live_assessment_citation_is_validated_and_snippet_does_not_pass(monkeypatch):
    from app.services.retrieval import EvidenceCandidate
    from uuid import uuid4

    evidence = [EvidenceCandidate(
        id=uuid4(), stance="context", source_type="web_search_snippet",
        provenance="live_search_snippet_unverified_page", url="https://example.test/source",
        document_id=None, title="Example", excerpt="The test archive opened in 2020.",
        source_text="The test archive opened in 2020.",
    )]
    monkeypatch.setattr("app.services.verification.live_retrieve", lambda text: evidence)
    monkeypatch.setattr("app.services.verification.live_assess", lambda role, text, sources: AssessmentDraft(
        role, "supports" if role == "support" else "no_challenge", "Mocked role output",
        [Citation(sources[0].id, sources[0].excerpt)] if role == "support" else [],
    ))
    result = verify_one_claim(extract_claims("The test archive opened in 2020.")[0], use_demo=False)
    assert result.finding.provisional_status == ClaimStatus.insufficient_evidence
    assert "WEB_SNIPPET_UNVERIFIED" in result.finding.reason_codes


def test_llm_provider_failure_does_not_become_support(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "https://example.test/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        with pytest.raises(ProviderFailure):
            live_assess("support", "The test archive opened in 2020.", [EvidenceCandidate(
                id=__import__("uuid").uuid4(), stance="context", source_type="web_search_snippet",
                provenance="live_search_snippet_unverified_page", url="https://example.test/source",
                document_id=None, title="Example", excerpt="The test archive opened in 2020.",
                source_text="The test archive opened in 2020.",
            )], client=client)
