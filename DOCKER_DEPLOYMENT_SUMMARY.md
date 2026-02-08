# 🐳 Docker Deployment - TAMAMLANAN İŞLEMLER

## ✅ Oluşturulan Dosyalar

### Docker Konfigürasyon Dosyaları

```
docker/
├── docker-compose.yml              # Ana orchestration dosyası
├── gateway.Dockerfile              # Gateway API için
├── simple-api.Dockerfile           # Basit API için (Port 8001)
├── streamlit-simple.Dockerfile     # Streamlit Client (Port 8501)
├── streamlit-gateway.Dockerfile    # Gateway Client (Port 8502)
├── setup.sh                        # Kurulum scripti
└── README.md                       # Detaylı dokümantasyon
```

### API ve Client Dosyaları

```
apps/
├── api/
│   ├── main.py                     # [Mevcut] Basit API
│   └── gateway.py                  # [YENİ] Full Gateway API
├── web/
│   ├── streamlit_app.py            # [Mevcut] Basit Client
│   └── chat_client.py              # [YENİ] Gateway Client
└── ARCHITECTURE.md                 # [YENİ] Mimari dokümantasyon

tests/
├── test_integration.py
├── test_ollama.py
└── test_gateway.py                 # [YENİ] Gateway test süiti
```

---

## 🎯 PORT YAPISI (Çakışma Yok!)

