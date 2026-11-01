"""History HTTP routes."""

import uuid

from fastapi.testclient import TestClient

from tests.factories import make_research_session, scalar_result


def test_list_history_returns_the_callers_sessions(auth_client: TestClient, mock_session, mock_user) -> None:
    rows = [make_research_session(mock_user, query="one"), make_research_session(mock_user, query="two")]
    mock_session.execute.return_value = scalar_result(rows, many=True)

    response = auth_client.get("/history/")

    assert response.status_code == 200
    assert [item["query"] for item in response.json()] == ["one", "two"]


def test_list_history_can_be_empty(auth_client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result([], many=True)

    response = auth_client.get("/history/")

    assert response.status_code == 200
    assert response.json() == []


def test_delete_history_returns_the_service_payload(auth_client: TestClient, mock_session, mock_user) -> None:
    research = make_research_session(mock_user)
    mock_session.execute.return_value = scalar_result(research)

    response = auth_client.delete(f"/history/{research.id}")

    assert response.status_code == 200
    assert response.json() == {"status": 200, "msg": "Session deleted successfully"}
    mock_session.delete.assert_awaited_once_with(research)
    mock_session.commit.assert_awaited()


def test_delete_history_returns_404_when_the_session_is_missing(auth_client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result(None)

    response = auth_client.delete(f"/history/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"
