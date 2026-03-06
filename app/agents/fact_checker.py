"""
This module contains the fact_checker_agent, which cross-references key claims
using an LLM to identify contradictions and rate each claim's validity.
"""

from app.agents.db_helpers import log_agent_start, update_agent_log
from app.agents.llm import llm
from app.agents.state import ResearchState
from app.db.models import AgentStatus


async def fact_checker_agent(state: ResearchState) -> dict:
    """
    Fact Checker Node

    - Takes the key claims from the state
    - takes the key claims given, passes to the llm and the llm cross-references them, identifies any contradictions and rate each claims
    - returns the report as a dict

    Input state: key_claims
    Output state: fact_check_report
    """
    db_session = state["db_session"]
    session_id = state["session_id"]
    log = await log_agent_start(db_session, session_id, "fact_checker_agent")
    key_claims = state["key_claims"]
    if not key_claims:
        await update_agent_log(
            db_session, log.id, "No claims to check", AgentStatus.FAILED
        )
        return {"fact_check_report": {"report": "no claims to check"}}
    prompt = f"""
        You are a fact cheker agent, that is gonna take the key_claims given by the key claims agent
        and then cross-reference them, identify any contradictions and rate each claims as
        'verified', 'contradicted', or 'uncertain'
        Here are the key claims: {key_claims}
    """
    try:
        response = await llm.ainvoke(prompt)
        await update_agent_log(
            db_session,
            log.id,
            f"Fact check complete: {len(key_claims)} claims evaluated",
        )
        return {"fact_check_report": {"report": response.content}}
    except Exception as exc:
        await update_agent_log(db_session, log.id, f"Error: {exc}", AgentStatus.FAILED)
        raise
