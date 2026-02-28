# QueryNest 🔍

A multi-agent AI research assistant that autonomously searches the web, summarizes findings, fact-checks results, and compiles a structured report — all from a single query.

> ⚠️ **Work in Progress** — This project is actively being developed.

## What it does

You give it a question like _"What is the current state of nuclear fusion?"_ and it:

1. Searches the web for relevant articles
2. Extracts key claims from the results
3. Fact-checks and flags any conflicting information
4. Compiles everything into a clean, structured report

## Tech Stack

- **FastAPI** — REST API framework
- **LangGraph** — Multi-agent orchestration
- **LangChain** — LLM tooling
- **SQLModel** — ORM for database models
- **PostgreSQL (Neon)** — Cloud database
- **OpenAI GPT-4o** — LLM
- **Tavily** — Web search API for agents

## Project Status

- [x] Project setup
- [x] Database models
- [x] Database connection (Neon PostgreSQL)
- [ ] Auth routes (register, login)
- [ ] Research routes
- [ ] LangGraph agent pipeline
- [ ] WebSocket streaming
- [ ] Frontend

## Getting Started

```bash
uv venv
source .venv/bin/activate
uv sync
uv run uvicorn app.main:app --reload
```

## Environment Variables

Create a `.env` file in the root with:

```env
DATABASE_URL=your_neon_postgresql_url
JWT_SECRET=your_jwt_secret
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```
