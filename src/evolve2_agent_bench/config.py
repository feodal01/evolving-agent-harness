from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MODEL = "google/gemma-4-26b-a4b-it"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = OPENROUTER_BASE_URL

    @classmethod
    def from_env(cls, model: str = DEFAULT_MODEL) -> "OpenRouterConfig":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required.")
        return cls(api_key=api_key, model=model)
