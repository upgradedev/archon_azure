"""
Upload synthetic extracted documents to Azure Blob Storage for demo/testing.
Simulates what the extraction job would produce for the 7 sample PDFs.

Usage:
    python scripts/upload_demo_docs.py

Requires: azure-storage-blob (in backend requirements)
Credentials are read from .env or environment variables.
"""

import json
import os
from azure.storage.blob import BlobServiceClient

CONNECTION_STRING = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING",
    os.getenv("AZURITE_CONNECTION_STRING", "")
)
CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "archon")

documents = [
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


def main():
    if not CONNECTION_STRING:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not set")
        return

    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)

    # Ensure container exists
    try:
        client.create_container(CONTAINER)
        print(f"Created container: {CONTAINER}")
    except Exception:
        print(f"Container already exists: {CONTAINER}")

    payload = {"documents": documents, "upload_id": "demo-upload-001", "period": "2026-01"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    blob_name = "extracted/2026-01/demo-upload-001/documents.json"
    blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
    blob.upload_blob(body, overwrite=True)

    print(f"Uploaded {blob_name} ({len(body)} bytes, {len(documents)} documents)")
    print(f"Call analysis: POST http://<endpoint>:8001/analyze -d '{{\"period\": \"2026-01\"}}'")


if __name__ == "__main__":
    main()
