"""Shared helpers. Tests are offline: every OpenAlex response goes through httpx.MockTransport."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from seismohydro_kg.openalex.budget import BudgetGuard
from seismohydro_kg.openalex.client import OpenAlexClient

RATES = {"list": 0.0001, "search": 0.001, "singleton": 0.0, "content": 0.01}


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """No test writes into the real data/ directory or reads a real key."""
    monkeypatch.setenv("SHKG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


@pytest.fixture
def make_client() -> Callable[..., OpenAlexClient]:
    def build(
        handler: Callable[[httpx.Request], httpx.Response],
        run_cap: float = 1.0,
        daily_cap: float = 1.0,
        ledger=None,
        api_key: str | None = "test-key",
    ) -> OpenAlexClient:
        guard = BudgetGuard(run_cap_usd=run_cap, daily_cap_usd=daily_cap, ledger_path=ledger)
        return OpenAlexClient(
            guard=guard,
            rates_usd_per_call=RATES,
            usd_per_credit=0.0001,
            api_key=api_key,
            min_interval_s=0.0,
            max_retries=2,
            transport=httpx.MockTransport(handler),
            sleep=lambda _seconds: None,
        )

    return build
