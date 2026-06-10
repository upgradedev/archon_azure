"""
Azure Blob Storage service.

Used by the backend orchestrator to upload raw documents, read extracted
results, and cache analysis reports.

Local dev: connects to Azurite via AZURE_STORAGE_CONNECTION_STRING.
Production: connects to Azure Blob Storage via the same env var.
"""

import json
import os

from azure.storage.blob import BlobServiceClient, ContentSettings


def _client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )


CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "archon")


def _ensure_container() -> None:
    container = _client().get_container_client(CONTAINER)
    try:
        container.create_container()
    except Exception:
        pass  # already exists


def upload_file(blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    _ensure_container()
    client = _client()
    blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
    blob.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob_name


def download_json(blob_name: str) -> dict:
    client = _client()
    blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
    data = blob.download_blob().readall()
    return json.loads(data)


def list_keys(prefix: str) -> list[str]:
    container = _client().get_container_client(CONTAINER)
    return [b.name for b in container.list_blobs(name_starts_with=prefix)]


def put_json(blob_name: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, indent=2).encode()
    return upload_file(blob_name, body, "application/json")
