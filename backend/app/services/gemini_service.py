"""
Gemini Service for DevPilot AI.
Integrates with the official Google Gen AI SDK (google-genai).
Provides model verification, streaming generation, content generation,
conversation history, and function calling support.
"""

import logging
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client: Optional[genai.Client] = None
        
        if self._is_valid_key(self.api_key):
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self._client = None

    @staticmethod
    def _is_valid_key(key: Optional[str]) -> bool:
        return bool(key and key.strip() and not key.strip().startswith("your_"))

    def get_client(self) -> genai.Client:
        if not self._is_valid_key(self.api_key):
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env "
                "or obtain a key from https://aistudio.google.com/api-keys"
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def test_connection(self) -> Dict[str, Any]:
        """
        Verify Gemini API connectivity with configured model.
        Returns detailed status including latency, model name, and configuration status.
        """
        if not self._is_valid_key(self.api_key):
            return {
                "success": False,
                "configured": False,
                "model": self.model,
                "message": (
                    "GEMINI_API_KEY is not configured. Please provide a valid API key "
                    "from Google AI Studio (https://aistudio.google.com/api-keys)."
                ),
            }

        start_time = time.perf_counter()
        try:
            client = self.get_client()
            # Issue a minimal ping prompt to verify key validity and quota
            response = client.models.generate_content(
                model=self.model,
                contents="Ping. Respond with 'PONG' only.",
                config=types.GenerateContentConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            reply_text = response.text.strip() if response.text else ""
            return {
                "success": True,
                "configured": True,
                "model": self.model,
                "latency_ms": elapsed_ms,
                "reply": reply_text,
                "message": f"Successfully connected to Gemini API using model '{self.model}'."
            }
        except APIError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Gemini API Error: {e.message} (code: {e.code})")
            return {
                "success": False,
                "configured": True,
                "model": self.model,
                "error_code": e.code,
                "latency_ms": elapsed_ms,
                "message": f"Gemini API Error: {e.message}"
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected connection error: {str(e)}")
            return {
                "success": False,
                "configured": True,
                "model": self.model,
                "latency_ms": elapsed_ms,
                "message": f"Connection failed: {str(e)}"
            }

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        retries: int = 3
    ) -> str:
        """
        Generate content with exponential backoff retry logic for retryable network/quota errors.
        """
        client = self.get_client()
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens
        )

        last_error = None
        for attempt in range(retries):
            try:
                # Use loop.run_in_executor to avoid blocking the asyncio event loop
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config
                    )
                )
                if response and response.text:
                    return response.text
                return ""
            except APIError as e:
                last_error = e
                # Check for rate limit or temporary server errors (429, 500, 503)
                if e.code in (429, 500, 503) and attempt < retries - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Gemini API temporary error ({e.code}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = (2 ** attempt) + 1
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise RuntimeError(f"Failed to generate response after {retries} attempts: {last_error}")

    async def stream_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens from Gemini.
        """
        client = self.get_client()
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction
        )

        loop = asyncio.get_running_loop()
        # Fetch stream iterator
        stream = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=config
            )
        )

        for chunk in stream:
            if chunk.text:
                yield chunk.text


# Default singleton instance
gemini_service = GeminiService()
