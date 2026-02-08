"""
Streamlit Web Client for Upsonic Chat API Gateway
Supports session management, chat history, and real-time updates
"""

import os
import streamlit as st
import httpx
import asyncio
import json

# API Configuration
API_BASE_URL = os.environ.get("UPSONIC_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("UPSONIC_API_KEY", "dev-key-change-in-production")

# Headers
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Page configuration
st.set_page_config(
    page_title="Upsonic Chat Gateway Client",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


async def send_chat_message(
    message: str, user_id: str, session_id: str = None, model: str = None
):
    """Send chat message to Gateway API."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/chat",
                headers=headers,
                json={
                    "message": message,
                    "user_id": user_id,
                    "session_id": session_id,
                    "model": model or "ollama/qwen2.5:7b",
                },
            )

            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 401:
                return False, {"error": "API Key geçersiz"}
            elif response.status_code == 429:
                return False, {"error": "Rate limit aşıldı. Lütfen bekleyin."}
            else:
                return False, {"error": f"API Hatası: {response.status_code}"}

    except httpx.ConnectError:
        return False, {"error": "Gateway'e bağlanılamıyor. API çalışıyor mu?"}
    except Exception as e:
        return False, {"error": f"Hata: {str(e)}"}


async def get_chat_history(session_id: str):
    """Get chat history from Gateway API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/chat/{session_id}/history", headers=headers
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"API Hatası: {response.status_code}"}

    except Exception as e:
        return False, {"error": str(e)}


async def fetch_available_models():
    """Fetch available models from Gateway API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/models")

            if response.status_code == 200:
                data = response.json()
                return True, data.get("models", []), data.get("source", "unknown")
            else:
                return False, [], "fallback"
    except Exception as e:
        return False, [], "error"


def get_models_sync():
    """Get models synchronously."""

    async def run_fetch():
        return await fetch_available_models()

    return asyncio.run(run_fetch())


def render_sidebar():
    """Render sidebar with settings."""
    st.sidebar.title("⚙️ Ayarlar")

    # User configuration
    st.sidebar.markdown("### 👤 Kullanıcı")
    user_id = st.sidebar.text_input(
        "User ID",
        value=st.session_state.get("user_id", "user_1"),
        help="Benzersiz kullanıcı kimliği",
    )
    st.session_state.user_id = user_id

    # Session configuration
    st.sidebar.markdown("### 💬 Session")
    session_id = st.sidebar.text_input(
        "Session ID",
        value=st.session_state.get("session_id", ""),
        help="Boş bırakırsanız otomatik oluşturulur",
    )
    st.session_state.session_id = session_id

    # Model selection - DYNAMIC from API!
    st.sidebar.markdown("### 🤖 Model")

    # Fetch models from API (cached in session state)
    if "available_models" not in st.session_state:
        with st.sidebar:
            with st.spinner("Modeller yükleniyor..."):
                success, models, source = get_models_sync()
                st.session_state.available_models = models
                st.session_state.models_source = source
                if success and source == "ollama":
                    st.success(f"✅ {len(models)} model Ollama'dan yüklendi")
                else:
                    st.warning(f"⚠️ Ollama'dan alınamadı, varsayılanlar kullanılıyor")

    available_models = st.session_state.get(
        "available_models",
        [
            "ollama/qwen2.5:7b",
            "ollama/llama3.2:3b",
            "ollama/llama3.2:1b",
            "ollama/gemma3:4b",
        ],
    )
    models_source = st.session_state.get("models_source", "default")

    model = st.sidebar.selectbox(
        "Model",
        available_models,
        index=0,
        help=f"Kullanılacak model (Kaynak: {models_source})",
    )

    # Show model source
    if models_source == "ollama":
        st.sidebar.caption(f"🟢 Canlı: Ollama'dan {len(available_models)} model")
    else:
        st.sidebar.caption(f"⚪ Varsayılan: {len(available_models)} model")

    # Show session info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Session Bilgisi")

    if "message_count" in st.session_state:
        st.sidebar.metric("Mesaj Sayısı", st.session_state.message_count)

    if "total_cost" in st.session_state and st.session_state.total_cost:
        st.sidebar.metric("Toplam Maliyet", f"${st.session_state.total_cost:.4f}")

    # Load history button
    if st.sidebar.button("📚 Geçmişi Yükle"):
        if session_id:
            with st.spinner("Yükleniyor..."):
                success, data = asyncio.run(get_chat_history(session_id))
                if success:
                    st.session_state.messages = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in data.get("messages", [])
                    ]
                    st.session_state.message_count = data.get("message_count", 0)
                    st.session_state.total_cost = data.get("total_cost", 0)
                    st.success(f"✅ {data.get('message_count', 0)} mesaj yüklendi")
                else:
                    st.error(f"❌ {data.get('error', 'Bilinmeyen hata')}")
        else:
            st.warning("⚠️ Session ID girin")

    # Clear chat
    if st.sidebar.button("🗑️ Sohbeti Temizle"):
        st.session_state.messages = []
        st.session_state.message_count = 0
        st.session_state.total_cost = 0
        st.rerun()

    return user_id, session_id, model


def render_chat_interface(user_id: str, session_id: str, model: str):
    """Render chat interface."""
    st.markdown("### 💬 Sohbet")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Mesajınızı yazın..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Düşünüyor..."):
                success, data = asyncio.run(
                    send_chat_message(prompt, user_id, session_id, model)
                )

                if success:
                    response = data.get("message", "")
                    st.markdown(response)

                    # Add to history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

                    # Update metrics
                    st.session_state.message_count = data.get("message_count", 0)
                    st.session_state.total_cost = data.get("cost_usd", 0)

                    # Update session_id if new
                    if not session_id and data.get("session_id"):
                        st.session_state.session_id = data.get("session_id")

                else:
                    error_msg = data.get("error", "Bilinmeyen hata")
                    st.error(f"❌ {error_msg}")


def main():
    """Main Streamlit application."""

    # Header
    st.title("💬 Upsonic Chat Gateway Client")
    st.markdown("Session management, chat history, and cost tracking")

    # Info box
    with st.expander("ℹ️ Hakkında", expanded=False):
        st.markdown("""
        **Upsonic Chat Gateway Özellikleri:**
        
        - 🔐 **API Key Authentication**
        - 💬 **Session Management** (Sohbet geçmişi)
        - 🧠 **Memory Persistence** (SQLite/Redis)
        - 💰 **Cost Tracking** (USD cinsinden maliyet)
        - 📚 **Chat History** (Geçmiş mesajlar)
        - ⏱️ **Rate Limiting** (60 req/min)
        
        **Backend:** `apps/api/gateway.py`
        """)

    # Render sidebar
    user_id, session_id, model = render_sidebar()

    # Render chat
    render_chat_interface(user_id, session_id, model)

    # Footer
    st.markdown("---")
    st.caption(f"Upsonic Chat Gateway Client • API: {API_BASE_URL}")


if __name__ == "__main__":
    main()
