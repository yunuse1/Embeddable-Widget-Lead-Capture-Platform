from datetime import datetime, timedelta, timezone

from app.models import NotificationJob, Submission
from app.services import notification_worker


class FakeQuery:
    def __init__(self, job):
        self.job = job

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def with_for_update(self, *args, **kwargs):
        return self


class FakeDB:
    def __init__(self, job):
        self.job = job
        self.commits = 0

    def scalar(self, query):
        return self.job

    def scalars(self, query):
        class Result:
            def all(inner_self):
                if (
                    self.job.status == "processing"
                    and self.job.processing_started_at is not None
                    and self.job.processing_started_at
                    <= datetime.now(timezone.utc)
                    - timedelta(seconds=notification_worker.PROCESSING_TIMEOUT_SECONDS)
                ):
                    return [self.job]
                return []

        return Result()

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        return None


def make_job():
    submission = Submission(
        id=1,
        widget_id=1,
        data={"email": "lead@example.com", "name": "Test Lead"},
    )
    job = NotificationJob(
        id=1,
        submission_id=1,
        job_type="webhook",
        status="pending",
        attempts=0,
        available_at=datetime.now(timezone.utc),
        submission=submission,
    )
    return job


def test_claim_next_job_moves_pending_job_to_processing():
    job = make_job()
    db = FakeDB(job)

    result = notification_worker.claim_next_job(db)

    assert result is job
    assert job.status == "processing"
    assert job.processing_started_at is not None
    assert db.commits == 1


def test_stale_processing_job_is_returned_to_pending():
    job = make_job()
    job.status = "processing"
    job.processing_started_at = datetime.now(timezone.utc) - timedelta(
        seconds=notification_worker.PROCESSING_TIMEOUT_SECONDS + 1
    )
    db = FakeDB(job)

    recovered = notification_worker.recover_stale_jobs(db)

    assert recovered == 1
    assert job.status == "pending"
    assert job.processing_started_at is None
    assert job.available_at <= datetime.now(timezone.utc)
    assert db.commits == 1


def test_non_stale_processing_job_is_not_recovered():
    job = make_job()
    job.status = "processing"
    job.processing_started_at = datetime.now(timezone.utc)
    db = FakeDB(job)

    recovered = notification_worker.recover_stale_jobs(db)

    assert recovered == 0
    assert job.status == "processing"
    assert job.processing_started_at is not None
    assert db.commits == 0


def test_failed_delivery_keeps_job_retryable_and_submission_intact(monkeypatch):
    job = make_job()

    def fail_delivery(_job):
        raise RuntimeError("webhook unavailable")

    monkeypatch.setattr(notification_worker, "deliver_webhook", fail_delivery)

    class DB:
        def commit(self):
            pass

    db = DB()
    notification_worker.process_job(db, job)

    assert job.submission.id == 1
    assert job.submission.data["email"] == "lead@example.com"
    assert job.status == "pending"
    assert job.attempts == 1
    assert job.last_error == "webhook unavailable"
    assert job.processed_at is None
    assert job.processing_started_at is None
    assert job.available_at > datetime.now(timezone.utc)


def test_successful_delivery_marks_job_processed(monkeypatch):
    job = make_job()

    monkeypatch.setattr(notification_worker, "deliver_webhook", lambda _job: None)

    class DB:
        def commit(self):
            pass

    db = DB()
    notification_worker.process_job(db, job)

    assert job.status == "processed"
    assert job.attempts == 0
    assert job.last_error is None
    assert job.processed_at is not None
    assert job.processing_started_at is None


def test_failed_delivery_is_permanently_failed_after_max_attempts(monkeypatch):
    job = make_job()
    job.attempts = notification_worker.MAX_ATTEMPTS - 1

    def fail_delivery(_job):
        raise RuntimeError("webhook unavailable")

    monkeypatch.setattr(notification_worker, "deliver_webhook", fail_delivery)

    class DB:
        def commit(self):
            pass

    db = DB()
    notification_worker.process_job(db, job)

    assert job.status == "failed"
    assert job.attempts == notification_worker.MAX_ATTEMPTS
    assert job.last_error == "webhook unavailable"
    assert job.processed_at is not None
    assert job.processing_started_at is None


def test_processed_job_does_not_trigger_webhook_again(monkeypatch):
    job = make_job()
    job.status = "processed"
    job.processed_at = datetime.now(timezone.utc)

    calls = 0

    def track_delivery(_job):
        nonlocal calls
        calls += 1

    monkeypatch.setattr(notification_worker, "deliver_webhook", track_delivery)

    class DB:
        def commit(self):
            raise AssertionError("processed job should not be committed again")

    notification_worker.process_job(DB(), job)

    assert calls == 0
    assert job.status == "processed"
