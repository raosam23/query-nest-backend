from app.core.config import settings
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model='gpt-4o-mini', api_key=settings.OPENAI_API_KEY)