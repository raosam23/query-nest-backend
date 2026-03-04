from app.agents.state import ResearchState

def supervisor(state: ResearchState) -> dict:
    '''
    Supervisor Node

    Acts as the orchestrator of the research pipeline.
    Reads the current state and decides which agent should run next
    based on what data is missing.

    - No search_result -> route to search agent
    - No key_claims -> route to summarizer agent
    - No fact_check_report -> route to fact_checker agent
    - No final_report -> route to writer agent
    - Everything done -> end of the graph

    Input State: full state
    Output State: next (routing decision)
    '''
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
    '''
    Route function for LangGraph conditional edges.
    Returns the next node name from state for LangGraph to navigate to.
    '''
    return state['next']