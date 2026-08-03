"""Groq chat-completions client for grounded clinical responses."""
from functools import lru_cache

from app.config import get_settings
from app.core.exceptions import LLMGenerationError
from app.services.llm.base import BaseLLMClient

settings = get_settings()


"""class GroqLLMClient(BaseLLMClient):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.LLM_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMGenerationError("GROQ_API_KEY is required to generate a response")
        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=settings.LLM_MAX_TOKENS,
                temperature=0,
                reasoning_effort="medium",
                reasoning_format="hidden",
            )
            content = response.choices[0].message.content
            if not content:
                raise LLMGenerationError("Groq returned an empty response")
            return content.strip()
        except LLMGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001 - expose a consistent domain error to the API
            raise LLMGenerationError(f"Groq generation failed: {exc}") from exc"""
import json
from groq import Groq

class GroqLLMClient(BaseLLMClient):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.LLM_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMGenerationError("GROQ_API_KEY is required to generate a response")
            
        try:
            # 1. Strict Grounding Override: Force the model to act solely as a parser for the given data
            strict_grounding_instructions = (
                "\n\n[CRITICAL EXECUTION RULES]\n"
                "You are a strict data-extraction and synthesis engine. You have zero external knowledge.\n"
                "1. You must answer the request using ONLY the explicit facts contained in the provided data below.\n"
                "2. DO NOT use your internal training data, external facts, or prior knowledge.\n"
                "3. If the provided data does not contain the answer, you must output exactly: 'Insufficient data provided to answer this request.' Do not hallucinate or guess.\n"
                "4. Do not include conversational filler, warnings, or advice.\n"
                "5. You must output your final answer wrapped inside a valid JSON object matching this schema:\n"
                '{\n  "analysis": "your factual text response extracted only from the data"\n}'
            )

            # 2. Structural Isolation: Use clear delimiters to separate directives from the target data
            combined_user_payload = (
                f"=== SYSTEM DIRECTIVES ===\n"
                f"{system_prompt}\n"
                f"{strict_grounding_instructions}\n\n"
                f"=== PROVIDED DATA & REQUEST ===\n"
                f"{user_prompt}\n"
                f"==============================="
            )

            # Initialize client
            client = Groq(api_key=self.api_key)
            
            # 3. API Call: Enforce JSON mode and zero temperature for deterministic, uncreative output
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    # Keep everything in the user role to bypass conversational filters/refusals
                    {"role": "user", "content": combined_user_payload},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=settings.LLM_MAX_TOKENS,
                temperature=0.0, # 0.0 is critical to prevent hallucinations and strictly stick to data
                reasoning_effort="medium",
                reasoning_format="hidden",
            )
            
            content = response.choices[0].message.content
            if not content:
                raise LLMGenerationError("Groq returned an empty response")
            
            # 4. Parsing: Safely unpack the forced JSON structure
            try:
                parsed_json = json.loads(content.strip())
                extracted_text = parsed_json.get("analysis", content)
                return extracted_text.strip()
            except json.JSONDecodeError:
                # Fallback in case the model failed to format JSON properly despite instructions
                return content.strip()

        except LLMGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMGenerationError(f"Groq generation failed: {exc}") from exc

@lru_cache
def get_llm_client() -> BaseLLMClient:
    """Cached so one Groq client configuration is reused per process."""
    return GroqLLMClient()
