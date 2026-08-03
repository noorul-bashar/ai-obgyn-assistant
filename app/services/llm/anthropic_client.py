"""
LLM Client supporting both Anthropic Claude API and Google GenAI (Gemini API).
Swaps automatically based on API key format or configured settings.
"""
from functools import lru_cache
import logging

from app.config import get_settings
from app.core.exceptions import LLMGenerationError
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)
settings = get_settings()


class AnthropicLLMClient(BaseLLMClient):
    """
    Wraps LLM generation. Supports both Anthropic Claude SDK and Google GenAI SDK
    depending on the API key prefix or model settings provided.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.LLM_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.api_key.startswith("sk-ant-"):
            return self._generate_anthropic(system_prompt, user_prompt)
        else:
            return self._generate_google(system_prompt, user_prompt)

    def _generate_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            model_name = self.model if self.model.startswith("claude") else "claude-3-5-sonnet-20241022"
            response = client.messages.create(
                model=model_name,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
            return "\n".join(text_blocks).strip()
        except Exception as exc:
            logger.error("Anthropic LLM generation failed: %s", exc)
            raise LLMGenerationError(str(exc)) from exc

    def _generate_google(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            model_name = self.model if self.model.startswith("gemini") else "gemini-2.5-flash"
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                ),
            )
            return (response.text or "").strip()
        except Exception as exc:
            logger.error("Google GenAI LLM generation failed: %s", exc)
            raise LLMGenerationError(str(exc)) from exc


@lru_cache
def get_llm_client() -> BaseLLMClient:
    """Cached so the LLM client is constructed once per process, not per request."""
    return AnthropicLLMClient()
