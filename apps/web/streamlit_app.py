"""
Streamlit Web Client for Upsonic AI Agent

Modern, enterprise-grade Streamlit interface for Upsonic AI Agent Framework.
Uses the new architecture: Streamlit → apps/web/client.py → apps/interface/rest/main.py → src/upsonic/

Features:
- Modern chat interface with message bubbles
- Model selection with live model list from API
- Session management and chat history
- API connection status monitoring
- Gateway authentication support
- Responsive sidebar with settings

Usage:
    uv run streamlit run apps/web/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import httpx
from apps.web.client import UpsonicClient, QueryResult
from apps.web.chat_client import ChatClient, ChatMessage

st.set_page_config(
    page_title="Upsonic AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.environ.get("UPSONIC_API_URL", "http://localhost:8000")
DEFAULT_MODEL = os.environ.get("UPSONIC_DEFAULT_MODEL", "ollama/llama3.2:1b")

DEFAULT_MODELS = [
    "ollama/phi",  # ~2GB - Smaller model
    "ollama/llama3.2:1b",  # ~1.3GB - Smallest Llama
    "ollama/llama3.2:3b",  # ~2GB
    "ollama/qwen2.5:7b",  # ~4.7GB - Needs more RAM
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "available_models" not in st.session_state:
    st.session_state.available_models = DEFAULT_MODELS


st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea15, #764ba215);
        border-left: 4px solid #667eea;
    }
    .assistant-message {
        background: linear-gradient(135deg, #11998e15, #38ef7d15);
        border-left: 4px solid #11998e;
    }
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .status-online {
        background: #d4edda;
        color: #155724;
    }
    .status-offline {
        background: #f8d7da;
        color: #721c24;
    }
    .status-loading {
        background: #fff3cd;
        color: #856404;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_client() -> UpsonicClient:
    """Get Upsonic client instance."""
    return UpsonicClient(base_url=API_BASE_URL)


def check_api_status() -> tuple[bool, dict]:
    """Check if API is online and healthy."""
    try:
        client = get_client()
        health = client.info()
        return True, health
    except Exception as e:
        return False, {"error": str(e)}


def get_available_models() -> tuple[list[str], str]:
    """Fetch available models from API."""
    try:
        client = get_client()
        models = client.get_models()
        return models, "api"
    except Exception:
        return DEFAULT_MODELS.copy(), "default"


def sync_query(
    user_query: str, model: str, enable_guardrails: bool = True
) -> tuple[bool, str]:
    """Send query to API."""
    try:
        client = get_client()

        # Check if guardrails should be enabled
        guardrails = (
            st.session_state.get("guardrails_enabled", True)
            if "guardrails_enabled" in st.session_state
            else enable_guardrails
        )

        # Send query with guardrails parameter
        result = client.query(user_query, model=model, enable_guardrails=guardrails)

        # Check if response is blocked
        if result.bot_response.startswith("⚠️ Content blocked"):
            return False, result.bot_response

        return True, result.bot_response
    except Exception as e:
        return False, str(e)


def render_header():
    """Render the main header."""
    st.markdown(
        """
        <div class="main-header">
            <h1>🤖 Upsonic AI Agent</h1>
            <p>Enterprise AI Assistant with Clean Architecture</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Render the sidebar with settings."""
    with st.sidebar:
        st.title("⚙️ Settings")

        st.markdown("### 🔌 API Connection")

        status_placeholder = st.empty()
        is_healthy, health_data = check_api_status()

        if is_healthy:
            status_placeholder.markdown(
                '<span class="status-indicator status-online">● API Online</span>',
                unsafe_allow_html=True,
            )
        else:
            status_placeholder.markdown(
                '<span class="status-indicator status-offline">● API Offline</span>',
                unsafe_allow_html=True,
            )

        api_url = st.text_input("API URL", value=API_BASE_URL, key="api_url")

        if st.button("🔄 Check Connection", key="check_conn"):
            with st.spinner("Checking..."):
                is_healthy, health_data = check_api_status()
                if is_healthy:
                    st.success(f"✅ Connected to {health_data.get('name', 'Upsonic')}")
                else:
                    st.error(
                        f"❌ Connection failed: {health_data.get('error', 'Unknown error')}"
                    )

        st.markdown("---")
        st.markdown("### 🤖 Model Selection")

        models, source = get_available_models()
        st.session_state.available_models = models

        selected_model = st.selectbox(
            "Choose Model",
            models,
            index=0,
            key="model_select",
            help=f"Source: {source}",
        )

        if source == "api":
            st.caption(f"🟢 Loaded {len(models)} models from API")
        else:
            st.caption(f"⚪ Using default models (API unavailable)")

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            key="temperature",
            help="Lower = more focused, Higher = more creative",
        )

        st.markdown("---")
        st.markdown("### 🛠️ Tools")

        # Initialize selected_tools in session state
        if "selected_tools" not in st.session_state:
            st.session_state.selected_tools = []

        # Tool selection with checkboxes
        st.caption("Select tools to enable:")

        available_tools = {
            "web_search": "🔍 Web Search (DuckDuckGo)",
            "code_execution": "💻 Code Execution (Python)",
            "memory": "🧠 Memory (Store/Retrieve)",
        }

        # Create checkboxes and collect selected tools
        selected_tools_list = []
        for tool_key, tool_label in available_tools.items():
            is_checked = st.checkbox(
                tool_label,
                value=tool_key in st.session_state.selected_tools,
                key=f"tool_{tool_key}",
            )
            if is_checked:
                selected_tools_list.append(tool_key)

        # Update session state only if changed
        if set(selected_tools_list) != set(st.session_state.selected_tools):
            st.session_state.selected_tools = selected_tools_list

        if st.session_state.selected_tools:
            st.caption(f"Active: {', '.join(st.session_state.selected_tools)}")
        else:
            st.caption("Auto mode: Agent will decide")

        st.markdown("---")

        # Safety Engine Settings (New Feature)
        st.markdown("### 🛡️ Safety Engine")

        # Fetch Safety Engine status
        safety_enabled = False
        safety_status = "inactive"
        safety_policies = []

        try:
            client = get_client()
            safety_response = client.get_safety_status()
            safety_enabled = safety_response.get("enabled", False)
            safety_status = safety_response.get("status", "inactive")
            safety_policies = safety_response.get("policies", [])
        except Exception as e:
            st.warning(f"⚠️ Could not fetch safety status: {e}")

        # Display Safety Engine status
        status_color = "#d4edda" if safety_enabled else "#f8d7da"
        status_text = "Aktif" if safety_status == "active" else "Pasif"

        st.markdown(
            f"""
            <div style="padding: 1rem; border-radius: 8px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.2rem;">🛡️</span>
                    <strong>Safety Engine:</strong>
                    <span style="padding: 0.25rem 0.75rem; border-radius: 4px; background: {status_color}; color: white; font-weight: bold;">
                        {status_text}
                    </span>
                </div>
                <div style="font-size: 0.9rem; color: #666;">
                    <strong>Aktif Policy'ler:</strong>
                    {", ".join(safety_policies) if safety_policies else "Yok"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Guardrails toggle checkbox
        guardrails_enabled = st.checkbox(
            "🚦 Guardrails Aktif Et",
            value=st.session_state.get("guardrails_enabled", True),
            key="guardrails_enabled",
            help="Safety Engine ile içerik kontrolünü aç/kapat. Pasif olduğunda tüm içerik kabul edilir.",
        )

        # Update session state
        st.session_state.guardrails_enabled = guardrails_enabled

        if guardrails_enabled:
            st.caption("✅ İçerik güvenliği etkin (Profanity, PII, Adult Content)")
            st.info("💡 Uyarı: Uygunsuz içerik otomatik olarak engellenecek.")
        else:
            st.caption("⚠️ İçerik güvenliği devre dışı")
            st.warning("⚠️ Dikkat: Tüm içerik kontrolsiz işlenecek.")

        st.markdown("---")
        st.markdown("### 💬 Chat Actions")

        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.messages = []
            st.session_state.session_id = None
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 System Info")
        st.markdown(f"**API URL:** `{api_url}`")
        st.markdown(f"**Model:** `{selected_model}`")
        st.markdown(f"**Messages:** {len(st.session_state.messages)}")

        with st.expander("🏗️ Architecture Info", expanded=False):
            st.markdown("""
            ```
            Streamlit → apps/web/client.py
                        ↓
                   apps/interface/rest
                        ↓
                   src/upsonic/agent
            ```
            """)
            st.caption("Powered by Upsonic Clean Architecture")

    return selected_model, temperature, api_url, st.session_state.selected_tools


def render_chat():
    """Render the main chat interface."""
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "timestamp" in message:
                    st.caption(f"🕐 {message['timestamp']}")

    return chat_container


def handle_user_input(user_input: str, model: str, tools: list):
    """Process user input and generate response."""
    if not user_input.strip():
        return

    timestamp = datetime.now().strftime("%H:%M")

    # Get guardrails setting
    guardrails_enabled = st.session_state.get("guardrails_enabled", True)

    # Add tools info to message if tools are selected
    tools_info = ""
    if tools:
        tools_info = f" (with tools: {', '.join(tools)})"

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
            "timestamp": timestamp,
            "tools": tools,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)
        if tools:
            st.caption(f"🕐 {timestamp} | 🛠️ {', '.join(tools)}")
        else:
            st.caption(f"🕐 {timestamp}")

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            # Pass query with guardrails setting to sync_query
            success, response = sync_query(
                user_input, model, enable_guardrails=guardrails_enabled
            )

            if success:
                st.markdown(response)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )
            else:
                if response.startswith("⚠️ Content blocked"):
                    # Blocked content - show warning
                    st.warning(f"🛡️ {response}")
                else:
                    # Other error
                    st.error(f"❌ Error: {response}")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )


