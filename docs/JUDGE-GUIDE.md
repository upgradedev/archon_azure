# Archon — Judge Evidence Guide

**Microsoft Agents League @ AI Skills Fest 2026**
Tracks: **Reasoning Agents** · **Enterprise Agents**

---

## Quick Links

| Resource | URL |
|---|---|
| CI workflow | https://github.com/upgradedev/archon_azure/actions/workflows/smoke-test.yml |

> The hosted Azure environment (dashboard, backend, MCP and analysis endpoints) was
> decommissioned in July 2026 after the contest concluded. Every flow in this guide
> can be reproduced on the local `docker compose` stack described in the README, so
> the command examples below use the local endpoints (backend `localhost:8000`,
> analysis `localhost:8001`, dashboard `localhost:3000`).

---

## Track Coverage Map

### Reasoning Agents Track

| Criterion | How Archon satisfies it | Evidence |
|---|---|---|
| Staged system with clear role separation | 4 extraction stages and 7 analysis stages. Most are deterministic Python functions rather than autonomous agents. | [`jobs/extraction/agents/`](../jobs/extraction/agents/) · [`endpoints/analysis/agents/`](../endpoints/analysis/agents/) |
| Microsoft Foundry agent framework | Optional NarratorAgent uses the Threads/Messages/Runs implementation of Microsoft Foundry Agent Service (classic) via `azure-ai-projects==1.0.0b10` | [`endpoints/analysis/agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| Multi-step processing | Extraction-time EventLinker groups bank confirmation + payroll register + payslips; four deterministic checks run over those groups. Analysis later reclassifies and validates documents independently. | [`agents/event_linker.py`](../jobs/extraction/agents/event_linker.py) · [`agents/validator.py`](../jobs/extraction/agents/validator.py) |
| Optional Search grounding | `AzureAISearchTool` can query `archon-knowledge` on the configured classic Agent Service path. The fallback is not necessarily grounded. | [`agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| External tools / MCP | `/mcp` endpoint — 3 tools: `list_periods`, `get_financial_report`, `analyze_period` | See MCP evidence below |
| Code quality & tests | Two deterministic Python unit-test suites — 36 extraction tests and 8 analysis tests — run as separately named pytest steps in the CI workflow on every push. Seven authenticated live-dashboard Playwright scenarios are authored but are separate from the smoke workflow. | [`jobs/extraction/tests/`](../jobs/extraction/tests/) · [`frontend/e2e/`](../frontend/e2e/) |

### Enterprise Agents Track

| Criterion | How Archon satisfies it | Evidence |
|---|---|---|
| M365 Copilot declarative agent (required) | Sideloadable zip with `manifest.json`, OpenAPI plugin, Adaptive Card responses | [`m365-agent/`](../m365-agent/) |
| Microsoft IQ integration (required) | The configured classic Agent Service path can attach Azure AI Search before generating the optional summary | [`agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| Business scenario | Seeded synthetic records illustrate the difference between a €3,994.74 bank transfer and a €6,930.00 employer-cost field. This is a demonstration, not evidence of live extraction accuracy or customer impact. | Demo seed → period `2026-01` |

---

## Seven-stage analysis pipeline (step by step)

```
POST /analyze {"period": "2026-01"}
    │
    ▼
1. ClassifierAgent      — re-classifies doc_type for analysis context (rule-based, no LLM)
    │
    ▼
2. PnLAgent             — builds a P&L-style view; seeded payroll registers can supply employer_cost_total
    │
    ▼
3. CashFlowAgent        — cash-flow proxy: all bank confirmations are outflows; sales are assumed collected; invoices/expenses are assumed paid
    │
    ▼
4. EmployeeAgent        — per-employee salary analytics from payslips + payroll register
    │
    ▼
5. ValidatorAgent       — period-level re-run of 4 consistency checks over documents:
                          R1 bank ≈ sum(payslips) ±2%
                          R2 employer_cost / net_pay in [1.25, 1.45] (IKA/EFKA range)
                          R3 payment dates align
                          R4 employee_count in register = payslip count
    │
    ▼
6. ReconciliationAgent  — vendor statement vs uploaded invoices diff (missing doc detection)
    │
    ▼
7. NarratorAgent        — optional downstream summary. It attempts Microsoft Foundry Agent Service (classic) when a project connection is configured; otherwise it uses Azure OpenAI
```

---

## MCP Evidence

```
GET http://localhost:8000/mcp

{
  "name": "archon-mcp",
  "protocolVersion": "2024-11-05",
  "transport": "streamable-http",
  "tools": ["list_periods", "get_financial_report", "analyze_period"]
}
```

| Tool | What it does |
|---|---|
| `list_periods` | Lists all periods with extracted documents in Blob Storage |
| `get_financial_report` | Returns the full cached FinancialReport for a period |
| `analyze_period` | Triggers the staged analysis pipeline and returns the live report |

---

## Optional narration and grounding evidence

When `AZURE_AI_PROJECT_CONNECTION_STRING` is set, NarratorAgent creates an ephemeral classic Agent Service agent and attaches `AzureAISearchTool`. It then creates a Thread, Message and Run and reads the resulting Messages. This code path can return citation annotations from retrieved content.

When that connection string is absent, the service uses Azure OpenAI Chat Completions. Search grounding on the fallback path requires separate Search endpoint and key settings. CI does not prove the credentialed Agent Service, Search or live extraction paths, so grounded or cited output must be verified separately in the target Azure environment.

To verify on the local stack:
```bash
curl -s http://localhost:8001/reports/2026-01 \
  | python -m json.tool | grep -A5 "executiveSummary"
```

---

## Seeded Demo Walkthrough (3 minutes)

The hosted demo was decommissioned in July 2026; the same walkthrough runs on the
local stack (`docker compose up`, then seed as below).

1. Open http://localhost:3000
2. Period `2026-01` auto-selects (or choose from dropdown)
3. **Metric tiles** render values computed from pre-structured synthetic records
4. **P&L chart** shows the seeded payroll register's employer-cost field separately from the seeded bank transfer
5. **Validation badges** display the period-level R1–R4 results; skipped checks are currently encoded as informational passes
6. **Executive Summary** may show a generated narrative; citations depend on the configured narration path
7. **Upload Documents**: click to open the drawer — drag PDFs, select period, click Extract & Analyze

Seed fresh demo data if needed:
```bash
curl -X POST http://localhost:8001/seed-demo
```

---

## Test Coverage

| Suite | Tests | What is tested |
|---|---:|---|
| `test_classifier.py` (extraction) | 14 | Greek/English keyword inference, accent/final-sigma normalization and DocType reclassification rules |
| `test_event_linker.py` (extraction) | 9 | 3-document extraction-time linking, multi-company grouping, synthetic payroll gap invariant |
| `test_validator.py` (extraction) | 13 | Extraction-time R1–R4 pass/fail/skip behavior and Pydantic optional fields |
| `test_cashflow_agent.py` (analysis) | 8 | Current cash-flow proxy assumptions |
| **Python suites** | **36 extraction + 8 analysis** | Deterministic; no live extraction, no network, no Azure credentials |
| `dashboard.spec.ts` | 7 scenarios | Authenticated checks against the configured live dashboard; not run in the smoke workflow; not live-extraction evidence |

Current pass/fail status for both Python suites is published by the [CI workflow](https://github.com/upgradedev/archon_azure/actions/workflows/smoke-test.yml) on every push to `master`.

Run locally:
```bash
# Python unit tests from repository root (no network, no LLM).
# Run the suites as two separate pytest processes — each suite carries its own
# top-level `models`/`agents` packages, which collide in a single process.
PYTHONDONTWRITEBYTECODE=1 python -m pytest jobs/extraction/tests -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python -m pytest endpoints/analysis/tests -q -p no:cacheprovider

# Playwright UI checks (require configured live frontend and saved auth state)
cd frontend && npx playwright test
```

### CI evidence boundary

The smoke workflow has two distinct checks:

1. The workflow runs the extraction suite (36 tests) and the analysis suite (8 tests) as two separately named pytest steps.
2. The container smoke path seeds pre-extracted synthetic JSON, sets `CI_SKIP_EXTRACTION=1`, and exercises analysis over that seed.

The smoke path does not validate credentialed model extraction, Microsoft Foundry Agent Service, Azure AI Search, Microsoft 365 tenant integration, or the seven Playwright scenarios.

---

## Azure infrastructure and deployment boundary

| Service | Resource | Purpose |
|---|---|---|
| Azure Container Apps | `archon-backend` | FastAPI orchestration + MCP server |
| Azure Container Apps | `archon-analysis` | Seven-stage analysis pipeline; six stages are deterministic functions and narration is optional |
| Azure Container Apps Jobs | `archon-extraction` | Model-assisted extraction plus deterministic classification, linking and validation (on demand) |
| Azure Blob Storage | `archon` container | Raw docs · extracted JSON · cached reports |
| Azure Database for PostgreSQL | `archon-pg` | Provisioned schema target; not queried by the inspected runtime path |
| Azure OpenAI | GPT-4o (vision + optional narration fallback) | Document extraction and optional narration when no Foundry project connection is configured |
| Microsoft Foundry | Existing hub/project referenced by Bicep | Optional classic Agent Service narration path |
| Azure AI Search | Search service provisioned by Bicep; index/connection require separate setup | Optional narration grounding |
| Azure Key Vault | `archon-kv` | Secrets (no hardcoded credentials) |
| Application Insights | `archon-ai` | OpenTelemetry traces |
| Azure Static Web Apps | `archon-frontend` | React dashboard (CDN-hosted) |

[`infra/main.bicep`](../infra/main.bicep) provisions the core storage, compute, Search service, OpenAI, PostgreSQL, Key Vault and monitoring resources. It references the Microsoft Foundry hub/project and Search connection as existing resources. The analysis identity's required project-scope Contributor assignment is documented in Bicep as manual because the deployment principal lacks `roleAssignments/write`. GitHub Actions therefore does not prove a fully self-contained Bicep deployment.
