import pytest
from fastapi import HTTPException

from app.routers.submissions import (
    MAX_FIELDS,
    MAX_PAYLOAD_BYTES,
    MAX_VALUE_LENGTH,
    validate_submission_data,
)


def test_public_submission_validation_limits_are_explicit():
    assert MAX_PAYLOAD_BYTES == 32_000
    assert MAX_FIELDS == 30
    assert MAX_VALUE_LENGTH == 2_000


def test_public_submission_rejects_long_field_name():
    with pytest.raises(HTTPException) as exc:
        validate_submission_data({"x" * 101: "value"})

    assert exc.value.status_code == 422
    assert exc.value.detail == "Field name is too long"
