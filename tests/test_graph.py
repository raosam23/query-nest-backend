"""Compiled research graph: wiring, a full mocked run, and the empty-search loop."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.graph.builder import build_graph
from tests.factories import make_state


def test_build_graph_wires_every_agent_back_to_the_supervisor() -> None:
    drawn = build_graph().get_graph()
    nodes = set(drawn.nodes)
    edges = {(edge.source, edge.target) for edge in drawn.edges}

    assert {"supervisor", "search", "summarize", "fact_check", "write"} <= nodes
    assert ("__start__", "supervisor") in edges
    assert ("supervisor", "__end__") in edges
    for node in ("search", "summarize", "fact_check", "write"):
        assert (node, "supervisor") in edges
        assert ("supervisor", node) in edges


def _patch_agents(monkeypatch: pytest.MonkeyPatch, **nodes: Callable[..., Awaitable[dict[str, Any]]]) -> None:
    for name, function in nodes.items():
        monkeypatch.setattr(f"app.graph.builder.{name}", function)


@pytest.mark.asyncio
async def test_graph_runs_search_then_summary_then_fact_check_then_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def fake_search(state: dict[str, Any]) -> dict[str, Any]:
        seen.append("search")
        return {"search_results": [{"url": "https://www.iaea.org/fusion", "title": "IAEA", "content": "brief"}]}

    async def fake_summarize(state: dict[str, Any]) -> dict[str, Any]:
        seen.append("summarize")
        assert state["search_results"][0]["title"] == "IAEA"
        return {"key_claims": ["Fusion is experimental."]}

    async def fake_fact_check(state: dict[str, Any]) -> dict[str, Any]:
        seen.append("fact_check")
        assert state["key_claims"] == ["Fusion is experimental."]
        return {"fact_check_report": {"report": "verified"}}

    async def fake_write(state: dict[str, Any]) -> dict[str, Any]:
        seen.append("write")
        assert state["fact_check_report"] == {"report": "verified"}
        return {"final_report": "Summary of the findings."}

    _patch_agents(
        monkeypatch,
        search_agent=fake_search,
        summarizer_agent=fake_summarize,
        fact_checker_agent=fake_fact_check,
        writer_agent=fake_write,
    )

    result = await build_graph().ainvoke(make_state())

    assert seen == ["search", "summarize", "fact_check", "write"]
    assert result["final_report"] == "Summary of the findings."
    assert result["next"] == "end"


@pytest.mark.asyncio
async def test_graph_retries_empty_search_once_then_finishes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def empty_search(state: dict[str, Any]) -> dict[str, Any]:
        return {"search_results": [], "search_attempts": state["search_attempts"] + 1}

    _patch_agents(monkeypatch, search_agent=empty_search)

    result = await build_graph().ainvoke(make_state())

    assert result["search_attempts"] == 2
    assert result["next"] == "end"
    assert "No sources found" in result["final_report"]
