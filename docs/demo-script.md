# Archon — Demo Video Script v4
## Microsoft Agents League @ AI Skills Fest 2026
### Tracks: Reasoning Agents + Enterprise Agents
### Target duration: 5 minutes | ~760 words at 152 wpm

---

> **TTS COPY-PASTE:** Use `docs/tts-narration.txt` — pure spoken text, no formatting.
> The narration sections below are for reference / sync only (not for ElevenLabs).

---

## SCREEN FLOW

| Timecode  | Screen                                          |
|-----------|-------------------------------------------------|
| 0:00–0:40 | **Slide 1** — Title                             |
| 0:40–1:20 | **Slide 2** — The Problem                       |
| 1:20–2:00 | **Slide 3** — The Solution (Upload → Correlate → Done) |
| 2:00–2:30 | **Slide 4** — Architecture                      |
| 2:30–2:35 | **Slide 5** — Live Demo transition (brief)      |
| 2:35–3:10 | **Browser** — Dashboard, upload modal           |
| 3:10–3:50 | **Browser** — Dashboard tiles, drill-down       |
| 3:50–4:15 | **Browser** — Executive summary, citations      |
| 4:15–4:20 | **Slide 6** — Teams transition (brief)          |
| 4:20–4:45 | **Teams** — Copilot agent conversation          |
| 4:45–5:00 | **Slide 7** — Closing                           |

---

## NARRATION SCRIPT (reference — sync with tts-narration.txt)

---

### [0:00 – 0:40] — TITLE (Slide 1)

Every month, small business owners sit down to close their books.

They have a bank statement. They have payroll documents. They have invoices, receipts, and tax filings. Each document tells a different version of the same story — with different amounts, different dates, and no obvious way to connect them.

To know their true financial position, they need to correlate all of these. Manually. Every single month.

Archon automates that correlation — using a pipeline of seven specialised AI agents that read every document, find the connections, and produce an accurate P and L in seconds.

---

### [0:40 – 1:20] — THE PROBLEM (Slide 2)

Here is the core problem.

A single payroll event — paying your employees for the month — generates at least four separate documents, each telling a partial story.

The bank statement records what arrived and left. Net amounts only. Incomplete without context.

The payroll register holds the full employer cost — gross salaries plus employer social contributions — the number that actually belongs in your P and L.

Invoices and receipts capture revenue and supplier costs. Each one a fragment of the full picture.

Individual payslips break down each employee's allocation — gross pay, deductions, tax withholding per person. They cross-check the register total.

These four documents describe the same month. But you cannot match them by amount alone. They require context. They require correlation. Most businesses record only the bank line. The result is a P and L that understates the true cost — and does not comply with the accounting standard that requires the full employer benefit expense.

---

### [1:20 – 2:00] — THE SOLUTION (Slide 3)

Archon solves this in three steps.

Upload. Drop your documents — invoices, bank statements, payroll files — in any format, any language. Archon handles the rest.

Agents correlate. Seven specialised agents read every document, classify it, link related documents across types, validate consistency, and reconcile the numbers.

Accurate P and L. The result is a complete financial report — revenue, expenses, cash flow, and an executive summary that cites the accounting standards behind every claim.

The key capability is the Event Linker — the agent that looks across document types and says: this bank transfer, this payroll register, and these payslips are all describing the same event. Fuse them. Report the true number.

That correlation, which used to take a skilled accountant hours, now takes seconds.

---

### [2:00 – 2:30] — ARCHITECTURE (Slide 4)

Archon runs entirely on Microsoft Azure.

The extraction phase uses GPT-4o vision to read scanned documents. The Event Linker groups related records. The Validator runs four cross-document consistency checks.

The analysis phase runs three more agents — P and L, Cash Flow, and Employee — each focused on one part of the financial picture.

The final agent — the Narrator — runs inside Azure AI Foundry using Foundry I-Q grounding. It connects to an Azure AI Search knowledge index containing international accounting standards and local regulatory documents.

Before writing a single sentence of the executive summary, the Narrator retrieves the relevant standard and cites it. Not generated from training data. Retrieved, verified, cited.

---

### [2:30 – 2:35] — LIVE DEMO TRANSITION (Slide 5)

*Arrow key to Slide 5 — pause 3 seconds — then Alt+Tab to browser*

