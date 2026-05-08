from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(["uv", "run", "python", "-m", "compileall", "-q", "src", "scripts"])
    run(["uv", "run", "evolve2", "model-check"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
