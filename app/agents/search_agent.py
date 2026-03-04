from app.core.config import settings
from app.agents.state import ResearchState
from fastapi import HTTPException, status
from langchain_community.tools.tavily_search import TavilySearchResults

search_tool = TavilySearchResults(max_results=5, tavily_api_key=settings.TAVILY_API_KEY)

async def search_agent(state: ResearchState) -> dict:
    '''
    Search Agent Node
    - Takes the user query from the state
    - Searches the web using Tavily API
    - Returns a list of relevant articles and sources

    Input state: query
    Output state: search_results
    '''
    user_query = state['query']
    if not user_query:
        return {'search_results': []}
    results = await search_tool.ainvoke({'query': user_query})
    if isinstance(results, str):
        # Exception caused in Tavily
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f'Search agent failed: {results}')
    return {'search_results': results}