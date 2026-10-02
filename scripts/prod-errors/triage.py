# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_TRIAGE
# ROLE: Production error triage runner — fetches Bugsink issues and creates GitHub issues.
# DEPENDENCIES: bugsink_client, subprocess, json, sys, os
# GRACE_ANCHORS: [TRIAGE_RUNNER]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-TRIAGE
# purpose: Fetch unresolved Bugsink issues with > 3 events, deduplicate against GitHub issues using bugsink-issue:<id> marker, create GitHub issues (if needed), and send alerts to Telegram (@vi_astro_bot).
# owns:
#   - scripts/prod-errors/triage.py
# inputs: CLI flags (--dry-run, --alert), environment variables (BUGSINK_URL, BUGSINK_TOKEN, GH_REPO, AUTO_FIX_ENABLED, MIN_EVENTS_THRESHOLD, TELEGRAM_BOT_TOKEN, TELEGRAM_DIGEST_CHAT_ID)
# outputs: stdout summary digest
# dependencies:
#   - scripts/prod-errors/bugsink_client.py (BugsinkClient)
#   - gh CLI via subprocess
# side_effects: creates GitHub issues, sends Telegram alerts
# failure_policy: logs error and continues or exits with non-zero code on unhandled failure; Telegram delivery failures never break the run
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


def format_human_summary(kind: str, route: str, event_data: dict) -> dict[str, str]:
    """Produce human-readable summary, affected scope, and urgency guidance."""
    data = event_data.get("data") if isinstance(event_data.get("data"), dict) else {}
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    http_info = extra.get("http") if isinstance(extra.get("http"), dict) else {}
    payload = extra.get("payload") if isinstance(extra.get("payload"), dict) else {}
    tags = data.get("tags") if isinstance(data.get("tags"), dict) else {}

    http_status = str(http_info.get("status") or "")
    http_method = str(http_info.get("method") or "")
    target_route = str(http_info.get("route_template") or tags.get("route") or payload.get("route") or route)
    operation = str(payload.get("operation") or "")

    # Analyze nature of the error
    summary = f"{kind} на {target_route}"
    impact = "Неизвестно"
    urgency = "⚠️ Средний (нужно проверить)"

    # Specific known patterns
    if route == "/api/_log" or "frontend." in str(data.get("message", "")):
        # Frontend error logged back to API
        if http_status == "401":
            summary = f"401 Unauthorized при запросе {target_route}"
            impact = "Пользователь с истекшей сессией или без авторизации открыл экран"
            urgency = "ℹ️ Низкий (штатное поведение при экспирации auth токена)"
        elif http_status == "404":
            summary = f"404 Not Found при запросе {target_route}"
            impact = "Запрошен несуществующий ресурс/дата/профиль"
            urgency = "ℹ️ Низкий (штатная ошибка клиента)"
        elif http_status.startswith("5"):
            summary = f"Сетевая/серверная ошибка {http_status} на {target_route}"
            impact = f"Фронтенд не смог получить данные для {operation or target_route}"
            urgency = "🚨 Высокий (бэкенд падает или недоступен)"
        else:
            summary = f"Ошибка на клиенте (фронтенд): {operation or target_route}"
            impact = f"Сбой в интерфейсе или обработке данных: {operation or target_route}"
            urgency = "⚠️ Средний (ошибка в JS на фронтенде)"
    elif route.startswith("/api/"):
        if "500" in http_status or kind in ("InternalServerError", "Exception", "RuntimeError", "KeyError"):
            summary = f"Падение бэкенда (500) на {http_method} {route}"
            impact = f"Эндпоинт {route} ломается при обработке запросов"
            urgency = "🚨 Срочно (500 на API, пользователи получают ошибку)"
        else:
            summary = f"Ошибка API {kind} на {route}"
            impact = f"Сбой при вызове эндпоинта {route}"
            urgency = "⚠️ Средний"

    return {
        "summary": summary,
        "impact": impact,
        "urgency": urgency,
        "target_route": target_route,
        "http_status": http_status,
    }


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

    # Enrich from the latest event: release, top stack frame, diagnostic payload.
    release = "unknown"
    top_frame = "unknown"
    frames_preview = ""
    diag_lines: list[str] = []
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
        # Structured diagnostics (contract name, reason_code, route) — for
        # frontend contract errors these matter more than minified frames.
        extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
        http_info = extra.get("http") if isinstance(extra.get("http"), dict) else {}
        if http_info:
            diag_lines.append(
                f"- **http:** `{http_info.get('method', '?')} {http_info.get('route_template', '?')}` -> `{http_info.get('status', '?')}`"
            )
        payload = extra.get("payload") if isinstance(extra.get("payload"), dict) else {}
        for key in sorted(payload):
            diag_lines.append(f"- **payload.{key}:** `{str(payload[key])[:200]}`")
    except Exception as err:
        sys.stderr.write(f"Warning: failed to enrich issue {issue_id} from latest event: {err}\n")

    diag_preview = "\n".join(diag_lines) if diag_lines else "No diagnostic payload."

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

