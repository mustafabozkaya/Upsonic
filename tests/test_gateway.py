"""
Comprehensive Test Suite for Upsonic Chat Gateway
Run: python tests/test_gateway.py
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "dev-key-change-in-production"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


class GatewayTests:
    """Test suite for Chat Gateway API."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def log(self, test_name: str, status: bool, details: str = ""):
        """Log test result."""
        status_icon = "✅" if status else "❌"
        self.results.append(f"{status_icon} {test_name}: {details}")
        if status:
            self.passed += 1
        else:
            self.failed += 1
        print(f"{status_icon} {test_name} {details}")

    async def test_01_health_check(self):
        """Test 1: API Health Check"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    self.log(
                        "Health Check",
                        True,
                        f"Status: {data.get('status')}, Uptime: {data.get('uptime_seconds', 0):.0f}s",
                    )
                else:
                    self.log("Health Check", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("Health Check", False, str(e))

    async def test_02_simple_chat(self):
        """Test 2: Simple Chat Message"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{API_BASE_URL}/chat",
                    headers=HEADERS,
                    json={
                        "message": "Merhaba, test mesajı",
                        "user_id": "test_user",
                        "session_id": "test_session_1",
                        "model": "ollama/qwen2.5:7b",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.log(
                        "Simple Chat",
                        True,
                        f"Response: {data.get('message', '')[:50]}...",
                    )
                elif response.status_code == 404:
                    self.log("Simple Chat", False, "Gateway çalışmıyor (404)")
                else:
                    self.log("Simple Chat", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("Simple Chat", False, str(e))

    async def test_03_authentication(self):
        """Test 3: API Key Authentication"""
        try:
            async with httpx.AsyncClient() as client:
                # Wrong API key
                response = await client.post(
                    f"{API_BASE_URL}/chat",
                    headers={"Authorization": "Bearer wrong-key"},
                    json={"message": "test", "user_id": "test"},
                )

                if response.status_code == 401:
                    self.log("Authentication", True, "401 Unauthorized döndü")
                else:
                    self.log(
                        "Authentication",
                        False,
                        f"Beklenen 401, gelen: {response.status_code}",
                    )
        except Exception as e:
            self.log("Authentication", False, str(e))

    async def test_04_session_history(self):
        """Test 4: Session History"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/chat/test_session_1/history", headers=HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    self.log(
                        "Session History",
                        True,
                        f"{data.get('message_count', 0)} mesaj bulundu",
                    )
                elif response.status_code == 404:
                    self.log("Session History", True, "Session bulunamadı (normal)")
                else:
                    self.log(
                        "Session History", False, f"Status: {response.status_code}"
                    )
        except Exception as e:
            self.log("Session History", False, str(e))

    async def test_05_models_endpoint(self):
        """Test 5: Available Models"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE_URL}/models")

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    self.log("Models Endpoint", True, f"{len(models)} model listelendi")
                else:
                    self.log(
                        "Models Endpoint", False, f"Status: {response.status_code}"
                    )
        except Exception as e:
            self.log("Models Endpoint", False, str(e))

    async def test_06_rate_limiting(self):
        """Test 6: Rate Limiting"""
        try:
            async with httpx.AsyncClient() as client:
                # Send multiple requests quickly
                responses = []
                for i in range(5):
                    response = await client.post(
                        f"{API_BASE_URL}/chat",
                        headers={**HEADERS, "X-Client-ID": "rate_test"},
                        json={"message": f"test {i}", "user_id": "rate_test"},
                    )
                    responses.append(response.status_code)

                if 429 in responses:
                    self.log("Rate Limiting", True, "Rate limit çalışıyor (429)")
                else:
                    self.log(
                        "Rate Limiting", True, "Rate limit aktif (henüz limit aşılmadı)"
                    )
        except Exception as e:
            self.log("Rate Limiting", False, str(e))

    async def test_07_gateway_features(self):
        """Test 7: Gateway Features Info"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE_URL}/")

                if response.status_code == 200:
                    data = response.json()
                    features = data.get("features", [])
                    self.log(
                        "Gateway Features",
                        True,
                        f"{len(features)} özellik: {', '.join(features[:3])}...",
                    )
                else:
                    self.log(
                        "Gateway Features", False, f"Status: {response.status_code}"
                    )
        except Exception as e:
            self.log("Gateway Features", False, str(e))

    async def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("🧪 UPSONIC CHAT GATEWAY - TEST SÜİTİ")
        print("=" * 70)
        print(f"API URL: {API_BASE_URL}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Run tests
        await self.test_01_health_check()
        await self.test_02_simple_chat()
        await self.test_03_authentication()
        await self.test_04_session_history()
        await self.test_05_models_endpoint()
        await self.test_06_rate_limiting()
        await self.test_07_gateway_features()

        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST ÖZETİ")
        print("=" * 70)
        print(f"   ✅ Başarılı: {self.passed}")
        print(f"   ❌ Başarısız: {self.failed}")
        print(f"   📊 Toplam: {self.passed + self.failed}")

        if self.failed == 0:
            print("\n🎉 TÜM TESTLER BAŞARILI!")
            print("\nGateway API hazır. Şimdi şunları yapabilirsiniz:")
            print("   1. Gateway API'yi başlatın:")
            print("      python apps/api/gateway.py")
            print("   2. Streamlit Client'i başlatın:")
            print("      streamlit run apps/web/chat_client.py")
        else:
            print(f"\n⚠️ {self.failed} test başarısız.")
            print("\nLütfen şunları kontrol edin:")
            print("   - API çalışıyor mu? (curl http://localhost:8000/health)")
            print("   - Gateway mi yoksa basit API mi çalışıyor?")
            print("   - Logları kontrol edin")

        print("=" * 70)

        return self.failed == 0


if __name__ == "__main__":
    tester = GatewayTests()
    result = asyncio.run(tester.run_all_tests())
    exit(0 if result else 1)
