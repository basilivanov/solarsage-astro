#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: TEST_AGENT_EVAL — focused tests for the local agent-eval runner
# ROLE: Verify configuration, Git isolation, provider parsing and cost math.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-AGENT-EVAL
# purpose: Test scripts.agent_eval without invoking a paid model.
# owns:
#   - scripts/test_agent_eval.py
# inputs: temporary Git repositories and synthetic provider traces.
# outputs: pytest assertions.
# dependencies: pytest and scripts.agent_eval.
# side_effects: creates temporary files/repositories only.
# emitted_logs: none.
# invariants: no network, CLI or model call is made.
# failure_policy: pytest reports a failing runner contract.
# END_MODULE_CONTRACT: M-TEST-AGENT-EVAL

# START_MODULE_MAP: M-TEST-AGENT-EVAL
# public_entrypoints:
#   - test_* functions
# semantic_blocks:
#   - CONFIG_AND_COMMANDS
#   - USAGE_AND_COST
#   - GIT_ISOLATION
# owned_tests: self
# END_MODULE_MAP: M-TEST-AGENT-EVAL

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.agent_eval import (
    ModelSpec,
    PriceSpec,
    TaskSpec,
    Usage,
    build_model_command,
    calculate_normalized_cost,
    capture_patch,
    create_worktree,
    load_models,
    load_prices,
    parse_codex_usage,
    parse_opencode_usage,
    remove_worktree,
    sanitized_verification_env,
    validate_base,
    write_opencode_eval_config,
)


def _price(**overrides: object) -> PriceSpec:
    values = {
        "key": "test-price",
        "provider": "test",
        "as_of": "2026-07-30",
        "source": "https://example.invalid/pricing",
        "input_per_million": 0.20,
        "cached_input_per_million": 0.02,
        "cache_write_per_million": 0.25,
        "output_per_million": 1.20,
        "input_includes_cached": True,
        "output_includes_reasoning": True,
    }
    values.update(overrides)
    return PriceSpec(**values)


def test_build_model_commands_pin_runner_and_prompt_mode() -> None:
    codex = ModelSpec(
        key="luna",
        runner="codex",
        executable="codex",
        model="gpt-5.6-luna",
        usage_parser="codex_jsonl",
        pricing_key="p",
        effort="high",
    )
    command, stdin = build_model_command(codex, title="eval:test:A")
    assert stdin is True
    assert command[:3] == ["codex", "exec", "--json"]
    assert "gpt-5.6-luna" in command
    assert "danger-full-access" in command
    assert 'model_reasoning_effort="high"' in command
    assert "features.multi_agent=false" in command
    assert command[-1] == "-"

    opencode = ModelSpec(
        key="gemini",
        runner="opencode",
        executable="opencode",
        model="cliproxy/gemini-3.6-flash-high",
        usage_parser="opencode_jsonl",
        pricing_key="p",
        agent="repo-eval",
    )
    command, stdin = build_model_command(opencode, title="eval:test:B")
    assert stdin is False
    assert command[:3] == ["opencode", "run", "--pure"]
    assert "repo-eval" in command


def test_repository_configs_load_dotted_keys_as_single_ids() -> None:
    models = load_models()
    prices = load_prices()
    assert set(models) == {"luna-high", "gemini-3.6-high"}
    assert models["gemini-3.6-high"].model == "cliproxy/gemini-3.6-flash-high"
    assert prices["gpt-5.6-luna-2026-07-30"].output_per_million == 1.20


def test_opencode_eval_policy_is_repo_owned_and_no_delegation(tmp_path: Path) -> None:
    path = write_opencode_eval_config(tmp_path)
    policy = json.loads(path.read_text(encoding="utf-8"))["agent"]["repo-eval"]
    assert policy["mode"] == "primary"
    assert policy["permission"]["task"] == "deny"
    assert policy["permission"]["external_directory"] == "deny"
    assert policy["permission"]["bash"]["git commit*"] == "deny"


def test_verification_environment_drops_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_TEST_API_KEY", "must-not-pass")
    assert "EVAL_TEST_API_KEY" not in sanitized_verification_env()


