"""
PDF extractor.

Strategy:
  1. Try pdfplumber for digital (text-layer) PDFs.
  2. If text yield is too low (scanned), convert pages to images
     and delegate to ImageExtractor.
"""

import json
import tempfile
from pathlib import Path

import pdfplumber
import fitz  # PyMuPDF
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseExtractor
from .image import ImageExtractor, EXTRACTION_PROMPT
from .utils import build_document, _clean_json
from models.document import ExtractedDocument

MIN_TEXT_CHARS = 80


class PdfExtractor(BaseExtractor):
    def __init__(self):
        from services.llm import get_client
        self.image_extractor = ImageExtractor()
        self.client = get_client()
        self.model_name = __import__("os").getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "gpt-4o")

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def extract(self, path: Path) -> ExtractedDocument:
        text = _extract_text(path)
        if len(text.strip()) >= MIN_TEXT_CHARS:
            return self._extract_from_text(path, text)
        return self._extract_via_vision(path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _extract_from_text(self, path: Path, text: str) -> ExtractedDocument:
        prompt = (
            "You are a financial document extraction specialist.\n"
            "Extract from the following document text (may be Greek or English).\n\n"
            f"DOCUMENT TEXT:\n{text[:4000]}\n\n"
            + EXTRACTION_PROMPT
        )
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(_clean_json(raw))
        return build_document(
            source_file=path.name,
            data=data,
            extraction_model=self.model_name,
            raw_text_excerpt=text[:500],
            default_confidence=0.9,
        )

    def _extract_via_vision(self, path: Path) -> ExtractedDocument:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            doc = fitz.open(str(path))
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            pix.save(str(tmp_path))
            result = self.image_extractor.extract(tmp_path)
            result.source_file = path.name
            return result
        finally:
            tmp_path.unlink(missing_ok=True)


def _extract_text(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:5]:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)
