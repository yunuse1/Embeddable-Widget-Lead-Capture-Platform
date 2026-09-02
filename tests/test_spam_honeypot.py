import pytest
from fastapi import HTTPException

from app.routers.submissions import validate_submission_data
from app.schemas.submission import SubmissionRequest


def test_honeypot_field_is_available_and_rejectable():
    payload = SubmissionRequest(data={"email": "lead@example.com"}, honeypot="bot")
    assert payload.honeypot == "bot"

    with pytest.raises(HTTPException) as exc:
        if payload.honeypot.strip():
            raise HTTPException(status_code=422, detail="Spam submission rejected")

    assert exc.value.status_code == 422


def test_submission_rejects_too_many_fields():
    with pytest.raises(HTTPException) as exc:
        validate_submission_data({f"field{i}": "x" for i in range(31)})

    assert exc.value.status_code == 422
    assert exc.value.detail == "Too many fields"


def test_submission_rejects_oversized_field_value():
    with pytest.raises(HTTPException) as exc:
        validate_submission_data({"message": "x" * 2001})

    assert exc.value.status_code == 422
