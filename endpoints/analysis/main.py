"""
Archon — Financial Analysis Endpoint (Azure)
Runs as an Azure Container Apps always-on service.

Pipeline (single-responsibility agents in sequence):
  1. ClassifierAgent       — re-classify doc_type for analysis context
  2. PnLAgent              — P&L aggregation (uses employer_cost from register, not bank net)
  3. CashFlowAgent         — cash flow derivation (uses bank transfers for real cash movements)
  4. EmployeeAgent         — per-employee salary analytics from payslip + register
  5. ValidatorAgent        — cross-document consistency re-validation
  6. ReconciliationAgent   — vendor statement vs uploaded invoices diff
  7. NarratorAgent         — Azure OpenAI + Foundry IQ grounded executive summary

Reads from Azure Blob Storage:
  extracted/{period}/*/documents.json

Writes to:
  reports/{period}/report.json
"""

import json
import logging
import os
from datetime import datetime, timezone

from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from agents.classifier import classify
from agents import pnl_agent, cashflow_agent, employee_agent, validator_agent, reconciliation_agent
from agents.narrator import build_summary
from models.financial import ExtractedDoc, FinancialReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("archon.analysis")


class Settings(BaseSettings):
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "archon"
    database_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


app = FastAPI(title="Archon Analysis Endpoint (Azure)", version="2.1.0")


def _blob_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)


def _load_documents(period: str) -> list[ExtractedDoc]:
    prefix = f"extracted/{period}/"
    container = _blob_client().get_container_client(settings.azure_storage_container)
    docs: list[ExtractedDoc] = []

    for blob in container.list_blobs(name_starts_with=prefix):
        if blob.name.endswith("documents.json"):
            blob_client = _blob_client().get_blob_client(
                container=settings.azure_storage_container, blob=blob.name
            )
            body = blob_client.download_blob().readall()
            payload = json.loads(body)
            for d in payload.get("documents", []):
                try:
                    docs.append(ExtractedDoc(**d))
                except Exception as exc:
                    log.warning("Skipping malformed document: %s", exc)
    return docs


def _cache_report(period: str, report: FinancialReport, generated_at: str) -> None:
    payload = {"jobId": "n/a", "report": report.model_dump(), "generatedAt": generated_at}
    body = json.dumps(payload, ensure_ascii=False).encode()
    blob = _blob_client().get_blob_client(
        container=settings.azure_storage_container,
        blob=f"reports/{period}/report.json",
    )
    blob.upload_blob(body, overwrite=True)


class AnalyzeRequest(BaseModel):
    period: str


class AnalyzeResponse(BaseModel):
    jobId: str
    report: FinancialReport
    generatedAt: str


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    log.info("=== Analysis start — period=%s ===", req.period)

    all_docs = _load_documents(req.period)
    if not all_docs:
        raise HTTPException(status_code=404, detail=f"No extracted documents for period {req.period}")
    log.info("Loaded %d documents", len(all_docs))

    all_docs = classify(all_docs)
    fin_docs = [d for d in all_docs if d.doc_type != "account_statement"]
    log.info("Financial docs: %d, Account statements: %d",
             len(fin_docs), len(all_docs) - len(fin_docs))

    pnl = pnl_agent.build_pnl(req.period, fin_docs)
    expense_breakdown = pnl_agent.build_expense_breakdown(fin_docs)
    top_vendors = pnl_agent.build_vendor_summary(fin_docs)
    key_metrics = pnl_agent.build_key_metrics(fin_docs, pnl.revenue, pnl.expenses)

    cash_flow = cashflow_agent.build_cashflow(req.period, fin_docs, pnl)
    validation_results = validator_agent.run(req.period, fin_docs)
    employee_summaries = employee_agent.build_employee_summaries(req.period, fin_docs)
    payroll_events = employee_agent.build_payroll_event_summaries(req.period, fin_docs, validation_results)
    vendor_reconciliations = reconciliation_agent.run(req.period, all_docs)

    report = FinancialReport(
        period=req.period,
        pnl=pnl,
        cashFlow=cash_flow,
        expenseBreakdown=expense_breakdown,
        topVendors=top_vendors,
        keyMetrics=key_metrics,
        payrollEvents=payroll_events,
        employeeSummaries=employee_summaries,
        validationResults=validation_results,
        vendorReconciliations=vendor_reconciliations,
        executiveSummary="",
    )
    report.executiveSummary = build_summary(report)

    generated_at = datetime.now(timezone.utc).isoformat()
    _cache_report(req.period, report, generated_at)

    log.info("=== Analysis complete — period=%s ===", req.period)
    return AnalyzeResponse(jobId="n/a", report=report, generatedAt=generated_at)


@app.get("/reports/{period}", response_model=AnalyzeResponse)
def get_report(period: str):
    try:
        blob = _blob_client().get_blob_client(
            container=settings.azure_storage_container,
            blob=f"reports/{period}/report.json",
        )
        body = blob.download_blob().readall()
        return json.loads(body)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"No report for period {period}") from exc


@app.get("/health")
def health():
    return {"status": "ok", "service": "archon-analysis-azure", "version": "2.1.0"}
