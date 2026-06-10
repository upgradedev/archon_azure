"""DOCX / DOC extractor — uses python-docx then delegates to text LLM."""

import json
import os
from pathlib import Path

from docx import Document
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseExtractor
from .image import EXTRACTION_PROMPT, _clean_json, _safe_doc_type, _safe_float, _safe_line_items
from models.document import ExtractedDocument, DocType, LineItem


class DocxExtractor(BaseExtractor):
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
        )
        self.model = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "gpt-4o")

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in {".docx", ".doc"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def extract(self, path: Path) -> ExtractedDocument:
        text = _extract_docx_text(path)
        prompt = (
            "You are a financial document extraction specialist.\n"
            "Extract from the following document text (may be Greek or English).\n\n"
            f"DOCUMENT TEXT:\n{text[:4000]}\n\n"
            + EXTRACTION_PROMPT
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(_clean_json(raw.strip()))

        return ExtractedDocument(
            source_file=path.name,
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
            raw_text_excerpt=text[:500],
            extraction_model=self.model,
            confidence=float(data.get("confidence") or 0.88),
        )


def _extract_docx_text(path: Path) -> str:
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())
    return "\n".join(paragraphs)
