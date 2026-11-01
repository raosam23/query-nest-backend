"""Install dummy settings before the application is imported.

The FastAPI app builds its settings, database engine, ChatOpenAI client, and
Tavily tool at import time. Tests never call OpenAI, Tavily, or Postgres.
These values are placeholders so importing the app does not require a developer
.env file or a real API key. Existing environment variables win, which is what
CI uses.
"""

import os

_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "JWT_SECRET": "test-secret-key-for-tests-only",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRE_MINUTES": "60",
    "OPENAI_API_KEY": "sk-test-key-not-used-in-tests",
    "TAVILY_API_KEY": "tvly-test-key-not-used-in-tests",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGSMITH_TRACING": "false",
}

for _key, _value in _DEFAULTS.items():
    os.environ.setdefault(_key, _value)

ENV_READY = True
