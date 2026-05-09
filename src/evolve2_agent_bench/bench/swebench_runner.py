from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset

from evolve2_agent_bench.agent.base import BaselineLangChainAgent
from evolve2_agent_bench.config import OpenRouterConfig
from evolve2_agent_bench.trace import RunTraces


DATASET_NAME = "princeton-nlp/SWE-bench_Verified"
SPLIT = "test"


@dataclass(frozen=True)
class RunPaths:
    project_root: Path
    run_id: str
    run_dir: Path
    worktree_dir: Path


def make_run_id(instance_id: str) -> str:
    safe_id = instance_id.replace("/", "__")
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{safe_id}"


def load_task(instance_id: str) -> dict[str, Any]:
    dataset = load_dataset(DATASET_NAME, split=SPLIT)
    for row in dataset:
        if row["instance_id"] == instance_id:
            return dict(row)
    raise ValueError(f"Instance not found in {DATASET_NAME}/{SPLIT}: {instance_id}")


def public_task_view(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "base_commit": task["base_commit"],
        "problem_statement": task["problem_statement"],
        "version": task.get("version"),
        "created_at": task.get("created_at"),
        "difficulty": task.get("difficulty"),
    }


def run_git(args: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=True,
    )


def prepare_workspace(task: dict[str, Any], paths: RunPaths) -> Path:
    repo_dir = paths.worktree_dir / task["instance_id"]
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_url = f"https://github.com/{task['repo']}.git"
    paths.worktree_dir.mkdir(parents=True, exist_ok=True)
    repo_dir.mkdir(parents=True)
    run_git(["init", "--quiet"], cwd=repo_dir)
    run_git(["remote", "add", "origin", repo_url], cwd=repo_dir)
    run_git(
        ["fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", task["base_commit"]],
        cwd=repo_dir,
        timeout=900,
    )
    run_git(["checkout", "--quiet", "FETCH_HEAD"], cwd=repo_dir)
    run_git(["switch", "-c", f"agent/{paths.run_id}"], cwd=repo_dir)
    return repo_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_patch(workspace: Path, patch_path: Path) -> str:
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--binary"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        check=True,
    )
    patch_path.write_text(proc.stdout, encoding="utf-8")
    return proc.stdout


def write_prediction(task: dict[str, Any], model: str, patch: str, path: Path) -> None:
    record = {
        "instance_id": task["instance_id"],
        "model_name_or_path": model,
        "model_patch": patch,
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")


def evaluate_prediction(
    paths: RunPaths,
    task: dict[str, Any],
    model: str,
    prediction_path: Path,
    timeout_seconds: int,
    traces: RunTraces,
) -> dict[str, Any]:
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        DATASET_NAME,
        "--split",
        SPLIT,
        "--instance_ids",
        task["instance_id"],
        "--predictions_path",
        str(prediction_path),
        "--max_workers",
        "1",
        "--run_id",
        paths.run_id,
        "--timeout",
        str(timeout_seconds),
        "--cache_level",
        "env",
        "--clean",
        "False",
    ]
    started = time.monotonic()
    traces.append(
        "evaluation_start",
        {
            "stream": "evaluation",
            "command": cmd,
            "instance_id": task["instance_id"],
            "prediction_path": str(prediction_path),
        },
    )
    proc = subprocess.run(
        cmd,
        cwd=paths.run_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds + 1800,
    )
    elapsed = time.monotonic() - started
    (paths.run_dir / "evaluation_stdout.log").write_text(proc.stdout, encoding="utf-8")
    (paths.run_dir / "evaluation_stderr.log").write_text(proc.stderr, encoding="utf-8")

    report_path = paths.run_dir / f"{model.replace('/', '__')}.{paths.run_id}.json"
    summary: dict[str, Any] = {
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "report_path": str(report_path),
        "stdout_path": str(paths.run_dir / "evaluation_stdout.log"),
        "stderr_path": str(paths.run_dir / "evaluation_stderr.log"),
    }
    if report_path.exists():
        summary["report"] = json.loads(report_path.read_text(encoding="utf-8"))
    traces.append("evaluation_finish", {"stream": "evaluation", **summary})
    return summary


def run_one_task(
    project_root: Path,
    instance_id: str,
    config: OpenRouterConfig,
    max_iterations: int,
    agent_max_tokens: int,
    evaluation_timeout: int,
) -> dict[str, Any]:
    run_id = make_run_id(instance_id)
    paths = RunPaths(
        project_root=project_root,
        run_id=run_id,
        run_dir=project_root / "artifacts" / "runs" / run_id,
        worktree_dir=project_root / "artifacts" / "worktrees" / run_id,
    )
    traces = RunTraces.create(paths.run_dir)
    task = load_task(instance_id)
    public_task = public_task_view(task)
    traces.append(
        "run_start",
        {
            "stream": "run",
            "run_id": run_id,
            "instance_id": instance_id,
            "dataset": DATASET_NAME,
            "split": SPLIT,
            "model": config.model,
        },
    )
    traces.append("task_loaded", {"stream": "run", "task": public_task})
    write_json(paths.run_dir / "task.json", public_task)
    write_json(
        paths.run_dir / "config.json",
        {
            "model": config.model,
            "dataset": DATASET_NAME,
            "split": SPLIT,
            "max_iterations": max_iterations,
            "agent_max_tokens": agent_max_tokens,
            "evaluation_timeout": evaluation_timeout,
        },
    )

    started = time.monotonic()
    traces.append("workspace_prepare_start", {"stream": "run", "worktree_dir": str(paths.worktree_dir)})
    workspace = prepare_workspace(task, paths)
    traces.append("workspace_prepare_finish", {"stream": "run", "workspace": str(workspace)})
    agent = BaselineLangChainAgent(config=config, traces=traces, max_tokens=agent_max_tokens)
    agent_result = agent.run(workspace=workspace, task=task, max_iterations=max_iterations)
    patch = make_patch(workspace, paths.run_dir / "patch.diff")
    traces.append(
        "patch_created",
        {
            "stream": "run",
            "patch_path": str(paths.run_dir / "patch.diff"),
            "patch_bytes": len(patch.encode("utf-8")),
            "patch": patch,
        },
    )
    prediction_path = paths.run_dir / "prediction.jsonl"
    write_prediction(task, config.model, patch, prediction_path)
    traces.append(
        "prediction_written",
        {"stream": "run", "prediction_path": str(prediction_path)},
    )
    evaluation = evaluate_prediction(
        paths,
        task,
        config.model,
        prediction_path,
        evaluation_timeout,
        traces,
    )
    wall_seconds = round(time.monotonic() - started, 3)

    result = {
        "run_id": run_id,
        "instance_id": instance_id,
        "workspace": str(workspace),
        "agent_summary": agent_result.summary,
        "agent_iterations": agent_result.iterations,
        "patch_bytes": len(patch.encode("utf-8")),
        "wall_seconds": wall_seconds,
        "evaluation": evaluation,
    }
    write_json(paths.run_dir / "result.json", result)
    traces.append("run_finish", {"stream": "run", "result": result})
    return result
