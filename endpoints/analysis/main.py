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


# ─────────────────────────────────────────────────────────────────────────────
# Demo seed endpoint — uploads synthetic demo documents for testing/demo
# Requires no external credentials; runs inside the container using its own
# storage connection. Call once before running e2e-live.py.
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_DOCUMENTS = [
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/attiki_odos_invoice_202601.pdf",
        "doc_type": "invoice", "detected_language": "el", "issue_date": "2026-01-31",
        "vendor_name": "ATTIKI ODOS AE", "vendor_tax_id": "094506571",
        "recipient_name": "REFLECTIVE IKE", "currency": "EUR",
        "original_currency": None, "original_amount": None,
        "subtotal": 68.87, "vat_amount": 16.53, "vat_rate_pct": 24.0,
        "vat_treatment": "standard", "total_amount": 85.40,
        "payment_due_date": "2026-02-14", "invoice_number": "ATTIKI-202601-0042",
        "notes": "Tolls January 2026 - Egnatia Odos", "confidence": 0.97,
        "employee_count": None, "gross_pay_total": None, "employer_cost_total": None,
        "net_pay_total": None, "employee_name": None, "employee_code": None,
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/anthropic_invoice_202601.pdf",
        "doc_type": "invoice", "detected_language": "en", "issue_date": "2026-01-31",
        "vendor_name": "Anthropic, PBC", "vendor_tax_id": None,
        "recipient_name": "Upgrade Fousekis E & Co", "currency": "EUR",
        "original_currency": "USD", "original_amount": 312.44,
        "subtotal": 300.07, "vat_amount": 0.0, "vat_rate_pct": 0.0,
        "vat_treatment": "reverse_charge", "total_amount": 300.07,
        "payment_due_date": "2026-02-14", "invoice_number": "INV-BF69A412-0042",
        "notes": "Claude API usage Jan 2026. Reverse charge Art 44.", "confidence": 0.96,
        "employee_count": None, "gross_pay_total": None, "employer_cost_total": None,
        "net_pay_total": None, "employee_name": None, "employee_code": None,
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/azure_invoice_202601.pdf",
        "doc_type": "invoice", "detected_language": "en", "issue_date": "2026-02-01",
        "vendor_name": "Microsoft Azure EMEA", "vendor_tax_id": "IE8256796U",
        "recipient_name": "Upgrade Fousekis E & Co", "currency": "EUR",
        "original_currency": "USD", "original_amount": 284.20,
        "subtotal": 272.92, "vat_amount": 0.0, "vat_rate_pct": 0.0,
        "vat_treatment": "reverse_charge", "total_amount": 272.92,
        "payment_due_date": None, "invoice_number": "EUINGR26-AZ-00142",
        "notes": "Azure Container Apps + OpenAI Jan 2026. B2B EU reverse charge.", "confidence": 0.95,
        "employee_count": None, "gross_pay_total": None, "employer_cost_total": None,
        "net_pay_total": None, "employee_name": None, "employee_code": None,
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/payroll_register_202601.pdf",
        "doc_type": "payroll_register", "detected_language": "el", "issue_date": "2026-01-31",
        "vendor_name": "REFLECTIVE IKE", "vendor_tax_id": "801234567",
        "recipient_name": None, "currency": "EUR",
        "original_currency": None, "original_amount": None,
        "subtotal": None, "vat_amount": None, "vat_rate_pct": None,
        "vat_treatment": None, "total_amount": 6930.00,
        "payment_due_date": "2026-01-31", "invoice_number": None,
        "notes": "Payroll register January 2026. 3 employees.", "confidence": 0.98,
        "employee_count": 3, "gross_pay_total": 5500.00, "employer_cost_total": 6930.00,
        "net_pay_total": 3994.74, "employee_name": None, "employee_code": None,
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/bank_confirmation_202601.pdf",
        "doc_type": "bank_confirmation", "detected_language": "el", "issue_date": "2026-01-31",
        "vendor_name": "TRAPEZA PEIRAIOS AE", "vendor_tax_id": None,
        "recipient_name": "REFLECTIVE IKE", "currency": "EUR",
        "original_currency": None, "original_amount": None,
        "subtotal": None, "vat_amount": None, "vat_rate_pct": None,
        "vat_treatment": None, "total_amount": 3994.74,
        "payment_due_date": None, "invoice_number": "TXN-20260131-44821",
        "notes": "Mass payroll transfer confirmation. Ref: PAYROLL-202601-REF", "confidence": 0.99,
        "employee_count": 3, "gross_pay_total": None, "employer_cost_total": None,
        "net_pay_total": 3994.74, "employee_name": None, "employee_code": None,
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/payslip_emp001_202601.pdf",
        "doc_type": "payslip", "detected_language": "el", "issue_date": "2026-01-31",
        "vendor_name": "REFLECTIVE IKE", "vendor_tax_id": "801234567",
        "recipient_name": "Papadopoulos Nikos", "currency": "EUR",
        "original_currency": None, "original_amount": None,
        "subtotal": None, "vat_amount": None, "vat_rate_pct": None,
        "vat_treatment": None, "total_amount": 1312.44,
        "payment_due_date": "2026-01-31", "invoice_number": None,
        "notes": "Payslip January 2026. IKA employee 16%, employer 26%.", "confidence": 0.98,
        "employee_count": None, "gross_pay_total": None, "employer_cost_total": 2268.00,
        "net_pay_total": 1312.44, "employee_name": "Papadopoulos Nikos", "employee_code": "EMP-001",
        "statement_balance": None, "statement_overdue": None, "statement_entries": None,
    },
    {
        "source_file": "raw-docs/2026-01/demo-upload-001/microsoft_statement_202601.pdf",
        "doc_type": "account_statement", "detected_language": "en", "issue_date": "2026-01-31",
        "vendor_name": "Microsoft Azure EMEA", "vendor_tax_id": "IE8256796U",
        "recipient_name": "Upgrade Fousekis E & Co", "currency": "EUR",
        "original_currency": None, "original_amount": None,
        "subtotal": None, "vat_amount": None, "vat_rate_pct": None,
        "vat_treatment": None, "total_amount": 272.92,
        "payment_due_date": None, "invoice_number": None,
        "notes": "Statement Jan 2026. Outstanding: EUR 272.92. Overdue: EUR 0.", "confidence": 0.97,
        "employee_count": None, "gross_pay_total": None, "employer_cost_total": None,
        "net_pay_total": None, "employee_name": None, "employee_code": None,
        "statement_balance": 272.92, "statement_overdue": 0.0,
        "statement_entries": [
            {"document_number": "EUINGR26-AZ-00142", "posting_date": "2026-02-01",
             "due_date": "2026-03-01", "original_amount": 272.92,
             "remaining_amount": 272.92, "is_overdue": False},
        ],
    },
]


