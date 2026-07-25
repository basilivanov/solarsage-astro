# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_FIX_RUNNER
# ROLE: Automated fix runner using git worktrees and OpenCode headless agent.
# DEPENDENCIES: subprocess, json, sys, os, datetime, pathlib
# GRACE_ANCHORS: [FIX_RUNNER]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-FIX_RUNNER
# purpose: Read a GitHub prod-error issue, check protected path safeguards, create git worktree, generate ТЗ, run opencode headless agent, verify changes, and submit PR or post failure comment.
# owns:
#   - scripts/prod-errors/fix_runner.py
# inputs: issue_number (CLI argument)
# outputs: stdout execution log
# dependencies: git, gh, opencode CLI via subprocess
# side_effects: creates worktree, runs opencode, commits, pushes branch, creates PR or posts comment
# failure_policy: catches execution failures, comments on issue, cleans up worktree
# END_MODULE_CONTRACT: M-SCRIPTS-FIX_RUNNER

# START_MODULE_MAP: M-SCRIPTS-FIX_RUNNER
# public_entrypoints:
#   - main
# semantic_blocks:
#   - FIX_RUNNER_CORE: worktree creation, opencode invocation, verification and PR submission
# END_MODULE_MAP: M-SCRIPTS-FIX_RUNNER

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROTECTED_PATTERNS = [
    "apps/api/app/services/billing",
    "apps/api/app/api/payment",
    "apps/api/app/services/telegram_auth",
    "apps/api/app/api/auth",
]


