"""
This module defines the state structure for the research workflow.
"""

import operator
from typing import Annotated, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession


class ResearchState(TypedDict):
    """
    ResearchState defines the typing for the state passed between agents
    in the research workflow.
    """

    query: str
    search_results: Annotated[list, operator.add]
    key_claims: Annotated[list, operator.add]
    fact_check_report: dict
    final_report: str
    next: str
    session_id: str
    db_session: AsyncSession
