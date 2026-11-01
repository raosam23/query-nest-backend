"""Pydantic request and response models declared on the routes."""

import uuid

import pytest
from pydantic import ValidationError

from app.api.routes.auth import AuthRequest, LoginResponse, RegisterResponse
from app.api.routes.history import DeleteResponse
from app.api.routes.research import ResearchRequest, ResearchResponse, SourceResponse
from app.db.models import SessionStatus


def test_auth_request_requires_email_and_password() -> None:
    with pytest.raises(ValidationError):
        AuthRequest(email="ada@example.com")  # type: ignore[call-arg]

    parsed = AuthRequest(email="ada@example.com", password="secret-password")

    assert parsed.email == "ada@example.com"
    assert parsed.password == "secret-password"


def test_login_and_register_responses_keep_the_declared_fields() -> None:
    login = LoginResponse(access_token="abc", token_type="bearer")
    registered = RegisterResponse(message="Account created successfully", email="ada@example.com")

    assert login.model_dump() == {"access_token": "abc", "token_type": "bearer"}
    assert registered.email == "ada@example.com"


def test_research_request_rejects_a_blank_query() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(query="")

    parsed = ResearchRequest(query="What is nuclear fusion?")

    assert parsed.query == "What is nuclear fusion?"


def test_research_response_defaults_report_and_timestamp_to_none() -> None:
    session_id = uuid.uuid4()
    parsed = ResearchResponse(id=session_id, query="fusion", status=SessionStatus.PENDING)

    assert parsed.final_report is None
    assert parsed.created_at is None
    assert parsed.status == SessionStatus.PENDING


def test_source_response_allows_missing_source_fields() -> None:
    parsed = SourceResponse(id=uuid.uuid4())

    assert parsed.url is None
    assert parsed.title is None
    assert parsed.snippet is None
    assert parsed.credibility_score is None


def test_delete_response_carries_the_status_and_message() -> None:
    parsed = DeleteResponse(status=200, msg="Session deleted successfully")

    assert parsed.model_dump() == {"status": 200, "msg": "Session deleted successfully"}
