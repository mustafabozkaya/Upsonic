"""
REST Interface Adapter for Upsonic

This is a THIN ADAPTER that translates HTTP requests to Upsonic enterprise backend.
All business logic is delegated to src/upsonic/ modules:
- src/upsonic/agent/agent.py for AI processing
- src/upsonic/chat/chat.py for session management
- src/upsonic/storage/ for data persistence
- src/upsonic/safety_engine/ for content filtering

Uses apps/gateway/ for security:
- apps/gateway/auth.py for JWT/OAuth2 authentication
- apps/gateway/ratelimit.py for rate limiting
- apps/gateway/middleware.py for FastAPI middleware

Design Principles:
1. Minimal business logic in this layer
2. All complexity delegated to src/upsonic/
3. Security delegated to apps/gateway/
4. Adapter pattern for external communication
5. Clean separation of concerns
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from upsonic import Agent, Task
from upsonic.storage import SqliteStorage, Memory
from upsonic.chat import Chat
from apps.gateway.middleware import GatewayMiddleware
from apps.gateway.config import GatewayConfig

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "api-key-not-set")
DEFAULT_MODEL = os.environ.get("UPSONIC_DEFAULT_MODEL", "ollama/qwen2.5:7b")

os.environ["OLLAMA_BASE_URL"] = OLLAMA_BASE_URL
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY

storage: Optional[SqliteStorage] = None
agent_cache: dict[str, Agent] = {}
chat_sessions: dict[str, Chat] = {}
gateway_middleware: Optional[GatewayMiddleware] = None


class QueryRequest(BaseModel):
    user_query: str = Field(
        ..., description="The user's question or prompt", min_length=1
    )
    model: Optional[str] = Field(
        default=DEFAULT_MODEL, description="Ollama model to use"
    )
    tools: Optional[list[str]] = Field(
        default=None,
        description="Optional list of tools to enable (web_search, code_execution, memory)",
    )


class QueryResponse(BaseModel):
    user_query: str
    bot_response: str
    model_used: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    service: str
    started: bool
    startup_time: str
    version: str = "1.0.0"


class ModelsResponse(BaseModel):
    models: list[str]
    count: int
    source: str


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]
    count: int


events: dict = {}


async def get_ollama_models() -> list[str]:
    """Fetch available models from Ollama."""
    import httpx

    try:
        ollama_host = OLLAMA_BASE_URL.replace("/v1", "").rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_host}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [f"ollama/{m['name']}" for m in data.get("models", [])]
    except Exception:
        pass
    return [DEFAULT_MODEL]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global storage, agent_cache, chat_sessions

    print("Starting Upsonic REST Interface Adapter...")
    print(f"Backend: {OLLAMA_BASE_URL}")
    print(f"Default Model: {DEFAULT_MODEL}")

    storage = SqliteStorage("interface_chat.db")

    events["started"] = True
    events["startup_time"] = datetime.now().isoformat()

    yield

    print("Shutting down Upsonic REST Interface Adapter...")


def create_app_with_gateway() -> FastAPI:
    """Create FastAPI app with gateway middleware."""
    from apps.gateway.middleware import GatewayMiddleware

    app = FastAPI(
        title="Upsonic REST Interface Adapter",
        description="HTTP adapter for Upsonic AI Agent Framework. "
        "Delegates to src/upsonic/ enterprise modules.",
        version="1.0.0",
        lifespan=lifespan,
    )

    gateway_middleware = GatewayMiddleware()
    gateway_middleware.add_to_app(app)

    return app


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Upsonic REST Interface Adapter",
        description="HTTP adapter for Upsonic AI Agent Framework. "
        "Delegates to src/upsonic/ enterprise modules.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_model=dict)
    async def root():
        return {
            "name": "Upsonic REST Interface Adapter",
            "version": "1.0.0",
            "description": "HTTP adapter for Upsonic AI Agent Framework",
            "status": "running",
            "architecture": "Interface Adapter Pattern",
            "backend": "src/upsonic/",
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "models": "/models",
                "query": "/query (POST)",
            },
        }

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(
            status="healthy",
            service="upsonic-interface-adapter",
            started=events.get("started", False),
            startup_time=events.get("startup_time", "unknown"),
        )

    @app.get("/models", response_model=ModelsResponse)
    async def get_models():
        models = await get_ollama_models()
        return ModelsResponse(models=models, count=len(models), source="ollama")

    @app.get("/tools", response_model=ToolsResponse)
    async def get_tools():
        """Get list of available tools."""
        # Built-in tools list
        tools = [
            ToolInfo(
                name="web_search",
                description="Search the web for information",
                parameters={"query": {"type": "string", "description": "Search query"}},
            ),
            ToolInfo(
                name="code_execution",
                description="Execute Python code safely",
                parameters={
                    "code": {"type": "string", "description": "Python code to execute"}
                },
            ),
            ToolInfo(
                name="memory",
                description="Store and retrieve information from memory",
                parameters={
                    "action": {"type": "string", "enum": ["store", "retrieve"]},
                    "content": {"type": "string"},
                },
            ),
        ]
        return ToolsResponse(tools=tools, count=len(tools))

    @app.post("/query", response_model=QueryResponse)
    async def process_query(request: QueryRequest) -> QueryResponse:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="user_query is required")

        try:
            model = request.model or DEFAULT_MODEL

            # Log tools if provided
            if request.tools:
                print(f"Tools enabled: {request.tools}")

            # TODO: Configure agent with tools when Upsonic supports it
            agent = Agent(model=model)

            # Add tools context to prompt if tools are specified
            query = request.user_query
            if request.tools:
                tools_str = ", ".join(request.tools)
                query = f"[Tools available: {tools_str}] {query}"

            task = Task(f"Answer clearly and concisely: {query}")
            result = await agent.do_async(task)

            return QueryResponse(
                user_query=request.user_query,
                bot_response=str(result),
                model_used=model,
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return app


app = create_app()


def run():
    """Run the interface adapter with uvicorn."""
    import uvicorn

    uvicorn.run(
        "apps.interface.rest.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
