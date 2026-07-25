# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_TRIAGE
# ROLE: Production error triage runner — fetches Bugsink issues and creates GitHub issues.
# DEPENDENCIES: bugsink_client, subprocess, json, sys, os
# GRACE_ANCHORS: [TRIAGE_RUNNER]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-TRIAGE
# purpose: Fetch unresolved Bugsink issues, deduplicate against GitHub issues using bugsink-issue:<id> marker, create GitHub issues, invoke fix_runner.py, and output digest.
# owns:
#   - scripts/prod-errors/triage.py
# inputs: CLI flags (--dry-run), environment variables (BUGSINK_URL, BUGSINK_TOKEN, GH_REPO, MAX_FIXES_PER_RUN)
# outputs: stdout summary digest
# dependencies:
#   - scripts/prod-errors/bugsink_client.py (BugsinkClient)
#   - gh CLI via subprocess
# side_effects: creates GitHub issues, invokes fix_runner.py
# failure_policy: logs error and continues or exits with non-zero code on unhandled failure
# END_MODULE_CONTRACT: M-SCRIPTS-TRIAGE

# START_MODULE_MAP: M-SCRIPTS-TRIAGE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - TRIAGE_CORE: triage and GitHub issue deduplication
# END_MODULE_MAP: M-SCRIPTS-TRIAGE

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bugsink_client import BugsinkClient


def gh_issue_exists(repo: str, bugsink_issue_id: str) -> bool:
    """Check if GitHub issue already exists for bugsink-issue:<id>."""
    search_query = f"bugsink-issue:{bugsink_issue_id}"
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--label", "prod-error",
        "--state", "all",
        "--search", search_query,
        "--json", "number",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        items = json.loads(res.stdout)
        return len(items) > 0
    except Exception as err:
        sys.stderr.write(f"Warning: Failed to check existing GitHub issue for {bugsink_issue_id}: {err}\n")
        return False


def create_github_issue(repo: str, issue_data: dict, dry_run: bool) -> str | None:
    """Create GitHub issue for Bugsink error report.

    Field mapping follows the canonical Bugsink Issue schema:
    id, friendly_id, calculated_type, calculated_value, transaction,
    digested_event_count, first_seen, last_seen.
    """
    issue_id = str(issue_data.get("id") or "unknown")
    friendly_id = str(issue_data.get("friendly_id") or issue_id)
    kind = str(issue_data.get("calculated_type") or "Error")
    value = str(issue_data.get("calculated_value") or "")
    count = issue_data.get("digested_event_count") or 0
    first_seen = issue_data.get("first_seen") or "unknown"
    last_seen = issue_data.get("last_seen") or "unknown"
    route = str(issue_data.get("transaction") or "unknown")
    bugsink_url = os.environ.get("BUGSINK_URL", "http://127.0.0.1:18095").rstrip("/")

    # Enrich from the latest event: release and top stack frame.
    release = "unknown"
    top_frame = "unknown"
    frames_preview = ""
    try:
        client = BugsinkClient()
        event = client.get_latest_event(issue_id)
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        release = str(data.get("release") or "unknown")
        exception = data.get("exception") if isinstance(data.get("exception"), dict) else {}
        values = exception.get("values") if isinstance(exception.get("values"), list) else []
        frames = values[0].get("stacktrace", {}).get("frames", []) if values else []
        if frames:
            last = frames[-1]
            top_frame = f"{last.get('filename', '?')}:{last.get('function', '?')}"
            shown = frames[-5:]
            frames_preview = "\n".join(
                f"- `{f.get('filename', '?')}` in `{f.get('function', '?')}` line {f.get('lineno', '?')}"
                for f in shown
            )
    except Exception as err:
        sys.stderr.write(f"Warning: failed to enrich issue {issue_id} from latest event: {err}\n")

    title = f"{kind} at {top_frame} ({route})"
    body = f"""## Production Error Report

- **Bugsink Marker:** `bugsink-issue:{issue_id}`
- **Kind:** `{kind}`
- **Message:** `{value[:500]}`
- **Top Frame / Culprit:** `{top_frame}`
- **Route:** `{route}`
- **Event Count:** `{count}`
- **First Seen:** `{first_seen}`
- **Last Seen:** `{last_seen}`
- **Release:** `{release}`
- **Bugsink Link:** {bugsink_url}/issues/{friendly_id}

### Stack frames (latest event, innermost last)
{frames_preview or "No stack frames available."}

### Description
Automated production error report captured from Bugsink self-hosted error tracker.
"""

    if dry_run:
        print(f"[DRY-RUN] Would create GitHub issue: {title}")
        return None

    cmd = [
        "gh", "issue", "create",
        "--repo", repo,
        "--label", "prod-error",
        "--title", title,
        "--body", body,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issue_url = res.stdout.strip()
        print(f"Created GitHub issue: {issue_url}")
        # Extract issue number from URL (e.g. https://github.com/org/repo/issues/123 -> 123)
        parts = issue_url.rstrip("/").split("/")
        return parts[-1] if parts[-1].isdigit() else None
    except Exception as err:
        sys.stderr.write(f"Error creating GitHub issue: {err}\n")
        return None


def run_triage(dry_run: bool = False) -> None:
    repo = os.environ.get("GH_REPO", "basilivanov/solarsage-astro")
    max_fixes = int(os.environ.get("MAX_FIXES_PER_RUN", "3"))

    print(f"Starting production error triage (repo: {repo}, dry_run: {dry_run})...")

    client = BugsinkClient()
    try:
        unresolved = client.list_unresolved(min_events=3, limit=10)
    except Exception as err:
        sys.stderr.write(f"Failed to fetch Bugsink issues: {err}\n")
        sys.exit(1)

    print(f"Found {len(unresolved)} unresolved Bugsink issues with >= 3 events.")

    created_issues: list[str] = []

    for item in unresolved:
        issue_id = str(item.get("id") or item.get("issue_id"))
        if not issue_id or issue_id == "None":
            continue

        if gh_issue_exists(repo, issue_id):
            print(f"Skipping bugsink-issue:{issue_id} (already tracked in GitHub).")
            continue

        new_issue_num = create_github_issue(repo, item, dry_run)
        if new_issue_num:
            created_issues.append(new_issue_num)

    print(f"\nTriage complete. Created {len(created_issues)} new GitHub issues.")

    if not dry_run and created_issues:
        script_dir = Path(__file__).resolve().parent
        fix_runner = script_dir / "fix_runner.py"

        for num in created_issues[:max_fixes]:
            print(f"\nInvoking fix_runner.py for Issue #{num}...")
            subprocess.run([sys.executable, str(fix_runner), num])


def main() -> None:
    parser = argparse.ArgumentParser(description="Production Error Triage")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without side effects")
    args = parser.parse_args()

    run_triage(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
