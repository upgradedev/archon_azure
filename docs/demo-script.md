# Archon — Demo Video Script v2
## Microsoft Agents League @ AI Skills Fest 2026
### Tracks: Reasoning Agents + Enterprise Agents
### Target duration: 5 minutes | ~780 words at 155 wpm

---

## SCREEN FLOW

| Timecode  | Screen                                      | Slide / URL |
|-----------|---------------------------------------------|-------------|
| 0:00–0:40 | **Slide 1** — Title card                   | `docs/presentation.html` → Slide 1 |
| 0:40–1:30 | **Slide 2** — The Problem (4 doc streams)  | Slide 2 |
| 1:30–2:15 | **Slide 3** — The EFKA gap deep-dive       | Slide 3 |
| 2:15–2:45 | **Slide 4** — Architecture                 | Slide 4 |
| 2:45–3:15 | **Browser** — Dashboard + upload modal     | `https://gentle-sky-08574a603.7.azurestaticapps.net` |
| 3:15–3:50 | **Browser** — Dashboard tiles + breakdown  | same tab |
| 3:50–4:15 | **Browser** — Executive summary, citations | scroll to summary section |
| 4:15–4:45 | **Teams** — Archon Copilot agent chat      | Teams client |
| 4:45–5:00 | **Slide 5** — Closing card                 | `docs/presentation.html` → Slide 5 |

---

## NARRATION SCRIPT

---

### [0:00 – 0:40] — TITLE / SCENE SETTING

> *Screen: Slide 1. Logo animates in. Track badges visible.*

Every month, a small business owner in Greece sits down with a pile of documents to close the books.

There is a bank statement. There is a payroll register — what Greek accountants call the **ΑΠΔ**, the Αναλυτική Περιοδική Δήλωση, the periodic declaration filed with EFKA. There are individual payslips, one per employee. And there is a receipt from AADE — the Greek tax authority — for income tax withheld.

These four documents describe the same payroll event. But they do not agree on the amount. And no single one of them tells the whole truth.

**Archon** is an agentic AI platform that reads all four, fuses them automatically, and produces a P&L report that is accurate, cited, and boardroom-ready.

---

### [0:40 – 1:30] — THE PROBLEM (Slide 2)

> *Screen: Slide 2. Four document cards visible. Pause on the gap callout at the bottom.*

Here is the core problem — illustrated with real numbers from our January 2026 demo dataset.

The **bank confirmation** shows a net salary transfer of three thousand nine hundred ninety-four euros to four employee accounts. Most SMBs stop here. They record this as payroll expense.

But it is wrong. Here is why.

The **payroll register** — the ΑΠΔ — is filed with EFKA: *Ε-Φ-Κ-Α*. EFKA — Ενιαίος Φορέας Κοινωνικής Ασφάλισης — is Greece's unified social insurance fund, the successor to the older *I-K-A*. Every Greek employer must pay approximately twenty-two percent of gross salary directly to EFKA as the employer's social contribution. This payment goes straight to the insurance institution. It never appears in the bank payroll line.

The **individual payslips** break down each employee's allocation: gross pay, the employee's own EFKA deduction, and income tax withheld.

And the **withheld income tax** travels to AADE — the Ανεξάρτητη Αρχή Δημοσίων Εσόδων — as a fourth, entirely separate transfer.

These four streams cannot be matched by date, by amount, or by bank counterparty. They require multi-document correlation by company, by period, and by Greek regulatory logic.

That reconciliation gap, at the bottom of this slide, is negative seventy-three point five percent. Recording only the bank line understates true payroll cost by almost three-quarters.

---

### [1:30 – 2:15] — THE EFKA GAP (Slide 3)

> *Screen: Slide 3. Left column (bank) vs right column (payroll register). Pause on EFKA pill at bottom.*

This slide shows the gap in numbers.

The bank statement shows three thousand nine hundred ninety-four euros and seventy-four cents. That is what arrived in employees' accounts.

The payroll register — filed with EFKA under Law four-three-eight-seven of twenty-sixteen — shows the true employer cost: six thousand nine hundred thirty euros.

The difference: two thousand nine hundred thirty-five euros, coming from two invisible streams. The employer's EFKA contribution — approximately twenty-two percent of gross — paid directly to the insurance institution. And income tax withheld — routed directly to the tax authority.

Under **IAS 19**, paragraph ten — the International Accounting Standard for employee benefits — the employer benefit expense must include all of this. The bank statement alone produces a non-compliant P&L.

Archon detects this gap automatically. Every time.

---

### [2:15 – 2:45] — ARCHITECTURE (Slide 4)

> *Screen: Slide 4. Three-phase agent grid + Foundry IQ callout.*

Archon runs as a seven-agent pipeline on Microsoft Azure.

**Phase one — Extract.** An Extractor reads scanned PDFs using GPT-4o vision. A Classifier distinguishes document subtypes. An Event Linker fuses all payroll documents for the same company and period into one reconciled event. A Validator runs four cross-document consistency rules.

**Phase two — Analyse.** The P&L Agent uses the payroll register's employer cost — not the bank figure — for the expense line. The Cash Flow Agent reads actual bank transfers. The Employee Agent builds per-person salary analytics.

**Phase three — Deliver.** The Narrator agent runs inside **Azure AI Foundry** using the AzureAISearchTool, connected to a knowledge index of ten regulatory documents: IFRS standards, EFKA tables, and Greek tax law. Every claim is cited. Every summary is grounded.

The result reaches users through a React dashboard and through Microsoft Teams as a declarative Copilot agent.

---

### [2:45 – 3:15] — DEMO: WEB APP UPLOAD

> *Screen: Switch to browser. Dashboard pre-loaded at period 2026-01. Open the upload modal.*

Let me show Archon in action.

