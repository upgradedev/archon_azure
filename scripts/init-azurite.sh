#!/usr/bin/env bash
# Initialize Azurite container for local dev.
# Called automatically by docker compose after Azurite is healthy.

CONN="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"

# Install azure-cli blob extension if needed
pip install azure-storage-blob -q 2>/dev/null || true

python3 - <<'EOF'
import os
from azure.storage.blob import BlobServiceClient

conn = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"
client = BlobServiceClient.from_connection_string(conn)
try:
    client.create_container("archon")
    print("Container 'archon' created")
except Exception:
    print("Container 'archon' already exists")
EOF
