#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: MODULE_AGENT_EVAL — local reproducible coding-agent benchmark runner
# ROLE: Freeze real Git snapshots, run configured coding agents in isolated
#       worktrees, and capture patches, verification, usage, timing, and cost.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL
# purpose: Execute repository-owned agent eval tasks locally against immutable
#   Git commits and produce evidence for a later human, candidate-blind review.
# owns:
#   - scripts/agent_eval.py
# inputs: evals task/model/pricing TOML, local Git repository and configured CLIs.
# outputs: ignored .eval-runs/<run-id> evidence directories and stdout summary.
# dependencies: Python 3.12 stdlib, git, Codex CLI and/or OpenCode CLI.
# side_effects: creates/removes detached Git worktrees, invokes paid models only
#   for the explicit run command, runs trusted verification shell commands, and
#   writes local evidence files; never commits, pushes, or edits the main tree.
# emitted_logs: none.
# invariants:
#   - every candidate starts from the task's exact base commit and tree;
#   - candidates run sequentially and never share a worktree;
#   - validate/list never invoke a model;
#   - model failures are recorded as eval outcomes, not hidden as runner success;
#   - the controller never injects credential values into prompts/artifacts.
# failure_policy: configuration/controller failures exit non-zero; candidate
#   timeouts, test failures and scope violations remain recorded candidate data.
# END_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL

# START_MODULE_MAP: M-SCRIPTS-AGENT-EVAL
# public_entrypoints:
#   - main
# semantic_blocks:
#   - CONFIG: load and validate task/model/pricing contracts.
#   - GIT_WORKTREES: create, fingerprint and safely remove isolated worktrees.
#   - PROCESS: invoke CLIs and verification with bounded process groups.
#   - USAGE_COST: normalize provider usage and immutable price snapshots.
#   - EVAL_RUN: orchestrate baseline and candidate evidence.
#   - CLI: list, validate and paid run commands.
# owned_tests:
#   - scripts/test_agent_eval.py
# END_MODULE_MAP: M-SCRIPTS-AGENT-EVAL

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_ROOT = REPO_ROOT / "evals"
DEFAULT_RUNS_ROOT = REPO_ROOT / ".eval-runs"
RUNNER_VERSION = "agent-eval-1"
OPENCODE_EVAL_AGENT = "repo-eval"
OPENCODE_PROJECT_CONFIG = "opencode.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SENSITIVE_ENV_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|API_KEY|DATABASE_URL|COOKIE|TELEGRAM|YOOKASSA)",
    re.IGNORECASE,
)
SAFE_SENSITIVE_ENV = {"OPENCODE_CONFIG", "CODEX_HOME"}


@dataclass(frozen=True)
class VerificationSpec:
    name: str
    command: str
    timeout_seconds: int


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    directory: Path
    base_sha: str
    base_tree: str
    prompt_path: Path
    rubric_path: Path
    timeout_seconds: int
    allowed_paths: tuple[str, ...]
    dependency_links: tuple[str, ...]
    verification: tuple[VerificationSpec, ...]


@dataclass(frozen=True)
class ModelSpec:
    key: str
    runner: str
    executable: str
    model: str
    usage_parser: str
    pricing_key: str
    effort: str | None = None
    agent: str | None = None
    variant: str | None = None
    pass_env: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriceSpec:
    key: str
    provider: str
    as_of: str
    source: str
    input_per_million: float
    cached_input_per_million: float
    cache_write_per_million: float
    output_per_million: float
    input_includes_cached: bool
    output_includes_reasoning: bool
    long_context_threshold: int | None = None
    long_context_input_multiplier: float = 1.0
    long_context_output_multiplier: float = 1.0


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    reported_cost_usd: float | None = None


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int | None
    timed_out: bool
    wall_seconds: float
    stdout_path: str
    stderr_path: str


class EvalConfigError(ValueError):
    """Raised when a repository-owned eval contract is invalid."""


