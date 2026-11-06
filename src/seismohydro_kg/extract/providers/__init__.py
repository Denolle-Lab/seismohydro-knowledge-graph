"""Pluggable extraction models. To add one: write an adapter and add a config/extraction.yaml entry.

Adapters load lazily, so running a local model never needs Claude credentials, and the reverse.
"""

from __future__ import annotations

from typing import Any

from seismohydro_kg.config import CONFIG_DIR, load_yaml
from seismohydro_kg.extract.providers.base import Provider


def extraction_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "extraction.yaml")


def load_provider(name: str | None = None, config: dict[str, Any] | None = None) -> Provider:
    """Build the provider named in config/extraction.yaml, or the default one."""
    config = config or extraction_config()
    name = name or config["default_provider"]
    if name not in config["providers"]:
        raise ValueError(f"unknown provider {name!r}: choose from {', '.join(config['providers'])}")
    settings = config["providers"][name]
    adapter = settings["adapter"]
    if adapter == "claude":
        from seismohydro_kg.extract.providers.claude import ClaudeProvider

        prices = config["cost_assumptions"]["price_usd_per_mtok"][settings["model"]]
        return ClaudeProvider(
            model=settings["model"],
            prices=prices,
            effort=settings["effort"],
            thinking=settings["thinking"],
            prompt_caching=settings["prompt_caching"],
            name=name,
        )
    if adapter == "openai_compatible":
        from seismohydro_kg.extract.providers.local import LocalProvider

        return LocalProvider(model=settings["model"], base_url=settings["base_url"], name=name)
    raise ValueError(f"provider {name!r} has unknown adapter {adapter!r}")
