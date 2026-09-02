from types import SimpleNamespace

from app.models import Submission
from app.routers import submissions


class FakeScalarDB:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.refreshed = []

    def scalar(self, query):
        return self.existing

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushes += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None and isinstance(obj, Submission):
                obj.id = 42

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_get_idempotency_key_accepts_and_normalizes_header():
    request = SimpleNamespace(headers={"Idempotency-Key": "  checkout-123  "})

    assert submissions.get_idempotency_key(request) == "checkout-123"


def test_get_idempotency_key_rejects_empty_header():
    request = SimpleNamespace(headers={"Idempotency-Key": "   "})

    assert submissions.get_idempotency_key(request) is None


def test_duplicate_submission_can_be_detected_before_insert():
    existing = SimpleNamespace(id=42)
    db = FakeScalarDB(existing=existing)
    request = SimpleNamespace(headers={"Idempotency-Key": "checkout-123"})

    key = submissions.get_idempotency_key(request)
    result = db.scalar(None)

    assert key == "checkout-123"
    assert result.id == 42
    assert db.added == []
    assert db.commits == 0


def test_idempotency_key_is_stored_on_submission():
    submission = Submission(
        widget_id=7,
        data={"email": "lead@example.com"},
        idempotency_key="checkout-123",
    )

    assert submission.idempotency_key == "checkout-123"
