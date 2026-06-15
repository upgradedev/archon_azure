# Archon — Judge Evidence Guide

**Microsoft Agents League @ AI Skills Fest 2026**
Tracks: **Reasoning Agents** · **Enterprise Agents**

---

## Quick Links

| Resource | URL |
|---|---|
| Live Dashboard | https://gentle-sky-08574a603.7.azurestaticapps.net |
| Demo Video (5 min) | https://youtu.be/NanSqsQMTBg |
| Backend Health | https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health |
| MCP Endpoint | https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/mcp |
| Analysis Health | https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health |
| CI (passing) | https://github.com/upgradedev/archon_azure/actions |

---

## Track Coverage Map

### Reasoning Agents Track

| Criterion | How Archon satisfies it | Evidence |
|---|---|---|
| Multi-agent system with clear role separation | 11 single-responsibility agents across two pipelines (4 extraction + 7 analysis) | [`jobs/extraction/agents/`](../jobs/extraction/agents/) · [`endpoints/analysis/agents/`](../endpoints/analysis/agents/) |
| Azure AI Foundry agent framework | NarratorAgent creates ephemeral Foundry agent per request via `azure-ai-projects` SDK (b10) | [`endpoints/analysis/agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| Multi-step reasoning | EventLinkerAgent fuses bank confirmation + payroll register + payslips; 4 cross-document validation rules (R1–R4); NarratorAgent synthesises cited summary | [`agents/event_linker.py`](../jobs/extraction/agents/event_linker.py) · [`agents/validator.py`](../jobs/extraction/agents/validator.py) |
| Microsoft IQ — Foundry IQ | AzureAISearchTool on `archon-knowledge` index (10 regulatory docs: IFRS IAS 1/19, Law 4387/2016, Greek VAT N.2859/2000, IKA/EFKA tables) | [`agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| External tools / MCP | `/mcp` endpoint — 3 tools: `list_periods`, `get_financial_report`, `analyze_period` | See MCP evidence below |
| Code quality & tests | 43 pytest unit tests (no mocks, no network) + 7 Playwright E2E | [`jobs/extraction/tests/`](../jobs/extraction/tests/) · [`frontend/e2e/`](../frontend/e2e/) |

### Enterprise Agents Track

| Criterion | How Archon satisfies it | Evidence |
|---|---|---|
| M365 Copilot declarative agent (required) | Sideloadable zip with `manifest.json`, OpenAPI plugin, Adaptive Card responses | [`m365-agent/`](../m365-agent/) |
| Microsoft IQ integration (required) | Foundry IQ — NarratorAgent retrieves regulation passages and cites them inline in the executive summary | [`agents/narrator.py`](../endpoints/analysis/agents/narrator.py) |
| Real business value | The 1.735× payroll cost gap (bank net €3,994.74 vs employer cost €6,930.00) is detected automatically — a financially material error SMBs make every month | Live demo → period `2026-01` |

---

## 7-Agent Analysis Pipeline (Step-by-Step)

```
POST /analyze {"period": "2026-01"}
    │
    ▼
1. ClassifierAgent      — re-classifies doc_type for analysis context (rule-based, no LLM)
    │
    ▼
2. PnLAgent             — builds P&L using employer_cost_total (not bank net); Revenue €8,500 · Expenses €7,588
    │
    ▼
3. CashFlowAgent        — cash flow from bank_confirmation transfers only (real cash, not accrual)
    │
    ▼
4. EmployeeAgent        — per-employee salary analytics from payslips + payroll register
    │
    ▼
5. ValidatorAgent       — 4 cross-document consistency rules:
                          R1 bank ≈ sum(payslips) ±2%
                          R2 employer_cost / net_pay in [1.25, 1.45] (IKA/EFKA range)
                          R3 payment dates align
                          R4 employee_count in register = payslip count
    │
    ▼
6. ReconciliationAgent  — vendor statement vs uploaded invoices diff (missing doc detection)
    │
    ▼
7. NarratorAgent        — Foundry ephemeral agent + AzureAISearchTool → cited executive summary
```

---

## MCP Evidence

```
GET https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/mcp

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
| `analyze_period` | Triggers the 7-agent pipeline and returns the live report |

---

## Foundry IQ — Citation Evidence

The NarratorAgent calls `AzureAISearchTool` on the `archon-knowledge` index before writing the executive summary. The index contains 10 regulatory documents. A live citation from the executive summary for period `2026-01`:

> *"Per IAS 19 paragraph 10, the employee benefit expense must include employer EFKA contributions under Law 4387/2016, which arrive at the insurance institution as a separate transfer and are not visible in the bank confirmation alone."*

Every claim in the executive summary links to a retrieved source passage. The `Sources:` line appears inline at the end of the summary body.

To verify live:
```bash
curl -s https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io/reports/2026-01 \
  | python -m json.tool | grep -A5 "executiveSummary"
```

---

## Live Demo Walkthrough (3 minutes)

1. Open https://gentle-sky-08574a603.7.azurestaticapps.net
2. Period `2026-01` auto-selects (or choose from dropdown)
3. **Metric tiles** render: Revenue €8,500 · Expenses €7,588 · Net Profit €912
4. **P&L chart** shows payroll as the dominant expense category at €6,930 (employer cost — not the €3,994 bank transfer)
5. **Validation badges**: 4 green checks — R1 bank≈payslips, R2 IKA ratio, R3 dates, R4 employee count
6. **Executive Summary**: scroll down — citations appear as `Sources: IAS 19 · Law 4387/2016`
7. **Upload Documents**: click to open the drawer — drag PDFs, select period, click Extract & Analyze

Seed fresh demo data if needed:
```bash
curl -X POST https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io/seed-demo
```

---

## Test Coverage

| Suite | Count | What is tested |
|---|---|---|
| `test_classifier.py` | 13 | Accent-normalised Greek keyword inference, DocType reclassification rules |
| `test_event_linker.py` | 9 | 3-document payroll fusion, multi-company grouping, payroll gap invariant (1.734×) |
| `test_validator.py` | 13 | R1–R4 rules (pass/fail/skip), ADR-006 Pydantic optional fields |
| `test_cashflow_agent.py` | 8 | Core invariant: cash = bank transfer, not employer cost |
| `dashboard.spec.ts` | 7 | Playwright E2E: metric tiles, Foundry IQ tag, period selector, upload drawer |
| **Total** | **50** | |

Run locally:
```bash
# Python unit tests (no network, no LLM)
cd jobs/extraction && pytest tests/ -v
cd endpoints/analysis && pytest tests/ -v

# Playwright E2E (requires live frontend)
cd frontend && npx playwright test
```

---

## Azure Infrastructure (Deployed)

| Service | Resource | Purpose |
|---|---|---|
| Azure Container Apps | `archon-backend` | FastAPI orchestration + MCP server |
| Azure Container Apps | `archon-analysis` | 7-agent analysis pipeline |
| Azure Container Apps Jobs | `archon-extraction` | 4-agent extraction pipeline (on-demand) |
| Azure Blob Storage | `archon` container | Raw docs · extracted JSON · cached reports |
| Azure Database for PostgreSQL | `archon-pg` | Document metadata · employee records |
| Azure OpenAI | GPT-4o (vision + analysis) | Document extraction + analysis |
| Azure AI Foundry | `archon-foundry` | Ephemeral agents + Foundry IQ |
| Azure AI Search | `archon-knowledge` | 10-doc regulatory knowledge index |
| Azure Key Vault | `archon-kv` | Secrets (no hardcoded credentials) |
| Application Insights | `archon-ai` | OpenTelemetry traces |
| Azure Static Web Apps | `archon-frontend` | React dashboard (CDN-hosted) |

All infrastructure deployed via Bicep IaC ([`infra/main.bicep`](../infra/main.bicep)) and GitHub Actions ([`.github/workflows/smoke-test.yml`](../.github/workflows/smoke-test.yml)).
