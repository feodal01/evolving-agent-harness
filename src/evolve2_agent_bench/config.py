from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MODEL = "glm5-fp8"
DEFAULT_BASE_URL = "https://REDACTED"


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMConfig":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY is required.")
        return cls(
            api_key=api_key,
            model=model or os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        )


# Backward compatibility alias
OpenRouterConfig = LLMConfig
