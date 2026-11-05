"""Any model behind an OpenAI-compatible server on your own hardware, such as vLLM running OLMo.

Calls are free, so no spending cap is needed, and text stays on the machines that `base_url` names.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

from seismohydro_kg.extract.providers.base import (
    INVALID_JSON,
    OK,
    TRUNCATED,
    Completion,
    ExtractionRequest,
    ProviderError,
)

logging.getLogger("httpx").setLevel(logging.WARNING)


class LocalProvider:
    metered = False

    def __init__(
        self,
        model: str,
        base_url: str,
        name: str = "local",
        timeout_s: float = 600.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # A shared machine needs its own port: whatever listens on this address receives the text.
        chosen = os.environ.get("SHKG_LOCAL_BASE_URL") or base_url
        self.name, self.model, self.base_url = name, model, chosen.rstrip("/")
        headers = {}
        # Other users on a shared machine can reach an open port, so servers should require a key.
        if os.environ.get("SHKG_LOCAL_API_KEY"):
            headers["Authorization"] = f"Bearer {os.environ['SHKG_LOCAL_API_KEY']}"
        self._http = httpx.Client(headers=headers, timeout=timeout_s, transport=transport)

    def worst_case_usd(self, request: ExtractionRequest) -> float:
        return 0.0

    def complete(self, request: ExtractionRequest) -> Completion:
        body = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": request.schema, "strict": True},
            },
        }
        try:
            response = self._http.post(f"{self.base_url}/chat/completions", json=body)
        except httpx.TransportError as exc:
            raise ProviderError(
                f"{self.name}: no server at {self.base_url} ({type(exc).__name__}). "
                "See docs/student-quickstart.md to start one."
            ) from None
        if response.status_code != 200:
            raise ProviderError(
                f"{self.name}: HTTP {response.status_code} from {self.base_url}. If that is not "
                "your model server, it received abstract text: set SHKG_LOCAL_BASE_URL."
            )
        payload = response.json()
        usage = payload.get("usage") or {}
        tally = {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }
        choice = payload["choices"][0]
        if choice.get("finish_reason") == "length":
            return Completion(TRUNCATED, **tally)
        try:
            return Completion(OK, data=json.loads(choice["message"]["content"] or ""), **tally)
        except json.JSONDecodeError:
            return Completion(INVALID_JSON, **tally)
