# AI_HEADER
# module: M-ORCH-DOCS
# wave: W-ORCH-1
# purpose: Orchestrator documentation

# GRACE Orchestrator

GRACE-ready orchestrator runtime adapter for managing wave execution.

## Features

- Load waves from `development-plan.xml`
- Track wave status (pending, in_progress, completed)
- Resolve dependencies
- Validate wave packets
- CLI interface

## Usage

### Show status

```bash
python scripts/grace-orch status
```

Output:
```
📊 GRACE Orchestrator Status

Total waves: 52
✅ Completed: 48
🔄 In progress: 0
⏳ Pending: 4
Progress: 92.3%
```

### Show next waves

```bash
python scripts/grace-orch next
```

Output:
```
🚀 Ready to execute (2 waves):

  W-ORCH-1 — GRACE-ready orchestrator runtime adapter
    Phase: future-waves

  W-SOLARSAGE-SVC — Split reference collector
    Phase: future-waves
```

### Mark wave as completed

```bash
python scripts/grace-orch complete W-ORCH-1
```

## Architecture

### Core Components

1. **GraceOrchestrator** — Core orchestrator logic
   - Load waves from XML
   - Track status
   - Resolve dependencies

2. **PacketValidator** — Validate wave packets
   - Check required sections
   - Verify GRACE compliance

3. **CLI** — Command-line interface
   - `status` — Show progress
   - `next` — Show ready waves
   - `complete` — Mark wave as completed

## Wave Status

- **pending** — Not started, waiting for dependencies
- **in_progress** — Currently being worked on
- **completed** — Finished and verified
- **blocked** — Dependencies not satisfied

## Packet Validation

Required sections in wave packets:
- `# Decision` — What was decided
- `## Acceptance Criteria` — Checklist of requirements
- `## Evidence` — Files/tests proving completion

Recommended:
- `AI_HEADER` — Module metadata
- `## Negative Tests` — Edge cases

## Integration

### Python API

```python
from grace.orchestrator import GraceOrchestrator

orch = GraceOrchestrator(Path('grace/development-plan.xml'))

# Get progress
progress = orch.get_progress()
print(f"Completed: {progress['completed']}/{progress['total']}")

# Get ready waves
ready = orch.get_ready_waves()
for wave in ready:
    print(f"{wave.id} — {wave.title}")

# Mark completed
orch.mark_completed('W-1.1')
```

### CI Integration

```yaml
# .github/workflows/grace.yml
name: GRACE Orchestrator

on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate packets
        run: python scripts/grace-orch validate
```
