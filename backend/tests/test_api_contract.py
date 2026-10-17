from pathlib import Path
import json

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas import JobOut, ReviewRequest, VerificationRequest


def test_contract_examples_and_generated_openapi():
    root = Path(__file__).resolve().parents[2]
    examples = root / "contracts" / "examples"
    VerificationRequest.model_validate_json((examples / "verify-request.json").read_text())
    VerificationRequest.model_validate_json((examples / "promise-request.json").read_text())
    JobOut.model_validate_json((examples / "job-completed.json").read_text())
    assert json.loads((root / "contracts" / "openapi.json").read_text()) == app.openapi()


def test_review_correction_requires_text():
    try:
        ReviewRequest(decision="correct", reviewer_id="reviewer", rationale="The value is wrong")
        assert False, "missing correction should fail"
    except ValidationError:
        pass


def test_no_database_does_not_silently_use_memory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["database_ready"] is False
        response = client.post("/api/v1/verify", json={"text": "A claim."})
        assert response.status_code == 503
        assert response.json()["code"] == "DATABASE_UNAVAILABLE"


def test_local_frontend_preflight_is_explicitly_allowed():
    with TestClient(app) as client:
        response = client.options("/api/v1/verify", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
