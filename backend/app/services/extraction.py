"""Bounded deterministic extraction; live extraction can replace this adapter."""

import re
from dataclasses import dataclass


class ClaimLimitExceeded(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedClaim:
    text: str
    start_offset: int
    end_offset: int
    checkability: str
    high_risk: bool


RISK_WORDS = re.compile(r"\b(diagnos(?:is|e)|treat(?:ment)?|medicine|dose|legal|lawsuit|invest(?:ment)?|stock|loan|emergency|safety)\b", re.I)
OPINION_WORDS = re.compile(r"(?:^\s*i\s+(?:like|love|prefer)\b|\b(?:is|looks)\s+beautiful\b|\bis\s+my\s+favorite\b)", re.I)


def extract_claims(text: str, max_claims: int = 5) -> list[ExtractedClaim]:
    if max_claims < 1:
        raise ValueError("max_claims must be positive")
    parts = list(re.finditer(r"[^.!?;]+(?:[.!?;]+|$)", text))
    claims: list[ExtractedClaim] = []
    for match in parts:
        raw = match.group()
        trimmed = raw.strip()
        if not trimmed:
            continue
        start = match.start() + len(raw) - len(raw.lstrip())
        end = start + len(trimmed)
        high_risk = bool(RISK_WORDS.search(trimmed))
        subjective = bool(OPINION_WORDS.search(trimmed)) and not re.search(r"\b(?:and|but)\b|\d", trimmed, re.I)
        checkability = "not_checkable" if not high_risk and (trimmed.endswith("?") or subjective) else "checkable"
        claims.append(ExtractedClaim(trimmed, start, end, checkability, high_risk))
    if len(claims) > max_claims:
        raise ClaimLimitExceeded("input contains more than the configured maximum claims")
    return claims