def fetch_github_issue(repo: str, issue_number: str) -> dict:
    """Fetch GitHub issue details via gh CLI."""
    cmd = ["gh", "issue", "view", issue_number, "--repo", repo, "--json", "number,title,body,labels"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def is_protected_issue(title: str, body: str) -> bool:
    """Check if issue touches protected billing or auth paths."""
    text = f"{title}\n{body}".lower()
    for pattern in PROTECTED_PATTERNS:
        if pattern.lower() in text:
            return True
    return False


def run_fix_for_issue(issue_number: str) -> None:
    repo = os.environ.get("GH_REPO", "basilivanov/solarsage-astro")
    model = os.environ.get("PROD_ERRORS_MODEL", "cliproxy/gemini-3.6-flash-high")
    repo_root = Path(__file__).resolve().parents[2]
    config_file = repo_root / "scripts" / "prod-errors" / "opencode.prod-errors.json"

    print(f"Processing prod-error Issue #{issue_number}...")

    try:
        issue = fetch_github_issue(repo, issue_number)
    except Exception as err:
        sys.stderr.write(f"Failed to fetch Issue #{issue_number}: {err}\n")
        sys.exit(1)

    title = issue.get("title", "")
    body = issue.get("body", "")

    if is_protected_issue(title, body):
        msg = f"Auto-fix skipped for Issue #{issue_number}: issue touches protected billing/auth code."
        print(msg)
        subprocess.run(["gh", "issue", "comment", issue_number, "--repo", repo, "--body", msg])
        return

    worktree_name = f"prod-error-{issue_number}"
    worktree_path = repo_root / ".worktrees" / worktree_name
    branch_name = f"fix/prod-error-{issue_number}"

    # Extract the Bugsink marker from the issue body so the PR body carries it
    # and resolve_after_deploy.py can map merged PRs back to Bugsink issues.
    marker_match = re.search(r"bugsink-issue:[a-zA-Z0-9_-]+", body)
    bugsink_marker = marker_match.group(0) if marker_match else None

    # Clean up old worktree/branch if exists
    if worktree_path.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=repo_root)

    print(f"Creating git worktree at {worktree_path}...")
    subprocess.run(["git", "fetch", "origin"], cwd=repo_root, check=True)
    res = subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, str(worktree_path), "origin/main"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        # Branch might already exist, checkout existing branch
        subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_root)
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), "origin/main"],
            cwd=repo_root,
            check=True,
        )

    try:
        # Generate ТЗ document inside worktree
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tz_doc_path = worktree_path / "docs" / "work" / f"{today_str}_prod-error-{issue_number}_TZ.md"
        tz_doc_path.parent.mkdir(parents=True, exist_ok=True)

        tz_content = f"""# Auto-Fix ТЗ — Production Error #{issue_number}

## Objective
Fix production error reported in Issue #{issue_number}:
Title: {title}

## Context
{body}

## Rules & Directives
- Implement minimal, robust fix for the reported issue in the affected files.
- Do NOT modify billing (`apps/api/app/services/billing*`, `apps/api/app/api/payment*`) or auth (`apps/api/app/services/telegram_auth*`, `apps/api/app/api/auth*`).
- Maintain existing codebase patterns and GRACE header annotations.
- Do NOT execute `git commit` or `git push` directly (the test runner manages commits).
- Ensure all targeted tests pass.
"""
        tz_doc_path.write_text(tz_content, encoding="utf-8")

        prompt = f"Read ТЗ in {tz_doc_path.relative_to(worktree_path)} and fix the issue. Run targeted tests to verify."

        # Headless opencode reads opencode.json from the project directory;
        # stage the prod-errors permission profile as the worktree config.
        worktree_opencode_config = worktree_path / "opencode.json"
        shutil.copyfile(config_file, worktree_opencode_config)

        # Checks need the main checkout's installed dependencies (worktree has
        # none): symlink node_modules and the API venv; removed before staging.
        node_modules_link = worktree_path / "node_modules"
        venv_link = worktree_path / "apps" / "api" / ".venv"
        node_modules_link.symlink_to(repo_root / "node_modules")
        venv_link.symlink_to(repo_root / "apps" / "api" / ".venv")

        print(f"Executing opencode run in worktree using model {model}...")
        env = dict(os.environ)
        opencode_cmd = ["opencode", "run", "-m", model, prompt]
        opencode_res = subprocess.run(opencode_cmd, cwd=worktree_path, timeout=1200, capture_output=True, text=True, env=env)

        if opencode_res.returncode != 0:
            raise RuntimeError(f"OpenCode run failed: {opencode_res.stderr or opencode_res.stdout}")

        # Check git status for modified files
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=worktree_path, capture_output=True, text=True, check=True)
        modified_lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]

        if not modified_lines:
            raise RuntimeError("OpenCode executed but left zero modified files.")

        print(f"Modified files ({len(modified_lines)}):")
        for m in modified_lines:
            print(f"  {m}")

        # Targeted Verification
        print("Running targeted verification checks...")
        has_frontend = any(".ts" in line or ".tsx" in line for line in modified_lines)
        has_backend = any("apps/api/" in line for line in modified_lines)

        if has_frontend:
            print("Running TypeScript typecheck...")
            tsc_res = subprocess.run(["npx", "tsc", "--noEmit"], cwd=worktree_path, capture_output=True, text=True)
            if tsc_res.returncode != 0:
                raise RuntimeError(f"TypeScript typecheck failed:\n{tsc_res.stdout}\n{tsc_res.stderr}")

        if has_backend:
            print("Running Python backend tests...")
            py_res = subprocess.run(
                ["bash", "-c", "cd apps/api && .venv/bin/python -m pytest tests/ -q"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )
            if py_res.returncode != 0:
                raise RuntimeError(f"Pytest verification failed:\n{py_res.stdout}\n{py_res.stderr}")

        # Remove check-only symlinks and the staged opencode config so they
        # never land in the commit.
        node_modules_link.unlink(missing_ok=True)
        venv_link.unlink(missing_ok=True)
        worktree_opencode_config.unlink(missing_ok=True)

        # All checks passed! Stage, commit, push, create PR
        print("All verification checks passed! Submitting PR...")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
        commit_msg = f"fix: {title} (prod-error #{issue_number})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=worktree_path, check=True)
        subprocess.run(["git", "push", "origin", branch_name], cwd=worktree_path, check=True)

        marker_line = f"\n- Bugsink marker: `{bugsink_marker}`" if bugsink_marker else ""
        pr_body = f"Fixes #{issue_number}\n\nAutomated fix created by prod-error runner for Issue #{issue_number}.\n\n### Summary\n- Title: `{title}`{marker_line}"
        pr_cmd = ["gh", "pr", "create", "--repo", repo, "--label", "prod-fix", "--title", f"fix: {title} (#{issue_number})", "--body", pr_body]
        pr_res = subprocess.run(pr_cmd, cwd=worktree_path, capture_output=True, text=True, check=True)

        print(f"Successfully created PR: {pr_res.stdout.strip()}")

    except Exception as err:
        error_msg = str(err)
        print(f"Fix attempt failed for Issue #{issue_number}: {error_msg}")
        comment_body = f"Auto-fix attempt failed for Issue #{issue_number}.\n\n```\n{error_msg[:2000]}\n```"
        subprocess.run(["gh", "issue", "comment", issue_number, "--repo", repo, "--body", comment_body])

    finally:
        print(f"Cleaning up worktree at {worktree_path}...")
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=repo_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated Fix Runner for Production Error")
    parser.add_argument("issue_number", type=str, help="GitHub Issue Number")
    args = parser.parse_args()

    run_fix_for_issue(args.issue_number)


if __name__ == "__main__":
    main()
