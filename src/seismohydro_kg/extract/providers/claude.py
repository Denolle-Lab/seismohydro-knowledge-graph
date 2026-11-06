"""Claude through the official SDK. Real-time calls: Message Batches arrive with the M4 bulk run."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from seismohydro_kg.extract.providers.base import (
    INVALID_JSON,
    OK,
    REFUSED,
    TRUNCATED,
    Completion,
    ExtractionRequest,
    ProviderError,
)

# Multipliers on the input price, from the Claude API reference (read 2026-11-05).
CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25
# A deliberately low estimate of characters per token, so the budget check errs high.
_CHARS_PER_TOKEN_LOW = 2.5


class ClaudeProvider:
    metered = True

    def __init__(
        self,
        model: str,
        prices: dict[str, float],
        effort: str = "low",
        thinking: str = "adaptive",
        prompt_caching: bool = True,
        name: str = "claude",
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.name, self.model = name, model
        self._input_rate = prices["input"] / 1e6
        self._output_rate = prices["output"] / 1e6
        self._effort, self._thinking, self._caching = effort, thinking, prompt_caching
        self._client = client or anthropic.Anthropic()

    def worst_case_usd(self, request: ExtractionRequest) -> float:
        characters = len(request.system) + len(request.user)
        input_tokens = characters / _CHARS_PER_TOKEN_LOW
        return (
            input_tokens * self._input_rate * CACHE_WRITE_MULTIPLIER
            + request.max_output_tokens * self._output_rate
        )

    def _send(self, request: ExtractionRequest) -> Any:
        system: dict[str, Any] = {"type": "text", "text": request.system}
        if self._caching:
            system["cache_control"] = {"type": "ephemeral"}
        try:
            return self._client.messages.create(
                model=self.model,
                max_tokens=request.max_output_tokens,
                thinking={"type": self._thinking},
                output_config={
                    "effort": self._effort,
                    "format": {"type": "json_schema", "schema": request.schema},
                },
                system=[system],
                messages=[{"role": "user", "content": request.user}],
            )
        except anthropic.AuthenticationError:
            raise ProviderError(
                "claude: the API key was rejected. Check ANTHROPIC_API_KEY."
            ) from None
        except anthropic.RateLimitError:
            raise ProviderError("claude: rate limited after retries. Run again.") from None
        except anthropic.APIStatusError as exc:
            # exc.message is left out on purpose: it can echo parts of the request.
            raise ProviderError(f"claude: HTTP {exc.status_code}, {type(exc).__name__}") from None
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"claude: network failure, {type(exc).__name__}") from None
        except TypeError:
            # Raised by the SDK when it finds no credentials at all.
            raise ProviderError("claude: no credentials. Set ANTHROPIC_API_KEY.") from None

    def complete(self, request: ExtractionRequest) -> Completion:
        response = self._send(request)
        usage = response.usage
        cached = usage.cache_read_input_tokens or 0
        written = usage.cache_creation_input_tokens or 0
        tally = {
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": cached,
            "cache_write_tokens": written,
            "output_tokens": usage.output_tokens,
            "usd": (
                usage.input_tokens * self._input_rate
                + cached * self._input_rate * CACHE_READ_MULTIPLIER
                + written * self._input_rate * CACHE_WRITE_MULTIPLIER
                + usage.output_tokens * self._output_rate
            ),
        }
        if response.stop_reason == "refusal":
            return Completion(REFUSED, **tally)
        if response.stop_reason == "max_tokens":
            return Completion(TRUNCATED, **tally)
        text = next((block.text for block in response.content if block.type == "text"), None)
        try:
            return Completion(OK, data=json.loads(text or ""), **tally)
        except json.JSONDecodeError:
            return Completion(INVALID_JSON, **tally)
