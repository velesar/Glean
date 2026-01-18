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


class LogEntry(BaseModel):
    """Log entry model."""
    timestamp: str
    level: str = "info"  # info, warning, error, success
    message: str


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
    logs: list[LogEntry] = []
    user_id: Optional[int] = None

    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log entry to the job."""
        self.logs.append(LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
        ))


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


# In-memory cache for active jobs (synced with database)
_job_cache: dict[str, Job] = {}


def create_job(job_type: JobType, scout_type: Optional[str] = None,
               config: Optional[dict] = None, user_id: Optional[int] = None) -> Job:
    """Create a new job and persist to database."""
    job_id = str(uuid.uuid4())[:8]
    job = Job(
        id=job_id,
        type=job_type,
        status=JobStatus.PENDING,
        started_at=datetime.now().isoformat(),
        scout_type=scout_type,
        user_id=user_id,
    )

    # Persist to database
    db = get_db()
    db.create_job(job_id, job_type.value, scout_type, config, user_id)

    # Cache for active job tracking
    _job_cache[job_id] = job
    return job


def get_job_from_db(job_id: str) -> Optional[Job]:
    """Get job from cache or database."""
    # Check cache first for active jobs
    if job_id in _job_cache:
        return _job_cache[job_id]

    # Load from database
    db = get_db()
    job_data = db.get_job(job_id)
    if job_data:
        logs = [LogEntry(**log) for log in (job_data.get('logs') or [])]
        return Job(
            id=job_data['id'],
            type=JobType(job_data['type']),
            status=JobStatus(job_data['status']),
            progress=job_data['progress'] or 0,
            message=job_data['message'] or "",
            result=job_data['result'],
            started_at=job_data['started_at'],
            completed_at=job_data['completed_at'],
            error=job_data['error'],
            scout_type=job_data['scout_type'],
            logs=logs,
            user_id=job_data.get('user_id'),
        )
    return None


def sync_job_to_db(job: Job) -> None:
    """Sync job state to database."""
    db = get_db()
    logs_data = [log.model_dump() for log in job.logs]
    db.update_job(
        job.id,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
        logs=logs_data,
        completed=job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
    )


async def run_scout_job(job_id: str, config: ScoutConfig):
    """Run scout job in background."""
    job = _job_cache.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.add_log(f"Starting scout job", "info")
    sync_job_to_db(job)
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
                job.add_log(f"Running {st.value} scout...", "info")
                sync_job_to_db(job)

                saved, skipped = run_single_scout(db, st, config, job.user_id)
                total_saved += saved
                total_skipped += skipped
                job.add_log(f"{st.value}: {saved} discoveries, {skipped} duplicates", "info")

        else:
            job.message = f"Running {scout_type.value} scout..."
            job.progress = 10
            job.add_log(f"Running {scout_type.value} scout...", "info")
            sync_job_to_db(job)

            total_saved, total_skipped = run_single_scout(db, scout_type, config, job.user_id)
            job.add_log(f"Found {total_saved} discoveries, {total_skipped} duplicates", "info")

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {total_saved} discoveries, {total_skipped} duplicates"
        job.result = {"saved": total_saved, "skipped": total_skipped}
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Job completed successfully", "success")
        sync_job_to_db(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Job failed: {str(e)}", "error")
        sync_job_to_db(job)
    finally:
        # Remove from cache when done
        _job_cache.pop(job_id, None)


def run_single_scout(db, scout_type: ScoutType, config: ScoutConfig,
                     user_id: Optional[int] = None) -> tuple[int, int]:
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
        # Load Product Hunt credentials from user settings
        if user_id and not config.demo:
            api_key = db.get_setting(user_id, 'api_keys', 'producthunt_api_key')
            api_secret = db.get_setting(user_id, 'api_keys', 'producthunt_api_secret')
            if api_key and api_secret:
                scout_config['producthunt'] = {
                    'api_key': api_key,
                    'api_secret': api_secret,
                }
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
    job = _job_cache.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Starting analyzer..."
    job.add_log("Starting analyzer job", "info")
    sync_job_to_db(job)

    try:
        from src.analyzers import run_analyzer

        db = get_db()

        analyzer_config = {
            'limit': config.limit,
        }

        # Load API key from user settings if not using mock mode
        use_mock = config.mock
        if not use_mock and job.user_id:
            api_key = db.get_setting(job.user_id, 'api_keys', 'anthropic')
            if api_key:
                analyzer_config['api_key'] = api_key
                job.add_log("Using Anthropic API key from settings", "info")
            else:
                job.add_log("No Anthropic API key found in settings, falling back to mock mode", "warning")
                use_mock = True
        elif not use_mock:
            job.add_log("No user context available, falling back to mock mode", "warning")
            use_mock = True

        job.progress = 10
        job.message = "Analyzing discoveries..."
        job.add_log(f"Analyzing up to {config.limit} discoveries (mock={use_mock})", "info")
        sync_job_to_db(job)

        result = run_analyzer(db, analyzer_config, use_mock=use_mock)

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
        job.add_log(f"Processed {result['processed']} discoveries", "info")
        job.add_log(f"Extracted {result['tools_extracted']} tools, {result['claims_extracted']} claims", "info")
        if result['errors'] > 0:
            job.add_log(f"{result['errors']} errors during processing", "warning")
        job.add_log("Job completed successfully", "success")
        sync_job_to_db(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Job failed: {str(e)}", "error")
        sync_job_to_db(job)
    finally:
        _job_cache.pop(job_id, None)


async def run_curate_job(job_id: str, config: CurateConfig):
    """Run curation job in background."""
    job = _job_cache.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Starting curation..."
    job.add_log("Starting curation job", "info")
    sync_job_to_db(job)

    try:
        from src.curator import run_curation

        db = get_db()

        job.progress = 10
        job.message = "Scoring and ranking tools..."
        job.add_log(f"Scoring tools (min_score={config.min_score}, auto_merge={config.auto_merge})", "info")
        sync_job_to_db(job)

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
        job.add_log(f"Scored {result.tools_scored} tools (avg: {result.avg_score:.2f})", "info")
        job.add_log(f"Promoted {result.tools_promoted} tools to review", "info")
        if result.duplicates_merged > 0:
            job.add_log(f"Merged {result.duplicates_merged} duplicates", "info")
        job.add_log("Job completed successfully", "success")
        sync_job_to_db(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Job failed: {str(e)}", "error")
        sync_job_to_db(job)
    finally:
        _job_cache.pop(job_id, None)


async def run_update_job(job_id: str):
    """Run update check job in background."""
    job = _job_cache.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.message = "Checking for updates..."
    job.add_log("Starting update check job", "info")
    sync_job_to_db(job)

    try:
        from src.tracker import run_update_check

        db = get_db()

        job.progress = 10
        job.message = "Fetching tool pages..."
        job.add_log("Fetching approved tool pages for changes...", "info")
        sync_job_to_db(job)

        result = run_update_check(db)

        job.progress = 100
        job.status = JobStatus.COMPLETED
        job.message = f"Completed: {result['changes_detected']} changes found"
        job.result = {
            "tools_checked": result['tools_checked'],
            "changes_detected": result['changes_detected'],
        }
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Checked {result['tools_checked']} tools", "info")
        job.add_log(f"Detected {result['changes_detected']} changes", "info")
        job.add_log("Job completed successfully", "success")
        sync_job_to_db(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.now().isoformat()
        job.add_log(f"Job failed: {str(e)}", "error")
        sync_job_to_db(job)
    finally:
        _job_cache.pop(job_id, None)


@router.get("")
async def list_jobs(
    limit: int = 20,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List recent jobs from database."""
    db = get_db()
    job_list = db.list_jobs(limit=limit, status=status)

    # Merge with active cache jobs (in case db hasn't synced yet)
    result = []
    seen_ids = set()

    # Add active jobs from cache first (most recent state)
    for job in _job_cache.values():
        result.append(job.model_dump())
        seen_ids.add(job.id)

    # Add database jobs not in cache
    for job_data in job_list:
        if job_data['id'] not in seen_ids:
            result.append(job_data)

    # Sort by started_at (descending), then by id for stability
    # This ensures consistent ordering even when timestamps are identical
    result.sort(key=lambda j: (j.get('started_at') or '', j.get('id', '')), reverse=True)

    return {"jobs": result[:limit]}


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
    job = get_job_from_db(job_id)
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
    job = create_job(JobType.SCOUT, scout_type=config.scout_type.value, user_id=current_user.get('id'))
    background_tasks.add_task(run_scout_job, job.id, config)
    return {"job_id": job.id, "status": job.status, "scout_type": config.scout_type}


@router.post("/analyze")
async def start_analyze(
    config: AnalyzeConfig,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start an analyzer job."""
    job = create_job(JobType.ANALYZE, user_id=current_user.get('id'))
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
    # Check cache first for active jobs
    job = _job_cache.get(job_id)
    if job:
        if job.status == JobStatus.RUNNING:
            job.status = JobStatus.CANCELLED
            job.message = "Cancelled by user"
            job.completed_at = datetime.now().isoformat()
            sync_job_to_db(job)
            _job_cache.pop(job_id, None)
        return {"success": True, "status": job.status.value}

    # Check database
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        db = get_db()
        db.update_job(
            job_id,
            status="cancelled",
            message="Cancelled by user",
            completed=True
        )
        job.status = JobStatus.CANCELLED

    return {"success": True, "status": job.status.value}
