"""
Curator Module

Orchestrates curation: scoring, deduplication, and queue management.
"""

from dataclasses import dataclass
from typing import Optional

from src.curator.dedup import run_deduplication
from src.curator.scorer import ScoringResult, score_tool
from src.database import Database


@dataclass
class CurationResult:
    """Result of running curation."""
    tools_scored: int
    tools_promoted: int  # Moved to review queue
    tools_below_threshold: int
    duplicates_found: int
    duplicates_merged: int
    min_score: float
    max_score: float
    avg_score: float


def run_curation(
    db: Database,
    min_relevance: float = 0.3,
    auto_merge_duplicates: bool = True,
    max_review_queue: int = 50
) -> CurationResult:
    """Run the full curation pipeline.

    1. Find and merge duplicates
    2. Score all tools in 'analyzing' status
    3. Promote high-scoring tools to 'review' queue
    4. Keep low-scoring tools in 'analyzing' for more data

    Args:
        db: Database connection
        min_relevance: Minimum score to promote to review (0-1)
        auto_merge_duplicates: Automatically merge detected duplicates
        max_review_queue: Max tools to have in review queue
    """
    # Step 1: Deduplication
    dedup_result = run_deduplication(db, auto_merge=auto_merge_duplicates)

    # Step 2: Get tools to score
    tools = db.get_tools_by_status('analyzing')

    if not tools:
        return CurationResult(
            tools_scored=0,
            tools_promoted=0,
            tools_below_threshold=0,
            duplicates_found=dedup_result['duplicates_found'],
            duplicates_merged=dedup_result['merged'],
            min_score=0.0,
            max_score=0.0,
            avg_score=0.0
        )

    # Step 3: Score each tool
    scores = []
    for tool in tools:
        result = score_tool(db, tool['id'])
        scores.append(result)

        # Update score in database
        db.set_relevance_score(tool['id'], result.relevance_score)

    # Step 4: Check current review queue size
    current_review = db.get_tools_by_status('review')
    available_slots = max(0, max_review_queue - len(current_review))

    # Step 5: Promote high-scoring tools
    # Sort by score descending
    scores.sort(key=lambda x: x.relevance_score, reverse=True)

    promoted = 0
    below_threshold = 0

    for result in scores:
        if result.relevance_score >= min_relevance:
            if promoted < available_slots:
                db.update_tool_status(result.tool_id, 'review')
                promoted += 1
            # else: stays in analyzing, will be promoted when queue has space
        else:
            below_threshold += 1

    # Calculate stats
    all_scores = [r.relevance_score for r in scores]

    return CurationResult(
        tools_scored=len(scores),
        tools_promoted=promoted,
        tools_below_threshold=below_threshold,
        duplicates_found=dedup_result['duplicates_found'],
        duplicates_merged=dedup_result['merged'],
        min_score=min(all_scores),
        max_score=max(all_scores),
        avg_score=sum(all_scores) / len(all_scores)
    )


def get_scoring_details(db: Database, tool_id: int) -> Optional[ScoringResult]:
    """Get detailed scoring breakdown for a tool."""
    tool = db.get_tool(tool_id)
    if not tool:
        return None
    return score_tool(db, tool_id)
