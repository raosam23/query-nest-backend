"""
This module defines the search agent responsible for retrieving relevant
web results for a user query using the Tavily Search API. It is designed
to operate as a node within the research agent workflow.
"""

import uuid

from fastapi import HTTPException, status
from langchain_community.tools.tavily_search import TavilySearchResults

from app.agents.db_helpers import log_agent_start, update_agent_log
from app.agents.state import ResearchState
from app.core.config import settings
from app.db.models import AgentStatus, Source

search_tool = TavilySearchResults(max_results=5, tavily_api_key=settings.TAVILY_API_KEY)


async def search_agent(state: ResearchState) -> dict:
    """
    Search Agent Node
    - Takes the user query from the state
    - Searches the web using Tavily API
    - Returns a list of relevant articles and sources

    Input state: query
    Output state: search_results
    """
    db_session = state["db_session"]
    session_id = state["session_id"]
    log = await log_agent_start(db_session, session_id, "search_agent")
    user_query = state["query"]
    if not user_query:
        await update_agent_log(
            db_session,
            log.id,
            "User Query not found in the database",
            AgentStatus.FAILED,
        )
        return {"search_results": []}
    try:
        results = await search_tool.ainvoke({"query": user_query})
        if isinstance(results, str):
            # Exception caused in Tavily
            await update_agent_log(
                db_session,
                log.id,
                f"Search agent failed: {results}",
                AgentStatus.FAILED,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Search agent failed: {results}",
            )
        for result in results:
            source = Source(
                session_id=uuid.UUID(session_id),
                url=result.get("url"),
                title=result.get("title"),
                snippet=result.get("content"),
            )
            db_session.add(source)
        await db_session.commit()
        await update_agent_log(db_session, log.id, f"Found {len(results)} results")
        return {"search_results": results}
    except HTTPException:
        # We are already handling it above
        raise
    except Exception as exc:
        await update_agent_log(db_session, log.id, f"Error: {exc}", AgentStatus.FAILED)
        raise
