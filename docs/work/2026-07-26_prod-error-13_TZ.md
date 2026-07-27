# Auto-Fix ТЗ — Production Error #13

## Objective
Fix production error reported in Issue #13:
Title: Error at 0.6-ognw9gnoh.js:1:90921:<anonymous> (/api/_log)

## Context
## Production Error Report

- **Bugsink Marker:** `bugsink-issue:30d5419e-13b9-429c-b0ee-f5c4e1bc1fde`
- **Kind:** `Error`
- **Message:** `frontend.api_response_invalid`
- **Top Frame / Culprit:** `0.6-ognw9gnoh.js:1:90921:<anonymous>`
- **Route:** `/api/_log`
- **Event Count:** `1`
- **First Seen:** `2026-07-26T20:08:12.867139Z`
- **Last Seen:** `2026-07-26T20:08:12.867139Z`
- **Release:** `bab7b75845a7d655bc90b7b245337fddbf022466`
- **Bugsink Link:** http://127.0.0.1:18095/issues/SOLARSAGE-2

### Stack frames (latest event, innermost last)
- `01t._rzfzwyuq.js:1:64502` in `i` line 1
- `0.6-ognw9gnoh.js:1:88770)` in `<anonymous>` line 0
- `0.6-ognw9gnoh.js:1:90921` in `<anonymous>` line 1

### Description
Automated production error report captured from Bugsink self-hosted error tracker.

### Diagnostic context (added for retry, from Bugsink event 2026-07-26T20:08:12Z)
- **http:** `GET /api/day/{date}` -> `200` (duration 221 ms)
- **payload.operation:** `day.fetch` (caller: `lib/grace/api/client.ts` fetchDay)
- **payload.reason_code:** `invalid_json` — response body failed JSON.parse in instrumentedFetch contract check
- **payload.contract_name:** `TodayPayload` v1
- **correlation_id:** `h1_f7915a252db5221358905379`
- **release:** `bab7b75845a7d655bc90b7b245337fddbf022466`
- **client:** Telegram Android WebView

### Hypothesis to verify
HTTP 200 from `apps/api/app/api/day.py` (FastAPI always serializes TodayPayload to JSON), so a 200 with unparseable JSON suggests: empty/truncated body (client on flaky mobile network), or a proxy/middleware path returning a non-JSON 200. The frontend `clone.json()` failure is logged via `lib/log/instrumented-fetch.ts`. A minimal robust fix could be: treat 200+invalid_json as retryable in the day fetch path (single retry), and/or log the first bytes of the body shape hash for diagnosis. Do NOT modify billing/auth.
