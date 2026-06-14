"""Unit tests for ClassifierAgent — accent-normalised keyword inference. No network, no LLM."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.document import ExtractedDocument, DocType
from agents.classifier import run


def _doc(doc_type: DocType, notes: str = "", vendor: str = "", excerpt: str = "") -> ExtractedDocument:
    return ExtractedDocument(
        source_file="test.pdf",
        doc_type=doc_type,
        detected_language="el",
        issue_date=None,
        vendor_name=vendor or None,
        vendor_tax_id=None,
        recipient_name=None,
        currency="EUR",
        subtotal=None,
        vat_amount=None,
        vat_rate_pct=None,
        total_amount=1000.0,
        line_items=[],
        payment_due_date=None,
        invoice_number=None,
        notes=notes or None,
        raw_text_excerpt=excerpt,
        extraction_model="gpt-4o",
        confidence=0.9,
    )


class TestBankConfirmationReclassification:
    def test_unknown_with_bank_keyword_becomes_bank_confirmation(self):
        doc = _doc(DocType.UNKNOWN, notes="βεβαιωση μεταφορας μισθοδοσιας")
        result = run([doc])
        assert result[0].doc_type == DocType.BANK_CONFIRMATION

    def test_unknown_with_eurobank_keyword_becomes_bank_confirmation(self):
        doc = _doc(DocType.UNKNOWN, vendor="Eurobank Greece")
        result = run([doc])
        assert result[0].doc_type == DocType.BANK_CONFIRMATION

    def test_payroll_generic_with_bank_keyword_becomes_bank_confirmation(self):
        doc = _doc(DocType.PAYROLL, notes="κατασταση εμβασματων payroll batch")
        result = run([doc])
        assert result[0].doc_type == DocType.BANK_CONFIRMATION


class TestPayrollRegisterReclassification:
    def test_unknown_with_register_keyword_becomes_payroll_register(self):
        doc = _doc(DocType.UNKNOWN, notes="μισθοδοτικη κατασταση Ιανουαριος 2026")
        result = run([doc])
        assert result[0].doc_type == DocType.PAYROLL_REGISTER

    def test_unknown_with_efka_keyword_becomes_payroll_register(self):
        doc = _doc(DocType.UNKNOWN, excerpt="ασφαλιστικες εισφορες εφκα εργοδοτης")
        result = run([doc])
        assert result[0].doc_type == DocType.PAYROLL_REGISTER


class TestPayslipReclassification:
    def test_unknown_with_payslip_keyword_becomes_payslip(self):
        doc = _doc(DocType.UNKNOWN, notes="αποδειξη πληρωμης μισθου")
        result = run([doc])
        assert result[0].doc_type == DocType.PAYSLIP

    def test_unknown_with_english_payslip_keyword_becomes_payslip(self):
        doc = _doc(DocType.UNKNOWN, excerpt="payslip January 2026")
        result = run([doc])
        assert result[0].doc_type == DocType.PAYSLIP


class TestClassifierDoesNotTouchNonUnknown:
    def test_sales_doc_with_bank_keyword_is_not_changed(self):
        doc = _doc(DocType.SALES, notes="βεβαιωση μεταφορας")
        result = run([doc])
        assert result[0].doc_type == DocType.SALES

    def test_invoice_doc_is_never_reclassified(self):
        doc = _doc(DocType.INVOICE, notes="μισθοδοτικη κατασταση")
        result = run([doc])
        assert result[0].doc_type == DocType.INVOICE


class TestAccentInsensitivity:
    def test_accented_bank_keyword_matches(self):
        doc = _doc(DocType.UNKNOWN, notes="βεβαίωση μεταφοράς")
        result = run([doc])
        assert result[0].doc_type == DocType.BANK_CONFIRMATION

    def test_accented_register_keyword_matches(self):
        doc = _doc(DocType.UNKNOWN, notes="μισθοδοτική κατάσταση")
        result = run([doc])
        assert result[0].doc_type == DocType.PAYROLL_REGISTER


class TestNoKeywordMatch:
    def test_unknown_with_no_keywords_stays_unknown(self):
        doc = _doc(DocType.UNKNOWN, notes="random unrelated text here")
        result = run([doc])
        assert result[0].doc_type == DocType.UNKNOWN

    def test_empty_notes_stays_unknown(self):
        doc = _doc(DocType.UNKNOWN)
        result = run([doc])
        assert result[0].doc_type == DocType.UNKNOWN
