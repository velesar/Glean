"""
Jobs Router

Background job management for scouts, analyzers, etc.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from web.api.deps import get_current_user, get_db

router = APIRouter()


class JobType(str, Enum):
    SCOUT = "scout"
    ANALYZE = "analyze"
    CURATE = "curate"
    UPDATE = "update"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScoutType(str, Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    PRODUCTHUNT = "producthunt"
    WEB = "web"
    RSS = "rss"
    ALL = "all"


class Job(BaseModel):
    """Job model."""
    id: str
    type: JobType
    status: JobStatus
    progress: int = 0
    message: str = ""
    result: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    scout_type: Optional[str] = None


class ScoutConfig(BaseModel):
    """Scout job configuration."""
    scout_type: ScoutType = ScoutType.REDDIT
    demo: bool = True
    # Reddit options
    subreddits: Optional[list[str]] = None
    limit: int = 50
    # Twitter options
    queries: Optional[list[str]] = None
    # Product Hunt options
    days_back: int = 7
    min_votes: int = 10
    # Web Search options
    results_per_query: int = 10
    # RSS options
    feeds: Optional[list[str]] = None
    max_age_days: int = 7


class AnalyzeConfig(BaseModel):
    """Analyze job configuration."""
    mock: bool = True
    limit: int = 10


class CurateConfig(BaseModel):
    """Curate job configuration."""
    min_score: float = 0.3
    auto_merge: bool = True


# In-memory job storage (in production, use Redis or database)
jobs: dict[str, Job] = {}


def create_job(job_type: JobType, scout_type: Optional[str] = None) -> Job:
    """Create a new job."""
    job_id = str(uuid.uuid4())[:8]
    job = Job(
        id=job_id,
        type=job_type,
        status=JobStatus.PENDING,
        started_at=datetime.now().isoformat(),
        scout_type=scout_type,
    )
    jobs[job_id] = job
    return job


async def run_scout_job(job_id: str, config: ScoutConfig):
    """Run scout job in background."""
    job = jobs.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    scout_type = config.scout_type

    try:
        db = get_db()
        total_saved = 0
        total_skipped = 0

        if scout_type == ScoutType.ALL:
            # Run all scouts
            scouts_to_run = [
                ScoutType.REDDIT,
                ScoutType.TWITTER,
                ScoutType.PRODUCTHUNT,
                ScoutType.WEB,
                ScoutType.RSS,
            ]
            for i, st in enumerate(scouts_to_run):
                job.message = f"Running {st.value} scout..."
                job.progress = int((i / len(scouts_to_run)) * 90)

                saved, skipped = run_single_scout(db, st, config)
                total_saved += saved
                total_skipped += skipped

        else:
            job.message = f"Running {scout_type.value} scout..."
            job.progress = 10

            total_saved, total_skipped = run_single_scout(db, scout_type, config)

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {total_saved} discoveries, {total_skipped} duplicates"
        job.result = {"saved": total_saved, "skipped": total_skipped}
        job.completed_at = datetime.now().isoformat()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()


def run_single_scout(db, scout_type: ScoutType, config: ScoutConfig) -> tuple[int, int]:
    """Run a single scout and return (saved, skipped)."""
    scout_config = {'demo': config.demo}

    if scout_type == ScoutType.REDDIT:
        from src.scouts.reddit import run_reddit_scout
        scout_config['post_limit'] = config.limit
        scout_config['include_comments'] = True
        if config.subreddits:
            scout_config['subreddits'] = config.subreddits
        return run_reddit_scout(db, scout_config)

    elif scout_type == ScoutType.TWITTER:
        from src.scouts.twitter import run_twitter_scout
        scout_config['max_results'] = config.limit
        if config.queries:
            scout_config['search_queries'] = config.queries
        return run_twitter_scout(db, scout_config)

    elif scout_type == ScoutType.PRODUCTHUNT:
        from src.scouts.producthunt import run_producthunt_scout
        scout_config['days_back'] = config.days_back
        scout_config['min_votes'] = config.min_votes
        return run_producthunt_scout(db, scout_config)

    elif scout_type == ScoutType.WEB:
        from src.scouts.websearch import run_websearch_scout
        scout_config['results_per_query'] = config.results_per_query
        if config.queries:
            scout_config['search_queries'] = config.queries
        return run_websearch_scout(db, scout_config)

    elif scout_type == ScoutType.RSS:
        from src.scouts.rss import run_rss_scout
        scout_config['max_age_days'] = config.max_age_days
        if config.feeds:
            scout_config['feeds'] = [
                {'name': f, 'url': f, 'category': 'custom'}
                for f in config.feeds
            ]
        return run_rss_scout(db, scout_config)

    return (0, 0)


async def run_analyze_job(job_id: str, config: AnalyzeConfig):
    """Run analyzer job in background."""
    job = jobs.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Starting analyzer..."

    try:
        from src.analyzers import run_analyzer

        db = get_db()

        analyzer_config = {
            'limit': config.limit,
        }

        job.progress = 10
        job.message = "Analyzing discoveries..."

        result = run_analyzer(db, analyzer_config, use_mock=config.mock)

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {result['tools_extracted']} tools, {result['claims_extracted']} claims"
        job.result = {
            "processed": result['processed'],
            "tools_extracted": result['tools_extracted'],
            "claims_extracted": result['claims_extracted'],
            "errors": result['errors'],
        }
        job.completed_at = datetime.now().isoformat()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()


async def run_curate_job(job_id: str, config: CurateConfig):
    """Run curation job in background."""
    job = jobs.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Starting curation..."

    try:
        from src.curator import run_curation

        db = get_db()

        job.progress = 10
        job.message = "Scoring and ranking tools..."

        result = run_curation(
            db,
            min_relevance=config.min_score,
            auto_merge_duplicates=config.auto_merge,
        )

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {result.tools_promoted} promoted to review"
        job.result = {
            "tools_scored": result.tools_scored,
            "tools_promoted": result.tools_promoted,
            "duplicates_merged": result.duplicates_merged,
            "avg_score": round(result.avg_score, 2),
        }
        job.completed_at = datetime.now().isoformat()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()


async def run_update_job(job_id: str):
    """Run update check job in background."""
    job = jobs.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Checking for updates..."

    try:
        from src.tracker import run_update_check

        db = get_db()

        job.progress = 10
        job.message = "Fetching tool pages..."

        result = run_update_check(db)

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {result['changes_detected']} changes found"
        job.result = {
            "tools_checked": result['tools_checked'],
            "changes_detected": result['changes_detected'],
        }
        job.completed_at = datetime.now().isoformat()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()


@router.get("")
async def list_jobs(limit: int = 20, current_user: dict = Depends(get_current_user)):
    """List recent jobs."""
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda j: j.started_at or "",
        reverse=True
    )[:limit]

    return {"jobs": [j.model_dump() for j in sorted_jobs]}


@router.get("/scout-types")
async def get_scout_types(current_user: dict = Depends(get_current_user)):
    """Get available scout types with their descriptions."""
    return {
        "scout_types": [
            {
                "id": "reddit",
                "name": "Reddit",
                "description": "Scout Reddit for AI tool mentions",
                "icon": "reddit",
                "requires_api": True,
            },
            {
                "id": "twitter",
                "name": "Twitter/X",
                "description": "Scout Twitter for AI tool mentions",
                "icon": "twitter",
                "requires_api": True,
            },
            {
                "id": "producthunt",
                "name": "Product Hunt",
                "description": "Scout Product Hunt for new AI tool launches",
                "icon": "producthunt",
                "requires_api": True,
            },
            {
                "id": "web",
                "name": "Web Search",
                "description": "Scout web search results for AI tools",
                "icon": "search",
                "requires_api": True,
            },
            {
                "id": "rss",
                "name": "RSS Feeds",
                "description": "Scout RSS feeds for AI tool mentions",
                "icon": "rss",
                "requires_api": False,
            },
            {
                "id": "all",
                "name": "All Sources",
                "description": "Run all scouts",
                "icon": "globe",
                "requires_api": True,
            },
        ]
    }


@router.get("/{job_id}")
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get job status."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.post("/scout")
async def start_scout(
    config: ScoutConfig,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start a scout job."""
    job = create_job(JobType.SCOUT, scout_type=config.scout_type.value)
    background_tasks.add_task(run_scout_job, job.id, config)
    return {"job_id": job.id, "status": job.status, "scout_type": config.scout_type}


@router.post("/analyze")
async def start_analyze(
    config: AnalyzeConfig,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start an analyzer job."""
    job = create_job(JobType.ANALYZE)
    background_tasks.add_task(run_analyze_job, job.id, config)
    return {"job_id": job.id, "status": job.status}


@router.post("/curate")
async def start_curate(
    config: CurateConfig,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start a curation job."""
    job = create_job(JobType.CURATE)
    background_tasks.add_task(run_curate_job, job.id, config)
    return {"job_id": job.id, "status": job.status}


@router.post("/update")
async def start_update(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start an update check job."""
    job = create_job(JobType.UPDATE)
    background_tasks.add_task(run_update_job, job.id)
    return {"job_id": job.id, "status": job.status}


@router.delete("/{job_id}")
async def cancel_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a running job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        job.status = JobStatus.CANCELLED
        job.message = "Cancelled by user"
        job.completed_at = datetime.now().isoformat()

    return {"success": True, "status": job.status}
