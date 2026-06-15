# Archon — Demo Video Script v3
## Microsoft Agents League @ AI Skills Fest 2026
### Tracks: Reasoning Agents + Enterprise Agents
### Target duration: 5 minutes | ~760 words at 152 wpm

---

## SCREEN FLOW

| Timecode  | Screen                                     |
|-----------|--------------------------------------------|
| 0:00–0:40 | **Slide 1** — Title                        |
| 0:40–1:20 | **Slide 2** — The Problem                  |
| 1:20–2:00 | **Slide 3** — The Ease (Upload → Correlate → Done) |
| 2:00–2:30 | **Slide 4** — Architecture                 |
| 2:30–3:10 | **Browser** — Dashboard, upload modal      |
| 3:10–3:50 | **Browser** — Dashboard tiles, drill-down  |
| 3:50–4:15 | **Browser** — Executive summary, citations |
| 4:15–4:45 | **Teams** — Copilot agent conversation     |
| 4:45–5:00 | **Slide 5** — Closing                      |

---

## NARRATION SCRIPT

---

### [0:00 – 0:40] — TITLE

> *Screen: Slide 1. Logo fades in. Track badges appear.*

Every month, small business owners sit down to close their books.

They have a bank statement. They have payroll documents. They have invoices, receipts, and tax filings. Each document tells a different version of the same story — with different amounts, different dates, and no obvious way to connect them.

To know their true financial position, they need to correlate all of these. Manually. Every single month.

**Archon** automates that correlation — using a pipeline of specialised AI agents that read every document, find the connections, and produce an accurate P&L in seconds.

---

### [0:40 – 1:20] — THE PROBLEM (Slide 2)

> *Screen: Slide 2. Four document cards appear. Pause on the warning bar at the bottom.*

Here is the core problem.

A single payroll event — paying your employees for the month — generates at least four separate documents, each held by a different institution.

The **bank statement** shows the net amount transferred to employee accounts. That is only part of the story.

The **payroll register** is filed with the social insurance authority. It contains the full employer cost — gross salaries plus employer social contributions. A number that can be significantly higher than the bank transfer.

The **individual payslips** break down each employee's allocation — gross pay, employee social contribution, withheld income tax.

And the **tax filing** goes to the tax authority as a separate institutional payment.

These four documents describe the same event. But you cannot match them by date, by amount, or by counterparty. They require context. They require correlation.

Most small businesses record only the bank line. The result is a P&L that understates the true cost — and does not comply with the accounting standard that requires the full employer benefit expense.

---

### [1:20 – 2:00] — THE EASE (Slide 3)

> *Screen: Slide 3. Three-step flow. Then three result cards.*

Archon solves this in three steps.

**Upload.** Drop your documents — invoices, bank statements, payroll files — in any format, any language. Archon handles the rest.

**Agents correlate.** A pipeline of seven specialised agents reads every document, classifies it, links related documents across types, validates consistency, and reconciles the numbers.

**Accurate P&L.** The result is a complete financial report — revenue, expenses, cash flow, and an executive summary that cites the accounting standards behind every claim.

The key capability is the **Event Linker** — the agent that looks across document types and says: this bank transfer, this payroll register, and these four payslips are all describing the same event. Fuse them. Report the true number.

That correlation, which used to take a skilled accountant hours, now takes seconds.

---

### [2:00 – 2:30] — ARCHITECTURE (Slide 4)

> *Screen: Slide 4. Three-phase grid. Pause on Foundry IQ callout.*

Archon runs entirely on Microsoft Azure.

The extraction phase uses GPT-4o vision to read scanned documents. The Event Linker groups related records. The Validator runs four cross-document consistency checks.

The analysis phase runs three more agents — P&L, Cash Flow, and Employee — each focused on one part of the financial picture.

The final agent — the Narrator — runs inside **Azure AI Foundry** using Foundry IQ grounding. It connects to an Azure AI Search knowledge index containing international accounting standards and local regulatory documents.

Before writing a single sentence of the executive summary, the Narrator retrieves the relevant standard and cites it. Not generated from training data. Retrieved, verified, cited.

