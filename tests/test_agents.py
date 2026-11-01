"""Search, summarizer, fact checker, writer, and the rule-based supervisor."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.agents import fact_checker, llm as llm_module, search_agent, summarizer_agent, writer_agent
from app.agents.fact_checker import fact_checker_agent
from app.agents.search_agent import search_agent as run_search
from app.agents.summarizer_agent import summarizer_agent as run_summarizer
from app.agents.supervisor import route, supervisor
from app.agents.writer_agent import writer_agent as run_writer
from app.core.config import settings
from app.db.models import AgentStatus, Source
from tests.factories import LLMResponse, make_agent_log, make_state


def _patch_logs(monkeypatch: pytest.MonkeyPatch, module: object, agent_name: str) -> AsyncMock:
    log = make_agent_log(agent_name=agent_name)
    monkeypatch.setattr(module, "log_agent_start", AsyncMock(return_value=log))
    update = AsyncMock()
    monkeypatch.setattr(module, "update_agent_log", update)
    return update


def _patch_llm(monkeypatch: pytest.MonkeyPatch, module: object, ainvoke: AsyncMock) -> MagicMock:
    """Replace the module-level ChatOpenAI. Its methods are not pydantic fields."""
    llm = MagicMock()
    llm.ainvoke = ainvoke
    monkeypatch.setattr(module, "llm", llm)
    return llm


def _patch_search_tool(monkeypatch: pytest.MonkeyPatch, ainvoke: AsyncMock) -> MagicMock:
    tool = MagicMock()
    tool.ainvoke = ainvoke
    monkeypatch.setattr(search_agent, "search_tool", tool)
    return tool


def test_chat_model_is_gpt_4o_mini_and_reads_the_settings_key() -> None:
    assert llm_module.llm.model_name == "gpt-4o-mini"
    assert llm_module.llm.temperature == 0.0
    assert llm_module.llm.openai_api_key() == settings.OPENAI_API_KEY


def test_search_tool_requests_five_tavily_results() -> None:
    assert search_agent.search_tool.max_results == 5


@pytest.mark.asyncio
async def test_search_agent_fails_when_the_query_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, search_agent, "search_agent")
    state = make_state(query="")

    result = await run_search(state)

    assert result == {"search_results": []}
    assert update.await_args.args[2] == "User Query not found in the database"
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_search_agent_turns_a_tavily_error_string_into_503(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, search_agent, "search_agent")
    _patch_search_tool(monkeypatch, AsyncMock(return_value="unauthorized"))
    state = make_state()

    with pytest.raises(HTTPException) as exc:
        await run_search(state)

    assert exc.value.status_code == 503
    assert "unauthorized" in exc.value.detail
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_search_agent_scores_sources_and_stores_them(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, search_agent, "search_agent")
    results = [
        {"url": "https://www.iaea.org/fusion", "title": "IAEA", "content": "Official fusion brief"},
        {"url": "https://example.com/blog", "title": "Blog", "content": "A vague post"},
    ]
    _patch_search_tool(monkeypatch, AsyncMock(return_value=results))
    _patch_llm(
        monkeypatch,
        search_agent,
        AsyncMock(side_effect=[LLMResponse("0.93"), LLMResponse("not a score")]),
    )
    state = make_state()

    returned = await run_search(state)

    assert returned == {"search_results": results}
    sources = [call.args[0] for call in state["db_session"].add.call_args_list]
    assert all(isinstance(source, Source) for source in sources)
    assert sources[0].url == "https://www.iaea.org/fusion"
    assert sources[0].title == "IAEA"
    assert sources[0].snippet == "Official fusion brief"
    assert sources[0].credibility_score == 0.93
    assert sources[1].credibility_score is None
    assert str(sources[0].session_id) == state["session_id"]
    state["db_session"].commit.assert_awaited()
    prompt = search_agent.llm.ainvoke.await_args_list[0].args[0]
    assert "IAEA" in prompt
    assert "https://www.iaea.org/fusion" in prompt
    assert update.await_args.args[2] == "Found 2 results"


@pytest.mark.asyncio
async def test_search_agent_accepts_an_empty_result_list(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, search_agent, "search_agent")
    _patch_search_tool(monkeypatch, AsyncMock(return_value=[]))
    state = make_state()

    result = await run_search(state)

    assert result == {"search_results": []}
    assert update.await_args.args[2] == "Found 0 results"
    state["db_session"].add.assert_not_called()


@pytest.mark.asyncio
async def test_search_agent_records_and_reraises_tool_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, search_agent, "search_agent")
    _patch_search_tool(monkeypatch, AsyncMock(side_effect=RuntimeError("tavily down")))
    state = make_state()

    with pytest.raises(RuntimeError, match="tavily down"):
        await run_search(state)

    assert "tavily down" in update.await_args.args[2]
    assert update.await_args.args[3] == AgentStatus.FAILED
    state["db_session"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_summarizer_fails_when_there_are_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, summarizer_agent, "summarizer_agent")

    result = await run_summarizer(make_state(search_results=[]))

    assert result == {"key_claims": []}
    assert update.await_args.args[2] == "Search results are empty"
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_summarizer_returns_the_model_text_as_one_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, summarizer_agent, "summarizer_agent")
    _patch_llm(monkeypatch, summarizer_agent, AsyncMock(return_value=LLMResponse("1. Fusion is experimental.")))
    state = make_state(search_results=[{"title": "IAEA", "content": "brief"}])

    result = await run_summarizer(state)

    assert result == {"key_claims": ["1. Fusion is experimental."]}
    assert "brief" in summarizer_agent.llm.ainvoke.await_args.args[0]
    assert update.await_args.args[2] == "Extracted key claims succesfully"


@pytest.mark.asyncio
async def test_summarizer_records_model_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, summarizer_agent, "summarizer_agent")
    _patch_llm(monkeypatch, summarizer_agent, AsyncMock(side_effect=RuntimeError("model down")))

    with pytest.raises(RuntimeError, match="model down"):
        await run_summarizer(make_state(search_results=[{"title": "IAEA"}]))

    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_fact_checker_reports_when_there_are_no_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, fact_checker, "fact_checker_agent")

    result = await fact_checker_agent(make_state(key_claims=[]))

    assert result == {"fact_check_report": {"report": "no claims to check"}}
    assert update.await_args.args[2] == "No claims to check"
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_fact_checker_stores_the_model_text(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, fact_checker, "fact_checker_agent")
    _patch_llm(monkeypatch, fact_checker, AsyncMock(return_value=LLMResponse("claim 1: verified")))
    state = make_state(key_claims=["Fusion is experimental."])

    result = await fact_checker_agent(state)

    assert result == {"fact_check_report": {"report": "claim 1: verified"}}
    assert "Fusion is experimental." in fact_checker.llm.ainvoke.await_args.args[0]
    assert "1 claims evaluated" in update.await_args.args[2]


@pytest.mark.asyncio
async def test_fact_checker_records_model_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, fact_checker, "fact_checker_agent")
    _patch_llm(monkeypatch, fact_checker, AsyncMock(side_effect=RuntimeError("model down")))

    with pytest.raises(RuntimeError, match="model down"):
        await fact_checker_agent(make_state(key_claims=["a claim"]))

    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"key_claims": [], "fact_check_report": {"report": "verified"}},
        {"key_claims": ["a claim"], "fact_check_report": {}},
    ],
)
async def test_writer_stops_when_the_inputs_are_missing(monkeypatch: pytest.MonkeyPatch, overrides: dict) -> None:
    update = _patch_logs(monkeypatch, writer_agent, "writer_agent")

    result = await run_writer(make_state(**overrides))

    assert result == {"final_report": "Insufficient information to generate a report"}
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_writer_returns_a_fallback_when_the_model_returns_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, writer_agent, "writer_agent")
    _patch_llm(monkeypatch, writer_agent, AsyncMock(return_value=None))

    result = await run_writer(make_state(key_claims=["a claim"], fact_check_report={"report": "verified"}))

    assert result == {"final_report": "Failed to generate report"}
    assert update.await_args.args[2] == "Failed to generate report"
    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_writer_returns_the_report_text(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, writer_agent, "writer_agent")
    _patch_llm(monkeypatch, writer_agent, AsyncMock(return_value=LLMResponse("Summary\n\nConclusion")))
    state = make_state(
        query="What is nuclear fusion?",
        key_claims=["Fusion is experimental."],
        fact_check_report={"report": "verified"},
    )

    result = await run_writer(state)

    assert result == {"final_report": "Summary\n\nConclusion"}
    prompt = writer_agent.llm.ainvoke.await_args.args[0]
    assert "What is nuclear fusion?" in prompt
    assert "Fusion is experimental." in prompt
    assert "verified" in prompt
    assert "Length: 19 characters" in update.await_args.args[2]


@pytest.mark.asyncio
async def test_writer_records_model_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    update = _patch_logs(monkeypatch, writer_agent, "writer_agent")
    _patch_llm(monkeypatch, writer_agent, AsyncMock(side_effect=RuntimeError("model down")))

    with pytest.raises(RuntimeError, match="model down"):
        await run_writer(make_state(key_claims=["a claim"], fact_check_report={"report": "verified"}))

    assert update.await_args.args[3] == AgentStatus.FAILED


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "search"),
        ({"search_results": [{"url": "https://www.iaea.org"}]}, "summarize"),
        ({"search_results": [{"url": "https://www.iaea.org"}], "key_claims": ["claim"]}, "fact_check"),
        (
            {
                "search_results": [{"url": "https://www.iaea.org"}],
                "key_claims": ["claim"],
                "fact_check_report": {"report": "verified"},
            },
            "write",
        ),
        (
            {
                "search_results": [{"url": "https://www.iaea.org"}],
                "key_claims": ["claim"],
                "fact_check_report": {"report": "verified"},
                "final_report": "done",
            },
            "end",
        ),
    ],
)
def test_supervisor_routes_from_the_first_missing_piece(overrides: dict, expected: str) -> None:
    decision = supervisor(make_state(**overrides))

    assert decision == {"next": expected}


def test_route_returns_the_supervisor_decision() -> None:
    assert route(make_state(next="write")) == "write"
