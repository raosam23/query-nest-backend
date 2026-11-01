"""
Supervisor module.

Contains the supervisor node config and routing functions to coordinate the research pipeline.
"""

from app.agents.state import ResearchState

NO_SOURCES_REPORT = "No sources found for this query after retrying the search."
NO_CLAIMS_REPORT = "Unable to extract key claims from the search results after retrying."
GIVE_UP_REPORTS = frozenset({NO_SOURCES_REPORT, NO_CLAIMS_REPORT})


def supervisor(state: ResearchState) -> dict:
    """
    Supervisor Node

    Acts as the orchestrator of the research pipeline.
    Reads the current state and decides which agent should run next
    based on what data is missing.

    - No search_result -> route to search agent, then end after one retry
    - No key_claims -> route to summarizer agent, then end after one retry
    - No fact_check_report -> route to fact_checker agent
    - No final_report -> route to writer agent
    - Everything done -> end of the graph

    Input State: full state
    Output State: next (routing decision)
    """
    if not state["search_results"] and state.get("search_attempts", 0) < 2:
        return {"next": "search"}
    if not state["search_results"]:
        return {"next": "end", "final_report": NO_SOURCES_REPORT}
    if not state["key_claims"] and state.get("summarizer_attempts", 0) < 2:
        return {"next": "summarize"}
    if not state["key_claims"]:
        return {"next": "end", "final_report": NO_CLAIMS_REPORT}
    if not state["fact_check_report"]:
        return {"next": "fact_check"}
    if not state["final_report"]:
        return {"next": "write"}
    return {"next": "end"}


def route(state: ResearchState):
    """
    Route function for LangGraph conditional edges.
    Returns the next node name from state for LangGraph to navigate to.
    """
    return state["next"]
