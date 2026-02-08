"""
Upsonic Chat API Gateway
Complete chat system with Gateway pattern, Chat module, and Session management
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Header,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import httpx

# Upsonic imports
from upsonic import Agent, Task
from upsonic.chat import Chat, SessionManager
from upsonic.storage import SqliteStorage, RedisStorage

# Safety Engine - Guardrails
from upsonic.safety_engine import PolicyInput, RuleOutput, PolicyOutput
from upsonic.safety_engine.policies import (
    ProfanityBlockPolicy,
    PIIBlockPolicy,
    AdultContentBlockPolicy,
)

# Configuration
DEFAULT_MODEL = "ollama/qwen2.5:7b"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("UPSONIC_API_KEY", "dev-key-change-in-production")

os.environ["OLLAMA_BASE_URL"] = OLLAMA_BASE_URL

# Security
security = HTTPBearer()

# Gateway state
gateway_state = {
    "requests_count": 0,
    "start_time": None,
    "rate_limit_store": {},  # Simple in-memory rate limiting
}


# ============== GATEWAY MIDDLEWARES ==============


class GatewayMiddleware:
    """API Gateway middleware for authentication, rate limiting, and logging."""

    @staticmethod
    def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify API key."""
        if credentials.credentials != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return credentials.credentials

    @staticmethod
    def rate_limit(requests_per_minute: int = 60):
        """Rate limiting decorator."""

        def decorator(client_id: str = Header(default="anonymous")):
            now = time.time()
            window_start = now - 60  # 1 minute window

            # Clean old entries
            gateway_state["rate_limit_store"] = {
                k: v
                for k, v in gateway_state["rate_limit_store"].items()
                if v["timestamp"] > window_start
            }

            # Check current client
            client_requests = [
                v
                for k, v in gateway_state["rate_limit_store"].items()
                if v["client_id"] == client_id and v["timestamp"] > window_start
            ]

            if len(client_requests) >= requests_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {requests_per_minute} requests per minute.",
                )

            # Record request
            request_id = f"{client_id}_{now}"
            gateway_state["rate_limit_store"][request_id] = {
                "client_id": client_id,
                "timestamp": now,
            }

            return client_id

        return decorator


# ============== PYDANTIC MODELS ==============


class ChatRequest(BaseModel):
    """Chat message request."""

    message: str = Field(..., description="User message", min_length=1)
    session_id: Optional[str] = Field(
        default=None, description="Session ID for continuity"
    )
    model: Optional[str] = Field(
        default=DEFAULT_MODEL, description="Ollama model to use"
    )
    user_id: str = Field(..., description="User identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello!",
                "session_id": "session_123",
                "model": "ollama/qwen2.5:7b",
                "user_id": "user_456",
            }
        }


class ChatResponse(BaseModel):
    """Chat message response."""

    message: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    model_used: str = Field(..., description="Model used")
    timestamp: str = Field(..., description="Response timestamp")
    message_count: int = Field(..., description="Total messages in session")
    cost_usd: Optional[float] = Field(default=None, description="Cost in USD")


class SessionHistoryResponse(BaseModel):
    """Session history response."""

    session_id: str
    user_id: str
    messages: List[Dict]
    message_count: int
    total_cost: Optional[float]
    created_at: str
    last_active: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    uptime_seconds: float
    total_requests: int
    active_sessions: int


# ============== CHAT MANAGER ==============


