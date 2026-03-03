from app.agents.llm import llm
from app.agents.state import ResearchState

async def fact_checker_agent(state: ResearchState) -> dict:
    key_claims = state['key_claims']
    if not key_claims:
        return {'fact_check_report': {'report': 'no claims to check'}}
    prompt = f'''
        You are a fact cheker agent, that is gonna take the key_claims given by the key claims agent
        and then cross-reference them, identify any contradictions and rate each claims as
        'verified', 'contradicted', or 'uncertain'
        Here are the key claims: {key_claims} 
    '''
    response = await llm.ainvoke(prompt)
    return {'fact_check_report': {'report': response.content}}