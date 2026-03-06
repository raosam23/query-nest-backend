"""
Summarizer Agent Module.

This module provides the summarizer_agent function, which processes search
results and extracts key claims using an LLM.
"""

from app.agents.db_helpers import log_agent_start, update_agent_log
from app.agents.llm import llm
from app.agents.state import ResearchState
from app.db.models import AgentStatus


async def summarizer_agent(state: ResearchState) -> dict:
    """
    Summarizer Agent Node

    - Takes the search_results from the state
    - passes the info to the llm which extracts key claims as a list
    - And returns the list of key claims

    Input state: search_results
    Output state: key_claims
    """
    db_session = state["db_session"]
    session_id = state["session_id"]
    log = await log_agent_start(db_session, session_id, "summarizer_agent")
    search_result = state["search_results"]
    if not search_result:
        await update_agent_log(
            db_session, log.id, "Search results are empty", AgentStatus.FAILED
        )
        return {"key_claims": []}
    prompt = f"""
        You are an agent specialized in summarizing the results given by the search_agent.
        Information gotten by the search_agent is passed to you and you have to summarize it
        and then extract 5-6 key claims as a numbered list.
        The given search_result is: {search_result}
    """
    try:
        response = await llm.ainvoke(prompt)
        await update_agent_log(db_session, log.id, "Extracted key claims succesfully")
        return {"key_claims": [response.content]}
    except Exception as exc:
        await update_agent_log(db_session, log.id, f"Error: {exc}", AgentStatus.FAILED)
        raise
