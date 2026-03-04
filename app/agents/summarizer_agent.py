from app.agents.llm import llm
from app.agents.state import ResearchState

async def summarizer_agent(state: ResearchState) -> dict:
    '''
    Summarizer Agent Node

    - Takes the search_results from the state
    - passes the info to the llm which extracts key claims as a list
    - And returns the list of key claims

    Input state: search_results
    Output state: key_claims
    '''
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