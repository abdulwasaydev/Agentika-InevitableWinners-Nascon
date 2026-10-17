"""Review a downloaded official policy with two citation-bound LLM roles.

The full document is downloaded once by an operator, or supplied by the user.
The model selects quote IDs; the server restores the exact source substrings.
"""

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from ..providers.live import ProviderFailure, _chat_json
from ..schemas import ClaimStatus
from .assessment import AssessmentDraft, Citation
from .comparison import Comparison
from .evidence_validation import validate_assessment, validate_evidence
from .policy import Finding
from .retrieval import EvidenceCandidate

POLICY_PAGE = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"
POLICY_DOWNLOAD = (
    "https://docs.github.com/api/article/body"
    "?pathname=/en/site-policy/privacy-policies/github-general-privacy-statement"
)
POLICY_DIR = Path(__file__).resolve().parents[2] / "data"
POLICY_FILE = POLICY_DIR / "github_privacy_statement.md"
POLICY_META = POLICY_DIR / "github_privacy_statement.json"
POLICY_ORIGIN = "official_github_policy"
PASTED_POLICY_ORIGIN = "user_pasted_github_policy"


class PolicySourceUnavailable(ProviderFailure):
    pass


@dataclass(frozen=True)
class PolicySnapshot:
    text: str
    sha256: str
    retrieved_at: datetime


@dataclass(frozen=True)
class Passage:
    id: str
    heading: str
    text: str


def download_policy(*, client: httpx.Client | None = None) -> PolicySnapshot:
    """Refresh the local snapshot; never called implicitly from a job or test."""
    own = client is None
    client = client or httpx.Client(timeout=20)
    try:
        response = client.get(POLICY_DOWNLOAD, headers={"Accept": "text/markdown, text/plain"})
        response.raise_for_status()
        body = response.text.replace("\r\n", "\n").replace("\r", "\n")
        if len(body) < 10000 or "GitHub" not in body or "Personal Data" not in body:
            raise PolicySourceUnavailable("Official policy response was incomplete")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        retrieved_at = datetime.now().astimezone()
        POLICY_DIR.mkdir(parents=True, exist_ok=True)
        POLICY_FILE.write_text(body, encoding="utf-8")
        POLICY_META.write_text(json.dumps({
            "source_url": POLICY_PAGE, "download_url": POLICY_DOWNLOAD,
            "sha256": digest, "retrieved_at": retrieved_at.isoformat(),
        }, indent=2), encoding="utf-8")
        return PolicySnapshot(body, digest, retrieved_at)
    except httpx.HTTPError as exc:
        raise PolicySourceUnavailable("Could not download GitHub's official privacy statement") from exc
    finally:
        if own:
            client.close()