@app.post("/seed-demo")
def seed_demo():
    """
    Replace all extracted documents for 2026-01 with clean demo data.
    Deletes any existing blobs under extracted/2026-01/ first so old test-run
    data cannot contaminate the analysis result. Then uploads the 7 synthetic
    demo documents as the sole source for the period.
    Uses the container's own AZURE_STORAGE_CONNECTION_STRING — no external credentials needed.
    """
    period    = "2026-01"
    upload_id = "demo-upload-001"
    prefix    = f"extracted/{period}/"
    container = settings.azure_storage_container

    blob_svc = _blob_client()
    cont_client = blob_svc.get_container_client(container)

    # Delete every blob under extracted/2026-01/ (old runs, stale data)
    deleted = 0
    for b in cont_client.list_blobs(name_starts_with=prefix):
        cont_client.delete_blob(b.name)
        deleted += 1
    log.info("Deleted %d stale blobs under %s", deleted, prefix)

    # Upload fresh demo documents
    blob_name = f"{prefix}{upload_id}/documents.json"
    payload   = {"documents": _DEMO_DOCUMENTS, "upload_id": upload_id, "period": period}
    body      = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    blob_svc.get_blob_client(container=container, blob=blob_name).upload_blob(body, overwrite=True)

    log.info("Seeded demo data: %s (%d docs)", blob_name, len(_DEMO_DOCUMENTS))
    return {
        "seeded": True,
        "blob": blob_name,
        "docs": len(_DEMO_DOCUMENTS),
        "deleted_stale": deleted,
        "period": period,
    }
