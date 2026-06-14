# Archon Azure — Claude Context

## What this repo is

Archon Azure is the Microsoft Azure port of the Archon agentic financial intelligence platform.
Submitted to Microsoft Agents League @ AI Skills Fest 2026 (Reasoning Agents + Enterprise Agents tracks).

Repo: https://github.com/upgradedev/archon_azure (public, MIT)

## Session rescan protocol

Run at the start of every Claude Code session before making any changes:

```bash
cd repos/azure

# 1. Branch state
git log --oneline -10

# 2. Uncommitted work
git status

# 3. CI baseline — last run must be green on master
# Check: https://github.com/upgradedev/archon_azure/actions

# 4. Env vars baseline
grep -c "=" .env.example   # expect 14+
```

Stop and investigate before proceeding if CI is red or env var count drops.

## Architecture Decision Records

### ADR-001 — Trunk-based development
**Date:** 2026-06-14 | **Status:** Active
**Decision:** Short-lived branches + PR → CI pass → merge. No direct pushes to master.
**Reason:** Branch protection requires smoke-test to pass before merge.

### ADR-002 — gitleaks SecretScan as first CI stage
**Date:** 2026-06-14 | **Status:** Active
**Decision:** `gitleaks detect` runs as the first step in `smoke-test.yml` before any build.
**Reason:** Azure OpenAI and AI Search keys are real billable credentials.

### ADR-003 — Null-safe LLM JSON parsing
**Date:** 2026-06-14 | **Status:** Active
**Decision:** All LLM response field mappings use `data.get(key) or default`. Numeric fields use `_safe_float()`. Document construction goes through `extractors/utils.build_document()`.
**Reason:** `dict.get(key, default)` ignores `None` values returned by LLM. Pydantic raises `ValidationError` on required fields receiving `None` without the `or` pattern.

### ADR-004 — Ephemeral Foundry agents per request
**Date:** 2026-06-14 | **Status:** Active
**Decision:** `NarratorAgent._foundry_agent_summary` creates and deletes a Foundry agent per `/analyze` call.
**Reason:** Keeps Foundry workspace clean. `create_and_process_run` (SDK b10) already blocks until completion — no external polling loop needed.

### ADR-005 — Thread-safe extraction parameters
**Date:** 2026-06-14 | **Status:** Active
**Decision:** `jobs/extraction/main.py::main()` accepts `upload_id` and `period` as function parameters. `server.py` (local dev) passes them directly instead of setting `os.environ`.
**Reason:** Setting process-level environment variables in a multi-threaded local dev server is not safe under concurrent job submissions.

### ADR-006 — Pydantic optional fields must have explicit `= None` defaults
**Date:** 2026-06-14 | **Status:** Active
**Decision:** Every `field: SomeType | None` must have `= None` as a default.
**Reason:** Pydantic v2 treats `field: str | None` (no default) as required. Constructors that omit it raise `ValidationError`.

## Alice standards that apply (adapted for GitHub)

- Session rescan protocol (above)
- ADRs in CLAUDE.md for every key design decision
- gitleaks SecretScan as first CI stage
- Evaluator-style review before merging (smoke-test gate)

## Alice standards that do NOT apply

- ADO work item format (uses GitHub Issues)
- HEDNO tenant / Azure config (different Azure subscription)
- ADO branch naming (trunk-based development)
