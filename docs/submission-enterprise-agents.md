# Submission — Enterprise Agents Track

## Project Title
Archon — Agentic Financial Intelligence for SMBs (M365 Copilot Agent)

## Problem Solved
Business owners and CFOs need accurate financial answers without opening spreadsheets or waiting for accountants. Archon brings a seven-agent financial intelligence pipeline into Microsoft Teams and M365 Copilot Chat as a declarative agent — making CFO-level analysis available to any employee via natural language.

## How It Works
The `m365-agent/` directory contains a **Microsoft 365 Copilot declarative agent** (`archon-agent.zip`, `teams-manifest.json`) that extends M365 Copilot with Archon's financial intelligence capabilities.

**Declarative agent capabilities:**
- OpenAPI plugin connecting M365 Copilot to the Archon FastAPI backend (Azure Container Apps)
- Conversation starters: *"What was our P&L for January 2026?"*, *"What is our true payroll cost including IKA contributions?"*, *"Give me an executive summary of our financial health"*
- Natural-language answers grounded in the company's own uploaded financial documents

**Under the hood (when the Teams agent calls /api/analyze):**
1. The full seven-agent analysis pipeline runs on Azure Container Apps
2. The NarratorAgent uses **Azure AI Foundry with Foundry IQ** to ground the response in cited IFRS/EFKA regulation
3. The response returns as a natural-language M365 Copilot message with payroll reconciliation figures, P&L summary, and regulatory citations

## Why This Is Enterprise-Ready
- Key Vault-managed secrets (no plain-text credentials in config)
- Application Insights + OpenTelemetry distributed traces
- Managed identity authentication throughout (no API key exposure)
- CORS-locked API (production origins only)
- 23/23 automated e2e checks passing against live Azure deployment

## Technologies
Microsoft 365 Copilot (declarative agent) · Azure Container Apps · Azure AI Foundry · Azure OpenAI GPT-4o · Azure Key Vault · Application Insights · FastAPI · React frontend

## Deployment
Sideload `m365-agent/archon-agent.zip` via Teams Admin Center → Teams apps → Upload custom app.

## GitHub
https://github.com/upgradedev/archon_azure