### Diagnostic context (latest event)
{diag_preview}

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


REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_FIX_ATTEMPTS = int(os.environ.get("MAX_FIX_ATTEMPTS", "3"))


def gh_issue_fix_state(repo: str, issue_number: str) -> str:
    """Classify an open prod-error issue for the fix loop.

    Returns:
    - "pending": no automation outcome yet -> needs a fix_runner run
    - "retry":   previous attempts failed, attempts still left -> needs a rerun
    - "done":    fix branch/PR exists, permanently skipped, or attempts exhausted
    """
    try:
        res = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", f"fix/prod-error-{issue_number}"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        )
        if res.stdout.strip():
            return "done"
    except Exception as err:
        sys.stderr.write(f"Warning: branch check failed for issue #{issue_number}: {err}\n")
        return "done"

    try:
        res = subprocess.run(
            ["gh", "issue", "view", issue_number, "--repo", repo, "--json", "comments"],
            capture_output=True, text=True, check=True,
        )
        comments = json.loads(res.stdout).get("comments", [])
    except Exception as err:
        sys.stderr.write(f"Warning: comment check failed for issue #{issue_number}: {err}\n")
        return "done"

    failed_attempts = 0
    for comment in comments:
        body = str(comment.get("body") or "").lower()
        if "auto-fix skipped" in body:
            return "done"
        if "auto-fix attempt failed" in body:
            failed_attempts += 1
    if failed_attempts == 0:
        return "pending"
    if failed_attempts < MAX_FIX_ATTEMPTS:
        return "retry"
    return "done"


def find_pending_fix_issues(repo: str, limit: int = 10) -> list[str]:
    """Open prod-error issues that still need a fix attempt (never tried or retryable)."""
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--label", "prod-error",
        "--state", "open",
        "--json", "number",
        "--limit", "50",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        numbers = [str(item["number"]) for item in json.loads(res.stdout)]
    except Exception as err:
        sys.stderr.write(f"Warning: failed to list open prod-error issues: {err}\n")
        return []

    pending: list[str] = []
    for num in numbers:
        state = gh_issue_fix_state(repo, num)
        if state in ("pending", "retry"):
            pending.append(num)
            print(f"Issue #{num} queued for fix ({state}).")
        if len(pending) >= limit:
            break
    return pending