def load_policy() -> PolicySnapshot:
    try:
        body = POLICY_FILE.read_text(encoding="utf-8")
        meta = json.loads(POLICY_META.read_text(encoding="utf-8"))
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if meta["source_url"] != POLICY_PAGE or meta["sha256"] != digest or len(body) < 10000:
            raise ValueError("snapshot metadata does not match")
        return PolicySnapshot(body, digest, datetime.fromisoformat(meta["retrieved_at"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PolicySourceUnavailable(
            "Download the official policy with python backend/scripts/download_github_policy.py"
        ) from exc


def _passages(markdown: str) -> list[Passage]:
    heading = "GitHub General Privacy Statement"
    paragraphs: list[tuple[str, str]] = []
    lines: list[str] = []
    for line in markdown.splitlines() + [""]:
        if line.startswith("#"):
            if lines:
                paragraphs.append((heading, " ".join(lines)))
                lines = []
            heading = line.lstrip("# ").strip() or heading
        elif line.strip():
            lines.append(line.strip())
        elif lines:
            paragraphs.append((heading, " ".join(lines)))
            lines = []
    result: list[Passage] = []
    for section, paragraph in paragraphs:
        for offset in range(0, len(paragraph), 1500):
            segment = paragraph[offset:offset + 1500]
            result.append(Passage(f"p{len(result) + 1}", section, segment))
    return result


STOP = {"github", "the", "and", "that", "with", "from", "this", "their", "your", "you", "does", "not", "never", "always", "personal", "data", "privacy", "policy", "information"}


def select_passages(claim: str, markdown: str, limit: int = 8) -> list[Passage]:
    """Bounded lexical skim of the whole policy; LLM sees the ranked passages."""
    passages = _passages(markdown)
    words = {word.rstrip("s") for word in re.findall(r"[a-z]{4,}", claim.casefold()) if word not in STOP}
    if not words:
        words = {word for word in re.findall(r"[a-z]{4,}", claim.casefold()) if word not in {"github", "the"}}
    counts = {word: sum(word in passage.text.casefold() or word in passage.heading.casefold() for passage in passages) for word in words}
    def score(passage: Passage) -> float:
        haystack = (passage.heading + " " + passage.text).casefold()
        return sum((1 + math.log((len(passages) + 1) / (counts[word] + 1))) for word in words if word in haystack)
    ranked = sorted(passages, key=score, reverse=True)
    return [passage for passage in ranked[:limit] if score(passage) > 0]


def _assess(role: str, claim: str, passages: list[Passage], snapshot: PolicySnapshot,
            *, verified_source: bool) -> tuple[AssessmentDraft, list[EvidenceCandidate]]:
    positive = role == "support"
    position = "supports" if positive else "challenges"
    empty = "no_support" if positive else "no_challenge"
    quotes: dict[str, tuple[Passage, str]] = {}
    supplied = []
    for passage in passages:
        options = []
        # Overlap preserves context across chunk boundaries. Never ask the model
        # to reproduce markdown, Unicode, or punctuation character for character.
        for offset in range(0, len(passage.text), 640):
            quote = passage.text[offset:offset + 800].strip()
            if len(quote) < 12:
                continue
            quote_id = f"{passage.id}:q{len(options) + 1}"
            quotes[quote_id] = (passage, quote)
            options.append({"id": quote_id, "text": quote})
        supplied.append({**vars(passage), "quote_options": options})
    with httpx.Client(timeout=30) as client:
        result = _chat_json(
            f"You are the {role} analyst reading policy text attributed to GitHub. Look only for passages that directly {position} the precise claim. "
            "Account for qualifiers, scope, and exceptions. Do not treat missing text as proof. "
            f"Return JSON with position ({position} or {empty}), reasoning_summary (1-3 concise sentences), "
            'citations (0-2 objects of the form {"quote_id":"p1:q1"}), and limitations. '
            "Select only IDs from the supplied quote_options. Do not write or paraphrase quote text. "
            "Use the full passage to check scope and qualifications before selecting a quote. "
            "If no passage directly establishes your position, return no citations and the empty position.",
            {"claim": claim, "passages": supplied},
            client=client, max_tokens=1400,
        )
    raw = result.get("citations")
    if result.get("position") not in {position, empty} or not isinstance(raw, list) or len(raw) > 2:
        raise ProviderFailure(f"Invalid {role} analyst response")
    if result["position"] == position and not raw:
        # A model's uncited assertion is not evidence. Keep the role note, but
        # downgrade its position so it cannot influence the release decision.
        result["position"] = empty
        result["reasoning_summary"] = "The analyst asserted a position without an exact policy quote; its assertion was discarded."
        result["limitations"] = "No cited passage establishes this position."
    if result["position"] == empty and raw:
        # The role explicitly declined the position, so these quotes cannot
        # support it regardless of whether their text happens to match.
        raw = []
        result["reasoning_summary"] = "The analyst did not establish this position; its inconsistent citations were discarded."
        result["limitations"] = "No cited passage establishes this position."
    evidence: list[EvidenceCandidate] = []
    citations: list[Citation] = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"quote_id"} or not isinstance(item["quote_id"], str):
            raise ProviderFailure("Invalid policy citation", category="citation_validation", http_status=200)
        selected = quotes.get(item["quote_id"])
        if selected is None:
            raise ProviderFailure("Invalid policy citation ID", category="citation_validation", http_status=200)
        passage, quote = selected
        candidate = EvidenceCandidate(
            id=uuid4(), stance="support" if positive else "challenge",
            source_type="official_privacy_policy" if verified_source else "user_supplied_privacy_policy",
            provenance="github_docs_snapshot" if verified_source else "user_pasted_unverified",
            url=POLICY_PAGE if verified_source else None,
            document_id=f"GITHUB-{'PRIVACY' if verified_source else 'PASTED'}-{snapshot.sha256[:12]}",
            title=f"{'GitHub Privacy Statement' if verified_source else 'User-pasted policy text'} · {passage.heading}",
            excerpt=quote, source_text=passage.text, retrieved_at=snapshot.retrieved_at,
        )
        if not validate_evidence(candidate):
            raise ProviderFailure("Policy evidence failed validation")
        evidence.append(candidate)
        citations.append(Citation(candidate.id, quote))
    reasoning = result.get("reasoning_summary")
    limitations = result.get("limitations")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ProviderFailure("Policy analyst omitted notes")
    draft = AssessmentDraft(role, result["position"], reasoning[:2000], citations,
                            limitations[:1000] if isinstance(limitations, str) else "Only selected passages were reviewed by the model.")
    if not validate_assessment(draft, evidence):
        raise ProviderFailure("Policy analyst citations failed validation")
    return draft, evidence


def compare_policy_text(claim: str, snapshot: PolicySnapshot, *, verified_source: bool) -> Comparison:
    passages = select_passages(claim, snapshot.text)
    if not passages:
        raise PolicySourceUnavailable("No relevant policy passage was found")
    support, supporting = _assess("support", claim, passages, snapshot, verified_source=verified_source)
    challenge, challenging = _assess("challenge", claim, passages, snapshot, verified_source=verified_source)
    if challenging:
        result, provisional, reason = "conflicting", ClaimStatus.disputed, "OFFICIAL_POLICY_CHALLENGE"
        explanation = "The challenge analyst cited a passage that conflicts with the claim. Human review is required."
    elif supporting:
        result, provisional, reason = "consistent", ClaimStatus.supported, "OFFICIAL_POLICY_SUPPORT"
        explanation = "The support analyst cited a matching passage. Human review is required before release."
    else:
        result, provisional, reason = "insufficient_evidence", ClaimStatus.insufficient_evidence, "OFFICIAL_POLICY_INSUFFICIENT"
        explanation = "The selected policy passages did not establish this claim."
    finding = Finding(provisional, ClaimStatus.pending_review, True, [reason, "LLM_POLICY_SCAN_REVIEW_REQUIRED"])
    return Comparison(result, explanation,
                      ["Could another part of the policy change this interpretation?"],
                      supporting + challenging, support, challenge, finding)


def compare_official_policy(claim: str) -> Comparison:
    return compare_policy_text(claim, load_policy(), verified_source=True)
