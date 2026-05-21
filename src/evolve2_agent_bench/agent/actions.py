"""Legacy action schema — retained for trace analysis and hypothesis dossier references.

The ReAct agent now uses native LangChain tool calling instead of manual JSON
action parsing. This module is kept so that trace analyzers and meta-optimization
prompts can still reference the action vocabulary.
"""

from __future__ import annotations

from typing import Literal

KNOWN_ACTIONS: list[str] = ["run_shell", "read_file", "write_file"]
