from app.agents.fact_checker import fact_checker_agent
from app.agents.search_agent import search_agent
from app.agents.state import ResearchState
from app.agents.summarizer_agent import summarizer_agent
from app.agents.supervisor import route, supervisor
from app.agents.writer_agent import writer_agent
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

def build_graph() -> CompiledStateGraph:
    state = StateGraph(ResearchState)

    state.add_node('supervisor', supervisor)
    state.add_node('search', search_agent)
    state.add_node('summarize', summarizer_agent)
    state.add_node('fact_check', fact_checker_agent)
    state.add_node('write', writer_agent)

    state.set_entry_point('supervisor')

    state.add_conditional_edges('supervisor', route, {
        'search': 'search',
        'summarize': 'summarize',
        'fact_check': 'fact_check',
        'write': 'write',
        'end': END
    })

    state.add_edge('search', 'supervisor')
    state.add_edge('summarize', 'supervisor')
    state.add_edge('fact_check', 'supervisor')
    state.add_edge('write', 'supervisor')

    app = state.compile()
    return app