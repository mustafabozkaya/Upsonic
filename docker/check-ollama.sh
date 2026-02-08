#!/bin/bash
# Check if Ollama is running on host machine

echo "🔍 Host makinedeki Ollama kontrol ediliyor..."

# Try to connect to host Ollama
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
        echo "⚠️  Model bulunamadı. Ollama'ya model yükleyin:"
        echo "   ollama pull qwen2.5:7b"
    fi
    exit 0
else
    echo "❌ Ollama çalışmıyor veya erişilemiyor!"
    echo ""
    echo "🚀 Ollama'yı başlatmak için:"
    echo "   ollama serve"
    echo ""
    echo "💡 Model yüklemek için:"
    echo "   ollama pull qwen2.5:7b"
    echo "   ollama pull llama3.2:3b"
    exit 1
fi
