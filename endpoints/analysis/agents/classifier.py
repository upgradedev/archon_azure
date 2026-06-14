"""
Classifier agent — validates and re-classifies extracted documents.
Ensures doc_type is correct before P&L aggregation.

Company identity (COMPANY_TAX_ID, COMPANY_NAME) is the primary signal:
  - vendor_tax_id matches company  → document was ISSUED by us → sales (revenue)
  - recipient_name matches company → document was RECEIVED by us → expense/purchase
"""

import re
from models.financial import ExtractedDoc

_SALES_KEYWORDS = {
    "τιμολόγιο πώλησης", "sales invoice", "πώληση", "τπ ",
    "αποδεικτικό παροχής υπηρεσιών", "απυ", "δελτίο αποστολής",
    "invoice for services", "service invoice",
}

# Greek invoice number prefixes that strongly indicate a sales document
_SALES_INV_PREFIX = re.compile(r"^(ΤΠ|ΑΠΥ|ΔΑ|ΠΑ|ΤΙΜ|INV|SINV|SI)[- /]?\d", re.IGNORECASE)

_PAYROLL_KEYWORDS = {
    "μισθός", "μισθοδοσία", "salary", "payroll",
    "εργαζόμενος", "payslip", "μισθωτός",
}


def _norm_tax(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def classify(
    docs: list[ExtractedDoc],
    company_tax_id: str = "",
    company_name: str = "",
) -> list[ExtractedDoc]:
    norm_tax = _norm_tax(company_tax_id)
    norm_name = (company_name or "").strip().lower()

    for doc in docs:
        # Payroll fallback
        if doc.doc_type == "unknown" and _is_likely_payroll(doc):
            doc.doc_type = "payroll"
            continue

        # Sales detection — applies to any invoice-like type including "expense"
        if doc.doc_type in ("invoice", "expense", "unknown", "sales"):
            if _is_sales(doc, norm_tax, norm_name):
                doc.doc_type = "sales"

    return docs


def _is_likely_payroll(doc: ExtractedDoc) -> bool:
    text = (doc.notes or "").lower()
    return any(k in text for k in _PAYROLL_KEYWORDS)


def _is_sales(doc: ExtractedDoc, company_tax: str, company_name: str) -> bool:
    """
    Priority order:
      1. Vendor TAX ID matches our company's ΑΦΜ (strongest signal)
      2. Vendor name matches our company name
      3. Greek/English invoice number prefix (ΤΠ, ΑΠΥ, ΔΑ, INV …)
      4. Keyword match in notes
    """
    if company_tax:
        vendor_tax = _norm_tax(doc.vendor_tax_id)
        if vendor_tax and vendor_tax == company_tax:
            return True

    if company_name and doc.vendor_name:
        if company_name in doc.vendor_name.lower():
            return True

    if doc.invoice_number and _SALES_INV_PREFIX.match(doc.invoice_number.strip()):
        return True

    text = (doc.notes or "").lower()
    return any(k in text for k in _SALES_KEYWORDS)
