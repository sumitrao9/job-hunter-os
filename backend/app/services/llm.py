#!/usr/bin/env python3
"""Universal LLM service using litellm.

Supports 400+ providers (OpenAI, Anthropic, Google, Ollama, DeepSeek, Groq,
Azure, HuggingFace, etc.) with a single unified interface.

Falls back to direct Ollama HTTP calls when litellm is unavailable.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_has_litellm_checked = False
_HAS_LITELLM = False


def _ensure_litellm() -> bool:
    """Lazy-import litellm. Returns True if available, caches the result."""
    global _has_litellm_checked, _HAS_LITELLM
    if _has_litellm_checked:
        return _HAS_LITELLM
    _has_litellm_checked = True
    try:
        import litellm
        _HAS_LITELLM = True
    except ImportError:
        logger.warning("litellm not installed — falling back to Ollama-only mode")
    return _HAS_LITELLM

from app.config import settings
from app.services.ollama import OllamaService

PROVIDER_MODELS = {
    "ollama": ["llama3.1:8b", "llama3.2", "phi3:mini", "mistral", "gemma2"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    "google": ["gemini-1.5-flash", "gemini-1.5-pro"],
    "deepseek": ["deepseek-chat", "deepseek-coder"],
    "groq": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"],
}


class LLMService:
    """Universal LLM service with multi-provider support.

    Provider priority: OpenAI API key → Anthropic → Google → Ollama.
    Users can set OPENAI_API_KEY in .env for cloud models, or use Ollama locally.
    """

    def __init__(self):
        self._ollama = OllamaService()

    def _resolve_model(self) -> str:
        """Select the best available model from configured providers."""
        if settings.openai_api_key:
            return "gpt-4o-mini"
        if settings.ollama_url:
            models = self._ollama.list_models()
            for candidate in ["llama3.1:8b", "llama3.2", "phi3:mini", "mistral"]:
                if any(candidate in m for m in models):
                    return f"ollama/{candidate}"
            if models:
                return f"ollama/{models[0]}"
        raise RuntimeError(
            "No LLM provider configured. Set OPENAI_API_KEY for cloud models "
            "or run Ollama for local inference."
        )

    def check_connection(self) -> dict:
        """Test connectivity to the configured LLM provider."""
        try:
            model = self._resolve_model()
            if model.startswith("ollama/"):
                result = self._ollama.check_connection()
                return {"ok": result["ok"], "provider": "ollama", "models": result.get("models", [])}
            if not _ensure_litellm():
                return {"ok": False, "provider": "unknown", "error": "litellm not installed"}

            import litellm
            litellm.set_verbose(False)

            litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
            )
            return {"ok": True, "provider": model.split("/")[0] if "/" in model else model, "models": [model]}
        except Exception as exc:
            return {"ok": False, "provider": "none", "error": str(exc)}

    def list_providers(self) -> list[str]:
        """List configured LLM providers."""
        providers = []
        if settings.openai_api_key:
            providers.append("openai")
        if settings.openai_base_url and settings.openai_api_key:
            providers.append("openai-compatible")
        if settings.ollama_url:
            providers.append("ollama")
        return providers or ["ollama"]

    def list_models(self) -> dict[str, list[str]]:
        """List models available per provider."""
        result = {}
        for provider in self.list_providers():
            result[provider] = PROVIDER_MODELS.get(provider, [])
        if "ollama" not in result:
            try:
                result["ollama"] = self._ollama.list_models()
            except Exception:
                result["ollama"] = PROVIDER_MODELS["ollama"]
        return result

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        schema: dict | None = None,
    ) -> str:
        """Generate text using the configured LLM provider."""
        model = model or self._resolve_model()

        if model.startswith("ollama/") and not _ensure_litellm():
            # Direct Ollama call
            ollama_model = model.split("/", 1)[1]
            return self._ollama.generate(ollama_model, prompt, schema=schema, temperature=temperature)

        if not _ensure_litellm():
            raise RuntimeError("litellm is required for non-Ollama providers")

        import litellm

        messages = [{"role": "user", "content": prompt}]

        if schema:
            schema_hint = json.dumps(schema, indent=2)
            messages = [
                {"role": "system", "content": f"Respond with ONLY valid JSON matching this schema:\n{schema_hint}"},
                {"role": "user", "content": prompt},
            ]

        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""

        if schema:
            # Try to parse JSON from the response
            try:
                return text.strip()
            except Exception:
                pass

        return text.strip()

    def structured_generate(
        self,
        prompt: str,
        schema: dict,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> Any:
        """Generate structured JSON output matching a schema."""
        raw = self.generate(prompt, model=model, temperature=temperature, max_tokens=max_tokens, schema=schema)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if "```json" in raw:
                raw = raw.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0]
            return json.loads(raw.strip())

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> str:
        """Chat completion using the configured LLM provider."""
        model = model or self._resolve_model()

        if model.startswith("ollama/") and not _ensure_litellm():
            ollama_model = model.split("/", 1)[1]
            return self._ollama.chat(ollama_model, messages, temperature=temperature)

        if not _ensure_litellm():
            raise RuntimeError("litellm is required for non-Ollama providers")

        import litellm
        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


# Backward-compatible singleton
llm_service = LLMService()
