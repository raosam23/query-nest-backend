from app.agents.llm import llm
from app.agents.state import ResearchState
from langchain_openai import ChatOpenAI

async def summarizer_agent(state: ResearchState) -> dict:
    search_result = state['search_results']
    if not search_result:
        return {'key_claims': []}
    prompt = f'''
        You are an agent specialized in summarizing the results given by the search_agent.
        Information gotten by the search_agent is passed to you and you have to summarize it 
        and then extract 5-6 key claims as a numbered list.
        The given search_result is: {search_result}
    '''
    response = await llm.ainvoke(prompt)
    return {'key_claims': [response.content]}