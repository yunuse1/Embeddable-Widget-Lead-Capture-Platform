import time
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import NotificationJob


MAX_ATTEMPTS = 5
POLL_INTERVAL_SECONDS = 2
BASE_BACKOFF_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 10
PROCESSING_TIMEOUT_SECONDS = 60


def recover_stale_jobs(db: Session) -> int:
    """Return jobs stuck in processing to the pending queue after a worker crash."""
    stale_before = datetime.now(timezone.utc) - timedelta(
        seconds=PROCESSING_TIMEOUT_SECONDS
    )

    jobs = db.scalars(
        select(NotificationJob).where(
            NotificationJob.status == "processing",
            NotificationJob.processing_started_at <= stale_before,
        )
    ).all()

    for job in jobs:
        job.status = "pending"
        job.available_at = datetime.now(timezone.utc)
        job.processing_started_at = None

    if jobs:
        db.commit()

    return len(jobs)


def claim_next_job(db: Session) -> NotificationJob | None:
    now = datetime.now(timezone.utc)

    # Lock only notification_jobs. joinedload() would add a LEFT OUTER JOIN
    # to submissions, and PostgreSQL rejects FOR UPDATE on the nullable side
    # of that join. The submission relationship is loaded after the claim.
    job = db.scalar(
        select(NotificationJob)
        .where(
            NotificationJob.status == "pending",
            NotificationJob.available_at <= now,
        )
        .order_by(NotificationJob.id)
        .with_for_update(skip_locked=True)
    )

    if job is None:
        return None

    job.status = "processing"
    job.processing_started_at = now
    db.commit()
    db.refresh(job)
    return job


def deliver_webhook(job: NotificationJob) -> None:
    webhook_url = getattr(settings, "notification_webhook_url", None)
    if not webhook_url:
        raise RuntimeError("NOTIFICATION_WEBHOOK_URL is not configured")

    response = requests.post(
        webhook_url,
        json={
            "job_id": job.id,
            "submission_id": job.submission_id,
            "data": job.submission.data,
        },
        headers={"X-Notification-Job-Id": str(job.id)},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def process_job(db: Session, job: NotificationJob) -> None:
    # A completed job must never execute its external side effect again.
    # This protects against accidental duplicate worker invocation.
    if job.status in {"processed", "failed"}:
        return

    try:
        deliver_webhook(job)
    except Exception as exc:
        job.attempts += 1
        job.last_error = str(exc)[:4000]
        job.processing_started_at = None

        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            job.processed_at = datetime.now(timezone.utc)
        else:
            delay = BASE_BACKOFF_SECONDS * (2 ** (job.attempts - 1))
            job.status = "pending"
            job.available_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay
            )

        db.commit()
        return

    job.status = "processed"
    job.processed_at = datetime.now(timezone.utc)
    job.processing_started_at = None
    job.last_error = None
    db.commit()


def run_worker() -> None:
    print("Notification worker started")

    while True:
        db = SessionLocal()
        try:
            recover_stale_jobs(db)
            job = claim_next_job(db)
            if job is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            process_job(db, job)
        except Exception as exc:
            db.rollback()
            print(f"Worker error: {exc}")
        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
