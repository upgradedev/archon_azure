"""Unit tests for CashFlowAgent — core invariant: cash = bank transfer, not employer cost."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.financial import ExtractedDoc, MonthlyPnL
from agents.cashflow_agent import build_cashflow


def _doc(doc_type: str, amount: float) -> ExtractedDoc:
    return ExtractedDoc(
        source_file="doc.pdf",
        doc_type=doc_type,
        detected_language="el",
        issue_date=None,
        vendor_name=None,
        vendor_tax_id=None,
        recipient_name=None,
        currency="EUR",
        subtotal=None,
        vat_amount=None,
        vat_rate_pct=None,
        total_amount=amount,
        payment_due_date=None,
        invoice_number=None,
        notes=None,
        confidence=0.9,
    )


def _pnl(revenue: float = 10000.0, expenses: float = 7000.0) -> MonthlyPnL:
    return MonthlyPnL(
        period="2026-01",
        revenue=revenue,
        expenses=expenses,
        netProfit=revenue - expenses,
        grossMarginPct=30.0,
        operatingMarginPct=25.0,
    )


class TestCorePayrollCashInvariant:
    def test_operating_cash_uses_bank_confirmation_not_payroll_register(self):
        """Core invariant: cash out = bank net (actual transfer), not employer cost (gross)."""
        docs = [
            _doc("bank_confirmation", 3994.74),  # real cash out
            _doc("payroll_register", 6930.00),   # employer cost — must NOT enter cash flow
            _doc("sales", 10000.0),
        ]
        cf = build_cashflow("2026-01", docs, _pnl())
        # operating = 10000 (sales) - 3994.74 (bank) = 6005.26
        assert cf.operating == pytest.approx(6005.26, abs=0.01)

    def test_payroll_register_alone_does_not_create_cash_outflow(self):
        docs = [_doc("payroll_register", 6930.0)]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.operating == 0.0

    def test_payslip_alone_does_not_create_cash_outflow(self):
        docs = [_doc("payslip", 2000.0)]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.operating == 0.0


class TestCashFlowCalculation:
    def test_empty_docs_produce_zero_cash_flow(self):
        cf = build_cashflow("2026-01", [], _pnl())
        assert cf.operating == 0.0
        assert cf.investing == 0.0
        assert cf.financing == 0.0
        assert cf.net == 0.0

    def test_net_equals_operating_when_no_investing_or_financing(self):
        docs = [_doc("sales", 5000.0), _doc("bank_confirmation", 2000.0)]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.net == cf.operating

    def test_investing_and_financing_always_zero(self):
        docs = [_doc("sales", 5000.0), _doc("invoice", 1000.0)]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.investing == 0.0
        assert cf.financing == 0.0

    def test_operating_is_negative_when_outflows_exceed_inflows(self):
        docs = [_doc("bank_confirmation", 8000.0), _doc("sales", 3000.0)]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.operating < 0

    def test_non_payroll_expenses_are_subtracted_from_operating(self):
        docs = [
            _doc("sales", 10000.0),
            _doc("invoice", 2000.0),
            _doc("expense", 500.0),
        ]
        cf = build_cashflow("2026-01", docs, _pnl())
        assert cf.operating == pytest.approx(7500.0, abs=0.01)
