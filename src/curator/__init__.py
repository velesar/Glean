"""
Glean Curator Module

AI-driven ranking, deduplication, and queue management.
"""

from src.curator.scorer import score_tool, batch_score_tools, ScoringResult
from src.curator.dedup import find_duplicates, merge_duplicates, run_deduplication, DuplicateGroup
from src.curator.curator import run_curation, get_scoring_details, CurationResult

__all__ = [
    'score_tool',
    'batch_score_tools',
    'ScoringResult',
    'find_duplicates',
    'merge_duplicates',
    'run_deduplication',
    'DuplicateGroup',
    'run_curation',
    'get_scoring_details',
    'CurationResult',
]
