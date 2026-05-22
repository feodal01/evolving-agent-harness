from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    base_url: str

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.environ.get("LLM_API_KEY")
        model = os.environ.get("LLM_MODEL")
        base_url = os.environ.get("LLM_BASE_URL")
        missing = [k for k, v in [("LLM_API_KEY", api_key), ("LLM_MODEL", model), ("LLM_BASE_URL", base_url)] if not v]
        if missing:
            raise RuntimeError(f"Required env vars not set: {', '.join(missing)}")
        return cls(api_key=api_key, model=model, base_url=base_url)  # type: ignore[arg-type]