---

### [2:30 – 3:10] — DEMO: UPLOAD

> *Screen: Browser. Dashboard loaded. Open upload modal.*

Let me show you Archon in action.

I am opening the upload panel. Our demo set includes documents that a typical small business would generate in a single month: a bank transfer confirmation, a payroll register, and individual payslips.

The extraction job runs on Azure Container Apps Jobs — compute spins up on demand, processes the documents, and shuts down. No idle cost.

---

### [3:10 – 3:50] — DEMO: DASHBOARD

> *Screen: Dashboard. Pan across the P&L tiles. Click Expenses to drill into the breakdown.*

The dashboard is live.

Revenue is shown net of tax — the actual income, not the invoice face value.

The Expenses tile reflects the true employer cost from the payroll register — not the net bank transfer. The difference between those two numbers is the cost that most businesses miss.

The Validator passed all four consistency checks. The expense breakdown chart shows where the money actually went. Everything is cross-referenced, reconciled, and accurate.

---

### [3:50 – 4:15] — FOUNDRY IQ: CITED EXECUTIVE SUMMARY

> *Screen: Scroll to Executive Summary. Pause on the "Sources:" line.*

The executive summary is written by the Narrator agent.

Notice the last line: **Sources: IAS 1 · IAS 19.**

That is not a language model generating plausible financial commentary. That is retrieval-augmented generation. The Narrator agent retrieved the relevant accounting standard from the knowledge index, grounded its analysis against it, and cited the source.

Every claim in this summary is backed by a document. Foundry IQ makes that possible.

This is Reasoning Agents in production — seven specialised agents, each responsible for one part of the truth, Foundry IQ synthesising the final answer with citations.

---

### [4:15 – 4:45] — TEAMS COPILOT

> *Screen: Microsoft Teams. Archon Financial Intelligence agent open.*

Archon also lives inside Microsoft Teams as a declarative Copilot agent.

I type: *"What is our true payroll cost for January, and how does it compare to what the bank statement shows?"*

Archon calls the backend, retrieves the report, and answers in natural language — with the reconciled figure, the source breakdown, and a clear explanation of why the two numbers differ.

No spreadsheet. No phone call to the accountant. The answer is one message away, in the tool the team already uses every day.

This is Enterprise Agents: financial intelligence connected to Microsoft 365, available to any member of the organisation.

---

### [4:45 – 5:00] — CLOSE (Slide 5)

> *Screen: Slide 5.*

Seven agents. Four document types. One grounded financial truth.

Archon is open source — MIT licence — at github dot com slash upgradedev slash archon underscore azure.

Microsoft Agents League, AI Skills Fest 2026. Reasoning Agents and Enterprise Agents.

---

## RECORDING CHECKLIST

- [ ] `docs/presentation.html` open in Chrome, fullscreen (F11), Slide 1 active
- [ ] Second tab: `https://gentle-sky-08574a603.7.azurestaticapps.net` — period 2026-01, dashboard visible
- [ ] Executive summary visible with "Sources:" citation (scroll to confirm before recording)
- [ ] Teams: Archon Financial Intelligence agent open, ready to type
- [ ] Backend health confirmed: `/health` endpoint returns 200
- [ ] 1920×1080, browser zoom 100%
- [ ] OBS or Loom at 1080p 30fps

**Tab switch order:**
1. Presentation → Slides 1, 2, 3, 4 (arrow keys)
2. Alt+Tab → Browser (upload → dashboard → summary)
3. Alt+Tab → Teams (type question, show response)
4. Alt+Tab → Presentation → Slide 5

---

## TTS GUIDE (ElevenLabs)

- Style: calm, professional, measured — CFO register, not excited
- Pace: 150–158 wpm. Pause 0.6 s at `---` section breaks
- Emphasise: "correlate", "true cost", "cited", "grounded", "Event Linker"
- Do NOT emphasise: numbers, standard names (read flatly)
- "IAS" → spell out: I-A-S
- "P&L" → say "P and L"
- "M365" → say "Microsoft 365"
