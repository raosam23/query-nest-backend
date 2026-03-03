import operator
from typing import Annotated, TypedDict

class ResearchState(TypedDict):
    query: str
    search_results: Annotated[list, operator.add]
    key_claims: Annotated[list, operator.add]
    fact_check_report: dict
    final_report: str
    next: str
    session_id: str