I am opening the upload panel for the January twenty-twenty-six period. The documents are already loaded in our demo: a bank transfer confirmation, a payroll register — the ΑΠΔ — and four individual payslips.

Archon's Extraction Job runs on Azure Container Apps Jobs — GPU compute on demand, spun up per job, shut down when complete. No idle cost.

---

### [3:15 – 3:50] — DEMO: DASHBOARD

> *Screen: Dashboard. Pan across Revenue, Expenses, Net Profit, Net Margin tiles. Click Expenses to drill down into expense breakdown.*

The dashboard is live.

Revenue: eight thousand five hundred euros — net, excluding the twenty-four percent Greek VAT. Not the invoice face value. The actual revenue ex-tax.

Expenses: seven thousand five hundred eighty-eight euros. The payroll line in the expense breakdown reflects the full employer cost — six thousand nine hundred thirty euros — not the bank transfer amount. Archon is compliant with IAS nineteen by default.

The Validator agent passed all four consistency checks. Bank total within two percent of payslip sum. EFKA ratio within expected range. Payment date confirmed. Employee headcount matched.

---

### [3:50 – 4:15] — FOUNDRY IQ: CITED EXECUTIVE SUMMARY

> *Screen: Scroll to the Executive Summary section. Pause on the "Sources:" citation line.*

Now the most important part.

The executive summary is written by the Narrator agent running in **Azure AI Foundry**, grounded through **Foundry IQ** against our Azure AI Search knowledge index.

It does not say "payroll was high." It says — and I quote — *"Per IAS 19 paragraph ten, the employee benefit expense includes employer EFKA contributions under Law four-three-eight-seven slash twenty-sixteen, which arrive at the insurance institution as a separate transfer and are not visible in the bank confirmation alone."*

And at the bottom: **Sources: Law 4387/2016 · IAS 1 · IAS 19.**

That is not a language model generating plausible text. That is retrieval-augmented generation with document-level citation. Foundry IQ retrieved the relevant regulation, matched it to the multi-stream reconciliation performed by the analysis pipeline, and produced a cited, hallucination-resistant summary.

This is Reasoning Agents in production — seven specialised agents, each responsible for one part of the truth.

---

### [4:15 – 4:45] — ENTERPRISE AGENT: TEAMS COPILOT

> *Screen: Switch to Microsoft Teams. Archon Financial Intelligence agent open in Copilot Chat.*

Archon also lives inside Microsoft Teams as a **declarative Copilot agent**.

I type: *"What is our true payroll cost for January, including EFKA contributions?"*

Watch the response. Archon calls the backend API, retrieves the analysed report, and answers in natural language — with the true employer cost, the regulatory basis under Law four-three-eight-seven, and a clear explanation of why the bank statement would have given the wrong figure.

No spreadsheet. No accountant. The CFO-level answer is one message away, from inside the tool the team already uses every day.

This is Enterprise Agents: a declarative agent connecting Microsoft three-sixty-five to a live financial data pipeline, grounded in law, available to any employee in the organisation.

---

### [4:45 – 5:00] — CLOSE (Slide 5)

> *Screen: Slide 5. Metrics row visible. Badges. GitHub URL.*

Seven agents. One grounded financial truth.

Archon is open source under the MIT licence — github dot com slash upgradedev slash archon underscore azure.

Built for the Microsoft Agents League at AI Skills Fest twenty-twenty-six.

Submitted to two tracks: **Reasoning Agents** and **Enterprise Agents**.

---

## RECORDING CHECKLIST

Before hitting record:

- [ ] Open `docs/presentation.html` in Chrome — fullscreen (F11), Slide 1 active
- [ ] Second tab: `https://gentle-sky-08574a603.7.azurestaticapps.net` — period 2026-01 loaded, dashboard visible
- [ ] Teams: Archon Financial Intelligence agent open and ready to type
- [ ] Confirm backend health: `https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io/health`
- [ ] Confirm executive summary has "Sources:" citation (scroll to bottom of dashboard)
- [ ] Screen resolution 1920×1080, browser zoom 100%
- [ ] Microphone / TTS input ready
- [ ] OBS or Loom recording at 1080p, 30fps

**Tab order during recording:**
1. Presentation (Slide 1)  →  arrow key through Slides 2, 3, 4
2. Alt+Tab to Browser      →  scroll dashboard, click tiles
3. Alt+Tab to Teams        →  type question, show response
4. Alt+Tab to Presentation →  arrow key to Slide 5

---

## TTS / VOICE GUIDE (ElevenLabs or own voice)

**Style:** calm, professional, measured — CFO presentation register. Not excited. Not rushed.

**Pace:** 150–158 words per minute. Pause 0.6 s at `---` breaks. Pause 0.4 s after each numbered list item.

**Greek terms — pronunciation guide:**

| Term | Pronunciation | Meaning for viewers |
|---|---|---|
| ΕΦΚΑ / EFKA | "EF-ka" (not "ee-ef-kay-ay") | Greek social insurance fund |
| ΑΠΔ | spell out: "ah-pee-thee" | Payroll register filed with EFKA |
| IKA | "ee-KAH" | EFKA's predecessor (pre-2017) |
| AADE | "ah-AH-theh" | Greek tax authority |
| IAS | spell out: "I-A-S" | International Accounting Standard |
| N.4387/2016 | "Law four-three-eight-seven of twenty-sixteen" | Greek social insurance law |
| N.2859/2000 | "Law two-eight-five-nine of two-thousand" | Greek VAT law |

**Emphasis words (slight stress, not shout):**
- "all four" / "four streams" / "separate transfer"
- "grounded" / "cited" / "compliance"
- "true employer cost" / "not the bank figure"

**Do NOT emphasise:** law numbers, percentage figures (read flatly).
