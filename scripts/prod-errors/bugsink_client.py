# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_BUGSINK_CLIENT
# ROLE: Python REST API client for Bugsink error tracking.
# DEPENDENCIES: urllib.request, json, os
# GRACE_ANCHORS: [BUGSINK_CLIENT]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-BUGSINK-CLIENT
# purpose: Interact with Bugsink REST API to list unresolved issues, get issue details, and mark issues resolved.
# owns:
#   - scripts/prod-errors/bugsink_client.py
# inputs: BUGSINK_URL, BUGSINK_TOKEN, BUGSINK_PROJECT_ID
# outputs: issue lists and dictionaries
# dependencies: urllib.request, json, os
# side_effects: network requests to Bugsink
# failure_policy: raises RuntimeError on API errors
# END_MODULE_CONTRACT: M-SCRIPTS-BUGSINK-CLIENT

# START_MODULE_MAP: M-SCRIPTS-BUGSINK-CLIENT
# public_entrypoints:
#   - BugsinkClient
# semantic_blocks:
#   - CLIENT_CORE: BugsinkClient REST API operations
# END_MODULE_MAP: M-SCRIPTS-BUGSINK-CLIENT

from __future__ import annotations

import json
import os
from typing import Any
import urllib.request
import urllib.parse


class BugsinkClient:
    """REST API client for self-hosted Bugsink error tracker."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        project_id: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("BUGSINK_URL", "http://127.0.0.1:18095")).rstrip("/")
        self.token = token or os.environ.get("BUGSINK_TOKEN", "")
        # Numeric Bugsink project id (canonical API requires ?project=<int>).
        self.project_id = project_id or os.environ.get("BUGSINK_PROJECT_ID", "1")

    def _request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 204:
                    return None
                resp_bytes = resp.read()
                if not resp_bytes:
                    return None
                return json.loads(resp_bytes.decode("utf-8"))
        except Exception as err:
            raise RuntimeError(f"Bugsink API request failed [{method} {url}]: {err}") from err

    def list_unresolved(self, min_events: int = 3, limit: int = 10) -> list[dict[str, Any]]:
        """List unresolved, unmuted issues sorted by event count (desc).

        Canonical API contract: GET /api/canonical/0/issues/?project=<int>
        with sort=digested_event_count; there is no server-side query filter,
        so unresolved/muted/threshold filtering happens client-side.
        """
        endpoint = (
            f"/api/canonical/0/issues/?project={self.project_id}"
            "&sort=digested_event_count&order=desc"
        )
        res = self._request("GET", endpoint)
        if isinstance(res, dict) and isinstance(res.get("results"), list):
            items = res["results"]
        elif isinstance(res, list):
            items = res
        else:
            items = []

        unresolved = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("is_resolved") or item.get("is_muted"):
                continue
            count = int(item.get("digested_event_count") or 0)
            if count >= min_events:
                unresolved.append(item)

        return unresolved[:limit]

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        """Fetch details of a single issue by ID."""
        endpoint = f"/api/canonical/0/issues/{issue_id}/"
        res = self._request("GET", endpoint)
        return res if isinstance(res, dict) else {}

    def get_latest_event(self, issue_id: str) -> dict[str, Any]:
        """Fetch the newest event (full data payload) for an issue.

        The list endpoint omits event.data, so a detail fetch follows.
        Returns {} when the issue has no events.
        """
        endpoint = f"/api/canonical/0/events/?issue={issue_id}&order=desc"
        res = self._request("GET", endpoint)
        items = res.get("results") if isinstance(res, dict) else res
        if not isinstance(items, list) or not items:
            return {}
        event_id = items[0].get("id") if isinstance(items[0], dict) else None
        if not event_id:
            return {}
        detail = self._request("GET", f"/api/canonical/0/events/{event_id}/")
        return detail if isinstance(detail, dict) else {}

    def resolve(self, issue_id: str) -> bool:
        """Mark issue resolved in Bugsink (POST /issues/<id>/resolve/)."""
        endpoint = f"/api/canonical/0/issues/{issue_id}/resolve/"
        try:
            self._request("POST", endpoint, data={})
            return True
        except Exception:
            return False
