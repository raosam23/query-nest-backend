from app.agents.llm import llm
from app.agents.state import ResearchState

async def writer_agent(state: ResearchState) -> dict:
    '''
    Writer Agent Node

    - Takes the query, key claims and the fact check report.
    - Passes this information to the llm, which is then going to generate a structured report
    - Returns the report

    Input state: query, key_claims, fact_check_report
    Output state: final_report
    '''
    query = state['query']
    key_claims = state['key_claims']
    fact_check_report = state['fact_check_report']
    if not key_claims or not fact_check_report:
        return {'final_report': 'Insufficient information to generate a report'}
    prompt = f'''
        You are an expert writer agent who's main job is to write a structured, organized and a readable report about a topic. You are given the query, key_claims and the fact_check_report. From this information, you will be creating a structured report with sections: Summary, key Claims, FactCheck, Conclusion and a reference (if you can).
        The query is: {query}
        Key Claims are: {key_claims}
        The Fact check report is: {fact_check_report}
    '''

    response = await llm.ainvoke(prompt)
    return {'final_report': response.content}