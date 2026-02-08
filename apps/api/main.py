"""
Upsonic AI Agent API Server
Backend API for AI agent queries with Ollama provider
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from upsonic import Task, Agent

# Configuration
DEFAULT_MODEL = "ollama/qwen2.5:7b"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "api-key-not-set")

# Set Ollama environment variables
os.environ["OLLAMA_BASE_URL"] = OLLAMA_BASE_URL
os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY


# Request/Response models
class QueryRequest(BaseModel):
    """Request model for agent queries."""

    user_query: str = Field(
        ..., description="The user's question or prompt", min_length=1
    )
    model: Optional[str] = Field(
        default=DEFAULT_MODEL,
        description="Ollama model to use (e.g., 'ollama/llama3.2:3b')",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "What is Python programming language?",
                "model": "ollama/qwen2.5:7b",
            }
        }


class QueryResponse(BaseModel):
    """Response model for agent queries."""

    user_query: str = Field(..., description="The original user query")
    bot_response: str = Field(..., description="The AI agent's response")
    model_used: str = Field(..., description="The model that was used")
    timestamp: str = Field(..., description="ISO timestamp of the response")

    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "What is Python?",
                "bot_response": "Python is a high-level programming language...",
                "model_used": "ollama/qwen2.5:7b",
                "timestamp": "2024-01-15T10:30:00",
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    started: bool
    startup_time: str
    version: str = "1.0.0"


class ModelsResponse(BaseModel):
    """Response model for available models."""

    models: list[str] = Field(..., description="List of available Ollama models")
    count: int = Field(..., description="Number of available models")
    source: str = Field(..., description="Source of the model list")


# Lifespan context manager for startup/shutdown
events = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup and shutdown events."""
    # Startup
    print("🚀 Starting Upsonic API Server...")
    print(f"📦 Ollama Base URL: {OLLAMA_BASE_URL}")
    print(f"🤖 Default Model: {DEFAULT_MODEL}")
    events["started"] = True
    events["startup_time"] = datetime.now().isoformat()

    yield

    # Shutdown
    print("🛑 Shutting down Upsonic API Server...")
    events["started"] = False


# Create FastAPI app
app = FastAPI(
    title="Upsonic AI Agent API",
    description="REST API for Upsonic AI Agent Framework with Ollama provider. Supports multiple clients (Web, Mobile, CLI).",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Upsonic AI Agent API",
        "version": "1.0.0",
        "description": "REST API for Upsonic AI Agent Framework",
        "status": "running",
        "endpoints": {"docs": "/docs", "health": "/health", "query": "/query (POST)"},
        "features": [
            "Multi-model support",
            "Async processing",
            "RESTful API",
            "CORS enabled",
        ],
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        service="upsonic-api",
        started=events.get("started", False),
        startup_time=events.get("startup_time", "unknown"),
    )


@app.get("/models", response_model=ModelsResponse)
async def get_available_models():
    """
    Get list of available Ollama models.

    This endpoint queries the Ollama server to get dynamically
    the list of installed models.

    Returns:
        ModelsResponse containing the list of available models
    """
    import httpx

    try:
        # Ollama API endpoint for listing models
        # Remove /v1 suffix if present for Ollama native API
        ollama_host = OLLAMA_BASE_URL.replace("/v1", "").rstrip("/")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_host}/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                # Format models as ollama/<name>
                formatted_models = [f"ollama/{m['name']}" for m in models]

                return ModelsResponse(
                    models=formatted_models,
                    count=len(formatted_models),
                    source="ollama",
                )
            else:
                # Fallback to default models if Ollama API fails
                default_models = [
                    "ollama/llama3.2:3b",
                    "ollama/llama3.2:1b",
                    "ollama/qwen2.5:7b",
                    "ollama/gemma3:4b",
                ]
                return ModelsResponse(
                    models=default_models, count=len(default_models), source="fallback"
                )

    except Exception as e:
        # Return fallback models on error
        default_models = [
            "ollama/llama3.2:3b",
            "ollama/llama3.2:1b",
            "ollama/qwen2.5:7b",
            "ollama/gemma3:4b",
        ]
        return ModelsResponse(
            models=default_models, count=len(default_models), source="fallback"
        )


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a user query through the Upsonic AI Agent.

    This endpoint accepts a user query and optional model specification,
    processes it through the AI agent, and returns the response.

    Args:
        request: QueryRequest containing the user_query and optional model

    Returns:
        QueryResponse containing the bot's response and metadata

    Raises:
        HTTPException: If query processing fails
    """
    user_query = request.user_query
    model = request.model or DEFAULT_MODEL

    if not user_query or not user_query.strip():
        raise HTTPException(
            status_code=400,
            detail="user_query parameter is required and cannot be empty",
        )

    try:
        # Create task for the agent
        answering_task = Task(
            f"Answer the following question clearly and concisely: {user_query}"
        )

        # Create agent with specified Ollama model
        agent = Agent(model=model)

        # Execute the task
        result = await agent.print_do_async(answering_task)

        return QueryResponse(
            user_query=user_query,
            bot_response=result,
            model_used=model,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# Alternative programmatic API for direct Python usage
async def process_query_programmatic(
    user_query: str, model: Optional[str] = None
) -> dict:
    """
    Process a query programmatically (for direct Python usage).

    Args:
        user_query: The user's question
        model: Optional model specification

    Returns:
        Dictionary containing the response and metadata
    """
    if not user_query or not user_query.strip():
        return {
            "error": "user_query parameter is required",
            "user_query": user_query,
            "bot_response": None,
        }

    model_to_use = model or DEFAULT_MODEL

    try:
        # Create task for the agent
        answering_task = Task(
            f"Answer the following question clearly and concisely: {user_query}"
        )

        # Create agent with Ollama model
        agent = Agent(model=model_to_use)

        # Execute the task
        result = await agent.print_do_async(answering_task)

        return {
            "user_query": user_query,
            "bot_response": result,
            "model_used": model_to_use,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "user_query": user_query, "bot_response": None}


if __name__ == "__main__":
    import asyncio

    # Test the API programmatically
    async def test():
        print("\n🧪 Testing API programmatically...\n")

        test_cases = [
            {"user_query": "What is Python programming language?", "model": None},
            {"user_query": "Explain quantum computing", "model": "ollama/llama3.2:3b"},
        ]

        for i, test_input in enumerate(test_cases, 1):
            print(f"Test {i}:")
            print(f"  Query: {test_input['user_query']}")
            print(f"  Model: {test_input['model'] or DEFAULT_MODEL}")

            result = await process_query_programmatic(
                test_input["user_query"], test_input["model"]
            )

            if "error" in result and result["error"]:
                print(f"  ❌ Error: {result['error']}")
            else:
                print(f"  ✅ Response: {result['bot_response'][:100]}...")
            print()

    asyncio.run(test())
