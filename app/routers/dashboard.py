from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Submission, User, Widget


router = APIRouter(prefix="/dashboard", tags=["Owner Dashboard"])


@router.get("/submissions")
def list_submissions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Submission)
        .join(Widget, Submission.widget_id == Widget.id)
        .where(Widget.tenant_id == current_user.tenant_id)
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    total = db.scalar(
        select(func.count(Submission.id))
        .join(Widget, Submission.widget_id == Widget.id)
        .where(Widget.tenant_id == current_user.tenant_id)
    ) or 0

    return {
        "total": total,
        "items": [
            {
                "id": submission.id,
                "widget_id": submission.widget_id,
                "data": submission.data,
                "ip_address": submission.ip_address,
                "country": submission.country,
                "city": submission.city,
                "geo_provider": submission.geo_provider,
                "created_at": submission.created_at,
            }
            for submission in rows
        ],
    }


@router.get("/stats")
def submission_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = (
        select(Submission)
        .join(Widget, Submission.widget_id == Widget.id)
        .where(
            Widget.tenant_id == current_user.tenant_id,
            Submission.created_at >= since,
        )
    )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    daily_rows = db.execute(
        select(
            func.date(Submission.created_at).label("date"),
            func.count(Submission.id).label("count"),
        )
        .join(Widget, Submission.widget_id == Widget.id)
        .where(
            Widget.tenant_id == current_user.tenant_id,
            Submission.created_at >= since,
        )
        .group_by(func.date(Submission.created_at))
        .order_by(func.date(Submission.created_at))
    ).all()

    return {
        "period_days": days,
        "total_submissions": total,
        "daily": [
            {"date": str(row.date), "count": row.count}
            for row in daily_rows
        ],
    }


@router.get("/geo")
def geo_breakdown(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.execute(
        select(
            Submission.country,
            Submission.city,
            func.count(Submission.id).label("count"),
        )
        .join(Widget, Submission.widget_id == Widget.id)
        .where(
            Widget.tenant_id == current_user.tenant_id,
            Submission.created_at >= since,
        )
        .group_by(Submission.country, Submission.city)
        .order_by(func.count(Submission.id).desc())
    ).all()

    return {
        "period_days": days,
        "breakdown": [
            {
                "country": row.country,
                "city": row.city,
                "count": row.count,
            }
            for row in rows
        ],
    }