def test_parse_codex_jsonl_uses_completed_usage(tmp_path: Path) -> None:
    trace = tmp_path / "codex.jsonl"
    trace.write_text(
        "\n".join(
            [
                json.dumps({"type": "turn.started"}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 1000,
                            "cached_input_tokens": 200,
                            "output_tokens": 80,
                            "reasoning_output_tokens": 30,
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    usage = parse_codex_usage(trace)
    assert usage == Usage(input_tokens=1000, cached_input_tokens=200, output_tokens=80, reasoning_tokens=30)


def test_parse_opencode_jsonl_sums_step_finish_tokens(tmp_path: Path) -> None:
    export = tmp_path / "session.jsonl"
    export.write_text(
        "\n".join(
            [
                json.dumps({"type": "step_start", "sessionID": "ses_test"}),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_test",
                        "part": {
                            "cost": 0.01,
                            "tokens": {
                                "input": 600,
                                "output": 50,
                                "reasoning": 10,
                                "cache": {"read": 200, "write": 10},
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_test",
                        "part": {
                            "cost": 0.02,
                            "tokens": {
                                "input": 400,
                                "output": 30,
                                "reasoning": 10,
                                "cache": {"read": 100, "write": 0},
                            },
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    usage = parse_opencode_usage(export)
    assert usage.input_tokens == 1000
    assert usage.cached_input_tokens == 300
    assert usage.cache_write_input_tokens == 10
    assert usage.reasoning_tokens == 20
    assert usage.reported_cost_usd == pytest.approx(0.03)


def test_luna_cost_uses_current_snapshot_rates() -> None:
    result = calculate_normalized_cost(
        Usage(
            input_tokens=1_000_000,
            cached_input_tokens=200_000,
            cache_write_input_tokens=100_000,
            output_tokens=100_000,
        ),
        _price(),
    )
    # 0.7M*.20 + .2M*.02 + .1M*.25 + .1M*1.20
    assert result["normalizedCostUsd"] == pytest.approx(0.289)


def test_reasoning_is_not_double_counted_when_output_includes_it() -> None:
    result = calculate_normalized_cost(
        Usage(output_tokens=100_000, reasoning_tokens=50_000),
        _price(output_includes_reasoning=True),
    )
    assert result["normalizedCostUsd"] == pytest.approx(0.12)


def test_gemini_style_cost_adds_separate_reasoning_tokens() -> None:
    result = calculate_normalized_cost(
        Usage(input_tokens=1_000_000, cached_input_tokens=200_000, output_tokens=100_000, reasoning_tokens=50_000),
        _price(
            key="gemini",
            input_per_million=1.50,
            cached_input_per_million=0.15,
            cache_write_per_million=1.50,
            output_per_million=7.50,
            input_includes_cached=False,
            output_includes_reasoning=False,
        ),
    )
    # 1M*1.50 + .2M*.15 + (.1M+.05M)*7.50
    assert result["normalizedCostUsd"] == pytest.approx(2.655)


def test_worktree_starts_at_exact_base_and_captures_new_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Eval", "-c", "user.email=eval@example.invalid", "commit", "-qm", "base"],
        cwd=repo,
        check=True,
    )
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    task = TaskSpec(
        task_id="test-task",
        title="test",
        directory=tmp_path,
        base_sha=sha,
        base_tree=tree,
        prompt_path=tmp_path / "prompt.md",
        rubric_path=tmp_path / "rubric.md",
        timeout_seconds=10,
        allowed_paths=("README.md", "new.txt"),
        dependency_links=(),
        verification=(),
    )
    assert validate_base(task, repo_root=repo)["baseTree"] == tree

    run_root = repo / ".eval-runs" / "test"
    worktree = run_root / "worktrees" / "candidate-a"
    create_worktree(repo, worktree, sha, run_root)
    try:
        assert (worktree / "README.md").read_text(encoding="utf-8") == "base\n"
        (worktree / "README.md").write_text("changed\n", encoding="utf-8")
        (worktree / "new.txt").write_text("new\n", encoding="utf-8")
        paths, patch_hash = capture_patch(worktree, run_root / "candidate.patch")
        assert paths == ["README.md", "new.txt"]
        assert patch_hash
        assert "new.txt" in (run_root / "candidate.patch").read_text(encoding="utf-8")

        subprocess.run(["git", "add", "README.md", "new.txt"], cwd=worktree, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Eval",
                "-c",
                "user.email=eval@example.invalid",
                "commit",
                "-qm",
                "candidate commit",
            ],
            cwd=worktree,
            check=True,
        )
        committed_paths, _ = capture_patch(
            worktree,
            run_root / "candidate-committed.patch",
            base_ref=sha,
        )
        assert committed_paths == ["README.md", "new.txt"]
        assert "new.txt" in (run_root / "candidate-committed.patch").read_text(
            encoding="utf-8"
        )
    finally:
        remove_worktree(repo, worktree, run_root, ())
