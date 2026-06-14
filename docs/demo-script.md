# Archon — Demo Video Script
## Microsoft Agents League @ AI Skills Fest 2026
### Tracks: Reasoning Agents + Enterprise Agents
### Target duration: 5 minutes | ~750 words at 150 wpm

---

## SLIDES / SCREEN CUE GUIDE

| Timecode | Screen | Narration cue |
|---|---|---|
| 0:00–0:25 | Title card: Archon logo + tagline | Hook |
| 0:25–1:00 | Diagram: bank slip → gap → true cost | Problem |
| 1:00–1:45 | Azure architecture diagram | Solution overview |
| 1:45–2:30 | Browser: upload screen + file drag | Demo — upload |
| 2:30–3:15 | Browser: dashboard loading, P&L chart | Demo — analysis |
| 3:15–4:00 | Browser: executive summary with citations | Foundry IQ |
| 4:00–4:40 | Teams: Archon chat bubble + response | Enterprise agent |
| 4:40–5:00 | Title card: repo link + track badges | Close |

---

## NARRATION SCRIPT

### [0:00 – 0:25] — HOOK

> *Screen: Title card. "Archon — Agentic Financial Intelligence for SMBs."*

Every month, small business owners try to reconstruct their real payroll cost from a pile of documents.

The problem is: no single document tells the whole story.

The bank confirmation shows only the net salary transfer to employees. The payroll register adds the employer social-security contribution to EFKA. The individual payslips break down each employee's allocation. And the tax authority receives income-tax withholdings in a completely separate transfer.

To know your true payroll cost, you need to correlate all four streams. That is exactly what Archon does — automatically.

---

### [0:25 – 1:00] — THE PROBLEM

> *Screen: Diagram showing four document streams feeding into a single reconciled payroll figure.*

Here is a real example from our synthetic demo dataset for January 2026.

The bank confirmation shows a net employee transfer of three thousand nine hundred ninety-four euros. That is what most SMBs record as their payroll cost.

But the payroll register reveals the employer EFKA contribution — a separate institutional payment. The individual payslips confirm each employee's allocation. And the tax authority receives withheld income tax as yet another separate stream.

These are not the same transaction. They cannot be matched by date, by amount, or by counterparty — they require multi-document correlation by company, by period, and by regulatory logic.

Archon's Event Linker agent performs that correlation automatically. The result: a single, accurate financial event that reflects the true employer cost.

---

### [1:00 – 1:45] — THE SOLUTION: ARCHON ON AZURE

> *Screen: Architecture diagram. Highlight each component as named.*

Archon is a multi-agent AI platform built entirely on Microsoft Azure.

Documents are uploaded through a React frontend and stored in Azure Blob Storage.

An extraction job running on Azure Container Apps uses GPT-4o vision to read scanned PDFs — invoices, payroll registers, bank confirmations, individual payslips — in Greek or English.

A six-agent analysis pipeline then runs: Classifier, P&L Agent, Cash Flow Agent, Employee Agent, Validator, and finally the Narrator — which uses **Azure AI Foundry with Foundry IQ grounding** against an Azure AI Search knowledge index.

The knowledge index contains Greek accounting law, IKA-EFKA contribution tables, IFRS standards IAS 1 and IAS 19, and VAT law N.2859 slash 2000.

Every executive summary is grounded. Every regulatory claim is cited.

---

### [1:45 – 2:30] — DEMO: DOCUMENT UPLOAD

> *Screen: Browser at the Archon dashboard. Drag three PDF files onto the upload zone.*

Let me show you Archon in action.

I am uploading three document types that represent a single payroll event for January 2026: a bank transfer confirmation, a payroll register, and four individual payslips.

Archon's Event Linker agent recognises that these three documents are the same event — same company, same period — and fuses them into one accurate financial record.

The extraction job runs on Azure Container Apps Jobs, spinning up GPU compute on demand and shutting down when complete. No idle cost.

---

### [2:30 – 3:15] — DEMO: ANALYSIS DASHBOARD

> *Screen: Dashboard renders. P&L chart, expense breakdown, validation badges appear.*

The dashboard is now live.

