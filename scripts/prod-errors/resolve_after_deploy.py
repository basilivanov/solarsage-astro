# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_RESOLVE_AFTER_DEPLOY
# ROLE: Resolve deployed Bugsink issues after production release.
# DEPENDENCIES: bugsink_client, subprocess, json, sys, os, re
# GRACE_ANCHORS: [RESOLVE_AFTER_DEPLOY]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-RESOLVE-AFTER-DEPLOY
# purpose: Parse merged PRs with label prod-fix included in specified release_sha, extract bugsink-issue:<id> markers, and call BugsinkClient.resolve(id).
# owns:
#   - scripts/prod-errors/resolve_after_deploy.py
# inputs: release_sha (CLI argument), environment variables (GH_REPO, BUGSINK_URL, BUGSINK_TOKEN)
# outputs: stdout resolution summary
# dependencies:
#   - scripts/prod-errors/bugsink_client.py (BugsinkClient)
#   - gh CLI via subprocess
# side_effects: calls Bugsink REST API to mark issues resolved
# failure_policy: logs error and continues resolving remaining issues
# END_MODULE_CONTRACT: M-SCRIPTS-RESOLVE-AFTER-DEPLOY

# START_MODULE_MAP: M-SCRIPTS-RESOLVE-AFTER-DEPLOY
# public_entrypoints:
#   - main
# semantic_blocks:
#   - RESOLVE_CORE: resolve deployed Bugsink issues
# END_MODULE_MAP: M-SCRIPTS-RESOLVE-AFTER-DEPLOY

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

from bugsink_client import BugsinkClient

BUGSINK_MARKER_REGEX = re.compile(r"bugsink-issue:([a-zA-Z0-9_-]+)")


def get_merged_prod_fix_prs(repo: str) -> list[dict]:
    """Fetch merged PRs with label prod-fix."""
    cmd = [
        "gh", "pr", "list",
        "--repo", repo,
        "--label", "prod-fix",
        "--state", "merged",
        "--json", "number,title,body,mergeCommit",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as err:
        sys.stderr.write(f"Failed to fetch merged PRs from gh CLI: {err}\n")
        return []


def resolve_deployed_issues(release_sha: str) -> None:
    repo = os.environ.get("GH_REPO", "basilivanov/solarsage-astro")
    print(f"Resolving Bugsink issues for deployed release_sha: {release_sha} (repo: {repo})...")

    client = BugsinkClient()
    prs = get_merged_prod_fix_prs(repo)
    print(f"Found {len(prs)} merged prod-fix PRs.")

    resolved_count = 0

    for pr in prs:
        body = pr.get("body", "")
        title = pr.get("title", "")
        combined = f"{title}\n{body}"

        matches = BUGSINK_MARKER_REGEX.findall(combined)
        for bugsink_id in set(matches):
            print(f"Marking Bugsink issue {bugsink_id} as resolved...")
            ok = client.resolve(bugsink_id)
            if ok:
                resolved_count += 1
                print(f"Successfully resolved Bugsink issue {bugsink_id}.")
            else:
                sys.stderr.write(f"Failed to resolve Bugsink issue {bugsink_id}.\n")

    print(f"\nResolution complete. Resolved {resolved_count} Bugsink issues.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Bugsink issues after production deploy")
    parser.add_argument("release_sha", type=str, help="Deployed release SHA")
    args = parser.parse_args()

    resolve_deployed_issues(args.release_sha)


if __name__ == "__main__":
    main()
