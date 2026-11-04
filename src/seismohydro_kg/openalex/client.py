"""Thin OpenAlex client with per-response cost accounting.

pyalex 0.21 was checked for this role. It handles keys and cursors but does not expose the cost
of each response, which the budget guard needs, so this small client stays.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx

from seismohydro_kg.config import data_dir, load_budget
from seismohydro_kg.openalex.budget import BudgetGuard

BASE_URL = "https://api.openalex.org"
PER_PAGE_MAX = 100
USER_AGENT = "seismohydro-knowledge-graph"
_MAX_RETRY_AFTER_S = 300

# httpx logs full URLs at INFO. Quiet it so nothing request-specific reaches CI logs.
logging.getLogger("httpx").setLevel(logging.WARNING)


class OpenAlexError(RuntimeError):
    pass


class ApiKeyRequired(OpenAlexError):
    """Cursor paging past the first page needs a free API key."""


class PlanUpgradeRequired(OpenAlexError):
    """The request uses a paid feature, for example `from_updated_date`."""


def cost_class(params: dict[str, Any]) -> str:
    """Which rate a request pays. Any search filter pays the search rate, even with group_by."""
    if params.get("search") or ".search" in str(params.get("filter", "")):
        return "search"
    return "list"


class OpenAlexClient:
    def __init__(
        self,
        guard: BudgetGuard,
        rates_usd_per_call: dict[str, float],
        usd_per_credit: float,
        api_key: str | None = None,
        min_interval_s: float = 1.1,
        max_retries: int = 5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.guard = guard
        self.rates = rates_usd_per_call
        self.usd_per_credit = usd_per_credit
        self.has_key = bool(api_key)
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self._sleep = sleep
        self._last_request = 0.0
        headers = {"User-Agent": USER_AGENT}
        if api_key:
            # Header rather than query parameter, so the key cannot appear in a logged URL.
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(
            base_url=BASE_URL, headers=headers, transport=transport, timeout=60.0
        )

    def _pace(self) -> None:
        wait = self.min_interval_s - (time.monotonic() - self._last_request)
        if wait > 0:
            self._sleep(wait)
        self._last_request = time.monotonic()

    def _cost(self, response: httpx.Response, payload: dict[str, Any], estimate: float) -> float:
        cost = payload.get("meta", {}).get("cost_usd")
        if cost is not None:
            return float(cost)
        credits = response.headers.get("X-RateLimit-Credits-Used")
        if credits is not None:
            return float(credits) * self.usd_per_credit
        return estimate

    def get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        estimate = self.rates[cost_class(params)]
        self.guard.check(estimate)
        for attempt in range(self.max_retries + 1):
            self._pace()
            try:
                response = self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise OpenAlexError(f"network failure on {path}: {type(exc).__name__}") from exc
                self._sleep(2**attempt)
                continue
            if response.status_code == 200:
                payload = response.json()
                self.guard.charge(self._cost(response, payload, estimate))
                return payload
            detail = response.text[:300]
            if response.status_code == 401:
                raise ApiKeyRequired(f"{path}: HTTP 401, set OPENALEX_API_KEY. {detail}")
            if response.status_code == 429 and "Plan upgrade required" in detail:
                raise PlanUpgradeRequired(f"{path}: {detail}")
            if response.status_code == 429 or response.status_code >= 500:
                delay = float(response.headers.get("Retry-After", 2**attempt))
                if attempt == self.max_retries or delay > _MAX_RETRY_AFTER_S:
                    raise OpenAlexError(f"{path}: HTTP {response.status_code}, gave up. {detail}")
                self._sleep(delay)
                continue
            raise OpenAlexError(f"{path}: HTTP {response.status_code}. {detail}")
        raise OpenAlexError(f"{path}: retries exhausted")

    def group_counts(self, filter_: str, group_by: str) -> dict[str, int]:
        payload = self.get("/works", {"filter": filter_, "group_by": group_by})
        return {
            str(group.get("key_display_name", group["key"])): group["count"]
            for group in payload["group_by"]
        }

    def iter_pages(
        self, filter_: str, select: list[str], cursor: str = "*"
    ) -> Iterator[tuple[list[dict[str, Any]], str | None]]:
        """Yield (results, next_cursor). Start again from any next_cursor to resume."""
        while cursor:
            payload = self.get(
                "/works",
                {
                    "filter": filter_,
                    "select": ",".join(select),
                    "per_page": PER_PAGE_MAX,
                    "cursor": cursor,
                },
            )
            cursor = payload["meta"].get("next_cursor")
            yield payload["results"], cursor


def build_client(
    run_cap_usd: float, transport: httpx.BaseTransport | None = None
) -> OpenAlexClient:
    """Client wired to config/budget.yaml and the on-disk ledger."""
    config = load_budget()["openalex"]
    api_key = os.environ.get("OPENALEX_API_KEY") or None
    tier = "free_key" if api_key else "no_key"
    ledger: Path = data_dir() / "openalex_ledger.json"
    # A prepaid balance can pay for more than the free daily budget. Set this only when one exists.
    daily_cap = float(os.environ.get("SHKG_OPENALEX_DAILY_USD") or config["daily_usd"][tier])
    guard = BudgetGuard(run_cap_usd=run_cap_usd, daily_cap_usd=daily_cap, ledger_path=ledger)
    interval = config["min_interval_s"]["with_key" if api_key else "no_key"]
    return OpenAlexClient(
        guard=guard,
        rates_usd_per_call=config["rates_usd_per_call"],
        usd_per_credit=config["usd_per_credit"],
        api_key=api_key,
        min_interval_s=interval,
        max_retries=config["max_retries"],
        transport=transport,
    )
