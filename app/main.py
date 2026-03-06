"""
Main FastApi application module for QueryNest.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.history import router as history_router
from app.api.routes.research import router as research_router
from app.api.routes.websocket import router as websocket_router
from app.db.database import init_db


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Executed on startup"""
    await init_db()
    yield  # Control is returned to FastAPI to run the app


app = FastAPI(
    title="QueryNest",
    description="A research assistant that can answer complex questions by autonomously gathering information from the web and other sources.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to restrict to specific origins
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(history_router, prefix="/history", tags=["history"])
app.include_router(research_router, prefix="/research", tags=["research"])
app.include_router(websocket_router, tags=["websocket"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
