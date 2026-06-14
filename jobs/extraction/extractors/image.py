"""
Vision extractor — handles JPG, PNG, TIFF, WEBP, and scanned PDF pages.

Uses Azure OpenAI GPT-4o (vision) via AzureOpenAI client.
The model reads Greek natively; no translation step needed.
"""

import base64
import io
import os
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image

from .base import BaseExtractor
from .utils import build_document, _clean_json, _safe_doc_type, _safe_float, _safe_line_items
from models.document import ExtractedDocument

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp"}

EXTRACTION_PROMPT = """You are a financial document extraction specialist.
Analyse this document — it may be in Greek or English.

Extract ALL of the following fields as a JSON object (use null for missing fields).
Choose doc_type from EXACTLY one of these values:
  invoice, sales, expense, payroll_register, bank_confirmation, payslip, payroll, account_statement, unknown

{
  "doc_type": "one of the values listed above",
  "detected_language": "ISO 639-1 code, e.g. el or en",
  "issue_date": "YYYY-MM-DD or null",
  "vendor_name": "string or null",
  "vendor_tax_id": "string or null",
  "recipient_name": "string or null",
  "currency": "EUR",
  "subtotal": null,
  "vat_amount": null,
  "vat_rate_pct": null,
  "total_amount": 0.0,
  "line_items": [],
  "payment_due_date": "YYYY-MM-DD or null",
  "invoice_number": "string or null",
  "notes": "string or null",
  "confidence": 0.9
}

IMPORTANT: Return ONLY the raw JSON object. No markdown fences, no extra text.
"""


class ImageExtractor(BaseExtractor):
    def __init__(self):
        from services.llm import get_client
        self.client = get_client()
        self.model = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "gpt-4o")

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in IMAGE_EXTENSIONS

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def extract(self, path: Path) -> ExtractedDocument:
        import json
        img_b64 = _encode_image(path)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
            max_tokens=2048,
            temperature=0.1,
        )

        raw = response.choices[0].message.content or "{}"
        data = json.loads(_clean_json(raw))

        return build_document(
            source_file=path.name,
            data=data,
            extraction_model=self.model,
            raw_text_excerpt="[image document]",
            default_confidence=0.85,
        )


def _encode_image(path: Path) -> str:
    with Image.open(path) as img:
        img = img.convert("RGB")
        max_side = 1600
        w, h = img.size
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()
