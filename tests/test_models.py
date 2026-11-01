"""SQLModel tables and status enums."""

from app.db.models import AgentLog, AgentStatus, SessionStatus, Source
from tests.factories import make_agent_log, make_research_session, make_user


def test_session_and_agent_status_values() -> None:
    assert SessionStatus.PENDING == "pending"
    assert SessionStatus.RUNNING == "running"
    assert SessionStatus.DONE == "done"
    assert SessionStatus.FAILED == "failed"
    assert AgentStatus.RUNNING == "running"
    assert AgentStatus.DONE == "done"
    assert AgentStatus.FAILED == "failed"


def test_research_rows_keep_the_fields_the_api_returns() -> None:
    user = make_user()
    research = make_research_session(user)

    assert research.user_id == user.id
    assert research.status == SessionStatus.PENDING
    assert research.final_report is None
    assert research.completed_at is None

    source = Source(
        session_id=research.id,
        url="https://www.iaea.org/fusion",
        title="IAEA",
        snippet="Fusion research",
        credibility_score=0.91,
    )
    log = make_agent_log(research.id, agent_name="writer_agent")

    assert source.credibility_score == 0.91
    assert isinstance(log, AgentLog)
    assert log.status == AgentStatus.RUNNING
    assert log.output is None
    assert log.completed_at is None
