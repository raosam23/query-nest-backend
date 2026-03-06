"""
Creates an instance of ChatOpenAI with gpt-4o-mini model and temperature 0.0
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=lambda: settings.OPENAI_API_KEY)