def send_telegram_digest(lines: list[str]) -> None:
    """Send a short triage digest to the owner's Telegram via the bot.

    Active only when both TELEGRAM_BOT_TOKEN and TELEGRAM_DIGEST_CHAT_ID are
    set. Delivery failures never break the runner.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_DIGEST_CHAT_ID", "")
    if not token or not chat_id:
        return

    import urllib.request

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                sys.stderr.write(f"Warning: Telegram digest returned HTTP {resp.status}\n")
    except Exception as err:
        sys.stderr.write(f"Warning: failed to send Telegram digest: {err}\n")


def run_triage(dry_run: bool = False) -> None:
    repo = os.environ.get("GH_REPO", "basilivanov/solarsage-astro")
    auto_fix_enabled = os.environ.get("AUTO_FIX_ENABLED", "false").lower() in ("true", "1", "yes")
    min_events_threshold = int(os.environ.get("MIN_EVENTS_THRESHOLD", "4"))  # > 3 events, so at least 4
    max_fixes = int(os.environ.get("MAX_FIXES_PER_RUN", "3"))

    print(f"Starting production error triage (repo: {repo}, dry_run: {dry_run}, min_events: >={min_events_threshold}, auto_fix: {auto_fix_enabled})...")

    client = BugsinkClient()
    try:
        # Only fetch issues with > 3 events (min_events >= 4)
        unresolved = client.list_unresolved(min_events=min_events_threshold, limit=20)
    except Exception as err:
        sys.stderr.write(f"Failed to fetch Bugsink issues: {err}\n")
        sys.exit(1)

    print(f"Found {len(unresolved)} unresolved Bugsink issues with >= {min_events_threshold} events.")

    created_issues: list[tuple[str, dict]] = []

    for item in unresolved:
        issue_id = str(item.get("id") or item.get("issue_id"))
        if not issue_id or issue_id == "None":
            continue

        if gh_issue_exists(repo, issue_id):
            print(f"Skipping bugsink-issue:{issue_id} (already tracked in GitHub).")
            continue

        new_issue_num = create_github_issue(repo, item, dry_run)
        if new_issue_num:
            created_issues.append((new_issue_num, item))

    print(f"\nTriage complete. Created {len(created_issues)} new GitHub issues.")

    # Send telegram alert for newly created issues (>3 events)
    if created_issues:
        alert_lines: list[str] = [f"🚨 <b>Bugsink Alert (&gt;3 событий)</b>: {len(created_issues)} новых issue:"]
        for num, item in created_issues:
            kind = str(item.get("calculated_type") or "Error")
            route = str(item.get("transaction") or "unknown")
            count = item.get("digested_event_count") or 0
            issue_id = str(item.get("id") or "")
            latest_event = client.get_latest_event(issue_id) if issue_id else {}
            human = format_human_summary(kind, route, latest_event)
            alert_lines.append(
                f"• #{num} <b>{human['summary']}</b>\n"
                f"  └ <b>Что затрагивает:</b> {human['impact']}\n"
                f"  └ <b>Срочность:</b> {human['urgency']}\n"
                f"  └ <b>Событий:</b> {count} | <b>Route:</b> <code>{route}</code>\n"
                f"  └ https://github.com/{repo}/issues/{num}"
            )
        send_telegram_digest(alert_lines)

    # Optional auto-fix loop (disabled by default)
    if auto_fix_enabled:
        created_numbers = [num for num, _ in created_issues]
        pending_issues = [n for n in find_pending_fix_issues(repo) if n not in created_numbers]
        if pending_issues:
            print(f"Pending unfixed prod-error issues: {', '.join('#' + n for n in pending_issues)}")

        fix_queue = (created_numbers + pending_issues)[:max_fixes]

        if not dry_run and fix_queue:
            script_dir = Path(__file__).resolve().parent
            fix_runner = script_dir / "fix_runner.py"

            for num in fix_queue:
                print(f"\nInvoking fix_runner.py for Issue #{num}...")
                subprocess.run([sys.executable, str(fix_runner), num])

            digest_lines: list[str] = []
            if created_issues:
                digest_lines.append(f"prod-errors: новых issue — {len(created_issues)}")
                digest_lines.extend(
                    f"#{num} https://github.com/{repo}/issues/{num}" for num in created_numbers
                )
            if pending_issues:
                digest_lines.append(f"повторные/зависшие: {', '.join('#' + n for n in pending_issues)}")
            digest_lines.append(f"авто-фикс запущен для {len(fix_queue)}: {', '.join('#' + n for n in fix_queue)}")
            send_telegram_digest(digest_lines)
    else:
        print("Auto-fix is disabled (AUTO_FIX_ENABLED=false).")


ALERT_STATE_PATH = Path(__file__).resolve().parent / ".alert-state.json"
ALERT_SPIKE_DELTA = 5


def run_alert() -> None:
    """Fast alert-only pass: issues with > 3 events and event spikes to Telegram.

    No GitHub issues, no fix runner. State (.alert-state.json) holds last seen
    digested_event_count per issue; first run initializes silently to avoid a
    one-time alert flood.
    """
    client = BugsinkClient()
    try:
        # Check issues with > 3 events (at least 4)
        issues = client.list_unresolved(min_events=4, limit=50)
    except Exception as err:
        sys.stderr.write(f"Failed to fetch Bugsink issues: {err}\n")
        sys.exit(1)

    state: dict[str, int] = {}
    first_run = not ALERT_STATE_PATH.is_file()
    if not first_run:
        try:
            state = json.loads(ALERT_STATE_PATH.read_text())
        except Exception:
            state = {}

    new_state: dict[str, int] = {}
    alert_lines: list[str] = []
    for item in issues:
        issue_id = str(item.get("id") or "")
        if not issue_id:
            continue
        count = int(item.get("digested_event_count") or 0)
        new_state[issue_id] = count
        kind = str(item.get("calculated_type") or "Error")
        route = str(item.get("transaction") or "unknown")
        prev = state.get(issue_id)
        if prev is None or count - int(prev) >= ALERT_SPIKE_DELTA:
            latest_event = client.get_latest_event(issue_id)
            human = format_human_summary(kind, route, latest_event)
            if prev is None:
                alert_lines.append(
                    f"🚨 NEW: <b>{human['summary']}</b>\n"
                    f"  └ <b>Что затрагивает:</b> {human['impact']}\n"
                    f"  └ <b>Срочность:</b> {human['urgency']}\n"
                    f"  └ <b>Событий:</b> {count} (>3) | <b>Route:</b> <code>{route}</code>"
                )
            else:
                alert_lines.append(
                    f"📈 SPIKE (+{count - int(prev)} ev): <b>{human['summary']}</b>\n"
                    f"  └ <b>Что затрагивает:</b> {human['impact']}\n"
                    f"  └ <b>Срочность:</b> {human['urgency']}\n"
                    f"  └ <b>Всего событий:</b> {count} | <b>Route:</b> <code>{route}</code>"
                )

    ALERT_STATE_PATH.write_text(json.dumps(new_state))

    if first_run:
        print(f"alert: state initialized with {len(new_state)} issues, no alerts sent")
        return

    if alert_lines:
        send_telegram_digest(["<b>Bugsink Alert (>3 событий):</b>"] + alert_lines[:10])
        for line in alert_lines:
            print(line)
    else:
        print("alert: no new or spiking issues with >3 events")


def main() -> None:
    parser = argparse.ArgumentParser(description="Production Error Triage")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without side effects")
    parser.add_argument("--alert", action="store_true", help="Fast alert-only pass (no issues/fixes)")
    args = parser.parse_args()

    if args.alert:
        run_alert()
    else:
        run_triage(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
