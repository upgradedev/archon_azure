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

## Current status (2026-06-14, session 6 — submission day)

**master:** `a266cf5` — all PRs merged, CI GREEN, all Azure infra live
**Deadline:** June 14, 2026 23:59 PT (~15h remaining as of 08:50 PDT)

### Subscription note (CRITICAL)
Archon is in **subscription `41f8b1f2-174f-4523-98d7-6ec4adea0806`** (tf Sponsorship, upgradegr tenant 2bcb5033).
Use `tf@upgrade.net.gr` for Azure CLI. Do NOT touch HEDNO subscriptions (d64d7037, etc.).

### Completed this session (session 6)

| Item | State |
|---|---|
| Key Vault + App Insights + narrative reframe | Done — PRs merged (session 5 continuation) |
| Architecture SVG (`docs/architecture.svg`) | Done — in repo |
| Playwright demo script (`scripts/demo-playwright.js`) | Done — in repo |
| `demo/` artifact directory created | Done — outside repo at `C:\dev\solutions\private_nebius_aiserverless_challenge\demo\` |
| Hackathon platform registration | Done — tf@upgrade.net.gr |
| **Platform Project 1 — Reasoning Agents** | **Created** — title/tagline/keywords/challenge saved; description+repo+media still to add |
| **Platform Project 2 — Enterprise Agents** | **Created** — title/tagline/keywords/challenge saved; description+repo+media still to add |
| `demo.webm` recorded (Playwright, 5 min, 15 MB) | **Done** — `scripts/demo-output/demo.webm` |
| ffmpeg 8.1.1 installed | Done — WinGet, full path in `demo/ffmpeg-combine.ps1` |
| Teams app zip — manifest fixed (devPreview) | Done — `m365-agent/archon-agent.zip` rebuilt |
| **E2E: ALL 23 CHECKS PASSED** | **VERIFIED LIVE** |
| **Foundry IQ: citations verified live** | **VERIFIED** |

### Open gaps — deadline order

| Priority | Gap | Notes |
|---|---|---|
| P0 | Add description + repo to both platform projects | Paste from `demo/submission-reasoning-agents.md` + `demo/submission-enterprise-agents.md` |
| P0 | Teams agent sideload | Teams Developer Portal → DevPreview → import zip → Continue past errors → Preview in Teams → record 40s |
| P0 | ElevenLabs narration MP3 | Paste `docs/demo-script.md` narration text → export MP3 → `demo/narration.mp3` |
| P0 | Merge video + narration | Run `demo/ffmpeg-combine.ps1` → `demo/archon-demo.mp4` |
| P0 | Upload to YouTube (public) | Add URL to both platform projects + Discord |
| P0 | Submit both platform projects | https://aka.ms/agentsleague/aisf |
| P0 | Post Discord | Paste from `demo/discord-announcement.md` at https://aka.ms/agentsleague/discord |
| P1 | Backend bearer token enforcement | FastAPI middleware to validate Entra ID JWT — declared in openapi.json but not enforced in code |
| P1 | MCP server (bonus criteria) | External MCP read/write = "Higher Rating"; ~2h work; significant score boost |

### Gap analysis vs Enterprise Agents track rubric

| Requirement | Status |
|---|---|
| M365 Copilot Chat Agent (REQUIRED) | ✅ Declarative agent in `m365-agent/` |
| Microsoft IQ Integration (REQUIRED) | ✅ Foundry IQ — AzureAISearchTool, ephemeral agents, citations verified |
| MCP Apps (bonus — Higher Rating) | ❌ Not implemented |
| External MCP Server (optional) | ❌ Not implemented |
| OAuth for MCP (optional) | ❌ N/A |
| Bearer auth enforced on backend | ⚠️ Declared in openapi.json but not validated in FastAPI code |

### Teams app manifest notes

`m365-agent/archon-agent.zip` requires `manifestVersion: devPreview` (not `1.17`) because
`copilotAgents` is a devPreview-only schema property. Graph API `appCatalogs/teamsApps`
(both v1.0 and beta) rejects this schema — upload ONLY via Teams Developer Portal (DevPreview mode)
or Teams client direct sideload. Custom AAD app `4bf12dfb-a136-47d8-8cba-40acc9f17b54` created
in upgradegr tenant for Graph API access — can be deleted after submission.

### Demo artifacts (outside repo)

Location: `C:\dev\solutions\private_nebius_aiserverless_challenge\demo\`

| File | Status |
|---|---|
| `submission-reasoning-agents.md` | Ready to paste |
| `submission-enterprise-agents.md` | Ready to paste |
| `discord-announcement.md` | Ready to paste |
| `youtube-description.md` | Ready to paste |
| `recording-checklist.md` | Done |
| `start-frontend.ps1` | Done |
| `ffmpeg-combine.ps1` | Done (uses full ffmpeg path — no shell restart needed) |
| `narration.mp3` | **MISSING — generate from ElevenLabs** |
| `archon-demo.mp4` | **MISSING — run ffmpeg-combine.ps1 after narration** |

### Live endpoints

| URL | Service |
|---|---|
| https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io | FastAPI backend |
| https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io | Analysis endpoint (7-agent) |

### Live demo P&L (2026-01)

| Metric | Value |
|---|---|
| Revenue | €8,500.00 (consulting sales invoice) |
| Expenses | €7,588.39 (invoices + payroll) |
| Net Profit | €911.61 |
| Employer cost (register) | €6,930.00 |
| Bank transfer (net) | €3,994.74 |
| **Payroll gap ratio** | **1.735 × (confirmed live)** |

## Alice standards that apply (adapted for GitHub)

- Session rescan protocol (above)
- ADRs in CLAUDE.md for every key design decision
- gitleaks SecretScan as first CI stage
- Evaluator-style review before merging (smoke-test gate)

## Alice standards that do NOT apply

- ADO work item format (uses GitHub Issues)
- HEDNO tenant / Azure config (different Azure subscription)
- ADO branch naming (trunk-based development)