class ChatManager:
    """Manages chat sessions using Upsonic Chat module with Guardrails."""

    def __init__(self):
        self.sessions: Dict[str, Chat] = {}
        self.storage = SqliteStorage("chat_sessions.db")  # veya RedisStorage()

    def check_guardrails(
        self, message: str
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check message against safety policies (Guardrails).

        Args:
            message: The message to check

        Returns:
            (is_safe, filtered_content, reason) tuple
            - is_safe: True if message is safe
            - filtered_content: Filtered content if blocked, None if safe
            - reason: Block reason if blocked, None if safe
        """
        policy_input = PolicyInput(input_texts=[message])

        # 1. Profanity Check
        try:
            rule_result, action_result, policy_result = ProfanityBlockPolicy.execute(
                policy_input
            )
            action_output = action_result.action_output or {}
            if action_output.get("action_taken") == "BLOCK":
                return (
                    False,
                    action_result.output_texts[0]
                    if action_result.output_texts
                    else None,
                    f"Profanity detected: {rule_result.details}",
                )
        except Exception as e:
            # Policy hata verirse logla ama mesaja izin ver
            print(f"Warning: Profanity policy error: {e}")

        # 2. PII (Personal Information) Check
        try:
            rule_result, action_result, policy_result = PIIBlockPolicy.execute(
                policy_input
            )
            action_output = action_result.action_output or {}
            if action_output.get("action_taken") == "BLOCK":
                return (
                    False,
                    action_result.output_texts[0]
                    if action_result.output_texts
                    else None,
                    f"PII detected: {rule_result.details}",
                )
        except Exception as e:
            print(f"Warning: PII policy error: {e}")

        # 3. Adult Content Check
        try:
            rule_result, action_result, policy_result = AdultContentBlockPolicy.execute(
                policy_input
            )
            action_output = action_result.action_output or {}
            if action_output.get("action_taken") == "BLOCK":
                return (
                    False,
                    action_result.output_texts[0]
                    if action_result.output_texts
                    else None,
                    f"Adult content detected: {rule_result.details}",
                )
        except Exception as e:
            print(f"Warning: Adult content policy error: {e}")

        return True, None, None

    def get_or_create_session(
        self, session_id: str, user_id: str, model: str = DEFAULT_MODEL
    ) -> Chat:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            # Create agent for this session
            agent = Agent(model=model)

            # Create Chat instance with Upsonic Chat module
            chat = Chat(
                session_id=session_id,
                user_id=user_id,
                agent=agent,
                storage=self.storage,
                full_session_memory=True,
                summary_memory=True,
            )

            self.sessions[session_id] = chat

        return self.sessions[session_id]

    async def send_message(
        self, session_id: str, user_id: str, message: str, model: str = DEFAULT_MODEL
    ) -> ChatResponse:
        """Send message and get response with Guardrails."""
        # GUARDRAILS - Safety Policy Check
        is_safe, filtered_content, block_reason = self.check_guardrails(message)
        if not is_safe:
            # Mesaj engellendi, filtrelenmiş içeriği veya hata döndür
            if filtered_content:
                # Filtrelenmiş içerik varsa onu kullan
                message = filtered_content
            else:
                # Engel mesajı döndür
                raise HTTPException(
                    status_code=400,
                    detail=f"Message blocked by safety policy: {block_reason}",
                )

        # Get or create session
        chat = self.get_or_create_session(session_id, user_id, model)

        # Send message using Chat module
        try:
            response_text = await chat.invoke(message)

            # Get session info (metrics Chat modülünde olmayabilir)
            # metrics = chat.metrics if hasattr(chat, 'metrics') else None

            return ChatResponse(
                message=response_text,
                session_id=session_id,
                user_id=user_id,
                model_used=model,
                timestamp=datetime.now().isoformat(),
                message_count=len(chat.all_messages),
                cost_usd=None,  # metrics.total_cost if metrics and hasattr(metrics, "total_cost") else None,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    def get_session_history(self, session_id: str) -> Optional[SessionHistoryResponse]:
        """Get session chat history."""
        if session_id not in self.sessions:
            return None

        chat = self.sessions[session_id]

        return SessionHistoryResponse(
            session_id=session_id,
            user_id=chat.user_id,
            messages=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp if hasattr(msg, "timestamp") else None,
                }
                for msg in chat.all_messages
            ],
            message_count=len(chat.all_messages),
            total_cost=None,  # chat.metrics.total_cost if hasattr(chat, 'metrics') and hasattr(chat.metrics, "total_cost") else None,
            created_at=datetime.now().isoformat(),  # Chat module'dan alınabilir
            last_active=datetime.now().isoformat(),
        )


# Initialize chat manager
chat_manager = ChatManager()


# ============== FASTAPI APP ==============


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan management."""
    print("🚀 Starting Chat API Gateway...")
    gateway_state["start_time"] = time.time()
    yield
    print("🛑 Shutting down Chat API Gateway...")


app = FastAPI(
    title="Upsonic Chat API Gateway",
    description="Production-ready Chat API with Gateway pattern, Session management, and Safety",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== API ENDPOINTS ==============


@app.get("/", response_model=dict)
async def root():
    """API information."""
    return {
        "name": "Upsonic Chat API Gateway",
        "version": "2.0.0",
        "description": "Production Chat API with Gateway pattern",
        "features": [
            "Session management",
            "Rate limiting",
            "Authentication",
            "Safety engine",
            "Cost tracking",
            "Chat history",
        ],
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST)",
            "history": "/chat/{session_id}/history",
            "models": "/models",
            "websocket": "/ws/chat",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with metrics."""
    uptime = (
        time.time() - gateway_state["start_time"] if gateway_state["start_time"] else 0
    )

    return HealthResponse(
        status="healthy",
        service="upsonic-chat-gateway",
        version="2.0.0",
        uptime_seconds=uptime,
        total_requests=gateway_state["requests_count"],
        active_sessions=len(chat_manager.sessions),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    api_key: str = Depends(GatewayMiddleware.verify_api_key),
    client_id: str = Depends(GatewayMiddleware.rate_limit(requests_per_minute=60)),
):
    """
    Send a chat message.

    Requires:
    - API Key (Authorization header)
    - Rate limited to 60 requests/minute
    """
    gateway_state["requests_count"] += 1

    # Generate session_id if not provided
    session_id = request.session_id or f"{request.user_id}_{int(time.time())}"

    return await chat_manager.send_message(
        session_id=session_id,
        user_id=request.user_id,
        message=request.message,
        model=request.model or DEFAULT_MODEL,
    )


@app.get("/chat/{session_id}/history", response_model=SessionHistoryResponse)
async def get_chat_history(
    session_id: str, api_key: str = Depends(GatewayMiddleware.verify_api_key)
):
    """Get chat session history."""
    history = chat_manager.get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


@app.get("/models", response_model=dict)
async def get_available_models():
    """Get available Ollama models."""
    try:
        ollama_host = OLLAMA_BASE_URL.replace("/v1", "").rstrip("/")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_host}/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = [f"ollama/{m['name']}" for m in data.get("models", [])]
                return {"models": models, "count": len(models), "source": "ollama"}
    except:
        pass

    # Fallback
    return {
        "models": ["ollama/qwen2.5:7b", "ollama/llama3.2:3b"],
        "count": 2,
        "source": "fallback",
    }


class ToolInfo(BaseModel):
    """Tool information."""

    name: str
    description: str
    category: str


class ToolsResponse(BaseModel):
    """Available tools response."""

    tools: List[ToolInfo]
    count: int


@app.get("/tools", response_model=ToolsResponse)
async def get_available_tools():
    """Get available Upsonic tools."""
    tools = [
        ToolInfo(
            name="web_search",
            description="Web arama yap (DuckDuckGo)",
            category="web_search",
        ),
        ToolInfo(
            name="code_execution",
            description="Python kodu çalıştır",
            category="execution",
        ),
        ToolInfo(
            name="url_context",
            description="URL içerik çek",
            category="web",
        ),
        ToolInfo(
            name="yfinance",
            description="Finansal veriler (Yahoo Finance)",
            category="financial",
        ),
        ToolInfo(
            name="tavily",
            description="Web arama (Tavily API)",
            category="web_search",
        ),
        ToolInfo(
            name="duckduckgo",
            description="Web arama (DuckDuckGo)",
            category="web_search",
        ),
    ]

    return ToolsResponse(tools=tools, count=len(tools))


# ============== WEBSOCKET (Real-time Chat) ==============


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    # Initialize session_id for exception handlers
    session_id = "unknown"

    try:
        # Wait for initial connection with session info
        init_data = await websocket.receive_json()
        session_id = init_data.get("session_id", f"ws_{int(time.time())}")
        user_id = init_data.get("user_id", "anonymous")
        model = init_data.get("model", DEFAULT_MODEL)

        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to chat server",
            }
        )

        # Chat loop
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            # Get response
            try:
                chat = chat_manager.get_or_create_session(session_id, user_id, model)
                response = await chat.invoke(message)

                await websocket.send_json(
                    {
                        "type": "message",
                        "content": response,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
