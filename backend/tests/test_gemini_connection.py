"""
DevPilot AI - Gemini API Connection Test
Tests the initialization, configuration, and connectivity of Google Gemini API.
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.gemini_service import GeminiService


def test_settings_loaded():
    assert settings.PROJECT_NAME == "DevPilot AI"
    assert settings.GEMINI_MODEL is not None
    print(f"[*] Configured Gemini Model: {settings.GEMINI_MODEL}")
    print(f"[*] Gemini configured: {settings.is_gemini_configured}")


def test_connection():
    service = GeminiService()
    result = service.test_connection()
    print(f"[*] Connection result: {result}")
    
    if not settings.is_gemini_configured:
        print("[!] GEMINI_API_KEY is not yet configured in backend/.env")
        assert result["configured"] is False
    else:
        print(f"[+] Gemini connection successful! Latency: {result.get('latency_ms')}ms")
        assert result["success"] is True


if __name__ == "__main__":
    test_settings_loaded()
    test_connection()
