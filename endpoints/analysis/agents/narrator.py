"""
Executive narrator — uses Azure AI Foundry agent SDK with Foundry IQ grounding.

Foundry IQ integration (azure-ai-projects SDK):
  The NarratorAgent runs as an Azure AI Foundry agent with a connected
  Azure AI Search knowledge index containing IFRS accounting standards,
  Greek IKA/EFKA payroll regulations, and VAT compliance rules.

  Using the azure-ai-projects AIProjectClient and the native FileSearch /
  AzureAISearch tool, the agent retrieves grounded, cited knowledge before
  writing the executive summary — preventing hallucination of financial
  figures or regulatory claims.

  This is the Foundry IQ intelligence layer as defined by Microsoft:
  "agentic knowledge retrieval — connects multiple enterprise sources,
  enforces permissions, and delivers cited, grounded answers."

  Fallback path:
    When AZURE_AI_PROJECT_CONNECTION_STRING is not set (e.g. local dev or
    CI without Foundry), the narrator falls back to a plain AzureOpenAI
    completion with Azure AI Search data_sources — still grounded, but
    without the Foundry agent runtime overhead.

Configuration:
  Foundry path (production):
    AZURE_AI_PROJECT_CONNECTION_STRING   — Foundry project connection string
    AZURE_AI_SEARCH_CONNECTION_NAME      — AI Search connection name in Foundry
    AZURE_AI_SEARCH_INDEX                — index to query (default: archon-knowledge)
    AZURE_OPENAI_ANALYSIS_DEPLOYMENT     — GPT-4o deployment name

  Fallback path (local / CI):
    AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / AZURE_OPENAI_API_VERSION
    AZURE_AI_SEARCH_ENDPOINT / AZURE_AI_SEARCH_KEY / AZURE_AI_SEARCH_INDEX
"""

import logging
import os
import time

from tenacity import retry, stop_after_attempt, wait_exponential

from models.financial import FinancialReport

log = logging.getLogger("archon.analysis")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_summary(report: FinancialReport) -> str:
    """
    Generate a CFO-level executive summary grounded in Foundry IQ knowledge.

    Tries the Foundry agent path first; falls back to Azure OpenAI On Your
    Data if the project connection string is absent.
    """
    prompt = _build_prompt(report)

    try:
        if os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING", "").strip():
            summary = _foundry_agent_summary(prompt)
            log.info("Narrator: Foundry IQ agent path — grounded summary produced")
        else:
            summary = _openai_fallback_summary(prompt)
            log.info("Narrator: fallback path — Azure OpenAI direct call")
        return summary
    except Exception as exc:
        log.warning("Narrator LLM failed (non-fatal): %s", exc)
        return (
            f"Financial summary for {report.period}: "
            f"Revenue \u20ac{report.pnl.revenue:,.2f}, "
            f"Expenses \u20ac{report.pnl.expenses:,.2f}, "
            f"Net Profit \u20ac{report.pnl.netProfit:,.2f}. "
            f"(Executive narrative unavailable \u2014 LLM error)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Foundry agent path  (azure-ai-projects SDK)
# ─────────────────────────────────────────────────────────────────────────────

def _foundry_agent_summary(prompt: str) -> str:
    """
    Run a single-turn Foundry agent with AzureAISearch grounding.

    The agent is ephemeral: created, used once, then deleted.
    This keeps the Foundry workspace clean between requests.

    Required env vars:
      AZURE_AI_PROJECT_CONNECTION_STRING
      AZURE_AI_SEARCH_CONNECTION_NAME
      AZURE_AI_SEARCH_INDEX
      AZURE_OPENAI_ANALYSIS_DEPLOYMENT
    """
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import AzureAISearchTool, MessageRole
    from azure.identity import DefaultAzureCredential

    conn_str = os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
    search_conn = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "archon-search")
    index_name = os.environ.get("AZURE_AI_SEARCH_INDEX", "archon-knowledge")
    deployment = os.environ.get("AZURE_OPENAI_ANALYSIS_DEPLOYMENT", "gpt-4o")

    client = AIProjectClient.from_connection_string(
        conn_str=conn_str,
        credential=DefaultAzureCredential(),
    )

    search_tool = AzureAISearchTool(
        index_connection_id=client.connections.get(connection_name=search_conn).id,
        index_name=index_name,
        query_type="semantic",
        top_k=3,
    )

    agent = client.agents.create_agent(
        model=deployment,
        name="archon-narrator",
        instructions=(
            "You are a CFO-level financial analyst with deep expertise in Greek tax law, "
            "IKA/EFKA payroll regulations (Law 4387/2016, current EFKA rates), and IFRS "
            "reporting standards. Use the connected knowledge base to produce accurate, "
            "regulation-cited executive summaries. Cite specific standards or law articles "
            "when making regulatory claims."
        ),
        tools=search_tool.definitions,
        tool_resources=search_tool.resources,
    )

    try:
        thread = client.agents.create_thread()
        client.agents.create_message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=prompt,
        )

        run = client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=agent.id,
        )

        # Poll until terminal state (create_and_process_run blocks, but be safe)
        _wait_for_run(client, thread.id, run.id)

        messages = client.agents.list_messages(thread_id=thread.id)
        # Last assistant message is the summary
        for msg in reversed(messages.data):
            if msg.role == MessageRole.ASSISTANT:
                for block in msg.content:
                    if hasattr(block, "text"):
                        return block.text.value.strip()
        raise RuntimeError("Foundry agent returned no assistant message")

    finally:
        client.agents.delete_agent(agent.id)