---

### [2:35 – 3:10] — DEMO: UPLOAD (Browser)

Let me show you Archon in action.

I am opening the upload panel. Our demo set includes documents that a typical small business would generate in a single month: a bank statement, a payroll register, and individual payslips.

The extraction job runs on Azure Container Apps Jobs — compute spins up on demand, processes the documents, and shuts down. No idle cost.

---

### [3:10 – 3:50] — DEMO: DASHBOARD (Browser)

The dashboard is live.

Revenue is shown net of tax — the actual income, not the invoice face value.

The Expenses tile reflects the true employer cost from the payroll register — not the net bank transfer. The difference between those two numbers is the cost that most businesses miss.

The Validator passed all four consistency checks. The expense breakdown chart shows where the money actually went. Everything is cross-referenced, reconciled, and accurate.

---

### [3:50 – 4:15] — FOUNDRY IQ: CITED EXECUTIVE SUMMARY (Browser)

The executive summary is written by the Narrator agent.

Notice the Sources line at the bottom of the executive summary — every regulatory document cited there was retrieved, not invented.

That is not a language model generating plausible financial commentary. That is retrieval-augmented generation. The Narrator agent queried the Azure AI Search knowledge index, retrieved the relevant standard, grounded its analysis against it, and cited the source. Every claim in this summary is backed by a document. Foundry I-Q makes that possible.

---

### [4:15 – 4:20] — TEAMS TRANSITION (Slide 6)

*Arrow key to Slide 6 — pause 3 seconds — then Alt+Tab to Teams*

---

### [4:20 – 4:45] — TEAMS COPILOT (Microsoft Teams)

Archon also lives inside Microsoft Teams as a declarative Copilot agent.

I type: What is our true payroll cost for this period, and how does it compare to what the bank statement shows?

Archon calls the backend, retrieves the report, and answers in natural language — with the reconciled figure, the source breakdown, and a clear explanation of why the two numbers differ.

No spreadsheet. No phone call to the accountant. The answer is one message away, in the tool the team already uses every day.

This is Enterprise Agents: financial intelligence connected to Microsoft 365, available to any member of the organisation.

---

### [4:45 – 5:00] — CLOSE (Slide 7)

*Alt+Tab back to Presentation → Arrow key to Slide 7*

Seven agents. Four document types. One grounded financial truth.

Archon is open source — MIT licence — at github dot com slash upgradedev slash archon underscore azure.

Microsoft Agents League, AI Skills Fest 2026. Reasoning Agents and Enterprise Agents.

---

## RECORDING CHECKLIST

- [ ] `docs/presentation.html` open in Chrome, fullscreen (F11), Slide 1 active
- [ ] Second tab: Azure Static Web App — period 2026-01, dashboard visible
- [ ] Executive summary visible with a "Sources:" citation line at the bottom (scroll to confirm before recording)
- [ ] Teams: Archon Financial Intelligence agent open, ready to type
- [ ] Backend health confirmed: `/health` endpoint returns 200
- [ ] 1920×1080, browser zoom 100%
- [ ] OBS or Loom at 1080p 30fps

**Tab switch order:**
1. Presentation → Slides 1, 2, 3, 4 (arrow keys)
2. Arrow key → Slide 5 (Live Demo transition) — pause 3s
3. Alt+Tab → Browser (upload → dashboard → executive summary)
4. Alt+Tab → Presentation → Slide 6 (Teams transition) — pause 3s
5. Alt+Tab → Teams (type question, show response)
6. Alt+Tab → Presentation → Slide 7 (Closing)

---

## TTS GUIDE (ElevenLabs)

**Copy-paste source:** `docs/tts-narration.txt` — the entire file, start to finish.
Stop before the "PRONUNCIATION NOTES" line at the bottom.

- Style: calm, professional, measured — CFO register, not excited
- Pace: 150–158 wpm
- Emphasise: "correlate", "true cost", "cited", "grounded", "Event Linker"
- Do NOT emphasise: numbers, standard names (read flatly)
- "I-A-S" → already written with hyphens → ElevenLabs reads as three letters
- "I-Q" → already written with hyphen → reads as two letters: eye-cue
- "P and L" → already written in full
- "Microsoft 365" → already written in full
