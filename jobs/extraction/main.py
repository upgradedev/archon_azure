"""
Archon — Document Extraction Job (Azure)
Runs as an Azure Container Apps Job (batch, on-demand).

Pipeline (single-responsibility agents in sequence):
  1. ExtractorAgent  — auto-detect file type, call GPT-4o vision/text, produce ExtractedDocument
  2. ClassifierAgent — rule-based refinement of doc_type (no LLM, deterministic)
  3. EventLinkerAgent — group payroll docs into unified PayrollEvents
  4. ValidatorAgent  — cross-document consistency rules, produce ValidationResults

Reads from Azure Blob Storage:
  raw-docs/{period}/{upload_id}/*

Outputs written to Azure Blob Storage:
  extracted/{period}/{upload_id}/documents.json
  extracted/{period}/{upload_id}/events.json
  extracted/{period}/{upload_id}/validation.json
"""

import json
import logging
import os
import tempfile
from pathlib import Path

from azure.storage.blob import BlobServiceClient

from agents import classifier, event_linker, validator
from extractors.image import ImageExtractor
from extractors.pdf import PdfExtractor
from extractors.docx import DocxExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("archon.extraction")

UPLOAD_ID = os.environ["UPLOAD_ID"]
PERIOD = os.environ["PERIOD"]
CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "archon")

EXTRACTORS = [PdfExtractor(), DocxExtractor(), ImageExtractor()]


# ── Azure Blob helpers ────────────────────────────────────────────────────────

def _blob_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )


def _list_raw_blobs() -> list[str]:
    prefix = f"raw-docs/{PERIOD}/{UPLOAD_ID}/"
    container = _blob_client().get_container_client(CONTAINER)
    return [
        b.name for b in container.list_blobs(name_starts_with=prefix)
        if not b.name.endswith("manifest.json")
    ]


def _download(blob_name: str, dest: Path) -> None:
    client = _blob_client()
    blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
    with open(dest, "wb") as f:
        f.write(blob.download_blob().readall())


def _put_json(blob_name: str, data: object) -> None:
    body = json.dumps(data, ensure_ascii=False, indent=2).encode()
    client = _blob_client()
    blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
    blob.upload_blob(body, overwrite=True, content_settings=None)


# ── extractor step ────────────────────────────────────────────────────────────

def _extract_blob(blob_name: str) -> dict | None:
    filename = blob_name.split("/")[-1]
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _download(blob_name, tmp_path)
        extractor = next((e for e in EXTRACTORS if e.can_handle(tmp_path)), None)
        if extractor is None:
            log.warning("No extractor for %s — skipping", filename)
            return None
        log.info("Extracting %s with %s", filename, type(extractor).__name__)
        doc = extractor.extract(tmp_path)
        return doc.model_dump()
    except Exception as exc:
        log.error("Failed to extract %s: %s", filename, exc)
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


# ── main pipeline ─────────────────────────────────────────────────────────────

def main():
    log.info("=== Extraction job start — upload=%s period=%s ===", UPLOAD_ID, PERIOD)

    # Step 1: extract raw blobs
    raw_blobs = _list_raw_blobs()
    log.info("Found %d blobs to process", len(raw_blobs))
    raw_docs = [r for b in raw_blobs if (r := _extract_blob(b)) is not None]
    log.info("Extracted %d documents", len(raw_docs))

    from models.document import ExtractedDocument
    typed_docs = []
    for d in raw_docs:
        try:
            typed_docs.append(ExtractedDocument(**d))
        except Exception as exc:
            log.warning("Skipping malformed extraction result: %s", exc)

    # Step 2: classify
    typed_docs = classifier.run(typed_docs)
    log.info("Classification complete")

    # Step 3: link payroll events
    events = event_linker.run(typed_docs)
    log.info("Linked %d payroll events", len(events))

    # Step 4: validate
    validation_results = validator.run(events)
    errors = sum(1 for r in validation_results if not r.passed and r.severity == "error")
    log.info("Validation: %d results, %d errors", len(validation_results), errors)

    base = f"extracted/{PERIOD}/{UPLOAD_ID}"

    _put_json(f"{base}/documents.json", {
        "period": PERIOD,
        "upload_id": UPLOAD_ID,
        "documents": [d.model_dump() for d in typed_docs],
    })

    _put_json(f"{base}/events.json", {
        "period": PERIOD,
        "upload_id": UPLOAD_ID,
        "events": [e.model_dump() for e in events],
    })

    _put_json(f"{base}/validation.json", {
        "period": PERIOD,
        "upload_id": UPLOAD_ID,
        "results": [r.model_dump() for r in validation_results],
        "summary": {
            "total": len(validation_results),
            "passed": sum(1 for r in validation_results if r.passed),
            "errors": errors,
            "warnings": sum(1 for r in validation_results if not r.passed and r.severity == "warning"),
        },
    })

    log.info("=== Extraction job complete — %d docs, %d events ===", len(typed_docs), len(events))


if __name__ == "__main__":
    main()
