"""
Glean Curator Module

AI-driven ranking, deduplication, and queue management.
"""

from src.curator.curator import CurationResult, get_scoring_details, run_curation
from src.curator.dedup import DuplicateGroup, find_duplicates, merge_duplicates, run_deduplication
from src.curator.scorer import ScoringResult, batch_score_tools, score_tool

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
