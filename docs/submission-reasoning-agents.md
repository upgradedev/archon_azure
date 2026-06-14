# Submission — Reasoning Agents Track

## Project Title
Archon — Agentic Financial Intelligence for SMBs

## Problem Solved
Small and medium businesses process payroll through four separate, non-overlapping document streams: bank confirmations (employee net pay), payroll registers (employer social-insurance contributions), individual payslips (per-employee allocation), and tax-authority withholdings. No single document shows the full employer cost. Reading only the bank statement systematically understates payroll expense and overstates profit — because EFKA social-insurance contributions and tax-authority remittances are separate institutional transfers invisible in the bank feed.

Archon solves this automatically using a seven-agent reasoning pipeline built on Microsoft Azure AI Foundry.

## How It Works
**Extraction pipeline (Azure Container Apps Job — 4 agents):**
1. **Extractor** — GPT-4o Vision reads Greek and English PDFs, invoices, payroll registers, and bank confirmations
2. **ClassifierAgent** — rule-based doc_type assignment (no LLM; deterministic)
3. **EventLinkerAgent** — correlates the four document streams by company + period into a single accurate payroll event
4. **ValidatorAgent** — runs four cross-document consistency rules (bank ≈ payslips ±2%, EFKA ratio, payment date, employee count)

**Analysis pipeline (Azure Container Apps — always-on, 7 agents):**
5–10. Classifier, PnLAgent (employer_cost from register, not bank net), CashFlowAgent, EmployeeAgent, ReconciliationAgent, ValidatorAgent
11. **NarratorAgent** — runs as a live **Azure AI Foundry ephemeral agent** via the azure-ai-projects SDK (b10), grounded via **AzureAISearchTool** against the `archon-knowledge` Azure AI Search index containing IFRS/IAS standards, Greek EFKA payroll regulations (Law 4387/2016), and VAT law (N.2859/2000). Produces a cited, hallucination-resistant CFO-level executive summary.

## Technologies
Azure AI Foundry (azure-ai-projects SDK) · Azure OpenAI GPT-4o · Azure AI Search (Foundry IQ) · Azure Container Apps · Azure Blob Storage · Azure Database for PostgreSQL · Azure Key Vault · Application Insights · React + Ant Design frontend

## Microsoft IQ
**Foundry IQ** — NarratorAgent uses the native Foundry agent runtime with AzureAISearchTool for knowledge-grounded, regulation-cited financial summaries. This is a "Best Use of IQ Tools" candidate.

## Live Demo
Backend: https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health
Analysis: https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health

## GitHub
https://github.com/upgradedev/archon_azure
