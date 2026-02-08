"""
Test script for Streamlit Client integration with FastAPI backend
"""

import asyncio
import httpx
import os
import sys

# Test configuration
API_BASE_URL = os.environ.get("UPSONIC_API_URL", "http://localhost:8000")


async def test_api_health():
    """Test 1: API Health Check"""
    print("\n🧪 Test 1: API Health Check")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API Sağlıklı")
                print(f"   📊 Status: {data.get('status')}")
                print(f"   🕐 Başlangıç: {data.get('startup_time')}")
                return True
            else:
                print(f"   ❌ API Status: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ API Bağlantı Hatası: {e}")
        return False


async def test_api_query():
    """Test 2: API Query Endpoint"""
    print("\n🧪 Test 2: API Query Endpoint")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/query",
                json={
                    "user_query": "Bu bir test mesajıdır",
                    "model": "ollama/qwen2.5:7b",
                },
            )

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Query başarılı")
                print(f"   🤖 Model: {data.get('model_used')}")
                print(f"   📝 Yanıt: {data.get('bot_response', '')[:100]}...")
                print(f"   ⏰ Timestamp: {data.get('timestamp')}")
                return True
            else:
                print(f"   ❌ Query Status: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return False
    except Exception as e:
        print(f"   ❌ Query Hatası: {e}")
        return False


def test_streamlit_code_structure():
    """Test 3: Streamlit Code Structure"""
    print("\n🧪 Test 3: Streamlit Kod Yapısı")

    try:
        with open("apps/web/streamlit_app.py", "r", encoding="utf-8") as f:
            code = f.read()

        checks = [
            ("API_BASE_URL tanımı", "API_BASE_URL = "),
            ("httpx import", "import httpx"),
            ("check_api_health fonksiyonu", "async def check_api_health"),
            ("query_api fonksiyonu", "async def query_api"),
            ("get_response_sync fonksiyonu", "def get_response_sync"),
            ("Streamlit import", "import streamlit"),
            ("st.set_page_config", "st.set_page_config"),
            ("st.chat_input", "st.chat_input"),
            ("main fonksiyonu", "def main():"),
            ('if __name__ == "__main__"', 'if __name__ == "__main__":'),
        ]

        all_passed = True
        for check_name, check_str in checks:
            if check_str in code:
                print(f"   ✅ {check_name}")
            else:
                print(f"   ❌ {check_name} eksik!")
                all_passed = False

        return all_passed
    except Exception as e:
        print(f"   ❌ Dosya okuma hatası: {e}")
        return False


def test_streamlit_syntax():
    """Test 4: Streamlit Syntax Check"""
    print("\n🧪 Test 4: Syntax Kontrolü")

    try:
        import ast

        with open("apps/web/streamlit_app.py", "r", encoding="utf-8") as f:
            code = f.read()

        ast.parse(code)
        print("   ✅ Python syntax doğru")

        # Check for common mistakes
        if "__main__:" in code and '__main__":' not in code:
            print("   ❌ __main__ syntax hatası tespit edildi!")
            return False

        print("   ✅ Syntax hatası yok")
        return True
    except SyntaxError as e:
        print(f"   ❌ Syntax Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Syntax kontrol hatası: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Upsonic Client/Server Entegrasyon Testleri")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("API Health", await test_api_health()))
    results.append(("API Query", await test_api_query()))
    results.append(("Code Structure", test_streamlit_code_structure()))
    results.append(("Syntax Check", test_streamlit_syntax()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST ÖZETİ")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"   {test_name:<20} {status}")

    print(f"\n   Toplam: {passed}/{total} test başarılı")

    if passed == total:
        print("\n🎉 TÜM TESTLER BAŞARILI! Sistem hazır.")
        print("\n🚀 Başlatma komutları:")
        print("   Terminal 1: python -m uvicorn apps.api.main:app --reload")
        print("   Terminal 2: streamlit run apps/web/streamlit_app.py")
        return True
    else:
        print(f"\n⚠️ {total - passed} test başarısız. Lütfen hataları düzeltin.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
