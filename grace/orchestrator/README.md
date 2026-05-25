# GRACE Orchestrator Project Adapter

This directory is the project-local contract between the portable
orchestration runtime and this repository.

Prefect is only the workflow runtime. GRACE readiness lives here: packet
schema, allowed-scope enforcement, verification profiles, evidence contracts,
and role prompts.

| File | Purpose |
| --- | --- |
| `project.yml` | Repository-specific runtime adapter. |
| `verification_profiles.yml` | Named verification commands. |
| `packet.schema.json` | Machine contract for new controller packets. |
| `roles/*.md` | Project-local role contracts/prompts. |
