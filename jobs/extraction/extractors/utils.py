"""Shared extraction helpers — document factory, JSON sanitisation, safe converters."""
from models.document import ExtractedDocument, DocType, LineItem


def build_document(
    source_file: str,
    data: dict,
    extraction_model: str,
    raw_text_excerpt: str,
    default_confidence: float = 0.85,
) -> ExtractedDocument:
    """Single construction point for ExtractedDocument across all extractors (DRY / ADR-003)."""
    return ExtractedDocument(
        source_file=source_file,
        doc_type=_safe_doc_type(data.get("doc_type")),
        detected_language=data.get("detected_language") or "el",
        issue_date=data.get("issue_date") or None,
        vendor_name=data.get("vendor_name") or None,
        vendor_tax_id=data.get("vendor_tax_id") or None,
        recipient_name=data.get("recipient_name") or None,
        currency=data.get("currency") or "EUR",
        subtotal=_safe_float(data.get("subtotal")),
        vat_amount=_safe_float(data.get("vat_amount")),
        vat_rate_pct=_safe_float(data.get("vat_rate_pct")),
        total_amount=_safe_float(data.get("total_amount")) or 0.0,
        line_items=_safe_line_items(data.get("line_items")),
        payment_due_date=data.get("payment_due_date") or None,
        invoice_number=data.get("invoice_number") or None,
        notes=data.get("notes") or None,
        raw_text_excerpt=raw_text_excerpt,
        extraction_model=extraction_model,
        confidence=float(data.get("confidence") or default_confidence),
    )


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def _safe_doc_type(value: str | None) -> DocType:
    try:
        return DocType(value) if value else DocType.UNKNOWN
    except ValueError:
        return DocType.UNKNOWN


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_line_items(value) -> list:
    if not value or not isinstance(value, list):
        return []
    items = []
    for li in value:
        if isinstance(li, dict) and "description" in li and "total" in li:
            try:
                items.append(LineItem(**li))
            except Exception:
                pass
    return items
