import json
from typing import Any

import httpx

from app.config import settings


class OllamaError(Exception):
    pass


class OllamaService:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")

    def check_connection(self) -> dict:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
            return {
                "ok": True,
                "models": [m.get("name", "") for m in data.get("models", [])],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def list_models(self) -> list[str]:
        result = self.check_connection()
        return result.get("models", []) if result.get("ok") else []

    def _request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout: int = 120,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.base_url}{endpoint}", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException as exc:
            raise OllamaError("Model request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama returned {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except Exception as exc:
            raise OllamaError(str(exc)) from exc

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if schema:
            payload["format"] = schema
            # Ground the model in the schema so it reliably returns JSON.
            schema_hint = json.dumps(schema, indent=2)
            payload["messages"] = [
                {"role": "system", "content": f"Return ONLY valid JSON matching this schema:\n{schema_hint}"},
                *messages,
            ]
        data = self._request("/api/chat", payload)
        return data.get("message", {}).get("content", "")

    def generate(
        self,
        model: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if schema:
            payload["format"] = schema
            schema_hint = json.dumps(schema, indent=2)
            payload["prompt"] = (
                "Respond using ONLY valid JSON. Do not include explanations.\n"
                f"Schema:\n{schema_hint}\n\n{prompt}"
            )
        data = self._request("/api/generate", payload)
        return data.get("response", "")

    def structured_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raw = self.chat(model, messages, schema=schema, temperature=temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from a markdown code block.
            if "```json" in raw:
                raw = raw.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0]
            return json.loads(raw.strip())
