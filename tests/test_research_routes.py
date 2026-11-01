"""Research HTTP routes. The graph itself is not executed here."""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.db.models import Source
from tests.factories import make_research_session, scalar_result


def test_start_research_returns_a_pending_session_and_schedules_the_graph(
    auth_client: TestClient,
    mock_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled = AsyncMock()
    monkeypatch.setattr("app.api.routes.research.run_research_graph", scheduled)

    response = auth_client.post("/research/", json={"query": "What is nuclear fusion?"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "What is nuclear fusion?"
    assert body["status"] == "pending"
    assert body["final_report"] is None
    assert body["created_at"] is not None
    scheduled.assert_awaited_once_with(body["id"])


def test_start_research_rejects_a_blank_query(auth_client: TestClient) -> None:
    response = auth_client.post("/research/", json={"query": ""})

    assert response.status_code == 422


def test_get_research_returns_the_session(auth_client: TestClient, mock_session, mock_user) -> None:
    research = make_research_session(mock_user, final_report="The report")
    mock_session.execute.return_value = scalar_result(research)

    response = auth_client.get(f"/research/{research.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(research.id)
    assert body["query"] == research.query
    assert body["status"] == "pending"
    assert body["final_report"] == "The report"


def test_get_research_returns_404_when_the_session_is_missing(auth_client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result(None)

    response = auth_client.get(f"/research/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_get_sources_returns_saved_rows(auth_client: TestClient, mock_session, mock_user) -> None:
    research = make_research_session(mock_user)
    source = Source(
        session_id=research.id,
        url="https://www.iaea.org/fusion",
        title="IAEA",
        snippet="Fusion research",
        credibility_score=0.95,
    )
    mock_session.execute.side_effect = [scalar_result(research), scalar_result([source], many=True)]

    response = auth_client.get(f"/research/{research.id}/sources")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(source.id),
            "url": "https://www.iaea.org/fusion",
            "title": "IAEA",
            "snippet": "Fusion research",
            "credibility_score": 0.95,
        }
    ]


def test_get_sources_returns_404_when_the_session_is_missing(auth_client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result(None)

    response = auth_client.get(f"/research/{uuid.uuid4()}/sources")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_get_sources_can_be_empty(auth_client: TestClient, mock_session, mock_user) -> None:
    research = make_research_session(mock_user)
    mock_session.execute.side_effect = [scalar_result(research), scalar_result([], many=True)]

    response = auth_client.get(f"/research/{research.id}/sources")

    assert response.status_code == 200
    assert response.json() == []
