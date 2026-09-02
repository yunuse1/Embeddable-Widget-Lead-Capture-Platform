from types import SimpleNamespace

from app.models import NotificationJob, Submission
from app.routers import submissions
from app.schemas.submission import SubmissionRequest


class FakeRequest:
    def __init__(self, key: str | None):
        self.headers = {}
        if key is not None:
            self.headers["Idempotency-Key"] = key
        self.client = SimpleNamespace(host="127.0.0.1")


class FakeDB:
    def __init__(self, widget):
        self.widget = widget
        self.submission = None
        self.notification_jobs = []
        self.added = []
        self.commits = 0
        self.flushes = 0

    def scalar(self, query):
        statement = str(query)
        if "widgets" in statement:
            return self.widget
        return self.submission

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushes += 1
        for obj in self.added:
            if isinstance(obj, Submission) and obj.id is None:
                obj.id = 42
                self.submission = obj
            elif isinstance(obj, NotificationJob) and obj not in self.notification_jobs:
                self.notification_jobs.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def refresh(self, obj):
        pass


def test_get_idempotency_key_accepts_and_normalizes_header():
    request = FakeRequest("  checkout-123  ")

    assert submissions.get_idempotency_key(request) == "checkout-123"


def test_get_idempotency_key_rejects_empty_header():
    request = FakeRequest("   ")

    assert submissions.get_idempotency_key(request) is None


def test_idempotency_key_is_stored_on_submission():
    submission = Submission(
        widget_id=7,
        data={"email": "lead@example.com"},
        idempotency_key="checkout-123",
    )

    assert submission.idempotency_key == "checkout-123"


def test_duplicate_requests_create_one_submission_and_one_notification_job(monkeypatch):
    widget = SimpleNamespace(id=7, public_id="widget-123", is_active=True)
    db = FakeDB(widget)
    payload = SubmissionRequest(
        data={"email": "lead@example.com", "name": "Test Lead"}
    )

    monkeypatch.setattr(
        submissions.submission_limiter,
        "allow",
        lambda _key: True,
    )
    monkeypatch.setattr(
        submissions,
        "enrich_ip",
        lambda _ip: SimpleNamespace(country=None, city=None, provider=None),
    )

    first = submissions.create_submission(
        public_id="widget-123",
        request=FakeRequest("checkout-123"),
        payload=payload,
        db=db,
    )
    second = submissions.create_submission(
        public_id="widget-123",
        request=FakeRequest("checkout-123"),
        payload=payload,
        db=db,
    )

    assert first.id == second.id == 42
    assert first.status == second.status == "accepted"
    assert db.commits == 1
    assert len([obj for obj in db.added if isinstance(obj, Submission)]) == 1
    assert len([obj for obj in db.added if isinstance(obj, NotificationJob)]) == 1
    assert db.submission.idempotency_key == "checkout-123"