def _wait_for_run(client, thread_id: str, run_id: str, timeout: int = 90) -> None:
    """Poll run status until terminal state or timeout."""
    terminal = {"completed", "failed", "cancelled", "expired"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.agents.get_run(thread_id=thread_id, run_id=run_id)
        if run.status in terminal:
            if run.status != "completed":
                raise RuntimeError(f"Foundry run ended with status={run.status}")
            return
        time.sleep(1.5)
    raise TimeoutError(f"Foundry run did not complete within {timeout}s")


# ─────────────────────────────────────────────────────────────────────────────
# Fallback path  (Azure OpenAI On Your Data — works without Foundry project)
# ─────────────────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _openai_fallback_summary(prompt: str) -> str:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
    )
    model = os.getenv("AZURE_OPENAI_ANALYSIS_DEPLOYMENT", "gpt-4o")
    extra_body = _search_data_source_config()

    kwargs = {"extra_body": extra_body} if extra_body else {}
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.4,
        **kwargs,
    )
    return (response.choices[0].message.content or "").strip()


def _search_data_source_config() -> dict:
    endpoint = os.environ.get("AZURE_AI_SEARCH_ENDPOINT", "").strip()
    key = os.environ.get("AZURE_AI_SEARCH_KEY", "").strip()
    if not endpoint or not key:
        return {}
    return {
        "data_sources": [{
            "type": "azure_search",
            "parameters": {
                "endpoint": endpoint,
                "index_name": os.getenv("AZURE_AI_SEARCH_INDEX", "archon-knowledge"),
                "authentication": {"type": "api_key", "key": key},
                "query_type": "semantic",
                "semantic_configuration": "default",
                "strictness": 3,
                "top_n_documents": 3,
                "in_scope": True,
                "role_information": (
                    "You are a CFO-level financial analyst with expertise in Greek tax law, "
                    "IKA/EFKA payroll regulations, and IFRS reporting standards. "
                    "Use retrieved knowledge to produce accurate, regulation-cited summaries."
                ),
            },
        }]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(report: FinancialReport) -> str:
    top_categories = ", ".join(e.category for e in report.expenseBreakdown[:3])
    payroll_gap = ""
    for ev in report.payrollEvents:
        if ev.employer_cost_total and ev.net_total:
            gap_pct = (ev.employer_cost_total - ev.net_total) / ev.net_total * 100
            payroll_gap = (
                f"\nPayroll: bank net \u20ac{ev.net_total:,.2f} vs true employer cost "
                f"\u20ac{ev.employer_cost_total:,.2f} (+{gap_pct:.1f}%)"
            )
            break

    return f"""You are a CFO-level financial analyst. Write a concise executive summary (3-4 sentences,
plain English, no bullet points) for the following monthly financial data.
Where relevant, cite applicable accounting standards or Greek tax/payroll regulations
(e.g. EFKA contribution rates under Law 4387/2016, IAS 1 presentation, Greek VAT Law 2859/2000).

Period: {report.period}
Revenue: \u20ac{report.pnl.revenue:,.2f}
Expenses: \u20ac{report.pnl.expenses:,.2f}
Net Profit: \u20ac{report.pnl.netProfit:,.2f}
Gross Margin: {report.pnl.grossMarginPct:.1f}%
Operating Margin: {report.pnl.operatingMarginPct:.1f}%
Revenue Growth MoM: {report.keyMetrics.revenueGrowthPct:.1f}%
Expense Ratio: {report.keyMetrics.expenseRatioPct:.1f}%
Invoice Count: {report.keyMetrics.invoiceCount}
Avg Invoice Value: \u20ac{report.keyMetrics.avgInvoiceValue:,.2f}
Collection Rate: {report.keyMetrics.collectionRatePct:.1f}%
Top Expense Categories: {top_categories}{payroll_gap}

Write the summary now:"""
