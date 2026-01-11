"""
Stats Router

Pipeline statistics and dashboard data.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from web.api.deps import get_db
from src.database import Database


router = APIRouter()


class PipelineStats(BaseModel):
    """Pipeline statistics response."""
    inbox: int
    analyzing: int
    review: int
    approved: int
    rejected: int
    total_tools: int
    unprocessed_discoveries: int
    total_claims: int
    total_sources: int


class ActivityItem(BaseModel):
    """Activity log item."""
    timestamp: str
    type: str
    message: str
    tool_name: str | None = None


@router.get("/stats", response_model=PipelineStats)
async def get_stats():
    """Get pipeline statistics for dashboard."""
    db = get_db()
    stats = db.get_pipeline_stats()

    return PipelineStats(
        inbox=stats["tools_by_status"]["inbox"],
        analyzing=stats["tools_by_status"]["analyzing"],
        review=stats["tools_by_status"]["review"],
        approved=stats["tools_by_status"]["approved"],
        rejected=stats["tools_by_status"]["rejected"],
        total_tools=stats["total_tools"],
        unprocessed_discoveries=stats["unprocessed_discoveries"],
        total_claims=stats["total_claims"],
        total_sources=stats["total_sources"],
    )


@router.get("/activity")
async def get_activity(limit: int = 20):
    """Get recent activity log."""
    db = get_db()
    conn = db.connect()

    # Get recent changelog entries as activity
    rows = conn.execute(
        """SELECT c.detected_at, c.change_type, c.description, t.name as tool_name
           FROM changelog c
           JOIN tools t ON c.tool_id = t.id
           ORDER BY c.detected_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()

    activities = []
    for row in rows:
        activities.append({
            "timestamp": row["detected_at"],
            "type": row["change_type"],
            "message": row["description"],
            "tool_name": row["tool_name"],
        })

    return {"activities": activities}
