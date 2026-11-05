"""What the pipeline needs from a model. Everything else about a model stays in its adapter.

An adapter sends one request and reports what came back and what it cost. It does not know about
vocabularies, offsets or graphs: those checks run once, in extract/llm.py, for every model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

OK = "ok"
REFUSED = "refused"
TRUNCATED = "truncated"
INVALID_JSON = "invalid_json"


class ProviderError(RuntimeError):
    """The call failed. Messages must not hold prompt or abstract text, since CI logs are public."""


@dataclass(frozen=True)
class ExtractionRequest:
    system: str  # the same for every work, so that it can be cached
    user: str
    schema: dict[str, Any]
    max_output_tokens: int


@dataclass(frozen=True)
class Completion:
    status: str
    data: dict[str, Any] | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0


class Provider(Protocol):
    name: str
    model: str
    metered: bool  # True when calls cost money, so a spending cap is required

    def worst_case_usd(self, request: ExtractionRequest) -> float:
        """An upper bound on one call, for the budget check before sending it."""
        ...

    def complete(self, request: ExtractionRequest) -> Completion:
        """Send one request. Raises ProviderError when the call itself fails."""
        ...