| Servis | Port | Açıklama |
|--------|------|----------|
| **Ollama** | 11434 | AI Model Server |
| **Gateway API** | 8000 | Full API (Auth, Rate Limit, Chat Modülü) |
| **Simple API** | 8001 | Basit API (Gateway'den farklı) |
| **Streamlit Simple** | 8501 | Basit Client UI |
| **Streamlit Gateway** | 8502 | Gateway Client UI (farklı port) |
| **Redis** | 6379 | Cache & Session Store |

✅ **Tüm portlar farklı - çakışma yok!**

---

## 🚀 BAŞLATMA ADIMLARI

### 1. Docker Kurulumunu Kontrol Et

```bash
cd docker
chmod +x setup.sh
./setup.sh
```

### 2. Tüm Servisleri Başlat

```bash
cd docker
docker-compose up -d
```

### 3. Servislerin Başladığını Kontrol Et

```bash
# Tüm servislerin durumu
docker-compose ps

# Health check
curl http://localhost:8000/health
curl http://localhost:8001/health

# Logları görüntüle
docker-compose logs -f
```

### 4. Web Arayüzlerine Eriş

- **Gateway API Docs**: http://localhost:8000/docs
- **Simple API Docs**: http://localhost:8001/docs
- **Streamlit Simple**: http://localhost:8501
- **Streamlit Gateway**: http://localhost:8502
- **Ollama API**: http://localhost:11434

---

## 🧪 TEST

### Manuel Test

```bash
# 1. Gateway Health Check
curl http://localhost:8000/health

# 2. Gateway Chat Test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "message": "Merhaba Docker!",
    "user_id": "test_user",
    "session_id": "test_session",
    "model": "ollama/qwen2.5:7b"
  }'

# 3. Simple API Test
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"user_query": "Merhaba", "model": "ollama/qwen2.5:7b"}'
```

### Python Test Süiti

```bash
python tests/test_gateway.py
```

---

## 🎨 ÖZELLİKLER

### Gateway API (Port 8000)
✅ **Authentication** - API Key ile güvenlik  
✅ **Rate Limiting** - 60 istek/dakika  
✅ **Chat Modülü** - Session + Memory + Cost Tracking  
✅ **Safety Engine** - Guardrails  
✅ **WebSocket** - Real-time chat  
✅ **Session History** - Sohbet geçmişi  

### Simple API (Port 8001)
✅ **Basit REST API** - Stateless query  
✅ **CORS** - Cross-origin desteği  
✅ **Health Check** - Monitoring  

### Streamlit Clients
✅ **Simple Client** (8501) - Basit API'ye bağlanır  
✅ **Gateway Client** (8502) - Gateway API'ye bağlanır  
✅ **Session Management UI** - Kullanıcı ve session ID girişi  
✅ **Cost Tracking** - Maliyet gösterimi  
✅ **Chat History** - Geçmiş yükleme  

---

## 🐳 DOCKER SERVİSLERİ

### 1. Ollama
- **Image**: `ollama/ollama:latest`
- **Port**: 11434
- **Volume**: `ollama_data` (modeller kalıcı)
- **Amaç**: LLM modellerini çalıştırma

### 2. Gateway API
- **Build**: `docker/gateway.Dockerfile`
- **Port**: 8000
- **Volume**: `gateway_data` (SQLite DB)
- **Bağlı**: Ollama, Redis
- **Amaç**: Production-ready API

### 3. Simple API
- **Build**: `docker/simple-api.Dockerfile`
- **Port**: 8001
- **Bağlı**: Ollama
- **Amaç**: Basit REST API

### 4. Streamlit Simple
- **Build**: `docker/streamlit-simple.Dockerfile`
- **Port**: 8501
- **Bağlı**: Simple API
- **Amaç**: Basit UI

### 5. Streamlit Gateway
- **Build**: `docker/streamlit-gateway.Dockerfile`
- **Port**: 8502
- **Bağlı**: Gateway API
- **Amaç**: Advanced UI

### 6. Redis
- **Image**: `redis:7-alpine`
- **Port**: 6379
- **Volume**: `redis_data`
- **Amaç**: Cache & Session store

---

## 🔧 KOMUTLAR

### Docker Compose

```bash
# Tüm servisleri başlat
docker-compose up -d

# Tüm servisleri durdur
docker-compose down

# Tek bir servisi yeniden başlat
docker-compose restart gateway-api

# Logları görüntüle
docker-compose logs -f

# Servis detayları
docker-compose ps

# Volume'ları temizle (TÜM VERİ SİLİNİR!)
docker-compose down -v
```

### Docker Temizlik

```bash
# Kullanılmayan container'ları temizle
docker container prune

# Kullanılmayan imageları temizle
docker image prune

# Kullanılmayan volume'ları temizle
docker volume prune

# Her şeyi temizle
docker system prune -a
```

---

## 🎯 PRODUCTION ÖNERİLERİ

### 1. Güvenlik
- API Key'leri değiştir: `dev-key-change-in-production`
- HTTPS sertifikası ekle
- Reverse proxy (Nginx/Traefik) kullan
- Rate limiting'i ayarla

### 2. Monitoring
- Prometheus + Grafana
- Centralized logging (ELK)
- Health check endpoint'lerini kullan

### 3. Backup
- SQLite database'ini yedekle
- Ollama modellerini yedekle
- Redis data'sını yedekle

### 4. Scaling
- Load balancer arkasına al
- Multiple Gateway API instances
- Redis cluster
- PostgreSQL (SQLite yerine)

---

## 🐛 TROUBLESHOOTING

### Port Çakışması
```bash
# Port kullanımını kontrol et
netstat -tuln | grep 8000

# Ya da docker-compose.yml'de port değiştir
```

### Ollama Bağlantı Hatası
```bash
# Ollama container'ını kontrol et
docker-compose logs ollama

# Manuel model indir
docker-compose exec ollama ollama pull qwen2.5:7b
```

### Memory Sorunları
```bash
# Docker memory kullanımı
docker stats

# Volume temizliği
docker volume prune
```

---

## 📊 BAŞARI ÖLÇÜTLERİ

✅ **Tüm Docker dosyaları oluşturuldu**  
✅ **Port çakışması önlendi** (8000, 8001, 8501, 8502)  
✅ **Gateway API tamamlandı** (Chat modülü ile)  
✅ **Test süiti hazır**  
✅ **Dokümantasyon tamamlandı**  

**Durum**: 🎉 **HAZIR!**

---

**Hazırlayan**: Winston, Barry, Murat, Sally  
**Tarih**: 2024-02-08  
**Versiyon**: 2.0.0-Docker
