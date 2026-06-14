# Agents League Discord — Announcement Template

Post in the #project-showcase or #submissions channel at https://aka.ms/agentsleague/discord

---

**Copy-paste message:**

---

🤖 **Archon — Agentic Financial Intelligence for SMBs**

Submitted to **Reasoning Agents** + **Enterprise Agents** tracks.

**The problem:** A payroll period generates four separate payment streams — employee net pay (bank), employer EFKA contributions (insurance institution), income-tax withholdings (tax authority), and individual payslips. No single document shows the full picture. Reading only the bank statement systematically understates payroll expense.

**What Archon does:** A 7-agent Azure pipeline that correlates all four streams automatically — and produces a CFO-level executive summary grounded in cited IFRS/Greek law via **Foundry IQ** (AzureAISearchTool on an Azure AI Search knowledge index).

**Stack:** Azure AI Foundry · GPT-4o · Azure AI Search · Azure Container Apps · M365 Copilot declarative agent · Key Vault · Application Insights

🔗 GitHub: https://github.com/upgradedev/archon_azure
📊 Live demo: https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health
🎬 Demo video: [YouTube link — add after upload]

Would love feedback! Happy to answer questions about the Foundry IQ integration or the multi-document correlation approach.

---

**Optional follow-up if anyone asks about Foundry IQ:**

The NarratorAgent creates an ephemeral Azure AI Foundry agent per `/analyze` request using `azure-ai-projects` SDK b10 — `AIProjectClient.from_connection_string` → `create_agent` with `AzureAISearchTool` → `create_and_process_run`. The knowledge index (`archon-knowledge`) holds IFRS/IAS 1/IAS 19, Greek EFKA contribution tables, and VAT law, so the agent cites the exact regulation it retrieves rather than hallucinating figures.