# START_BLOCK: CONFIG
def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError as exc:
        raise EvalConfigError(f"Missing config: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise EvalConfigError(f"Invalid TOML {path}: {exc}") from exc


def _safe_id(value: str, *, label: str) -> str:
    if not ID_RE.fullmatch(value):
        raise EvalConfigError(f"Invalid {label}: {value!r}")
    return value


def _safe_relative_path(value: str, *, label: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise EvalConfigError(f"Invalid {label}: {value!r}")
    return path.as_posix()


def load_task(task_id: str, *, evals_root: Path = EVALS_ROOT) -> TaskSpec:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.load_task
    # purpose: Load one immutable eval task and validate all path/snapshot fields.
    # inputs: task_id and optional evals_root.
    # returns: validated TaskSpec.
    # side_effects: reads task TOML and referenced Markdown files.
    # emitted_logs: none.
    # error_behavior: raises EvalConfigError for malformed/missing contracts.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.load_task
    task_id = _safe_id(task_id, label="task id")
    directory = (evals_root / "tasks" / task_id).resolve()
    expected_parent = (evals_root / "tasks").resolve()
    if directory.parent != expected_parent:
        raise EvalConfigError(f"Task escapes task root: {task_id}")
    raw = _read_toml(directory / "task.toml")
    if raw.get("schema_version") != 1:
        raise EvalConfigError(f"Unsupported task schema for {task_id}")
    if raw.get("id") != task_id:
        raise EvalConfigError(f"Task id mismatch: requested {task_id}, file has {raw.get('id')!r}")

    base_sha = str(raw.get("base_sha", ""))
    base_tree = str(raw.get("base_tree", ""))
    if not SHA_RE.fullmatch(base_sha) or not SHA_RE.fullmatch(base_tree):
        raise EvalConfigError("base_sha and base_tree must be full lowercase Git hashes")

    prompt_name = _safe_relative_path(str(raw.get("prompt_file", "")), label="prompt file")
    rubric_name = _safe_relative_path(str(raw.get("rubric_file", "")), label="rubric file")
    prompt_path = directory / prompt_name
    rubric_path = directory / rubric_name
    if not prompt_path.is_file() or not rubric_path.is_file():
        raise EvalConfigError(f"Task {task_id} is missing prompt or rubric")

    allowed = tuple(
        _safe_relative_path(str(item), label="allowed path")
        for item in raw.get("allowed_paths", [])
    )
    if not allowed:
        raise EvalConfigError(f"Task {task_id} has no allowed_paths")
    links = tuple(
        _safe_relative_path(str(item), label="dependency link")
        for item in raw.get("dependency_links", [])
    )

    verification: list[VerificationSpec] = []
    for item in raw.get("verification", []):
        name = _safe_id(str(item.get("name", "")), label="verification name")
        command = str(item.get("command", "")).strip()
        timeout = int(item.get("timeout_seconds", 0))
        if not command or timeout <= 0:
            raise EvalConfigError(f"Invalid verification entry {name!r}")
        verification.append(VerificationSpec(name, command, timeout))
    if not verification:
        raise EvalConfigError(f"Task {task_id} has no verification commands")

    timeout_seconds = int(raw.get("timeout_seconds", 0))
    if timeout_seconds <= 0:
        raise EvalConfigError(f"Task {task_id} timeout must be positive")
    return TaskSpec(
        task_id=task_id,
        title=str(raw.get("title", task_id)),
        directory=directory,
        base_sha=base_sha,
        base_tree=base_tree,
        prompt_path=prompt_path,
        rubric_path=rubric_path,
        timeout_seconds=timeout_seconds,
        allowed_paths=allowed,
        dependency_links=links,
        verification=tuple(verification),
    )


def load_models(*, evals_root: Path = EVALS_ROOT) -> dict[str, ModelSpec]:
    raw = _read_toml(evals_root / "models.toml")
    if raw.get("schema_version") != 1:
        raise EvalConfigError("Unsupported models schema")
    result: dict[str, ModelSpec] = {}
    for key, item in raw.get("models", {}).items():
        key = _safe_id(str(key), label="model key")
        runner = str(item.get("runner", ""))
        parser = str(item.get("usage_parser", ""))
        if runner not in {"codex", "opencode"}:
            raise EvalConfigError(f"Unsupported runner for {key}: {runner!r}")
        expected_parser = "codex_jsonl" if runner == "codex" else "opencode_jsonl"
        if parser != expected_parser:
            raise EvalConfigError(f"Model {key} must use {expected_parser}")
        model = str(item.get("model", "")).strip()
        pricing_key = str(item.get("pricing", "")).strip()
        executable = str(item.get("executable", runner)).strip()
        agent = str(item["agent"]) if item.get("agent") else None
        if not model or not pricing_key or not executable:
            raise EvalConfigError(f"Model {key} is missing executable/model/pricing")
        if runner == "opencode" and agent not in {None, OPENCODE_EVAL_AGENT}:
            raise EvalConfigError(
                f"OpenCode model {key} must use the repository-owned {OPENCODE_EVAL_AGENT} agent"
            )
        pass_env = tuple(str(value) for value in item.get("pass_env", []))
        result[key] = ModelSpec(
            key=key,
            runner=runner,
            executable=executable,
            model=model,
            usage_parser=parser,
            pricing_key=pricing_key,
            effort=str(item["effort"]) if item.get("effort") else None,
            agent=agent,
            variant=str(item["variant"]) if item.get("variant") else None,
            pass_env=pass_env,
        )
    if not result:
        raise EvalConfigError("No models configured")
    return result


def load_prices(*, evals_root: Path = EVALS_ROOT) -> dict[str, PriceSpec]:
    raw = _read_toml(evals_root / "pricing.toml")
    if raw.get("schema_version") != 1:
        raise EvalConfigError("Unsupported pricing schema")
    result: dict[str, PriceSpec] = {}
    for key, item in raw.get("pricing", {}).items():
        key = _safe_id(str(key), label="pricing key")
        result[key] = PriceSpec(
            key=key,
            provider=str(item.get("provider", "")),
            as_of=str(item.get("as_of", "")),
            source=str(item.get("source", "")),
            input_per_million=float(item["input_per_million"]),
            cached_input_per_million=float(item["cached_input_per_million"]),
            cache_write_per_million=float(item["cache_write_per_million"]),
            output_per_million=float(item["output_per_million"]),
            input_includes_cached=bool(item["input_includes_cached"]),
            output_includes_reasoning=bool(item["output_includes_reasoning"]),
            long_context_threshold=(
                int(item["long_context_threshold"])
                if item.get("long_context_threshold") is not None
                else None
            ),
            long_context_input_multiplier=float(item.get("long_context_input_multiplier", 1.0)),
            long_context_output_multiplier=float(item.get("long_context_output_multiplier", 1.0)),
        )
    return result


def parse_model_keys(value: str, available: dict[str, ModelSpec]) -> list[str]:
    keys = [item.strip() for item in value.split(",") if item.strip()]
    if not keys:
        raise EvalConfigError("At least one model is required")
    unknown = [key for key in keys if key not in available]
    if unknown:
        raise EvalConfigError(f"Unknown model(s): {', '.join(unknown)}")
    if len(set(keys)) != len(keys):
        raise EvalConfigError("Duplicate model keys are not allowed")
    return keys
# END_BLOCK: CONFIG


# START_BLOCK: GIT_WORKTREES
def _git(repo_root: Path, *args: str, check: bool = True, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=text,
    )


def validate_base(task: TaskSpec, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.validate_base
    # purpose: Prove that a task points at the exact committed Git tree.
    # inputs: TaskSpec and repository root.
    # returns: resolved commit/tree plus remote reachability metadata.
    # side_effects: read-only Git subprocesses.
    # emitted_logs: none.
    # error_behavior: raises EvalConfigError on missing/mismatched objects.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.validate_base
    try:
        commit = _git(repo_root, "rev-parse", "--verify", f"{task.base_sha}^{{commit}}").stdout.strip()
        tree = _git(repo_root, "rev-parse", f"{commit}^{{tree}}").stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise EvalConfigError(f"Task base commit is unavailable: {task.base_sha}") from exc
    if commit != task.base_sha:
        raise EvalConfigError(f"Task base resolved unexpectedly: {commit}")
    if tree != task.base_tree:
        raise EvalConfigError(f"Task tree mismatch: expected {task.base_tree}, got {tree}")
    remote = _git(repo_root, "branch", "-r", "--contains", commit, check=False).stdout.strip()
    tags = _git(repo_root, "tag", "--contains", commit, check=False).stdout.splitlines()
    return {
        "baseSha": commit,
        "baseTree": tree,
        "remoteReachable": bool(remote),
        "containingRemoteBranches": remote.splitlines() if remote else [],
        "containingTags": [tag for tag in tags if tag],
    }


def git_blob_sha256(repo_root: Path, base_sha: str, relative_path: str) -> str | None:
    result = _git(repo_root, "show", f"{base_sha}:{relative_path}", check=False, text=False)
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def _assert_under(path: Path, parent: Path) -> None:
    try:
        Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(parent)))
    except ValueError as exc:
        raise RuntimeError(f"Unsafe path outside eval run root: {path}") from exc


def create_worktree(repo_root: Path, worktree: Path, base_sha: str, run_root: Path) -> None:
    _assert_under(worktree, run_root)
    if worktree.exists():
        raise RuntimeError(f"Worktree path already exists: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo_root, "worktree", "add", "--detach", str(worktree), base_sha)


def link_dependencies(
    repo_root: Path,
    worktree: Path,
    relative_paths: Iterable[str],
) -> tuple[list[Path], list[str]]:
    created: list[Path] = []
    warnings: list[str] = []
    for relative in relative_paths:
        source = repo_root / relative
        destination = worktree / relative
        if not source.exists():
            warnings.append(f"dependency source missing: {relative}")
            continue
        if destination.exists() or destination.is_symlink():
            warnings.append(f"dependency destination already exists: {relative}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=source.is_dir())
        created.append(destination)
    return created, warnings


def unlink_dependency_links(worktree: Path, dependency_links: Iterable[Path]) -> None:
    for link in dependency_links:
        _assert_under(link, worktree)
        if link.is_symlink():
            link.unlink()


def remove_worktree(
    repo_root: Path,
    worktree: Path,
    run_root: Path,
    dependency_links: Iterable[Path],
) -> None:
    _assert_under(worktree, run_root)
    unlink_dependency_links(worktree, dependency_links)
    if worktree.exists():
        _git(repo_root, "worktree", "remove", "--force", str(worktree), check=False)


def changed_paths(worktree: Path) -> list[str]:
    output = _git(worktree, "status", "--porcelain=v1", "--untracked-files=all").stdout
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return sorted(set(paths))


def path_is_allowed(path: str, patterns: Iterable[str]) -> bool:
    return any(path == pattern or fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def changed_paths_since(worktree: Path, base_ref: str) -> list[str]:
    changed = set(changed_paths(worktree))
    diff_raw = _git(
        worktree,
        "diff",
        "--name-only",
        "-z",
        base_ref,
        text=False,
    ).stdout
    changed.update(
        item.decode("utf-8") for item in diff_raw.split(b"\0") if item
    )
    return sorted(changed)


def capture_patch(
    worktree: Path,
    output_path: Path,
    *,
    base_ref: str = "HEAD",
) -> tuple[list[str], str]:
    untracked_raw = _git(
        worktree,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        text=False,
    ).stdout
    untracked = [item.decode("utf-8") for item in untracked_raw.split(b"\0") if item]
    if untracked:
        _git(worktree, "add", "-N", "--", *untracked)
    patch = _git(
        worktree,
        "diff",
        "--binary",
        "--no-ext-diff",
        base_ref,
        text=False,
    ).stdout
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patch)
    return changed_paths_since(worktree, base_ref), hashlib.sha256(patch).hexdigest()
# END_BLOCK: GIT_WORKTREES


# START_BLOCK: PROCESS
def sanitized_agent_env(model: ModelSpec) -> dict[str, str]:
    allowed_sensitive = SAFE_SENSITIVE_ENV | set(model.pass_env)
    result = {
        key: value
        for key, value in os.environ.items()
        if not SENSITIVE_ENV_RE.search(key) or key in allowed_sensitive
    }
    # The installed /usr/local/bin/codex wrapper otherwise enables its
    # dangerous-bypass default. Keep the eval explicitly fail-closed.
    result["CODEX_DANGEROUS_BYPASS_DEFAULT"] = "0"
    result["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
    return result


def sanitized_verification_env() -> dict[str, str]:
    result = {
        key: value
        for key, value in os.environ.items()
        if not SENSITIVE_ENV_RE.search(key)
    }
    result["CI"] = "1"
    result["PYTHONNOUSERSITE"] = "1"
    return result


def write_opencode_eval_config(worktree: Path) -> Path:
    """Install the repository-owned, single-agent policy for one run."""
    path = worktree / OPENCODE_PROJECT_CONFIG
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"Eval refuses to replace existing {OPENCODE_PROJECT_CONFIG}")
    permission = {
        "*": "deny",
        "read": "allow",
        "list": "allow",
        "glob": "allow",
        "grep": "allow",
        "edit": "allow",
        "write": "allow",
        "patch": "allow",
        "lsp": "allow",
        "bash": {
            "*": "allow",
            "git commit*": "deny",
            "git push*": "deny",
            "git reset*": "deny",
            "git clean*": "deny",
            "git checkout*": "deny",
            "git switch*": "deny",
            "git restore*": "deny",
            "git worktree*": "deny",
            "git branch*": "deny",
            "git tag*": "deny",
            "git merge*": "deny",
            "git rebase*": "deny",
            "gh *": "deny",
            "curl *": "deny",
            "wget *": "deny",
            "ssh *": "deny",
            "scp *": "deny",
            "rsync *": "deny",
            "docker *": "deny",
            "systemctl *": "deny",
            "sudo *": "deny",
        },
        "task": "deny",
        "skill": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "question": "deny",
        "external_directory": "deny",
        "todowrite": "deny",
    }
    config = {
        "$schema": "https://opencode.ai/config.json",
        "agent": {
            OPENCODE_EVAL_AGENT: {
                "description": "Repository-owned single-agent coding eval policy",
                "mode": "primary",
                "permission": permission,
            }
        },
    }
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def debug_opencode_eval_agent(model: ModelSpec, worktree: Path) -> dict[str, Any]:
    result = subprocess.run(
        [model.executable, "debug", "agent", OPENCODE_EVAL_AGENT, "--pure"],
        cwd=worktree,
        env=sanitized_agent_env(model),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise EvalConfigError(f"OpenCode eval agent policy is unavailable: {detail}")
    resolved = result.stdout.strip()
    if not resolved:
        raise EvalConfigError("OpenCode eval agent policy resolved to empty output")
    return {
        "agent": OPENCODE_EVAL_AGENT,
        "resolvedSha256": hashlib.sha256(resolved.encode("utf-8")).hexdigest(),
    }


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> ProcessResult:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.run_process
    # purpose: Run one bounded process group and persist its stdout/stderr.
    # inputs: argv, cwd, timeout, artifact paths, optional env/stdin.
    # returns: ProcessResult including timeout and wall-clock evidence.
    # side_effects: starts/kills a subprocess group and writes two files.
    # emitted_logs: none.
    # error_behavior: executable startup errors propagate; timeouts are recorded.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.run_process
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    returncode: int | None = None
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=True,
        )
        try:
            process.communicate(input=stdin_text, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        returncode = process.returncode
    return ProcessResult(
        command=tuple(command),
        returncode=returncode,
        timed_out=timed_out,
        wall_seconds=round(time.monotonic() - started, 3),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )


def build_model_command(
    model: ModelSpec,
    *,
    title: str,
    worktree: Path | None = None,
) -> tuple[list[str], bool]:
    if model.runner == "codex":
        command = [
            model.executable,
            "exec",
            "--json",
            "--ephemeral",
            "-s",
            "danger-full-access",
            "-m",
            model.model,
        ]
        if worktree is not None:
            command.extend(["-C", str(worktree)])
        if model.effort:
            command.extend(["-c", f'model_reasoning_effort="{model.effort}"'])
        command.extend(["-c", 'approval_policy="never"'])
        command.extend(["-c", "features.multi_agent=false"])
        command.append("-")
        return command, True
    command = [
        model.executable,
        "run",
        "--pure",
    ]
    if worktree is not None:
        command.extend(["--dir", str(worktree)])
    command.extend([
        "--model",
        model.model,
        "--format",
        "json",
        "--title",
        title,
    ])
    command.extend(["--agent", model.agent or OPENCODE_EVAL_AGENT])
    if model.variant:
        command.extend(["--variant", model.variant])
    return command, False


def executable_version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = (result.stdout or result.stderr).strip()
    return value or None


def run_verification(worktree: Path, specs: Iterable[VerificationSpec], artifact_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in specs:
        result = run_process(
            ["bash", "-c", spec.command],
            cwd=worktree,
            timeout_seconds=spec.timeout_seconds,
            stdout_path=artifact_dir / f"verification-{spec.name}.stdout.log",
            stderr_path=artifact_dir / f"verification-{spec.name}.stderr.log",
            env=sanitized_verification_env(),
        )
        results.append(
            {
                "name": spec.name,
                "command": spec.command,
                "returncode": result.returncode,
                "timedOut": result.timed_out,
                "wallSeconds": result.wall_seconds,
                "passed": result.returncode == 0 and not result.timed_out,
                "stdout": str(Path(result.stdout_path).name),
                "stderr": str(Path(result.stderr_path).name),
            }
        )
    return results
# END_BLOCK: PROCESS


# START_BLOCK: USAGE_COST
def parse_codex_usage(path: Path) -> Usage:
    usage: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    if usage is None:
        raise ValueError("Codex trace has no turn.completed usage")
    return Usage(
        input_tokens=int(usage.get("input_tokens", 0)),
        cached_input_tokens=int(usage.get("cached_input_tokens", 0)),
        cache_write_input_tokens=int(usage.get("cache_write_input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        reasoning_tokens=int(usage.get("reasoning_output_tokens", 0)),
    )


def find_opencode_session_id(path: Path) -> str | None:
    keys = ("sessionID", "sessionId", "session_id")

    def visit(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
            for child in value.values():
                found = visit(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = visit(child)
                if found:
                    return found
        return None

    found: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            candidate = visit(json.loads(line))
        except json.JSONDecodeError:
            continue
        if candidate:
            found = candidate
    return found


def parse_opencode_jsonl_usage(path: Path) -> Usage:
    """Sum OpenCode live step_finish token parts exactly once."""
    input_tokens = 0
    cached_input_tokens = 0
    cache_write_input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    reported_cost = 0.0
    reported_cost_found = False
    found = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "step_finish":
            continue
        part = event.get("part")
        if not isinstance(part, dict) or not isinstance(part.get("tokens"), dict):
            continue
        tokens = part["tokens"]
        cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
        input_tokens += int(tokens.get("input", 0))
        cached_input_tokens += int(cache.get("read", 0))
        cache_write_input_tokens += int(cache.get("write", 0))
        output_tokens += int(tokens.get("output", 0))
        reasoning_tokens += int(tokens.get("reasoning", 0))
        if part.get("cost") is not None:
            reported_cost += float(part["cost"])
            reported_cost_found = True
        found = True
    if not found:
        raise ValueError("OpenCode JSON stream has no step_finish token parts")
    return Usage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_input_tokens=cache_write_input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        reported_cost_usd=reported_cost if reported_cost_found else None,
    )


# Compatibility alias for callers/tests that used the initial draft name.
parse_opencode_usage = parse_opencode_jsonl_usage


def calculate_normalized_cost(usage: Usage, price: PriceSpec) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.calculate_normalized_cost
    # purpose: Reprice normalized tokens with one immutable official snapshot.
    # inputs: normalized Usage and PriceSpec billing semantics.
    # returns: component breakdown and total USD without mutating usage.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: clamps inconsistent negative uncached tokens and warns.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.calculate_normalized_cost
    warnings: list[str] = []
    if price.input_includes_cached:
        uncached = usage.input_tokens - usage.cached_input_tokens - usage.cache_write_input_tokens
        if uncached < 0:
            warnings.append("cached/cache-write tokens exceed total input; uncached clamped to zero")
            uncached = 0
    else:
        uncached = usage.input_tokens

    input_multiplier = 1.0
    output_multiplier = 1.0
    if price.long_context_threshold and usage.input_tokens > price.long_context_threshold:
        # Provider traces expose aggregate turn usage, not the size of each
        # individual request. Do not silently apply a full-request surcharge to
        # an aggregate estimate; flag it for a manual billing review instead.
        warnings.append(
            "aggregate input exceeds long-context threshold; exact per-request surcharge is unknown"
        )

    billable_output = usage.output_tokens
    if not price.output_includes_reasoning:
        billable_output += usage.reasoning_tokens

    divisor = 1_000_000
    components = {
        "uncachedInput": uncached * price.input_per_million * input_multiplier / divisor,
        "cachedInput": (
            usage.cached_input_tokens
            * price.cached_input_per_million
            * input_multiplier
            / divisor
        ),
        "cacheWrite": (
            usage.cache_write_input_tokens
            * price.cache_write_per_million
            * input_multiplier
            / divisor
        ),
        "output": billable_output * price.output_per_million * output_multiplier / divisor,
    }
    total = sum(components.values())
    return {
        "pricingKey": price.key,
        "pricingAsOf": price.as_of,
        "pricingSource": price.source,
        "componentsUsd": {key: round(value, 8) for key, value in components.items()},
        "normalizedCostUsd": round(total, 8),
        "reportedCostUsd": usage.reported_cost_usd,
        "warnings": warnings,
    }
# END_BLOCK: USAGE_COST


# START_BLOCK: EVAL_RUN
def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controller_status(repo_root: Path) -> list[str]:
    return _git(repo_root, "status", "--short").stdout.splitlines()


def dependency_runtime_evidence(repo_root: Path, task: TaskSpec) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for relative in task.dependency_links:
        source = repo_root / relative
        item: dict[str, Any] = {
            "path": relative,
            "exists": source.exists(),
            "resolvedPath": str(source.resolve()) if source.exists() else None,
        }
        marker_names: tuple[str, ...] = ()
        if relative == "node_modules":
            marker_names = (".pnpm/lock.yaml", ".modules.yaml")
        elif relative.endswith(".venv"):
            marker_names = ("pyvenv.cfg",)
        item["markers"] = {
            marker: _sha256(source / marker)
            for marker in marker_names
            if (source / marker).is_file()
        }
        python = source / "bin" / "python"
        if python.is_file():
            version = subprocess.run(
                [str(python), "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            item["pythonVersion"] = (version.stdout or version.stderr).strip() or None
            installed = subprocess.run(
                [str(python), "-m", "pip", "freeze", "--all"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if installed.returncode == 0:
                normalized = "\n".join(sorted(installed.stdout.splitlines())) + "\n"
                item["installedPackagesSha256"] = hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest()
        evidence.append(item)
    return evidence


def build_manifest(
    task: TaskSpec,
    selected_models: Sequence[ModelSpec],
    prices: dict[str, PriceSpec],
    base_evidence: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    controller_head = _git(repo_root, "rev-parse", "HEAD").stdout.strip()
    return {
        "schemaVersion": 1,
        "runnerVersion": RUNNER_VERSION,
        "createdAt": datetime.now(UTC).isoformat(),
        "task": {
            "id": task.task_id,
            "title": task.title,
            "contractSha256": _sha256(task.directory / "task.toml"),
            "promptSha256": _sha256(task.prompt_path),
            "rubricSha256": _sha256(task.rubric_path),
            "timeoutSeconds": task.timeout_seconds,
            "allowedPaths": list(task.allowed_paths),
        },
        "base": {
            **base_evidence,
            "agentsSha256": git_blob_sha256(repo_root, task.base_sha, "AGENTS.md"),
            "pnpmLockSha256": git_blob_sha256(repo_root, task.base_sha, "pnpm-lock.yaml"),
            "packageLockSha256": git_blob_sha256(repo_root, task.base_sha, "package-lock.json"),
            "poetryLockSha256": git_blob_sha256(
                repo_root, task.base_sha, "apps/api/poetry.lock"
            ),
            "pyprojectSha256": git_blob_sha256(
                repo_root, task.base_sha, "apps/api/pyproject.toml"
            ),
        },
        "controller": {
            "head": controller_head,
            "dirty": bool(_controller_status(repo_root)),
            "runnerSha256": _sha256(Path(__file__)),
            "modelsSha256": _sha256(EVALS_ROOT / "models.toml"),
            "pricingSha256": _sha256(EVALS_ROOT / "pricing.toml"),
        },
        "requestedModels": [asdict(model) for model in selected_models],
        "pricingSnapshots": {
            model.pricing_key: asdict(prices[model.pricing_key])
            for model in selected_models
        },
        "dependencyRuntime": dependency_runtime_evidence(repo_root, task),
    }


def _candidate_labels(model_keys: Sequence[str]) -> dict[str, str]:
    shuffled = list(model_keys)
    secrets.SystemRandom().shuffle(shuffled)
    return {key: chr(ord("A") + index) for index, key in enumerate(shuffled)}


def _command_for_artifact(command: Sequence[str], prompt_in_argv: bool) -> list[str]:
    if prompt_in_argv and command:
        return [*command[:-1], "<EVAL_PROMPT>"]
    return list(command)


def run_baseline(
    task: TaskSpec,
    *,
    repo_root: Path,
    run_root: Path,
) -> list[dict[str, Any]]:
    worktree = run_root / "worktrees" / "baseline"
    artifact_dir = run_root / "baseline"
    links: list[Path] = []
    try:
        create_worktree(repo_root, worktree, task.base_sha, run_root)
        links, warnings = link_dependencies(repo_root, worktree, task.dependency_links)
        results = run_verification(worktree, task.verification, artifact_dir)
        _write_json(artifact_dir / "verification.json", {"warnings": warnings, "commands": results})
        return results
    finally:
        remove_worktree(repo_root, worktree, run_root, links)


def run_candidate(
    task: TaskSpec,
    model: ModelSpec,
    price: PriceSpec,
    label: str,
    *,
    repo_root: Path,
    run_root: Path,
    keep_worktrees: bool,
) -> dict[str, Any]:
    worktree = run_root / "worktrees" / f"candidate-{label.lower()}"
    artifact_dir = run_root / "candidates" / label.lower()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    links: list[Path] = []
    evidence: dict[str, Any] = {
        "candidate": label,
        "runner": model.runner,
        "modelKey": model.key,
        "model": model.model,
        "cliVersion": executable_version(model.executable),
        "pricingKey": price.key,
    }
    prompt = task.prompt_path.read_text(encoding="utf-8")
    opencode_config: Path | None = None
    try:
        create_worktree(repo_root, worktree, task.base_sha, run_root)
        links, link_warnings = link_dependencies(repo_root, worktree, task.dependency_links)
        evidence["dependencyWarnings"] = link_warnings

        if model.runner == "opencode":
            opencode_config = write_opencode_eval_config(worktree)
            evidence["openCodePolicy"] = {
                "configSha256": _sha256(opencode_config),
                **debug_opencode_eval_agent(model, worktree),
            }

        command, prompt_via_stdin = build_model_command(
            model,
            title=f"eval:{task.task_id}:{label}",
            worktree=worktree,
        )
        if not prompt_via_stdin:
            command.append(prompt)
        try:
            process = run_process(
                command,
                cwd=worktree,
                timeout_seconds=task.timeout_seconds,
                stdout_path=artifact_dir / "agent.stdout.jsonl",
                stderr_path=artifact_dir / "agent.stderr.log",
                env=sanitized_agent_env(model),
                stdin_text=prompt if prompt_via_stdin else None,
            )
        finally:
            if opencode_config is not None and opencode_config.exists():
                opencode_config.unlink()
            opencode_config = None
        evidence["agent"] = {
            "command": _command_for_artifact(command, not prompt_via_stdin),
            "returncode": process.returncode,
            "timedOut": process.timed_out,
            "wallSeconds": process.wall_seconds,
        }

        unlink_dependency_links(worktree, links)
        links = []
        agent_head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
        evidence["headIntegrity"] = {
            "expected": task.base_sha,
            "afterAgent": agent_head,
            "passed": agent_head == task.base_sha,
        }
        pre_paths, pre_patch_hash = capture_patch(
            worktree,
            artifact_dir / "candidate.patch",
            base_ref=task.base_sha,
        )
        evidence["changedPaths"] = pre_paths
        evidence["scopeViolations"] = [
            path for path in pre_paths if not path_is_allowed(path, task.allowed_paths)
        ]
        evidence["patchSha256"] = pre_patch_hash
        evidence["patchBytes"] = (artifact_dir / "candidate.patch").stat().st_size

        links, verification_link_warnings = link_dependencies(
            repo_root,
            worktree,
            task.dependency_links,
        )
        evidence["verificationDependencyWarnings"] = verification_link_warnings
        verification = run_verification(worktree, task.verification, artifact_dir)
        evidence["verification"] = verification
        unlink_dependency_links(worktree, links)
        links = []
        post_paths, post_patch_hash = capture_patch(
            worktree,
            artifact_dir / "candidate-after-verification.patch",
            base_ref=task.base_sha,
        )
        post_verification_head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
        evidence["headIntegrity"]["afterVerification"] = post_verification_head
        evidence["headIntegrity"]["passed"] = (
            agent_head == task.base_sha and post_verification_head == task.base_sha
        )
        evidence["verificationMutatedPatch"] = post_patch_hash != pre_patch_hash
        evidence["postVerificationChangedPaths"] = post_paths
        control_violations = [
            *(["candidate changed Git HEAD"] if not evidence["headIntegrity"]["passed"] else []),
            *(
                [f"out-of-scope paths: {', '.join(evidence['scopeViolations'])}"]
                if evidence["scopeViolations"]
                else []
            ),
        ]
        evidence["controllerValidity"] = {
            "passed": not control_violations,
            "violations": control_violations,
        }

        usage: Usage | None = None
        usage_error: str | None = None
        try:
            if model.usage_parser == "codex_jsonl":
                usage = parse_codex_usage(artifact_dir / "agent.stdout.jsonl")
            else:
                evidence["openCodeSessionId"] = find_opencode_session_id(
                    artifact_dir / "agent.stdout.jsonl"
                )
                usage = parse_opencode_jsonl_usage(artifact_dir / "agent.stdout.jsonl")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            usage_error = str(exc)

        if usage is not None:
            evidence["usage"] = asdict(usage)
            evidence["cost"] = calculate_normalized_cost(usage, price)
        else:
            evidence["usage"] = None
            evidence["cost"] = None
        evidence["usageError"] = usage_error
        _write_json(artifact_dir / "evidence.json", evidence)
        return evidence
    finally:
        if opencode_config is not None and opencode_config.exists():
            opencode_config.unlink()
        if not keep_worktrees:
            remove_worktree(repo_root, worktree, run_root, links)


def render_scorecard(
    task: TaskSpec,
    candidates: Sequence[dict[str, Any]],
    baseline: Sequence[dict[str, Any]],
) -> str:
    lines = [
        f"# Agent eval scorecard — {task.task_id}",
        "",
        "> Stage 1: inspect candidate patches and fill quality scores before opening `identity.json`.",
        "",
        f"Base: `{task.base_sha}` (`{task.base_tree}`)",
        "",
        "## Baseline verification",
        "",
        "| Check | Pass | Seconds |",
        "|---|---:|---:|",
    ]
    for item in baseline:
        lines.append(f"| {item['name']} | {'yes' if item['passed'] else 'no'} | {item['wallSeconds']} |")
    lines.extend(
        [
            "",
            "## Candidate-blind quality review",
            "",
            "| Candidate | Completion / 100 | Accuracy / 100 | Critical failure | Notes |",
            "|---|---:|---:|---|---|",
        ]
    )
    for candidate in sorted(candidates, key=lambda item: item["candidate"]):
        lines.append(f"| {candidate['candidate']} | TODO | TODO | TODO | TODO |")
    lines.extend(
        [
            "",
            f"Use `evals/tasks/{task.task_id}/{task.rubric_path.name}`. Do not use cost to score quality.",
            "",
            "## Objective evidence (open after quality scoring)",
            "",
            "| Candidate | Agent outcome | Seconds | Patch bytes | Control valid | Verification | Input | Cached | Cache write | Output | Reasoning | Normalized cost |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for candidate in sorted(candidates, key=lambda item: item["candidate"]):
        verification = candidate.get("verification", [])
        passed = sum(1 for item in verification if item.get("passed"))
        usage = candidate.get("usage") or {}
        cost = (candidate.get("cost") or {}).get("normalizedCostUsd")
        validity = candidate.get("controllerValidity", {}).get("passed")
        agent = candidate.get("agent", {})
        outcome = "timeout" if agent.get("timedOut") else f"rc={agent.get('returncode', 'n/a')}"
        lines.append(
            f"| {candidate['candidate']} | {outcome} | {agent.get('wallSeconds', 'n/a')} "
            f"| {candidate.get('patchBytes', 'n/a')} | {'yes' if validity else 'no'} "
            f"| {passed}/{len(verification)} "
            f"| {usage.get('input_tokens', 'n/a') if usage else 'n/a'} "
            f"| {usage.get('cached_input_tokens', 'n/a') if usage else 'n/a'} "
            f"| {usage.get('cache_write_input_tokens', 'n/a') if usage else 'n/a'} "
            f"| {usage.get('output_tokens', 'n/a') if usage else 'n/a'} "
            f"| {usage.get('reasoning_tokens', 'n/a') if usage else 'n/a'} "
            f"| {cost if cost is not None else 'n/a'} |"
        )
    lines.extend(
        [
            "",
            "## Revealed result",
            "",
            "- Candidate A: TODO",
            "- Candidate B: TODO",
            "- Verdict: TODO",
            "- Rationale: TODO",
            "",
        ]
    )
    return "\n".join(lines)


def execute_eval(
    task: TaskSpec,
    selected_models: Sequence[ModelSpec],
    prices: dict[str, PriceSpec],
    *,
    repo_root: Path = REPO_ROOT,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    run_id: str | None = None,
    keep_worktrees: bool = False,
    skip_baseline: bool = False,
) -> Path:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.execute_eval
    # purpose: Run one paid, candidate-blind local eval batch end to end.
    # inputs: frozen task, selected models/prices and local output options.
    # returns: completed local run directory.
    # side_effects: invokes configured agents/tests and manages Git worktrees.
    # emitted_logs: none.
    # error_behavior: controller failures propagate; candidate outcomes persist.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL.execute_eval
    base_evidence = validate_base(task, repo_root=repo_root)
    if run_id is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%sz")
        run_id = f"{timestamp}-{task.task_id}"
    run_id = _safe_id(run_id, label="run id")
    run_root = (runs_root / run_id).resolve()
    _assert_under(run_root, runs_root)
    if run_root.exists():
        raise RuntimeError(f"Run already exists: {run_root}")
    run_root.mkdir(parents=True)

    keys = [model.key for model in selected_models]
    manifest = build_manifest(task, selected_models, prices, base_evidence, repo_root=repo_root)
    labels = _candidate_labels(keys)
    _write_json(run_root / "manifest.json", manifest)
    _write_json(
        run_root / "identity.json",
        {
            "warning": "Open only after candidate-blind quality scoring",
            "candidates": {labels[key]: key for key in keys},
        },
    )
    packet_dir = run_root / "task-packet"
    packet_dir.mkdir()
    for source in (
        task.directory / "task.toml",
        task.prompt_path,
        task.rubric_path,
        EVALS_ROOT / "models.toml",
        EVALS_ROOT / "pricing.toml",
    ):
        shutil.copyfile(source, packet_dir / source.name)

    baseline = [] if skip_baseline else run_baseline(task, repo_root=repo_root, run_root=run_root)
    if baseline and not all(item.get("passed") for item in baseline):
        _write_json(run_root / "baseline-failed.json", {"baseline": baseline})
        raise RuntimeError(
            f"Baseline verification failed; paid candidate calls were skipped ({run_root})"
        )
    candidates: list[dict[str, Any]] = []
    for model in selected_models:
        price = prices.get(model.pricing_key)
        if price is None:
            raise EvalConfigError(f"Missing pricing entry {model.pricing_key} for {model.key}")
        candidates.append(
            run_candidate(
                task,
                model,
                price,
                labels[model.key],
                repo_root=repo_root,
                run_root=run_root,
                keep_worktrees=keep_worktrees,
            )
        )

    for candidate in candidates:
        label = candidate["candidate"].lower()
        source = run_root / "candidates" / label / "candidate.patch"
        shutil.copyfile(source, run_root / f"candidate-{label}.patch")
    _write_json(run_root / "objective-metrics.json", {"baseline": baseline, "candidates": candidates})
    (run_root / "scorecard.md").write_text(
        render_scorecard(task, candidates, baseline),
        encoding="utf-8",
    )
    return run_root
# END_BLOCK: EVAL_RUN


# START_BLOCK: CLI
def validate_configuration(
    task: TaskSpec,
    selected_models: Sequence[ModelSpec],
    prices: dict[str, PriceSpec],
    *,
    repo_root: Path,
    worktree_smoke: bool,
    baseline_smoke: bool,
) -> dict[str, Any]:
    base = validate_base(task, repo_root=repo_root)
    model_results: list[dict[str, Any]] = []
    for model in selected_models:
        if model.pricing_key not in prices:
            raise EvalConfigError(f"Missing pricing entry {model.pricing_key}")
        model_results.append(
            {
                "key": model.key,
                "runner": model.runner,
                "model": model.model,
                "executable": shutil.which(model.executable),
                "cliVersion": executable_version(model.executable),
                "pricing": model.pricing_key,
            }
        )
        if shutil.which(model.executable) is None:
            raise EvalConfigError(f"Executable not found for {model.key}: {model.executable}")

    smoke: dict[str, Any] | None = None
    if worktree_smoke:
        smoke_root = DEFAULT_RUNS_ROOT / f"validate-{os.getpid()}-{task.task_id}"
        worktree = smoke_root / "worktrees" / "smoke"
        links: list[Path] = []
        opencode_config: Path | None = None
        try:
            smoke_root.mkdir(parents=True, exist_ok=False)
            create_worktree(repo_root, worktree, task.base_sha, smoke_root)
            links, warnings = link_dependencies(repo_root, worktree, task.dependency_links)
            head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
            policies: list[dict[str, Any]] = []
            opencode_models = [model for model in selected_models if model.runner == "opencode"]
            if opencode_models:
                opencode_config = write_opencode_eval_config(worktree)
                for model in opencode_models:
                    policies.append(debug_opencode_eval_agent(model, worktree))
                opencode_config.unlink()
                opencode_config = None
            unlink_dependency_links(worktree, links)
            links = []
            smoke_paths = changed_paths(worktree)
            smoke = {
                "head": head,
                "dependencyWarnings": warnings,
                "clean": not smoke_paths,
                "changedPaths": smoke_paths,
                "openCodePolicies": policies,
            }
        finally:
            if opencode_config is not None and opencode_config.exists():
                opencode_config.unlink()
            remove_worktree(repo_root, worktree, smoke_root, links)
            shutil.rmtree(smoke_root, ignore_errors=True)
    baseline: list[dict[str, Any]] | None = None
    if baseline_smoke:
        baseline_root = DEFAULT_RUNS_ROOT / f"validate-baseline-{os.getpid()}-{task.task_id}"
        try:
            baseline_root.mkdir(parents=True, exist_ok=False)
            baseline = run_baseline(task, repo_root=repo_root, run_root=baseline_root)
        finally:
            shutil.rmtree(baseline_root, ignore_errors=True)
    return {
        "task": task.task_id,
        "base": base,
        "models": model_results,
        "worktreeSmoke": smoke,
        "baseline": baseline,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local reproducible coding-agent eval runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List repository-owned tasks and models (free)")

    validate = subparsers.add_parser("validate", help="Validate a task without model calls")
    validate.add_argument("task")
    validate.add_argument("--models", required=True, help="Comma-separated model keys")
    validate.add_argument("--worktree", action="store_true", help="Create/remove one free smoke worktree")
    validate.add_argument("--baseline", action="store_true", help="Run task verification without model calls")

    run = subparsers.add_parser("run", help="Run a paid local eval batch")
    run.add_argument("task")
    run.add_argument("--models", required=True, help="Comma-separated model keys")
    run.add_argument("--run-id")
    run.add_argument("--keep-worktrees", action="store_true")
    run.add_argument("--skip-baseline", action="store_true")
    run.add_argument(
        "--confirm-paid-run",
        action="store_true",
        help="Required guard acknowledging that configured model calls may cost money",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        models = load_models()
        prices = load_prices()
        if args.command == "list":
            tasks = sorted(path.parent.name for path in (EVALS_ROOT / "tasks").glob("*/task.toml"))
            print("Tasks:")
            for task in tasks:
                print(f"  {task}")
            print("Models:")
            for key, model in sorted(models.items()):
                print(f"  {key}: {model.runner} / {model.model}")
            return 0

        task = load_task(args.task)
        model_keys = parse_model_keys(args.models, models)
        selected = [models[key] for key in model_keys]
        if args.command == "validate":
            result = validate_configuration(
                task,
                selected,
                prices,
                repo_root=REPO_ROOT,
                worktree_smoke=args.worktree,
                baseline_smoke=args.baseline,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            baseline = result.get("baseline")
            return 0 if not baseline or all(item.get("passed") for item in baseline) else 2

        if not args.confirm_paid_run:
            raise EvalConfigError("Paid run refused: add --confirm-paid-run")
        run_root = execute_eval(
            task,
            selected,
            prices,
            run_id=args.run_id,
            keep_worktrees=args.keep_worktrees,
            skip_baseline=args.skip_baseline,
        )
        print(f"Eval completed: {run_root}")
        print(f"Review patches before identity: {run_root / 'scorecard.md'}")
        return 0
    except (EvalConfigError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"agent_eval: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK: CLI