def render_chat_input(selected_model: str, selected_tools: list):
    """Render chat input area."""
    # Get guardrails setting from session state
    guardrails_enabled = st.session_state.get("guardrails_enabled", True)

    if prompt := st.chat_input("Type your message...", key="chat_input"):
        handle_user_input(prompt, selected_model, selected_tools)


def render_examples():
    """Render example prompts."""
    with st.expander("💡 Example Prompts", expanded=False):
        col1, col2 = st.columns(2)

        examples = [
            "What is Python programming language?",
            "Explain machine learning in simple terms",
            "Write a Python function to calculate factorial",
            "What are the benefits of clean architecture?",
        ]

        for i, example in enumerate(examples):
            col = col1 if i % 2 == 0 else col2
            if col.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.pending_message = example
                st.rerun()


def main():
    """Main Streamlit application."""
    render_header()

    selected_model, temperature, api_url, selected_tools = render_sidebar()

    # Store selected tools in session state for use in chat
    if "current_tools" not in st.session_state:
        st.session_state.current_tools = []
    st.session_state.current_tools = selected_tools

    # Handle pending message from example buttons
    if "pending_message" in st.session_state and st.session_state.pending_message:
        msg = st.session_state.pending_message
        st.session_state.pending_message = None
        handle_user_input(msg, selected_model, selected_tools)

    render_chat()
    render_chat_input(selected_model, selected_tools)
    render_examples()

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.85rem;">
            🤖 Upsonic AI Agent | Built with Clean Architecture
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
