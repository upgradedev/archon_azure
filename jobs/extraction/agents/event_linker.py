"""
EventLinkerAgent — groups extracted documents into unified payroll events.

Single responsibility: identify that a bank confirmation, a payroll register,
and one or more payslips are all describing the *same* payroll event (same
company, same period, overlapping amounts) and package them together.

This solves the core insight: the bank confirmation alone understates the
true employer payroll cost by ~28% (net only vs gross + IKA contributions).
Only by linking all three doc subtypes can we compute the real P&L impact.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date

from models.document import ExtractedDocument, DocType
from models.event import PayrollEvent

log = logging.getLogger("archon.event_linker")

# When multiple payroll events exist for the same company+period,
# use amount proximity to prefer the closest-matching bank confirmation.
AMOUNT_TOLERANCE = 0.05  # 5% — used in _pick_best_bank_confirmation


def run(docs: list[ExtractedDocument]) -> list[PayrollEvent]:
    """
    Return one PayrollEvent per company+period group, linking the three
    payroll document subtypes wherever possible.
    """
    payroll_types = {
        DocType.BANK_CONFIRMATION,
        DocType.PAYROLL_REGISTER,
        DocType.PAYSLIP,
        DocType.PAYROLL,
    }
    payroll_docs = [d for d in docs if d.doc_type in payroll_types]

    if not payroll_docs:
        return []

    # Group by (company, period)
    groups: dict[tuple[str, str], list[ExtractedDocument]] = defaultdict(list)
    for doc in payroll_docs:
        key = (_company(doc), _period(doc))
        groups[key].append(doc)

    events: list[PayrollEvent] = []
    for (company, period), group in groups.items():
        event = _build_event(company, period, group)
        events.append(event)
        log.info(
            "Linked event company=%s period=%s docs=%d complete=%s",
            company, period, len(group), event.is_complete,
        )

    return events


def _build_event(company: str, period: str, docs: list[ExtractedDocument]) -> PayrollEvent:
    register = _pick_one(docs, DocType.PAYROLL_REGISTER)
    payslips = [d for d in docs if d.doc_type == DocType.PAYSLIP]

    # When multiple bank confirmations exist, prefer the one whose amount is
    # closest to the register net_pay_total within AMOUNT_TOLERANCE.
    bank = _pick_best_bank_confirmation(
        docs, DocType.BANK_CONFIRMATION, register
    )

    is_complete = all([bank is not None, register is not None, len(payslips) > 0])

    return PayrollEvent(
        period=period,
        company_name=company or None,
        bank_confirmation=bank,
        payroll_register=register,
        payslips=payslips,
        is_complete=is_complete,
    )


def _pick_best_bank_confirmation(
    docs: list[ExtractedDocument],
    doc_type: DocType,
    register: "ExtractedDocument | None",
) -> "ExtractedDocument | None":
    """
    Select the bank confirmation that best matches the payroll register net amount.
    Falls back to highest-confidence pick when no register or no amount data.
    """
    candidates = [d for d in docs if d.doc_type == doc_type]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if register and register.net_pay_total:
        ref = register.net_pay_total
        within_tolerance = [
            d for d in candidates
            if d.total_amount and abs(d.total_amount - ref) / ref <= AMOUNT_TOLERANCE
        ]
        if within_tolerance:
            return max(within_tolerance, key=lambda d: d.confidence)
    # Fallback: highest confidence
    return max(candidates, key=lambda d: d.confidence)


def _pick_one(docs: list[ExtractedDocument], doc_type: DocType) -> ExtractedDocument | None:
    matches = [d for d in docs if d.doc_type == doc_type]
    if not matches:
        return None
    if len(matches) > 1:
        # prefer highest confidence
        matches.sort(key=lambda d: d.confidence, reverse=True)
        log.warning("Multiple %s docs found; picking highest-confidence one.", doc_type)
    return matches[0]


def _company(doc: ExtractedDocument) -> str:
    return (doc.recipient_name or doc.vendor_name or "").strip()


def _period(doc: ExtractedDocument) -> str:
    """Return YYYY-MM from the document's issue_date, or 'unknown'."""
    if not doc.issue_date:
        return "unknown"
    try:
        d = date.fromisoformat(doc.issue_date)
        return f"{d.year:04d}-{d.month:02d}"
    except ValueError:
        return doc.issue_date[:7] if len(doc.issue_date) >= 7 else "unknown"
