"""
Relevance Scorer

Scores tools for relevance to AI sales automation.
"""

import re
from dataclasses import dataclass

from src.database import Database


@dataclass
class ScoringResult:
    """Result of scoring a tool."""
    tool_id: int
    relevance_score: float
    reasons: list[str]
    claim_count: int
    source_count: int


# Keywords and their weights for relevance scoring
RELEVANCE_SIGNALS = {
    # Strong signals (0.2 each)
    'high': [
        r'\bSDR\b', r'\bBDR\b', r'\bsales\s*rep\b',
        r'\bcold\s*(email|outreach|call)', r'\bprospecting\b',
        r'\blead\s*(gen|generation)\b', r'\boutreach\b',
        r'\bsales\s*automation\b', r'\bsales\s*engagement\b',
    ],
    # Medium signals (0.1 each)
    'medium': [
        r'\bCRM\b', r'\bpipeline\b', r'\bquota\b',
        r'\bconversion\b', r'\bresponse\s*rate\b',
        r'\bemail\s*(sequence|campaign)\b', r'\bLinkedIn\b',
        r'\bmeeting\b', r'\bdemo\b', r'\bclose\b',
    ],
    # Weak signals (0.05 each)
    'low': [
        r'\bAI\b', r'\bautomation\b', r'\bproductivity\b',
        r'\bworkflow\b', r'\bintegration\b', r'\banalytics\b',
    ],
}

# Category relevance weights
CATEGORY_WEIGHTS = {
    'prospecting': 1.0,
    'outreach': 1.0,
    'enrichment': 0.9,
    'conversation': 0.8,
    'crm': 0.7,
    'scheduling': 0.6,
    'analytics': 0.5,
    'coaching': 0.5,
    'other': 0.3,
}


def score_tool(db: Database, tool_id: int) -> ScoringResult:
    """Score a single tool for relevance."""
    tool = db.get_tool(tool_id)
    if not tool:
        return ScoringResult(tool_id, 0.0, ["Tool not found"], 0, 0)

    claims = db.get_claims_for_tool(tool_id)
    reasons = []
    score = 0.0

    # Base score from category
    category = tool.get('category', 'other') or 'other'
    category_weight = CATEGORY_WEIGHTS.get(category, 0.3)
    score += category_weight * 0.3
    reasons.append(f"Category '{category}': +{category_weight * 0.3:.2f}")

    # Score from claims
    if claims:
        # More claims = more signal
        claim_bonus = min(len(claims) * 0.05, 0.2)
        score += claim_bonus
        reasons.append(f"{len(claims)} claims: +{claim_bonus:.2f}")

        # Analyze claim content
        all_claim_text = ' '.join(c['content'] for c in claims)
        keyword_score, keyword_reasons = _score_keywords(all_claim_text)
        score += keyword_score
        reasons.extend(keyword_reasons)

        # Average confidence of claims
        avg_confidence = sum(c['confidence'] for c in claims) / len(claims)
        conf_bonus = avg_confidence * 0.15
        score += conf_bonus
        reasons.append(f"Avg confidence {avg_confidence:.2f}: +{conf_bonus:.2f}")

    # Score from description if present
    if tool.get('description'):
        desc_score, desc_reasons = _score_keywords(tool['description'])
        score += desc_score * 0.5  # Weight description less than claims
        if desc_reasons:
            reasons.append(f"Description keywords: +{desc_score * 0.5:.2f}")

    # Count unique sources
    source_ids = set(c.get('source_id') for c in claims if c.get('source_id'))
    if len(source_ids) > 1:
        multi_source_bonus = min(len(source_ids) * 0.05, 0.15)
        score += multi_source_bonus
        reasons.append(f"{len(source_ids)} sources: +{multi_source_bonus:.2f}")

    # Normalize to 0-1 range
    final_score = min(max(score, 0.0), 1.0)

    return ScoringResult(
        tool_id=tool_id,
        relevance_score=final_score,
        reasons=reasons,
        claim_count=len(claims),
        source_count=len(source_ids)
    )


def _score_keywords(text: str) -> tuple[float, list[str]]:
    """Score text based on relevance keywords."""
    if not text:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []

    # Check high-value keywords
    for pattern in RELEVANCE_SIGNALS['high']:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.15
            # Only add first few to reasons
            if len(reasons) < 3:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    reasons.append(f"'{match.group()}': +0.15")

    # Check medium keywords
    for pattern in RELEVANCE_SIGNALS['medium']:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.08

    # Check low keywords
    for pattern in RELEVANCE_SIGNALS['low']:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.03

    return min(score, 0.4), reasons  # Cap keyword contribution


def batch_score_tools(db: Database, tool_ids: list[int]) -> list[ScoringResult]:
    """Score multiple tools."""
    return [score_tool(db, tid) for tid in tool_ids]
