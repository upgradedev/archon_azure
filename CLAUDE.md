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

## Current status (2026-06-14, session 5)

**master:** `a266cf5` — PRs #8–#14 merged this session (Foundry IQ debugging chain)
**CI:** GREEN — smoke-test + deploy passing (PR #13 deploy succeeded; PR #14 deploy in progress)
**Live deployment:** All Azure Container Apps running (westeurope)

### Subscription note (CRITICAL)
Archon is in **subscription `41f8b1f2-174f-4523-98d7-6ec4adea0806`** (tf Sponsorship, upgradegr tenant 2bcb5033).
Use `tf@upgrade.net.gr` for Azure CLI. Do NOT touch HEDNO subscriptions (d64d7037, etc.).

| Item | State |
|---|---|
| All 16 audit issues fixed (B1,B2,H1-H6,M1-M6) | Done — ff7113f |
| Dead code + EventLinker tests | Done — 61b5f53 |
| Analysis startup crash + deploy jq error | Done — 6cc425e |
| `scripts/e2e-live.py` — live e2e test | Done — 9e2f834 |
| `/seed-demo` endpoint on analysis container | Done — f023b5c |
| Seed-demo purges stale blobs first | Done — 2910bd1 |
| Sales invoice added to demo data (revenue > 0) | Done — 6f93cf1 |
| **E2E test result: ALL 22 CHECKS PASSED** | **VERIFIED LIVE** |
| Foundry IQ — https:// prefix stripped | Done — 9cd9313 |
| Foundry IQ — connections.get() bypassed | Done — 8ea5c14 |
| Foundry IQ — Contributor role on archon-project | Done — az rest (ce86e394) — 2026-06-14 |
| Foundry IQ — Azure OpenAI connection in Foundry project | Done — az rest — 2026-06-14 |
| Foundry IQ — MessageRole.AGENT fix | Done — a266cf5 |
| **Foundry IQ — PENDING DEPLOY VERIFICATION** | **Deploy in progress** |

### Live endpoints

| URL | Service |
|---|---|
| https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io | FastAPI backend |
| https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io | Analysis endpoint |

### E2E test

Run anytime against the live deployment:

```bash
python scripts/e2e-live.py
```

The test auto-seeds 8 demo documents via `POST /seed-demo` on the analysis container (purges stale data first — idempotent). No credentials needed.

### Live demo P&L (2026-01)

| Metric | Value |
|---|---|
| Revenue | €8,500.00 (consulting sales invoice) |
| Expenses | €7,588.39 (invoices + payroll) |
| Net Profit | €911.61 |
| Employer cost (register) | €6,930.00 |
| Bank transfer (net) | €3,994.74 |
| **28% gap ratio** | **1.735 × (confirmed live)** |

### Known gaps (open before submission)

| Gap | Notes |
|---|---|
| Foundry IQ narrator | Deploy in progress (PR #14); test with `/health/foundry` after deploy |
| M365 agent not sideloaded | User action: Teams Admin Center → m365-agent/archon-agent.zip |
| Demo video not recorded | User action: 5 min, follow docs/demo-script.md |
| Submission not filed | User action: https://aka.ms/agentsleague/aisf — DEADLINE TODAY June 14 23:59 PT |

## Alice standards that apply (adapted for GitHub)

- Session rescan protocol (above)
- ADRs in CLAUDE.md for every key design decision
- gitleaks SecretScan as first CI stage
- Evaluator-style review before merging (smoke-test gate)

## Alice standards that do NOT apply

- ADO work item format (uses GitHub Issues)
- HEDNO tenant / Azure config (different Azure subscription)
- ADO branch naming (trunk-based development)
