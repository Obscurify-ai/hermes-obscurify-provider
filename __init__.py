"""Obscurify.ai as a Hermes model provider: pick Obscurify.ai in ``hermes model`` or pass ``--provider obscurify``.

Obscurify.ai (https://obscurify.ai) is a privacy-focused, OpenAI-compatible API. Over a plain custom
endpoint, this profile adds, each checked against the live API:

* A model list Hermes can run. ``/v1/models`` also lists decision models, which only answer
  structured questions (a chat request without their ``response_format`` is rejected), and models
  with less than the 64K tokens of context Hermes requires. Both are left out.
* Context windows from the catalog, so Hermes doesn't have to guess them for Obscurify.ai's model ids.
* Reasoning effort as the top-level ``reasoning_effort`` field. Models that don't reason ignore it,
  and turning reasoning off sends ``none``.

The catalog is public, so it is fetched without credentials, at most once an hour per process.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

API_KEY_ENV = "OBSCURIFY_API_KEY"
BASE_URL = "https://obscurify.ai/v1"
MODELS_URL = BASE_URL + "/models"

# Hermes refuses to start a model with less than 64K tokens of context.
MIN_CONTEXT = 64_000
CATALOG_TTL_SECONDS = 3600

# Hermes' effort levels, each mapped to the value Obscurify.ai accepts.
EFFORTS = {
    "none": "none",
    "minimal": "minimal",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "xhigh",
    "max": "max",
    "ultra": "max",
}

_catalog_lock = threading.Lock()
_catalog: dict[str, dict[str, Any]] = {}
_catalog_at = 0.0


def runs_in_hermes(entry: dict[str, Any]) -> bool:
    """Whether a ``/v1/models`` entry belongs in the Hermes model picker."""
    if not entry.get("id") or entry.get("decisions"):
        return False
    context = entry.get("context_length")
    return not isinstance(context, int) or context >= MIN_CONTEXT


def _load_catalog(timeout: float = 8.0) -> dict[str, dict[str, Any]] | None:
    """The public model catalog keyed by id, cached for an hour. None when it can't be fetched."""
    global _catalog, _catalog_at
    with _catalog_lock:
        if _catalog and time.monotonic() - _catalog_at < CATALOG_TTL_SECONDS:
            return _catalog
    request = urllib.request.Request(
        MODELS_URL, headers={"Accept": "application/json", "User-Agent": "hermes-obscurify-provider/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
    except Exception:
        return None
    items = data.get("data", []) if isinstance(data, dict) else []
    catalog = {item["id"]: item for item in items if isinstance(item, dict) and runs_in_hermes(item)}
    if not catalog:
        return None
    with _catalog_lock:
        _catalog, _catalog_at = catalog, time.monotonic()
    return catalog


def reasoning_effort_for(reasoning_config: Any) -> str | None:
    """The ``reasoning_effort`` value to send, or None to leave the field out (the model's default)."""
    if not isinstance(reasoning_config, dict):
        return None
    if reasoning_config.get("enabled") is False:
        return "none"
    requested = str(reasoning_config.get("effort") or "").strip().lower()
    return EFFORTS.get(requested)


class ObscurifyProfile(ProviderProfile):
    """Obscurify.ai's OpenAI-compatible endpoint with a runnable model list and catalog context windows."""

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, **context: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        effort = reasoning_effort_for(reasoning_config)
        return {}, ({"reasoning_effort": effort} if effort else {})

    def fetch_models(
        self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0
    ) -> list[str] | None:
        caller_base = (base_url or "").strip().rstrip("/")
        if caller_base and caller_base != BASE_URL:
            # A user-configured proxy in front of Obscurify.ai: list what it serves.
            return super().fetch_models(api_key=api_key, base_url=base_url, timeout=timeout)
        catalog = _load_catalog(timeout)
        return sorted(catalog) if catalog else None

    def get_model_context_length(self, model: str) -> int | None:
        # Hot path: answer only from an already-loaded catalog, never fetch here.
        entry = _catalog.get(model)
        context = entry.get("context_length") if entry else None
        return context if isinstance(context, int) and context > 0 else None

    def live_context_length(self, model: str, *, api_key: str = "", base_url: str = "") -> int | None:
        catalog = _load_catalog()
        entry = catalog.get(model) if catalog else None
        context = entry.get("context_length") if entry else None
        return context if isinstance(context, int) and context > 0 else None


obscurify = ObscurifyProfile(
    name="obscurify",
    aliases=("obscurify-ai", "obscurify.ai"),
    display_name="Obscurify.ai",
    description="Obscurify.ai — private, OpenAI-compatible API to 200+ models",
    signup_url="https://obscurify.ai/?utm_source=hermes",
    env_vars=(API_KEY_ENV,),
    base_url=BASE_URL,
    auth_type="api_key",
    default_aux_model="deepseek/deepseek-v4-flash",
    fallback_models=(
        "deepseek/deepseek-v4-flash",
        "z-ai/glm-5.3",
        "moonshotai/kimi-k2-0905",
        "qwen/qwen3-coder",
        "meta-llama/llama-3.3-70b-instruct",
    ),
    model_capabilities={
        "deepseek/deepseek-v4-flash": {
            "supports_reasoning": True,
            "supports_tools": True,
            "context_window": 1048576,
            "model_family": "deepseek",
        },
        "z-ai/glm-5.3": {
            "supports_reasoning": True,
            "supports_tools": True,
            "context_window": 1048576,
            "model_family": "glm",
        },
        "moonshotai/kimi-k2-0905": {
            "supports_reasoning": False,
            "supports_tools": True,
            "context_window": 262144,
            "model_family": "kimi",
        },
        "qwen/qwen3-coder": {
            "supports_reasoning": False,
            "supports_tools": True,
            "context_window": 262000,
            "model_family": "qwen",
        },
        "meta-llama/llama-3.3-70b-instruct": {
            "supports_reasoning": False,
            "supports_tools": True,
            "context_window": 131072,
            "model_family": "llama",
        },
    },
)

register_provider(obscurify)
