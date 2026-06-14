"""
PnLAgent — aggregates extracted documents into P&L metrics.

Single responsibility: pure Python arithmetic over classified documents.
No LLM call; deterministic and fast.

Uses employer_cost_total from payroll_register documents (when available)
as the authoritative payroll expense figure — not the bank net transfer —
to capture the full employer cost including IKA contributions.
"""

from collections import defaultdict
from models.financial import (
    ExtractedDoc, MonthlyPnL, ExpenseCategory, VendorSummary, KeyMetrics,
)
from .constants import PAYROLL_TYPES

EXPENSE_DOC_TYPES = {"invoice", "expense", "payroll", "payroll_register",
                     "bank_confirmation", "payslip"}
REVENUE_DOC_TYPES = {"sales"}


def build_pnl(period: str, docs: list[ExtractedDoc]) -> MonthlyPnL:
    revenue = sum(d.total_amount for d in docs if d.doc_type in REVENUE_DOC_TYPES)
    expenses = _compute_expenses(docs)
    # Operating expenses exclude payroll (already in cost-of-labour line) for margin calc
    non_payroll_opex = sum(
        d.total_amount for d in docs
        if d.doc_type in EXPENSE_DOC_TYPES and d.doc_type not in PAYROLL_TYPES
    )
    net_profit = revenue - expenses
    gross_margin = (net_profit / revenue * 100) if revenue else 0.0
    # Operating margin = (revenue - expenses) / revenue; same as gross when no D&A data
    operating_margin = gross_margin

    return MonthlyPnL(
        period=period,
        revenue=round(revenue, 2),
        expenses=round(expenses, 2),
        netProfit=round(net_profit, 2),
        grossMarginPct=round(gross_margin, 2),
        operatingMarginPct=round(operating_margin, 2),
    )


def build_expense_breakdown(docs: list[ExtractedDoc]) -> list[ExpenseCategory]:
    totals: dict[str, float] = defaultdict(float)
    for doc in docs:
        if doc.doc_type in EXPENSE_DOC_TYPES:
            cat = _categorise(doc)
            totals[cat] += _effective_amount(doc)

    grand_total = sum(totals.values()) or 1.0
    return [
        ExpenseCategory(
            category=cat,
            amount=round(amt, 2),
            percentage=round(amt / grand_total * 100, 1),
            monthOverMonthPct=0.0,
        )
        for cat, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]


def build_vendor_summary(docs: list[ExtractedDoc]) -> list[VendorSummary]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    # Track payment dates per vendor to compute avg days to pay
    issue_dates: dict[str, list[str]] = defaultdict(list)
    payment_dates: dict[str, list[str]] = defaultdict(list)

    for doc in docs:
        if doc.doc_type in EXPENSE_DOC_TYPES and doc.vendor_name:
            totals[doc.vendor_name] += doc.total_amount
            counts[doc.vendor_name] += 1
            if doc.issue_date:
                issue_dates[doc.vendor_name].append(doc.issue_date)
            if doc.doc_type == "bank_confirmation" and doc.issue_date:
                payment_dates[doc.vendor_name].append(doc.issue_date)

    return [
        VendorSummary(
            name=name,
            totalAmount=round(amt, 2),
            invoiceCount=counts[name],
            avgDaysToPay=_avg_days_to_pay(issue_dates.get(name, []), payment_dates.get(name, [])),
        )
        for name, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    ]


def build_key_metrics(docs: list[ExtractedDoc], revenue: float, expenses: float) -> KeyMetrics:
    invoices = [d for d in docs if d.doc_type == "sales"]
    invoice_count = len(invoices)
    avg_invoice = (sum(d.total_amount for d in invoices) / invoice_count) if invoice_count else 0.0

    # Collection rate: bank confirmations received vs invoices issued
    # If no invoice data, report 0.0 rather than a fabricated 95%
    confirmed_receipts = sum(
        d.total_amount for d in docs
        if d.doc_type == "bank_confirmation"
        and getattr(d, "doc_subtype", None) in ("receipt", "income", None)
        and d.total_amount > 0
    )
    collection_rate = (
        round(min(confirmed_receipts / revenue * 100, 100.0), 1)
        if revenue > 0 else 0.0
    )

    return KeyMetrics(
        revenueGrowthPct=0.0,  # requires prior-period data; 0.0 is accurate for single-period
        expenseRatioPct=round(expenses / revenue * 100, 1) if revenue else 0.0,
        cashBurnRate=round(expenses / 30, 2),
        invoiceCount=invoice_count,
        avgInvoiceValue=round(avg_invoice, 2),
        collectionRatePct=collection_rate,
    )


# ── internal helpers ──────────────────────────────────────────────────────────

def _compute_expenses(docs: list[ExtractedDoc]) -> float:
    """
    Use employer_cost_total from payroll_register as the true payroll cost.
    For all other expense docs use total_amount directly.
    De-duplicate payroll: if a register is present, skip bank_confirmation
    and payslips for the same period to avoid double-counting.
    """
    has_register = any(d.doc_type == "payroll_register" for d in docs)
    total = 0.0
    for doc in docs:
        if doc.doc_type in REVENUE_DOC_TYPES:
            continue
        if doc.doc_type == "payroll_register":
            # prefer employer_cost_total (includes IKA); fall back to total_amount
            total += doc.employer_cost_total or doc.total_amount
        elif doc.doc_type in ("bank_confirmation", "payslip") and has_register:
            continue  # already counted via register
        elif doc.doc_type in EXPENSE_DOC_TYPES:
            total += doc.total_amount
    return total


def _effective_amount(doc: ExtractedDoc) -> float:
    if doc.doc_type == "payroll_register":
        return doc.employer_cost_total or doc.total_amount
    return doc.total_amount


def _avg_days_to_pay(issue_dates: list[str], payment_dates: list[str]) -> int:
    """Return average days between invoice issue and payment; 0 when data is insufficient."""
    from datetime import date
    if not issue_dates or not payment_dates:
        return 0
    try:
        issues = sorted(date.fromisoformat(d) for d in issue_dates)
        payments = sorted(date.fromisoformat(d) for d in payment_dates)
        gaps = [(p - i).days for i, p in zip(issues, payments) if (p - i).days >= 0]
        return round(sum(gaps) / len(gaps)) if gaps else 0
    except (ValueError, TypeError):
        return 0


def _categorise(doc: ExtractedDoc) -> str:
    if doc.doc_type in ("payroll_register", "payroll", "payslip", "bank_confirmation"):
        return "Payroll"
    text = ((doc.notes or "") + " " + (doc.vendor_name or "")).lower()
    if any(k in text for k in ["ενοίκιο", "rent", "lease"]):
        return "Rent & Facilities"
    if any(k in text for k in ["ηλεκτρ", "electric", "power", "gas", "water", "utility"]):
        return "Utilities"
    if any(k in text for k in ["software", "saas", "cloud", "subscription"]):
        return "Software & Cloud"
    if any(k in text for k in ["marketing", "advertising", "διαφήμιση"]):
        return "Marketing"
    return "Operating Expenses"
