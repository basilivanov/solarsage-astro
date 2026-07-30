# SolarSage local agent evals

This directory stores immutable task definitions, model/pricing snapshots and
small human-reviewed results. Paid model execution is local only; GitHub is the
source of truth for tasks and accepted scorecards.

## Core rules

1. Every task pins a full `base_sha` and Git tree hash from the real repository.
2. A task version, prompt and rubric are immutable after the first scored run.
3. Every candidate gets an isolated detached worktree from the same base.
4. Agents do not commit/push or delegate to subagents.
5. Model time excludes dependency preparation and controller verification.
6. The controller records tests, scope, usage and price; a human scores quality.
7. Raw traces stay in ignored `.eval-runs/`; only reviewed compact results enter Git.

Code may continue changing after a task is frozen. New models can still run the
old task for a like-for-like comparison. To evaluate a newer architecture, add a
new task version with a new base SHA; never move an old task's base.

The source tree is frozen exactly; the heavy local `node_modules` and Python
virtualenv are linked rather than copied. Every run fingerprints their lock and
installed-package state. For a later old-snapshot rerun, prepare dependencies
from that task's pinned lockfiles and compare the recorded fingerprints. Models
inside one batch always share the same runtime, which keeps the direct A/B fair.

## Commands

```bash
python3 scripts/agent_eval.py list
python3 scripts/agent_eval.py validate checkin-mood-trend-v1 \
  --models luna-high,gemini-3.6-high \
  --worktree --baseline
python3 scripts/agent_eval.py run checkin-mood-trend-v1 \
  --models luna-high,gemini-3.6-high \
  --confirm-paid-run
```

`validate` is free and performs no model call. `run` is paid and prints the run
directory containing anonymized patches, raw evidence and a scorecard template.
Codex usage is read from its JSONL `turn.completed` event. OpenCode usage is
read from live `step_finish` JSON events; the local OpenCode 1.18.9 export
command is not used as the accounting source.

The controller creates a temporary `repo-eval` OpenCode agent inside each
candidate worktree. It disables subagents, web tools, questions, access outside
the worktree and Git history-changing commands, then removes that config before
capturing the candidate patch. `--pure` disables third-party OpenCode plugins.
This is a practical local guardrail, not an operating-system sandbox; do not run
eval prompts copied from untrusted parties.

The local Codex wrapper cannot nest its `workspace-write` bwrap sandbox on this
host (`RTM_NEWADDR` failure), so the Luna adapter uses explicit
`danger-full-access` with approvals disabled. The frozen worktree, exact scope
check and trusted repository-owned prompt are reproducibility controls, not a
security boundary. Run this harness only with trusted task packets and models.

`normalizedCostUsd` always uses the immutable official price snapshot committed
with the task. `reportedCostUsd` is kept separately; the local `cliproxy`
provider may report zero even when the comparable official API estimate is
non-zero. Luna's snapshot uses $0.20 input, $0.02 cached input and $1.20 output
per million tokens from the current official model page.

## Adding a model

Models already available through OpenCode need only a new table in
`models.toml` and an immutable official-price entry in `pricing.toml`. This is
the intended path for DeepSeek and other providers. Add runner code only when a
new CLI has a genuinely different execution/usage contract.

Never commit API keys or copy local provider configuration into this directory.
The run manifest records model/CLI identifiers and price snapshot IDs, not
credentials.

## Reviewing and keeping a result

1. Read `candidate-a.patch` and `candidate-b.patch` without opening identity or
   cost files.
2. Fill completion, accuracy, critical failures and notes in `scorecard.md`.
3. Reveal identities and compare measured time/tokens/normalized cost.
4. Copy only the completed scorecard, sanitized metrics and small patches into
   `evals/results/<run-id>/`, then commit them through normal review.

Do not infer a universal winner from one task. For a strict speed comparison,
run all candidates in one batch on the same host; results added months later are
still useful for code quality but latency is less directly comparable.
