#!/bin/bash
# Docker setup script for Upsonic Chat Gateway with Host Ollama

echo "🐳 Upsonic Docker Kurulumu (Host Ollama)"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker kurulu değil!"
    echo "Lütfen Docker'ı yükleyin: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose kurulu değil!"
    echo "Lütfen Docker Compose'u yükleyin"
    exit 1
fi

echo "✅ Docker ve Docker Compose kurulu"
echo ""

# Check if Ollama is running on host
echo "🔍 Host makinedeki Ollama kontrol ediliyor..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama çalışıyor (http://localhost:11434)"
    
    # Get available models
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$MODELS" ]; then
        echo "📦 Yüklü modeller:"
        echo "$MODELS" | while read model; do
            echo "   • $model"
        done
    else
        echo "⚠️  Model bulunamadı!"
        echo "💡 Model yüklemek için:"
        echo "   ollama pull qwen2.5:7b"
        echo "   ollama pull llama3.2:3b"
    fi
else
    echo "❌ Ollama çalışmıyor!"
    echo ""
    echo "🚀 Ollama'yı başlatmak için:"
    echo "   ollama serve"
    echo ""
    echo "Devam etmek istiyor musunuz? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📁 Dizinler oluşturuldu"
echo ""
echo "🚀 Servisleri başlatmak için:"
echo "   cd docker"
echo "   docker-compose up -d"
echo ""
echo "📊 Servisler başladıktan sonra:"
echo "   Gateway API:  http://localhost:8000"
echo "   Simple API:   http://localhost:8001"
echo "   Streamlit:    http://localhost:8501 (Simple)"
echo "   Gateway UI:   http://localhost:8502 (Gateway)"
echo "   Ollama:       http://localhost:11434 (Host makine)"
echo ""
echo "🧪 Testleri çalıştırmak için:"
echo "   python tests/test_gateway.py"
echo ""
echo "🛑 Servisleri durdurmak için:"
echo "   cd docker"
echo "   docker-compose down"
