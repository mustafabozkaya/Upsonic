# 🐳 Docker Deployment - HOST OLLAMA YAPISI

## 📋 ÖNEMLİ NOT

⚠️ **Ollama host makinede çalışıyor!** Docker container'ları host'daki Ollama'ya bağlanıyor.

- Host Ollama: http://localhost:11434
- Docker'dan erişim: http://host.docker.internal:11434

## 🎯 PORT YAPISI

| Servis | Port | Konum |
|--------|------|-------|
| **Ollama** | 11434 | Host Makine ⚠️ |
| **Gateway API** | 8000 | Docker |
| **Simple API** | 8001 | Docker |
| **Streamlit Simple** | 8501 | Docker |
| **Streamlit Gateway** | 8502 | Docker |
| **Redis** | 6379 | Docker |

✅ Port çakışması yok!

## 🚀 HIZLI BAŞLANGIÇ

### 1. Ollama'yı Kontrol Et

```bash
# Host makinede Ollama çalışıyor mu?
curl http://localhost:11434/api/tags

# Model yüklü mü?
ollama list

# Model yoksa yükle:
ollama pull qwen2.5:7b
```

### 2. Docker Servislerini Başlat

```bash
cd docker

# Ollama kontrolü ile birlikte başlat
chmod +x setup.sh
./setup.sh

# Servisleri başlat
docker-compose up -d
```

### 3. Test Et

```bash
# Hızlı test
chmod +x test.sh
./test.sh

# Veya manuel test
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## 📁 DOCKER DOSYA YAPISI

```
docker/
├── docker-compose.yml           # Ana orchestration (Ollama YOK)
├── gateway.Dockerfile          # Gateway API (host.docker.internal kullanır)
├── simple-api.Dockerfile       # Simple API (host.docker.internal kullanır)
├── streamlit-simple.Dockerfile # Streamlit Simple Client
├── streamlit-gateway.Dockerfile# Streamlit Gateway Client
├── setup.sh                    # Kurulum scripti (Ollama kontrolü)
├── check-ollama.sh            # Ollama kontrol scripti
├── test.sh                    # Hızlı test scripti
└── README.md                  # Detaylı dokümantasyon
```

## 🔧 DOCKER-COMPOSE.YML DEĞİŞİKLİKLERİ

### ❌ KALDIRILAN:
- Ollama servisi (container olarak)
- Ollama volume'u
- depends_on: ollama

### ✅ EKLENEN:
- `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`
- `extra_hosts: host.docker.internal`

## 🌐 SERVİS ERİŞİMİ

### Host Makineden:
```bash
# Ollama (Host)
curl http://localhost:11434/api/tags

# Gateway API (Docker)
curl http://localhost:8000/health

# Simple API (Docker)
curl http://localhost:8001/health

# Web Arayüzleri
curl http://localhost:8501  # Streamlit Simple
curl http://localhost:8502  # Streamlit Gateway
```

### Docker Container'dan Host'a:
```python
# Gateway API içinden Ollama'ya erişim
OLLAMA_BASE_URL = "http://host.docker.internal:11434/v1"
```

## 🧪 TEST KOMUTLARI

```bash
# 1. Ollama kontrol
curl http://localhost:11434/api/tags

# 2. Gateway API test
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"message":"Merhaba","user_id":"test"}'

# 3. Simple API test
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"user_query":"Merhaba","model":"ollama/qwen2.5:7b"}'

# 4. Tüm testler
./test.sh
```

## 🔍 SORUN GİDERME

### Ollama Bağlantı Hatası

**Hata:** Docker container Ollama'ya bağlanamıyor

**Çözüm:**
```bash
# 1. Ollama host'ta çalışıyor mu kontrol et
curl http://localhost:11434/api/tags

# 2. Ollama tüm IP'lere dinliyor mu kontrol et
ollama serve --help
# Varsayılan olarak 127.0.0.1 dinler, tüm IP'ler için:
OLLAMA_HOST=0.0.0.0 ollama serve

# 3. Windows'ta host.docker.internal erişimi
# Docker Desktop > Settings > Resources > Network
# "Use host networking" aktif mi kontrol et
```

### Port Çakışması

**Hata:** Port zaten kullanımda

**Çözüm:**
```bash
# Port kullanımını kontrol et
netstat -tuln | grep 8000

# Veya docker-compose.yml'de port değiştir
# ports:
#   - "8002:8000"  # Host portu değiştir
```

## 📊 SERVİS DURUMU

```bash
# Tüm servisleri gör
docker-compose ps

# Logları izle
docker-compose logs -f

# Belirli servis logu
docker-compose logs -f gateway-api
```

## 🎯 KOMUT REFERANSI

```bash
# Başlat
docker-compose up -d

# Durdur
docker-compose down

# Yeniden başlat
docker-compose restart

# Tek servisi yeniden başlat
docker-compose restart gateway-api

# Loglar
docker-compose logs -f

# Temizlik
docker-compose down -v  # Verileri de sil!
```

## ✅ BAŞARI ÖLÇÜTLERİ

- ✅ Ollama host makinede çalışıyor
- ✅ Docker servisleri host Ollama'ya bağlanıyor
- ✅ Port çakışması yok (8000, 8001, 8501, 8502)
- ✅ Gateway API Authentication çalışıyor
- ✅ Chat modülü Session management yapıyor
- ✅ Test scriptleri hazır

## 🎉 TAMAM!

Baba, Docker yapısı **Host Ollama** ile güncellendi!

**Önemli:** Ollama'yı başlatmayı unutma:
```bash
ollama serve
```

Parti modunda takım hazır! 🚀
