# Upsonic Docker Deployment Guide

## 🐳 Docker Mimarisi

Bu Docker kurulumu aşağıdaki servisleri içerir:

### Servisler ve Portlar

| Servis | Port | Açıklama |
|--------|------|----------|
| **Ollama** | 11434 | AI Model Server (LLM'ler burada çalışır) |
| **Gateway API** | 8000 | Full API Gateway (Auth, Rate Limiting, Chat Modülü) |
| **Simple API** | 8001 | Basit REST API (Gateway ile çakışmaz) |
| **Streamlit Simple** | 8501 | Basit API Client UI |
| **Streamlit Gateway** | 8502 | Gateway Client UI (8501 ile çakışmaz) |
| **Redis** | 6379 | Cache & Session Store |

### Port Çakışması Önleme

✅ **Gateway API** → 8000  
✅ **Simple API** → 8001 (farklı port)  
✅ **Streamlit Simple** → 8501  
✅ **Streamlit Gateway** → 8502 (farklı port)  

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
cd docker
chmod +x setup.sh
./setup.sh
```

### 2. Servisleri Başlatma

```bash
# Tüm servisleri başlat
docker-compose up -d

# Logları görüntüle
docker-compose logs -f

# Belirli bir servisin loglarını gör
docker-compose logs -f gateway-api
```

### 3. Servisleri Kontrol Etme

```bash
# Tüm servislerin durumu
docker-compose ps

# Health check
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### 4. Servisleri Durdurma

```bash
# Tüm servisleri durdur
docker-compose down

# Volumes ile birlikte temizle (TÜM VERİ SİLİNİR!)
docker-compose down -v
```

## 📡 API Kullanımı

### Gateway API (Port 8000)

```bash
# Health check
curl http://localhost:8000/health

# Chat mesajı gönder
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "message": "Merhaba!",
    "user_id": "user_123",
    "session_id": "session_456",
    "model": "ollama/qwen2.5:7b"
  }'

# Session history
curl http://localhost:8000/chat/session_456/history \
  -H "Authorization: Bearer dev-key-change-in-production"

# Mevcut modeller
curl http://localhost:8000/models
```

### Simple API (Port 8001)

```bash
# Health check
curl http://localhost:8001/health

# Query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Merhaba!",
    "model": "ollama/qwen2.5:7b"
  }'
```

## 🌐 Web Arayüzleri

### 1. Streamlit Simple Client (Port 8501)
- Basit API'ye bağlanır
- URL: http://localhost:8501
- Özellikler: Temel chat, dinamik model listesi

### 2. Streamlit Gateway Client (Port 8502)
- Gateway API'ye bağlanır
- URL: http://localhost:8502
- Özellikler: Session management, cost tracking, chat history

## 🔧 Ortam Değişkenleri

### `.env` dosyası oluşturun:

```env
# API Configuration
UPSONIC_API_KEY=your-production-api-key-here

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434/v1

# Database
UPSONIC_DB_URL=sqlite:///app/data/chat_sessions.db
```

## 🧪 Test

```bash
# Gateway testleri
python tests/test_gateway.py

# Tüm testler
pytest tests/ -v
```

## 📊 Monitoring

### Docker Stats
```bash
docker stats
```

### Logs
```bash
# Tüm loglar
docker-compose logs

# Tail mode
docker-compose logs -f --tail=100
```

## 🔒 Güvenlik Notları

1. **API Key**: Production'da `dev-key-change-in-production` değiştirilmeli
2. **Rate Limiting**: Gateway'de 60 req/min aktif
3. **CORS**: Development için `*` izinli, production'da kısıtlanmalı
4. **Network**: Servisler izole Docker network'ünde

## 🐛 Troubleshooting

### Port Çakışması
Eğer portlar çakışıyorsa:

```bash
# Hangi servis kullanıyor kontrol et
netstat -tuln | grep 8000

# Ya da docker-compose.yml'de portları değiştir
# ports:
#   - "8002:8000"  # Farklı host port
```

### Ollama Bağlantı Hatası
```bash
# Ollama container'ının çalıştığını kontrol et
docker-compose ps ollama

# Ollama loglarını kontrol et
docker-compose logs ollama

# Manuel model indirme
docker-compose exec ollama ollama pull qwen2.5:7b
```

### Memory Issues
```bash
# Docker memory limitlerini kontrol et
docker system info | grep Memory

# Volume temizliği
docker volume prune
```

## 📁 Veri Kalıcılığı

Aşağıdaki veriler Docker volumes'ta saklanır:

- `ollama_data`: İndirilen modeller
- `gateway_data`: SQLite database (chat sessions)
- `redis_data`: Cache verisi

**Not:** `docker-compose down -v` komutu TÜM veriyi siler!

## 🔄 Güncelleme

```bash
# Son imajları çek
docker-compose pull

# Yeniden başlat
docker-compose up -d

# Eski imajları temizle
docker image prune
```

## 🎯 Production Önerileri

1. **API Key**: Güçlü bir key kullanın
2. **HTTPS**: SSL/TLS sertifikası ekleyin
3. **Reverse Proxy**: Nginx veya Traefik kullanın
4. **Monitoring**: Prometheus + Grafana ekleyin
5. **Logging**: Centralized logging (ELK stack)
6. **Backup**: SQLite database'ini yedekleyin

---

**Hazırlayan**: Winston (Mimari), Barry (Implementasyon), Murat (Test), Sally (UI)
