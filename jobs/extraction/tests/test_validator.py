"""Unit tests for ValidatorAgent — R1-R4 financial consistency rules. No network, no LLM."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.document import ExtractedDocument, DocType
from models.event import PayrollEvent
from agents.validator import run


def _doc(doc_type: DocType, amount: float, **kwargs) -> ExtractedDocument:
    return ExtractedDocument(
        source_file=kwargs.get("source_file", "doc.pdf"),
        doc_type=doc_type,
        detected_language="el",
        issue_date=kwargs.get("issue_date"),
        vendor_name=None,
        vendor_tax_id=None,
        recipient_name=None,
        currency="EUR",
        subtotal=None,
        vat_amount=None,
        vat_rate_pct=None,
        total_amount=amount,
        line_items=[],
        payment_due_date=None,
        invoice_number=None,
        notes=None,
        raw_text_excerpt="",
        extraction_model="gpt-4o",
        confidence=0.9,
        employee_count=kwargs.get("employee_count"),
        employer_cost_total=kwargs.get("employer_cost_total"),
        net_pay_total=kwargs.get("net_pay_total"),
    )


def _event(bank=None, register=None, payslips=None, period="2026-01") -> PayrollEvent:
    return PayrollEvent(
        period=period,
        company_name="Αλφα Μεταλουργία ΑΕΒΕ",
        bank_confirmation=bank,
        payroll_register=register,
        payslips=payslips or [],
        is_complete=True,
    )


class TestR1BankVsPayslips:
    def test_passes_when_bank_matches_payslips_within_2pct(self):
        bank = _doc(DocType.BANK_CONFIRMATION, 3994.74)
        slips = [_doc(DocType.PAYSLIP, 1997.37), _doc(DocType.PAYSLIP, 1997.37)]
        results = run([_event(bank=bank, payslips=slips)])
        r1 = next(r for r in results if r.rule.startswith("R1"))
        assert r1.passed is True

    def test_fails_when_bank_deviates_more_than_2pct(self):
        bank = _doc(DocType.BANK_CONFIRMATION, 5000.0)
        slips = [_doc(DocType.PAYSLIP, 3000.0)]
        results = run([_event(bank=bank, payslips=slips)])
        r1 = next(r for r in results if r.rule.startswith("R1"))
        assert r1.passed is False
        assert r1.severity == "error"

    def test_skips_when_bank_absent(self):
        slips = [_doc(DocType.PAYSLIP, 1000.0)]
        results = run([_event(payslips=slips)])
        r1 = next(r for r in results if r.rule.startswith("R1"))
        assert r1.passed is True
        assert r1.severity == "info"

    def test_skips_when_payslips_absent(self):
        bank = _doc(DocType.BANK_CONFIRMATION, 3000.0)
        results = run([_event(bank=bank)])
        r1 = next(r for r in results if r.rule.startswith("R1"))
        assert r1.passed is True


class TestR2EmployerCostRatio:
    def test_passes_when_ratio_in_expected_range(self):
        # 6930 / 5000 = 1.386 — within [1.25, 1.45] — the 28% gap scenario
        reg = _doc(DocType.PAYROLL_REGISTER, 6930.0,
                   employer_cost_total=6930.0, net_pay_total=5000.0)
        results = run([_event(register=reg)])
        r2 = next(r for r in results if r.rule.startswith("R2"))
        assert r2.passed is True

    def test_fails_when_ratio_below_threshold(self):
        reg = _doc(DocType.PAYROLL_REGISTER, 5000.0,
                   employer_cost_total=5000.0, net_pay_total=5000.0)
        results = run([_event(register=reg)])
        r2 = next(r for r in results if r.rule.startswith("R2"))
        assert r2.passed is False

    def test_fails_when_ratio_above_threshold(self):
        reg = _doc(DocType.PAYROLL_REGISTER, 8000.0,
                   employer_cost_total=8000.0, net_pay_total=5000.0)
        results = run([_event(register=reg)])
        r2 = next(r for r in results if r.rule.startswith("R2"))
        assert r2.passed is False

    def test_skips_when_register_absent(self):
        results = run([_event()])
        r2 = next(r for r in results if r.rule.startswith("R2"))
        assert r2.passed is True


class TestR4EmployeeCount:
    def test_passes_when_count_matches_payslip_count(self):
        reg = _doc(DocType.PAYROLL_REGISTER, 6930.0, employee_count=3)
        slips = [_doc(DocType.PAYSLIP, 1000.0) for _ in range(3)]
        results = run([_event(register=reg, payslips=slips)])
        r4 = next(r for r in results if r.rule.startswith("R4"))
        assert r4.passed is True

    def test_fails_when_register_count_exceeds_payslips(self):
        reg = _doc(DocType.PAYROLL_REGISTER, 6930.0, employee_count=5)
        slips = [_doc(DocType.PAYSLIP, 1000.0) for _ in range(3)]
        results = run([_event(register=reg, payslips=slips)])
        r4 = next(r for r in results if r.rule.startswith("R4"))
        assert r4.passed is False

    def test_skips_when_register_absent(self):
        slips = [_doc(DocType.PAYSLIP, 1000.0) for _ in range(3)]
        results = run([_event(payslips=slips)])
        r4 = next(r for r in results if r.rule.startswith("R4"))
        assert r4.passed is True


class TestPydanticOptionalFieldsADR006:
    def test_extracted_document_with_only_required_fields_succeeds(self):
        """ADR-006: optional fields must have = None defaults; construction must not raise."""
        doc = _doc(DocType.BANK_CONFIRMATION, 3000.0)
        assert doc.employee_count is None
        assert doc.employer_cost_total is None
        assert doc.net_pay_total is None

    def test_payroll_event_with_none_bank_is_valid(self):
        event = _event()
        assert event.bank_confirmation is None
        assert event.payroll_register is None
        assert event.payslips == []
