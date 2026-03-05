# QueryNest 🔍
A multi-agent AI research assistant that autonomously searches the web, summarizes findings, fact-checks results, and compiles a structured report — all from a single query.

> ⚠️ **Work in Progress** — This project is actively being developed.

## What it does
You give it a question like _"What is the current state of nuclear fusion?"_ and it:
1. Searches the web for relevant articles
2. Extracts key claims from the results
3. Fact-checks and flags any conflicting information
4. Compiles everything into a clean, structured report
5. Streams live agent progress updates via WebSocket

## Tech Stack
- **FastAPI** — REST API framework
- **LangGraph** — Multi-agent orchestration
- **LangChain** — LLM tooling
- **SQLModel** — ORM for database models
- **PostgreSQL (Neon)** — Cloud database
- **OpenAI GPT-4o-mini** — LLM
- **Tavily** — Web search API for agents

## Architecture
```
User → POST /research → returns session_id immediately
                      → runs agents in background
User → WS /research/{session_id}/stream → receives live updates

Agent Pipeline:
Search Agent → Summarizer Agent → Fact Checker Agent → Writer Agent
                    ↑__________________________|
                         Supervisor routes
```

## API Endpoints
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | Register a new user | No |
| POST | `/auth/login` | Login and get JWT token | No |
| POST | `/research` | Start a new research session | Yes |
| GET | `/research/{id}` | Get a specific research session | Yes |
| GET | `/research/{id}/sources` | Get all sources for a session | Yes |
| GET | `/history` | Get all past research sessions | Yes |
| DELETE | `/history/{id}` | Delete a research session | Yes |
| WS | `/research/{id}/stream` | Stream live agent updates | Yes |

## Project Status
- [x] Project setup
- [x] Database models
- [x] Database connection (Neon PostgreSQL)
- [x] Auth routes (register, login)
- [x] Research routes
- [x] LangGraph agent pipeline
- [x] Agent and source logging to database
- [x] WebSocket streaming
- [x] Sources endpoint
- [ ] Frontend (NextJS)
- [ ] Dockerize

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
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

## WebSocket Usage
Connect to the WebSocket after getting a session_id from POST /research:
```javascript
const ws = new WebSocket('ws://localhost:8000/research/{session_id}/stream')
ws.onmessage = (event) => console.log(JSON.parse(event.data))
ws.onopen = () => console.log('WebSocket connected!')
```
Messages follow this format:
```json
{ "agent": "search_agent", "status": "running" }
{ "agent": "search_agent", "status": "done", "output": "Found 5 results" }