The P&L agent correctly reports payroll expense as six thousand nine hundred thirty euros — the full employer cost — not the bank transfer amount.

The Validator agent ran four cross-document consistency rules: bank total versus sum of payslips within two percent; EFKA ratio check; payment date validation; employee count match. All four passed.

The expense breakdown chart shows payroll as the primary cost category, correctly weighted at the employer cost level, not the net salary level.

This distinction matters for IAS 19 compliance — which requires the full employer benefit cost, including social contributions, in the P&L.

---

### [3:15 – 4:00] — FOUNDRY IQ: CITED EXECUTIVE SUMMARY

> *Screen: Scroll to the Executive Summary section. Highlight citation footnotes.*

Now the most important part.

The Narrator agent uses the **Azure AI Foundry agent runtime** with the **AzureAISearchTool** connected to our knowledge index.

Watch the executive summary. It does not just say "payroll was high." It explains: *"Accurate payroll cost for this period required correlating three document streams — the bank confirmation, the payroll register, and individual payslips — since each captures a distinct payment flow. Per IAS 19 paragraph 10, the employee benefit expense must include employer EFKA contributions under Law 4387 slash 2016, which arrive at the insurance institution as a separate transfer and are not visible in the bank confirmation alone."*

That sentence is grounded. It came from our AI Search index. Foundry IQ retrieved the relevant regulation, fused it with the multi-stream reconciliation performed by the analysis pipeline, and produced a cited, hallucination-resistant summary.

This is Reasoning Agents in production: seven specialised agents collaborating, each responsible for one part of the truth, Foundry IQ synthesising the final answer with regulatory citations.

---

### [4:00 – 4:40] — ENTERPRISE AGENT: TEAMS COPILOT

> *Screen: Switch to Microsoft Teams. Open the Archon Financial Intelligence chat.*

Archon also lives inside Microsoft Teams as a **declarative Copilot agent**.

A business owner types: *"What is our true payroll cost for January, including IKA contributions?"*

Watch Archon's response. It calls the Archon backend API, retrieves the analysed report, and answers — in natural language — with the true employer cost derived from all four payment streams, the regulatory basis under Law 4387/2016, and a clear explanation of why the bank statement alone would have given the wrong figure.

No spreadsheet. No accountant on the phone. The CFO-level answer is one message away, from inside the tool the team already uses every day.

This is Enterprise Agents: a declarative agent that connects Microsoft 365 to a live business data pipeline, grounded in law, and available to any employee in the organisation.

---

### [4:40 – 5:00] — CLOSE

> *Screen: Title card. GitHub repo URL. Two track badges: "Reasoning Agents" and "Enterprise Agents".*

Archon is open source under the MIT licence.

The full codebase — backend, six-agent pipeline, Foundry IQ narrator, M365 declarative agent, and Azure Bicep infrastructure — is available at github dot com slash upgradedev slash archon underscore azure.

Built for the Microsoft Agents League at AI Skills Fest 2026.

Submitted to two tracks: **Reasoning Agents** and **Enterprise Agents**.

Thank you.

---

## RECORDING CHECKLIST

Before hitting record, verify:

- [ ] Browser tab open at `https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io` — health check green
- [ ] Dashboard pre-loaded at period `2026-01` so charts render instantly
- [ ] Executive summary visible with citations (scroll down to confirm)
- [ ] Teams open with Archon Financial Intelligence sideloaded
- [ ] Test the Teams prompt "What is our true payroll cost for January?" — confirm it returns the correct figure
- [ ] Screen resolution 1920×1080, browser zoom at 100%
- [ ] Microphone / TTS input ready
- [ ] OBS or Loom recording confirmed at 1080p

## TTS INSTRUCTIONS (for ElevenLabs / HeyGen)

- Voice style: **calm, professional, slightly slow** — CFO presentation register
- Pace: 145–155 words per minute
- Pause 0.5 s after each section heading (the `---` breaks)
- Emphasise (slight stress): "four streams", "correlate", "separate transfer", "grounded", "cited"
- Do NOT emphasise law numbers — read them flatly as ordinal strings
- Pronunciation: "EFKA" → spell out E-F-K-A; "IAS" → spell out I-A-S; "IKA" → I-K-A
