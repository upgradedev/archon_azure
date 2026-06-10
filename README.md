# Archon — Automated Business P&L Intelligence (Azure)

> **Microsoft Agents League Contest @ AI Skills Fest 2026**
> Tracks: **Reasoning Agents** + **Enterprise Agents** · Microsoft IQ: **Foundry IQ**

Archon (Αρχων — Greek for "ruler/chief") is an agentic financial intelligence platform for small and medium businesses. It ingests raw business documents — Greek or English, scanned or digital — and produces a boardroom-ready P&L dashboard with regulation-cited executive summaries powered by Azure OpenAI and **Foundry IQ**.

[![Pipeline Smoke Test](https://github.com/upgradedev/archon_azure/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/upgradedev/archon_azure/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Core Insight — The 28% Problem

A bank payroll transfer confirmation shows €3,994.74 paid to employees. That's the number most businesses record. But the true employer payroll cost — gross wages plus IKA/EFKA social insurance contributions — is €6,930.00. **A difference of 73.5%.** Without Archon, that cost is systematically understated in every P&L.

Archon's **EventLinkerAgent** links the three document types that together describe a single payroll event:

| Document | Shows |
|---|---|
| Bank confirmation | Net cash actually transferred |
| Payroll register | Gross + IKA employer contributions (true cost) |
| Individual payslips | Per-employee breakdown |

Only by fusing all three can the true employer cost be accurately captured.

---

## Microsoft IQ Integration — Foundry IQ

Archon's **NarratorAgent** uses **Foundry IQ** via the **azure-ai-projects SDK** — the native Azure AI Foundry agent runtime — to ground its executive summaries in cited, authoritative sources:

```
NarratorAgent (azure-ai-projects AIProjectClient)
    │
    ├── Azure AI Foundry agent runtime
    │       ├── AzureAISearchTool → archon-search connection
    │       │       └── archon-knowledge index
    │       │               ├── IFRS / IAS standards summaries
    │       │               ├── Greek IKA/EFKA payroll regulations (Law 4387/2016)
    │       │               ├── VAT law (N.2859/2000, reverse charge Art.44)
    │       │               └── Financial reporting best practices
    │       └── GPT-4o deployment
    │
    └── Grounded, regulation-cited executive summary
```

**Why Foundry IQ matters here:** Financial AI without grounding hallucinates regulatory figures. When the NarratorAgent states "employer costs include IKA contributions at 26.67% of gross wages per Greek EFKA regulations," that claim is retrieved from the knowledge index and cited — not generated from training data alone.

The narrator uses the **azure-ai-projects** SDK (`AIProjectClient.from_connection_string` → `create_agent` → `AzureAISearchTool`) — the actual Foundry agent framework, not just Azure OpenAI with `extra_body`. A graceful fallback path (Azure OpenAI On Your Data) covers local dev and CI.

---

## Enterprise Agents Track — Microsoft 365 Copilot Integration

Archon is also submitted in the **Enterprise Agents** track. The `m365-agent/` directory contains a **Microsoft 365 Copilot declarative agent** that brings Archon into Teams and Copilot Chat:

```
Microsoft 365 Copilot Chat / Teams
        │ declarative agent (m365-agent/manifest.json)
        │ OpenAPI plugin   (m365-agent/openapi.json)
        ▼
Archon FastAPI Backend (Azure Container Apps)
  /api/analyze  →  6-agent pipeline + Foundry IQ summary
  /api/reports  →  cached financial reports
```

**Conversation starters available in Teams:**
- *"What was our P&L for January 2026?"*
- *"What is our true payroll cost including IKA contributions?"*
- *"Give me an executive summary of our financial health"*

See [`m365-agent/README.md`](m365-agent/README.md) for deployment steps.

---

## Architecture

```
Azure Static Web Apps (global CDN)
  React Frontend (Ant Design · Recharts · TypeScript)
        │ REST / JSON
Azure Container Apps (CPU)
  FastAPI Orchestration Backend
  /upload · /jobs · /analyze · /reports
        │                       │
        │ trigger job            │ call endpoint
┌───────▼──────────┐   ┌────────▼──────────────────────────────────────────────┐
│ Azure Container   │   │ Azure Container Apps (always-on)                      │
│ Apps Job          │   │ ──────────────────────────────────────────────────── │
│ (extraction)      │   │ 1. ClassifierAgent   — re-classify doc types          │
│ ──────────────    │   │ 2. PnLAgent          — employer_cost from register    │
│ 1. Extractor      │   │ 3. CashFlowAgent     — real cash from bank docs       │
│ 2. Classifier     │   │ 4. EmployeeAgent     — per-employee salary analytics  │
│ 3. EventLinker    │   │ 5. ValidatorAgent    — cross-doc consistency checks   │
│ 4. Validator      │   │ 6. ReconciliationAgent — vendor statement diffs       │
└───────┬──────────┘   │ 7. NarratorAgent     — Foundry IQ grounded summary    │
        │              └────────┬──────────────────────────────────────────────┘
        │ write                 │ read / write
┌───────▼───────────────────────▼────────────────────┐
│        Azure Blob Storage                           │
│  raw-docs/  ·  extracted/  ·  reports/              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Azure Database for PostgreSQL Flexible Server      │
│  documents · employees · payroll_events             │
│  employee_payroll · validation_results              │
└──────────────────────┬──────────────────────────────┘
              ┌────────┴────────┐
              │                 │
┌─────────────▼──────┐  ┌───────▼──────────────────────┐
│  Azure OpenAI       │  │  Azure AI Search              │
│  GPT-4o (vision)    │  │  Foundry IQ knowledge index   │
│  GPT-4o (analysis)  │  │  IFRS · IKA regs · VAT law   │
└────────────────────┘  └──────────────────────────────┘
```

---

## Agent Responsibilities

### Extraction Job (Azure Container Apps Job)

| Agent | Responsibility |
|---|---|
| **Extractor** | Auto-detect file type; call GPT-4o vision or text; produce ExtractedDocument per file |
| **ClassifierAgent** | Rule-based doc_type refinement — no LLM; distinguishes payroll_register / bank_confirmation / payslip |
| **EventLinkerAgent** | Group payroll docs by company + period; produce PayrollEvent linking all three subtypes |
| **ValidatorAgent** | Cross-document consistency (R1 bank≈payslips ±2%, R2 IKA ratio, R3 payment date, R4 employee count) |

### Analysis Endpoint (Azure Container Apps — always-on)

| Agent | Responsibility |
|---|---|
| **ClassifierAgent** | Re-classify for analysis context |
| **PnLAgent** | P&L aggregation — uses employer_cost_total (not bank net) for accurate payroll cost |
| **CashFlowAgent** | Cash flow — uses bank_confirmation transfers for real cash movements |
| **EmployeeAgent** | Per-employee salary analytics from payslips; payroll event summaries |
| **ReconciliationAgent** | Vendor statement vs uploaded invoices — surfaces missing documents |
| **ValidatorAgent** | Re-runs cross-document validation as a safety net across multi-batch uploads |
| **NarratorAgent** | **Foundry IQ** — Azure OpenAI + Azure AI Search grounded executive summary |

---

## Quickstart (Local Dev)

```bash
# Prerequisites: Docker Desktop, Python 3.12+

git clone https://github.com/upgradedev/archon_azure
cd archon_azure

cp .env.example .env
# Fill in: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
# Local dev uses Azurite (blob emulator) — no real Azure storage needed

docker compose up --build
```

Open http://localhost:3000

Generate synthetic Greek sample documents:
```bash
pip install reportlab
python scripts/generate-sample-data.py
```

Seed demo extracted documents (bypasses extraction job for demo):
```bash
pip install azure-storage-blob
python scripts/upload_demo_docs.py
```

Run end-to-end smoke test:
```bash
bash scripts/test-pipeline.sh
```

---

## Deploy to Azure

### One-command infra provisioning (Bicep)

```bash
az group create --name archon-rg --location westeurope

az deployment group create \
  --resource-group archon-rg \
  --template-file infra/main.bicep \
  --parameters postgresAdminPassword=<your-password>
```

### Build and push images

```bash
ACR=$(az acr show -n <your-acr> --query loginServer -o tsv)

# Extraction job
cd jobs/extraction
docker build -t $ACR/archon-extraction:latest .
docker push $ACR/archon-extraction:latest

# Analysis endpoint
cd ../../endpoints/analysis
docker build -t $ACR/archon-analysis:latest .
docker push $ACR/archon-analysis:latest
```

### Apply PostgreSQL schema

```bash
psql "$DATABASE_URL" -f backend/db/schema.sql
```

### Seed Foundry IQ knowledge index

Upload accounting standards documents to Azure AI Search index `archon-knowledge`:
- IFRS/IAS standards summaries (PDFs or chunked text)
- Greek IKA/EFKA contribution rate tables
- Greek VAT law (N.2859/2000) reverse charge provisions

Use the Azure AI Search portal or the REST API to upload and index these documents. The NarratorAgent queries this index automatically when `AZURE_AI_SEARCH_ENDPOINT` and `AZURE_AI_SEARCH_KEY` are set.

### Frontend (Azure Static Web Apps)

```bash
cd frontend
npm install && npm run build
az staticwebapp create --name archon-frontend --resource-group archon-rg \
  --source https://github.com/upgradedev/archon_azure --branch master \
  --app-location frontend --output-location dist
```

---

## Estimated Cost (demo scale)

| Service | Estimate |
|---|---|
| Azure Static Web Apps | Free |
| Azure Container Apps (backend) | ~$15–20/mo |
| Azure Container Apps (analysis) | ~$25–30/mo |
| Azure Container Apps Job (extraction) | ~$0.10 per run |
| Azure Blob Storage | ~$0.01/mo |
| Azure Database for PostgreSQL (Burstable B2ms) | ~$30/mo |
| Azure OpenAI (GPT-4o) | ~$0.005 per 1K tokens |
| Azure AI Search (Basic) | ~$75/mo |

---

## Cloud Portability

Archon is designed to be cloud-portable. Switch `JOB_RUNNER_BACKEND` and `AZURE_STORAGE_CONNECTION_STRING` env vars to run the same agent pipeline on Nebius, AWS, or GCP.

| Component | Azure | Nebius | AWS | GCP |
|---|---|---|---|---|
| Batch Job | Container Apps Job | AI Jobs | Batch | Cloud Run Jobs |
| Endpoint | Container Apps | AI Endpoints | ECS | Cloud Run |
| Storage | Blob Storage | Object Storage | S3 | GCS |
| Database | PostgreSQL Flexible | Managed PostgreSQL | RDS | Cloud SQL |
| LLM | Azure OpenAI | Inference API | Bedrock | Vertex AI |

The Nebius version of this project is at: [`repos/nebius/`](../nebius/)

---

## Submission Details

- **Contest:** Microsoft Agents League @ AI Skills Fest 2026
- **Track:** Reasoning Agents (Microsoft Foundry)
- **Microsoft IQ:** Foundry IQ (Azure AI Search grounding in NarratorAgent)
- **License:** MIT
- **Author:** Efthymios Fousekis
