import sys
import types

import pytest

from app.core.exceptions import LLMGenerationError
from app.services.llm.groq_client import GroqLLMClient


def test_groq_client_uses_requested_model_and_separate_system_message(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = types.SimpleNamespace(content="Grounded answer [Source 1].")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class FakeGroq:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    client = GroqLLMClient(api_key="groq-test-key", model="openai/gpt-oss-120b")

    answer = client.generate("system rules", "Pinecone context and question")

    assert answer == "Grounded answer [Source 1]."
    assert captured["api_key"] == "groq-test-key"
    assert captured["model"] == "openai/gpt-oss-120b"
    assert captured["messages"] == [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": "Pinecone context and question"},
    ]


def test_groq_client_requires_api_key():
    with pytest.raises(LLMGenerationError, match="GROQ_API_KEY"):
        GroqLLMClient(api_key="").generate("system", "question")
