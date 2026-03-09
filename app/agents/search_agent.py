"""
This module defines the search agent responsible for retrieving relevant
web results for a user query using the Tavily Search API. It is designed
to operate as a node within the research agent workflow.
"""

import uuid

from fastapi import HTTPException, status
from langchain_community.tools.tavily_search import TavilySearchResults

from app.agents.db_helpers import log_agent_start, update_agent_log
from app.agents.llm import llm
from app.agents.state import ResearchState
from app.core.config import settings
from app.db.models import AgentStatus, Source

search_tool = TavilySearchResults(max_results=5, tavily_api_key=settings.TAVILY_API_KEY)


async def search_agent(state: ResearchState) -> dict:
    """
    Search Agent Node
    - Takes the user query from the state
    - Searches the web using Tavily API
    - Computes the credibility score via an llm
    - Returns a list of relevant articles, sources and the credibility score

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
            prompt = f"""
            You are evaluating the credibility of a web search result.

            Rate the credibility of the following source on a scale from 0.0 (not credible) to 1.0 (highly credible).

            Evaluation criteria:
            - Domain reputation (e.g., well-known news sites, academic sources, official organizations)
            - Content quality (clarity, specificity, factual tone vs vague or sensational language)
            - Source type (peer-reviewed, news, blog, forum, anonymous content, etc.)

            Scoring guidelines:
            - 0.90 - 1.00: Highly credible — official organizations, government sites (.gov), peer-reviewed journals, major established news outlets
            - 0.70 - 0.89: Credible — reputable news sites, established sports/entertainment outlets, educational publishers, well-known magazines
            - 0.50 - 0.69: Somewhat credible — blogs, smaller news sites, user-generated content, unknown domains, sites with mixed content quality
            - 0.20 - 0.49: Low credibility — forums, Reddit, anonymous content, sensational or vague language, unverified sources
            - 0.00 - 0.19: Not credible — spam, misleading content, highly suspicious domains, no clear authorship


            Source information:
            Title: {result.get("title")}
            Snippet: {result.get("content")}
            Url: {result.get("url")}

            Return ONLY a single floating point number between 0.0 and 1.0 with up to 2 decimal places.
            Do not round off the ratings.

            Do not include any explanation, text, or formatting.
            """
            response = await llm.ainvoke(prompt)
            try:
                source.credibility_score = float(response.content.strip())
            except ValueError:
                source.credibility_score = None
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
