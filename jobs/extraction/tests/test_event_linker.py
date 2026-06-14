"""
Unit tests for EventLinkerAgent — the core architectural insight of Archon.

The linker fuses a bank confirmation + payroll register + payslips into a
single PayrollEvent so the analysis tier can compute the real employer cost
(which exceeds the bank transfer by ~28% due to IKA/EFKA contributions).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.document import ExtractedDocument, DocType
from models.event import PayrollEvent
from agents.event_linker import run


def _doc(doc_type: DocType, amount: float, **kwargs) -> ExtractedDocument:
    return ExtractedDocument(
        source_file=kwargs.get("source_file", f"{doc_type.value}.pdf"),
        doc_type=doc_type,
        detected_language="el",
        issue_date=kwargs.get("issue_date", "2026-01-31"),
        vendor_name=kwargs.get("vendor_name"),
        vendor_tax_id=None,
        recipient_name=kwargs.get("recipient_name", "Αλφα Μεταλουργία ΑΕΒΕ"),
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
        confidence=kwargs.get("confidence", 0.9),
        employee_count=kwargs.get("employee_count"),
        net_pay_total=kwargs.get("net_pay_total"),
        employer_cost_total=kwargs.get("employer_cost_total"),
    )


class TestCompleteTripleLink:
    def test_three_doc_types_produce_single_complete_event(self):
        """All three payroll subtypes linked → is_complete=True."""
        docs = [
            _doc(DocType.BANK_CONFIRMATION, 3994.74),
            _doc(DocType.PAYROLL_REGISTER, 6930.00, employer_cost_total=6930.0, net_pay_total=5000.0),
            _doc(DocType.PAYSLIP, 1997.37, source_file="slip1.pdf"),
            _doc(DocType.PAYSLIP, 1997.37, source_file="slip2.pdf"),
        ]
        events = run(docs)
        assert len(events) == 1
        ev = events[0]
        assert ev.is_complete is True
        assert ev.bank_confirmation is not None
        assert ev.payroll_register is not None
        assert len(ev.payslips) == 2

    def test_linked_amounts_match_original_docs(self):
        """The linked event preserves the original doc amounts — no mutation."""
        bank = _doc(DocType.BANK_CONFIRMATION, 3994.74)
        reg = _doc(DocType.PAYROLL_REGISTER, 6930.00, employer_cost_total=6930.0)
        slip = _doc(DocType.PAYSLIP, 3994.74)
        events = run([bank, reg, slip])
        ev = events[0]
        assert ev.bank_confirmation.total_amount == pytest.approx(3994.74)
        assert ev.payroll_register.total_amount == pytest.approx(6930.00)
        assert ev.payroll_register.employer_cost_total == pytest.approx(6930.00)


class TestIncompleteEvents:
    def test_bank_only_produces_incomplete_event(self):
        events = run([_doc(DocType.BANK_CONFIRMATION, 3994.74)])
        assert len(events) == 1
        assert events[0].is_complete is False
        assert events[0].payroll_register is None
        assert events[0].payslips == []

    def test_register_and_payslips_no_bank_produces_incomplete_event(self):
        docs = [
            _doc(DocType.PAYROLL_REGISTER, 6930.00),
            _doc(DocType.PAYSLIP, 3000.0),
        ]
        events = run(docs)
        assert len(events) == 1
        assert events[0].is_complete is False
        assert events[0].bank_confirmation is None


class TestNonPayrollDocsExcluded:
    def test_sales_and_invoice_docs_not_linked_into_events(self):
        docs = [
            _doc(DocType.BANK_CONFIRMATION, 3994.74),
            _doc(DocType.PAYROLL_REGISTER, 6930.00),
            _doc(DocType.PAYSLIP, 1997.37),
        ]
        # add non-payroll docs — they must be ignored
        from models.document import ExtractedDocument
        invoice = ExtractedDocument(
            source_file="inv.pdf", doc_type=DocType.INVOICE,
            detected_language="el", issue_date="2026-01-15",
            vendor_name="Supplier A", vendor_tax_id=None, recipient_name="Αλφα ΑΕΒΕ",
            currency="EUR", subtotal=None, vat_amount=None, vat_rate_pct=None,
            total_amount=5000.0, line_items=[], payment_due_date=None,
            invoice_number="INV-001", notes=None, raw_text_excerpt="",
            extraction_model="gpt-4o", confidence=0.9,
        )
        events = run(docs + [invoice])
        # Still one event
        assert len(events) == 1
        # Invoice amount does not appear in event totals
        assert events[0].bank_confirmation.total_amount == pytest.approx(3994.74)

    def test_empty_doc_list_returns_empty(self):
        assert run([]) == []


class TestMultiCompanyGrouping:
    def test_two_companies_produce_two_events(self):
        docs = [
            _doc(DocType.BANK_CONFIRMATION, 3994.74, recipient_name="Αλφα ΑΕΒΕ"),
            _doc(DocType.PAYROLL_REGISTER, 6930.00, recipient_name="Αλφα ΑΕΒΕ"),
            _doc(DocType.PAYSLIP, 1997.37, recipient_name="Αλφα ΑΕΒΕ"),
            _doc(DocType.BANK_CONFIRMATION, 8000.00, recipient_name="Βήτα ΕΠΕ"),
            _doc(DocType.PAYROLL_REGISTER, 12000.00, recipient_name="Βήτα ΕΠΕ"),
            _doc(DocType.PAYSLIP, 4000.00, recipient_name="Βήτα ΕΠΕ"),
        ]
        events = run(docs)
        assert len(events) == 2
        totals = {e.company_name: e.payroll_register.total_amount for e in events}
        assert totals.get("Αλφα ΑΕΒΕ") == pytest.approx(6930.00)
        assert totals.get("Βήτα ΕΠΕ") == pytest.approx(12000.00)


class TestBestBankConfirmationSelection:
    def test_multiple_banks_picks_closest_to_register_net(self):
        """When two bank confirmations exist, pick the one nearest net_pay_total."""
        reg = _doc(DocType.PAYROLL_REGISTER, 6930.00, net_pay_total=5000.0)
        # bank_a is close to net 5000 (within 5%)
        bank_a = _doc(DocType.BANK_CONFIRMATION, 5100.0, source_file="bank_a.pdf", confidence=0.7)
        # bank_b is far from net 5000
        bank_b = _doc(DocType.BANK_CONFIRMATION, 3000.0, source_file="bank_b.pdf", confidence=0.95)
        slip = _doc(DocType.PAYSLIP, 2500.0)

        events = run([reg, bank_a, bank_b, slip])
        assert len(events) == 1
        assert events[0].bank_confirmation.source_file == "bank_a.pdf"


class TestPayrollGapInvariant:
    def test_employer_cost_exceeds_bank_net_by_expected_ratio(self):
        """
        Core value proposition: after linking, employer_cost_total / bank.total > 1.25.
        The 28% gap (6930 vs 3994.74) is the demo scenario.
        """
        docs = [
            _doc(DocType.BANK_CONFIRMATION, 3994.74),
            _doc(DocType.PAYROLL_REGISTER, 6930.00, employer_cost_total=6930.0, net_pay_total=5000.0),
            _doc(DocType.PAYSLIP, 1997.37, source_file="s1.pdf"),
            _doc(DocType.PAYSLIP, 1997.37, source_file="s2.pdf"),
        ]
        events = run(docs)
        ev = events[0]
        bank_net = ev.bank_confirmation.total_amount
        employer_cost = ev.payroll_register.employer_cost_total
        gap_ratio = employer_cost / bank_net
        assert gap_ratio == pytest.approx(1.734, abs=0.01)  # 6930 / 3994.74 ≈ 1.734
        assert gap_ratio > 1.25  # never understate the cost
