"""
Reports Router

Generate and retrieve reports.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from web.api.deps import get_db, get_current_user
from src.reporters import generate_weekly_digest, generate_changelog, generate_tools_index


router = APIRouter()


@router.get("/weekly")
async def get_weekly_report(weeks: int = Query(1, ge=1, le=12), current_user: dict = Depends(get_current_user)):
    """Get weekly digest report."""
    db = get_db()
    report = generate_weekly_digest(db, weeks_back=weeks)
    return {"report": report, "format": "markdown"}


@router.get("/weekly/raw", response_class=PlainTextResponse)
async def get_weekly_report_raw(weeks: int = Query(1, ge=1, le=12), current_user: dict = Depends(get_current_user)):
    """Get weekly digest as raw Markdown."""
    db = get_db()
    return generate_weekly_digest(db, weeks_back=weeks)


@router.get("/changelog")
async def get_changelog_report(days: int = Query(7, ge=1, le=90), current_user: dict = Depends(get_current_user)):
    """Get changelog report."""
    db = get_db()
    report = generate_changelog(db, days=days)
    return {"report": report, "format": "markdown"}


@router.get("/changelog/raw", response_class=PlainTextResponse)
async def get_changelog_report_raw(days: int = Query(7, ge=1, le=90), current_user: dict = Depends(get_current_user)):
    """Get changelog as raw Markdown."""
    db = get_db()
    return generate_changelog(db, days=days)


@router.get("/index")
async def get_tools_index_report(current_user: dict = Depends(get_current_user)):
    """Get tools index report."""
    db = get_db()
    report = generate_tools_index(db)
    return {"report": report, "format": "markdown"}


@router.get("/index/raw", response_class=PlainTextResponse)
async def get_tools_index_raw(current_user: dict = Depends(get_current_user)):
    """Get tools index as raw Markdown."""
    db = get_db()
    return generate_tools_index(db)
