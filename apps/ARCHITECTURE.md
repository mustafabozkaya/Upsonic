# Upsonic AI Agent - Client/Server Architecture

## 🏗️ Mimari Genel Bakış

Bu proje **Client-Server** mimarisi kullanarak Upsonic AI Agent Framework'ü web arayüzüne taşır:

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT TIER                          │
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │   Web Browser   │    │   Mobile/Desktop App     │   │
│  │   (Streamlit)   │    │   (Any HTTP Client)      │   │
│  └────────┬────────┘    └────────────┬─────────────┘   │
└───────────┼──────────────────────────┼─────────────────┘
            │                          │
            │ HTTP/REST                │ HTTP/REST
            ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│                  API TIER (FastAPI)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  POST /query                                    │   │
│  │  ├── Pydantic Validation                        │   │
│  │  ├── Multi-model Support                        │   │
│  │  ├── Agent Execution (Ollama)                   │   │
│  │  └── JSON Response                              │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 AI TIER (Upsonic + Ollama)              │
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │   Upsonic       │───▶│   Ollama Server          │   │
│  │   Agent Framework│    │   (Local LLM)            │   │
│  └─────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## ✨ Özellikler

### Backend (FastAPI)
- ✅ **RESTful API** - Standart HTTP endpoint'leri
- ✅ **Multi-model Support** - Farklı Ollama modelleri arasında geçiş
- ✅ **CORS Enabled** - Cross-origin isteklere izin
- ✅ **Health Check** - Monitoring için `/health` endpoint'i
- ✅ **Pydantic Validation** - Tip güvenliği ve otomatik dokümantasyon
- ✅ **Async Processing** - Asenkron işleme desteği

### Frontend (Streamlit)
- ✅ **Pure Client** - Doğrudan Upsonic kullanmak yerine API'ye istek atar
- ✅ **Connection Monitoring** - API bağlantı durumunu izler
- ✅ **Model Selection** - Kullanıcı model seçebilir
- ✅ **Chat Interface** - Gerçek zamanlı sohbet arayüzü
- ✅ **Configuration** - Ortam değişkenleri ile yapılandırma

## 🚀 Başlangıç

### 1. Ortam Değişkenleri

`.env` dosyası oluşturun:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=api-key-not-set

# API Server Configuration (Client için)
UPSONIC_API_URL=http://localhost:8000
```

### 2. Backend'i Başlatın

```bash
# Terminal 1 - API Server
chmod +x scripts/run_api.sh
./scripts/run_api.sh

# Veya direkt:
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

API şu adreslerde çalışacak:
- API: http://localhost:8000
- Dokümantasyon: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Frontend'i Başlatın

```bash
# Terminal 2 - Streamlit Client
chmod +x scripts/run_streamlit.sh
./scripts/run_streamlit.sh

# Veya direkt:
streamlit run apps/web/streamlit_app.py
```

Streamlit şu adreste çalışacak:
- Web Arayüzü: http://localhost:8501

## 📡 API Kullanımı

### HTTP Endpoint'ler

#### 1. Query Endpoint
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Python nedir?",
    "model": "ollama/qwen2.5:7b"
  }'
```

**Response:**
```json
{
  "user_query": "Python nedir?",
  "bot_response": "Python, yüksek seviyeli bir programlama dilidir...",
  "model_used": "ollama/qwen2.5:7b",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### 2. Health Check
```bash
curl "http://localhost:8000/health"
```

#### 3. Root Info
```bash
curl "http://localhost:8000/"
```

### Python Client

```python
import httpx
import asyncio

async def query_agent(question: str, model: str = "ollama/qwen2.5:7b"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/query",
            json={
                "user_query": question,
                "model": model
            }
        )
        return response.json()

# Kullanım
result = asyncio.run(query_agent("Python nedir?"))
print(result["bot_response"])
```

## 🔧 Konfigürasyon

### Backend Konfigürasyonu

`apps/api/main.py` içinde:
- `DEFAULT_MODEL`: Varsayılan Ollama modeli
- `OLLAMA_BASE_URL`: Ollama sunucu adresi
- CORS ayarları (production'da kısıtlayın)

### Frontend Konfigürasyonu

Ortam değişkenleri:
- `UPSONIC_API_URL`: Backend API adresi
- `OLLAMA_BASE_URL`: Ollama sunucu adresi (opsiyonel, gösterim için)

## 🧪 Test

### Manuel Test

1. API'nin çalıştığını kontrol edin:
```bash
curl http://localhost:8000/health
```

2. Streamlit'te "Bağlantıyı Kontrol Et" butonuna tıklayın

3. Soru sorun ve yanıt aldığınızı doğrulayın

### Programatik Test

```bash
# API test
python apps/api/main.py

# Streamlit test
streamlit run apps/web/streamlit_app.py
```

## 📁 Proje Yapısı

```
apps/
├── api/
│   └── main.py              # FastAPI backend
└── web/
    └── streamlit_app.py     # Streamlit frontend (API client)

scripts/
├── run_api.sh               # API başlatma scripti
└── run_streamlit.sh         # Streamlit başlatma scripti

config/
└── upsonic_configs.json     # Yapılandırma ve şema tanımları
```

## 🎯 Mimari Avantajları

### 1. Separation of Concerns (SoC)
- **UI Layer**: Streamlit sadece presentation
- **Business Logic**: FastAPI'de konsantre
- **AI Layer**: Upsonic Agent framework

### 2. Ölçeklenebilirlik
- API bağımsız deploy edilebilir
- Load balancer arkasına alınabilir
- Containerization (Docker) kolay

### 3. Multi-Client Desteği
- Web (Streamlit)
- Mobile (iOS/Android HTTP client)
- CLI (curl, Python scripts)
- Tümü aynı API'yi kullanır

### 4. Test Edilebilirlik
- API endpoint'leri bağımsız test edilebilir
- Mock server ile UI testleri
- Integration testleri kolay

### 5. Güvenlik
- API anahtarları backend'de
- Authentication/Authorization merkezi
- Input validation Pydantic ile

## 🚀 Production İçin Öneriler

### 1. Güvenlik
- API Key authentication ekle
- HTTPS kullan
- Rate limiting implemente et
- CORS origins kısıtla

### 2. Monitoring
- Prometheus metrics ekle
- Logging yapılandırması
- Health check endpoint'ini kullan

### 3. Deployment
- Docker containerization
- Kubernetes deployment
- Load balancer arkasına al

### 4. Performance
- Redis caching ekle
- Connection pooling
- Async database (opsiyonel)

## 🐛 Hata Ayıklama

### API Bağlantı Hatası
```
❌ API sunucusuna bağlanılamıyor
```
**Çözüm:** API'nin çalıştığından emin olun: `python -m uvicorn apps.api.main:app --reload`

### Ollama Bağlantı Hatası
```
Error connecting to Ollama
```
**Çözüm:** Ollama'nın çalıştığından emin olun: `ollama serve`

### Model Hatası
```
Model not found
```
**Çözüm:** Model'i indirin: `ollama pull qwen2.5:7b`

## 📝 Lisans

MIT License

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'feat: Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

---

**Hazırlayanlar:** Winston (Mimari), Barry (Hızlı Geliştirici), Sally (UX), Amelia (Geliştirici), Murat (Test), Paige (Dokümantasyon)

**Parti Modu Katkıları:** 🎉
