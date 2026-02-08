"""
Streamlit Web Client for Upsonic AI Agent API
Pure client implementation - calls FastAPI backend
"""

import os
import streamlit as st
import httpx
import asyncio
from typing import Optional

# API Configuration
API_BASE_URL = os.environ.get("UPSONIC_API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Upsonic AI Agent Client",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Default models (fallback if API is not available)
DEFAULT_MODELS = [
    "ollama/qwen2.5:7b",
    "ollama/llama3.2:3b",
    "ollama/llama3.2:1b",
    "ollama/gemma3:4b",
]

# CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .api-status {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .api-online {
        background-color: #d4edda;
        color: #155724;
    }
    .api-offline {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""",
    unsafe_allow_html=True,
)


async def check_api_health() -> tuple[bool, dict]:
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": f"Status: {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


async def query_api(user_query: str, model: str) -> tuple[bool, str]:
    """
    Send query to the API server.

    Args:
        user_query: The user's question
        model: The Ollama model to use

    Returns:
        Tuple of (success, response_or_error)
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/query", json={"user_query": user_query, "model": model}
            )

            if response.status_code == 200:
                data = response.json()
                return True, data.get("bot_response", "No response received")
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                return False, error_msg

    except httpx.ConnectError:
        return (
            False,
            "❌ API sunucusuna bağlanılamıyor. Lütfen API'nin çalıştığından emin olun.",
        )
    except httpx.TimeoutException:
        return False, "⏱️ İstek zaman aşımına uğradı. Lütfen tekrar deneyin."
    except Exception as e:
        return False, f"❌ Beklenmeyen hata: {str(e)}"


def get_response_sync(query: str, model: str) -> tuple[bool, str]:
    """Get response from API synchronously."""

    async def run_query():
        return await query_api(query, model)

    return asyncio.run(run_query())


async def fetch_available_models():
    """
    Fetch available models from the API.

    Returns:
        Tuple of (success, list_of_models, source)
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/models")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                source = data.get("source", "unknown")
                return True, models, source
            else:
                return False, DEFAULT_MODELS, "fallback"

    except Exception as e:
        return False, DEFAULT_MODELS, "fallback"


def get_available_models_sync():
    """Get available models synchronously."""

    async def run_fetch():
        return await fetch_available_models()

    return asyncio.run(run_fetch())


def render_sidebar():
    """Render the sidebar with settings."""
    st.sidebar.title("⚙️ Ayarlar")

    # API URL configuration
    st.sidebar.markdown("### 🔌 API Bağlantısı")
    api_url = st.sidebar.text_input(
        "API URL", value=API_BASE_URL, help="FastAPI sunucusunun URL'i"
    )

    # Check API status
    if st.sidebar.button("🔄 Bağlantıyı Kontrol Et"):
        with st.sidebar:
            with st.spinner("Kontrol ediliyor..."):
                is_healthy, health_data = asyncio.run(check_api_health())
                if is_healthy:
                    st.success(
                        f"✅ API Çevrimiçi\n\nBaşlangıç: {health_data.get('startup_time', 'Bilinmiyor')}"
                    )
                else:
                    st.error(
                        f"❌ API Çevrimdışı\n\nHata: {health_data.get('error', 'Bağlantı hatası')}"
                    )

    st.sidebar.markdown("---")

    # Model selection - Dynamic from API
    st.sidebar.markdown("### 🤖 Model Ayarları")

    # Fetch available models (cached in session state)
    if "available_models" not in st.session_state:
        with st.sidebar:
            with st.spinner("Modeller yükleniyor..."):
                success, models, source = get_available_models_sync()
                st.session_state.available_models = models
                st.session_state.models_source = source
                if success and source == "ollama":
                    st.success(f"✅ {len(models)} model Ollama'dan yüklendi")
                else:
                    st.info(f"ℹ️ Varsayılan modeller kullanılıyor")

    available_models = st.session_state.get("available_models", DEFAULT_MODELS)
    models_source = st.session_state.get("models_source", "fallback")

    selected_model = st.sidebar.selectbox(
        "Model Seçiniz",
        available_models,
        index=0,
        help=f"Kullanılacak Ollama modelini seçin (Kaynak: {models_source})",
    )

    # Show model source
    if models_source == "ollama":
        st.sidebar.caption(f"🟢 Canlı: Ollama'dan {len(available_models)} model")
    else:
        st.sidebar.caption(f"⚪ Varsayılan: {len(available_models)} model")

    # Temperature slider
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Düşük değer daha tutarlı, yüksek değer daha yaratıcı yanıtlar üretir",
    )

    # Clear chat button
    if st.sidebar.button("🗑️ Sohbeti Temizle"):
        if "messages" in st.session_state:
            st.session_state.messages = []
        st.rerun()

    st.sidebar.markdown("---")

    # System status
    st.sidebar.markdown("### 📊 Sistem Durumu")
    st.sidebar.markdown(f"**API URL:** `{api_url}`")
    st.sidebar.markdown(f"**Aktif Model:** {selected_model}")
    st.sidebar.markdown(f"**Temperature:** {temperature}")
    st.sidebar.markdown(f"**Streamlit:** {st.__version__}")

    return selected_model, temperature, api_url


def render_chat_interface(selected_model: str):
    """Render the main chat interface."""
    st.markdown("### 💬 Sohbet")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Sorunuzu yazınız..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Düşünüyor..."):
                success, response = get_response_sync(prompt, selected_model)

                if success:
                    st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                else:
                    st.error(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )


def render_examples():
    """Render example questions section."""
    with st.expander("💡 Örnek Sorular", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Python nedir?"):
                st.session_state.user_input = "Python nedir?"

        with col2:
            if st.button("Türkiye'nin başkenti neresidir?"):
                st.session_state.user_input = "Türkiye'nin başkenti neresidir?"


def main():
    """Main Streamlit application."""

    # Header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🤖 Upsonic AI Agent Client")
    st.markdown("FastAPI backend ile çalışan modern AI chat arayüzü")
    st.markdown("</div>", unsafe_allow_html=True)

    # Show architecture info
    with st.expander("🏗️ Mimari Bilgisi", expanded=False):
        st.markdown("""
        **Client-Server Mimarisi:**
        
        ```
        Streamlit Client → HTTP/REST → FastAPI Server → Upsonic Agent → Ollama
        ```
        
        **Avantajlar:**
        - ✅ **Separation of Concerns**: UI ve iş mantığı ayrılmıştır
        - ✅ **Ölçeklenebilirlik**: API bağımsız deploy edilebilir
        - ✅ **Multi-Client**: Web, mobile, CLI aynı API'yi kullanabilir
        - ✅ **Test Edilebilirlik**: API endpoint'leri bağımsız test edilebilir
        - ✅ **Güvenlik**: API anahtarları ve yetkilendirme backend'de tutulur
        """)

    # Render sidebar and get settings
    selected_model, temperature, api_url = render_sidebar()

    # Render chat interface
    render_chat_interface(selected_model)

    # Render examples
    render_examples()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: gray;">
            Upsonic AI Agent Framework • FastAPI Backend • Streamlit Client
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
