from app.agents.state import ResearchState

def supervisor(state: ResearchState) -> dict:
    if not state['search_results']:
        return {'next': 'search'}
    if not state['key_claims']:
        return {'next': 'summarize'}
    if not state['fact_check_report']:
        return {'next': 'fact_check'}
    if not state['final_report']:
        return {'next': 'write'}
    return {'next': 'end'}

def route(state: ResearchState):
    return state['next']