"""Evidence retrieval adapters. Seeded material is explicitly synthetic."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@dataclass
class EvidenceCandidate:
    id: UUID
    stance: str
    source_type: str
    provenance: str
    url: str | None
    document_id: str | None
    title: str
    excerpt: str
    source_text: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    validity_status: str = "unchecked"


def seeded_retrieve(claim_text: str) -> list[EvidenceCandidate]:
    documents = {d["document_id"]: d for d in json.loads((FIXTURES / "demo_documents.json").read_text(encoding="utf-8"))}
    mappings = json.loads((FIXTURES / "demo_evidence.json").read_text(encoding="utf-8"))
    candidates = []
    for item in mappings:
        if item["claim_text"].strip().casefold() != claim_text.strip().casefold():
            continue
        document = documents[item["document_id"]]
        candidates.append(EvidenceCandidate(
            id=uuid4(), stance=item["stance"], source_type="synthetic_demo",
            provenance="synthetic_fixture", url=None, document_id=document["document_id"],
            title=document["title"], excerpt=item["excerpt"], source_text=document["body"],
        ))
    return candidates
