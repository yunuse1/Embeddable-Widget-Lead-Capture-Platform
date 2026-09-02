from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Submission, Widget
from app.rate_limit import submission_limiter
from app.schemas.submission import SubmissionRequest, SubmissionResponse
from app.services.geo import enrich_ip


router = APIRouter(prefix="/public", tags=["Public Submissions"])


MAX_FIELDS = 30
MAX_VALUE_LENGTH = 2000
MAX_PAYLOAD_BYTES = 32_000


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def validate_submission_data(data: dict[str, Any]) -> None:
    if len(data) > MAX_FIELDS:
        raise HTTPException(status_code=422, detail="Too many fields")

    for key, value in data.items():
        if len(key) > 100:
            raise HTTPException(status_code=422, detail="Field name is too long")
        if isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
            raise HTTPException(status_code=422, detail=f"Field '{key}' is too long")


@router.post(
    "/widgets/{public_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    public_id: str,
    request: Request,
    payload: SubmissionRequest,
    db: Session = Depends(get_db),
):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    widget = db.scalar(
        select(Widget).where(
            Widget.public_id == public_id,
            Widget.is_active.is_(True),
        )
    )
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")

    if payload.honeypot.strip():
        raise HTTPException(status_code=422, detail="Spam submission rejected")

    validate_submission_data(payload.data)

    client_ip = get_client_ip(request) or "unknown"
    rate_limit_key = f"submission:{widget.id}:{client_ip}"
    if not submission_limiter.allow(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please try again later.",
            headers={"Retry-After": "60"},
        )

    geo = enrich_ip(client_ip if client_ip != "unknown" else None)

    submission = Submission(
        widget_id=widget.id,
        data=payload.data,
        ip_address=client_ip if client_ip != "unknown" else None,
        country=geo.country,
        city=geo.city,
        geo_provider=geo.provider,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return SubmissionResponse(id=submission.id, status="accepted")
