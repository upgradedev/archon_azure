"""
Job runner abstraction — Azure Container Apps Jobs.

Supports Azure Container Apps Jobs in production.
Switch JOB_RUNNER_BACKEND env var to 'local' for docker-compose dev.

Azure Container Apps Jobs reference:
  https://learn.microsoft.com/en-us/azure/container-apps/jobs
"""

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone

import httpx

JOB_RUNNER_BACKEND = os.getenv("JOB_RUNNER_BACKEND", "azure")
EXTRACTION_SERVICE_URL = os.getenv("EXTRACTION_SERVICE_URL", "http://extraction:8002")


def submit_extraction_job(upload_id: str, period: str) -> dict:
    """Submit a document extraction job and return job metadata."""
    if JOB_RUNNER_BACKEND == "azure":
        return _submit_aca_job(upload_id, period)
    if JOB_RUNNER_BACKEND == "local":
        return _submit_local_job(upload_id, period)
    raise NotImplementedError(f"Job runner '{JOB_RUNNER_BACKEND}' not implemented")


def _submit_aca_job(upload_id: str, period: str) -> dict:
    """Start an Azure Container Apps Job execution."""
    job_name = os.environ["ACA_EXTRACTION_JOB_NAME"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    execution_name = f"extract-{period}-{uuid.uuid4().hex[:6]}"

    env_vars = " ".join([
        f"UPLOAD_ID={upload_id}",
        f"PERIOD={period}",
        f"AZURE_STORAGE_CONNECTION_STRING={os.environ['AZURE_STORAGE_CONNECTION_STRING']}",
        f"AZURE_STORAGE_CONTAINER={os.getenv('AZURE_STORAGE_CONTAINER', 'archon')}",
        f"AZURE_OPENAI_ENDPOINT={os.environ['AZURE_OPENAI_ENDPOINT']}",
        f"AZURE_OPENAI_API_KEY={os.environ['AZURE_OPENAI_API_KEY']}",
        f"AZURE_OPENAI_API_VERSION={os.getenv('AZURE_OPENAI_API_VERSION', '2024-05-01-preview')}",
        f"AZURE_OPENAI_VISION_DEPLOYMENT={os.getenv('AZURE_OPENAI_VISION_DEPLOYMENT', 'gpt-4o')}",
    ])

    cmd = [
        "az", "containerapp", "job", "start",
        "--name", job_name,
        "--resource-group", resource_group,
        "--env-vars", env_vars,
        "--output", "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    aca_response = json.loads(result.stdout)

    return {
        "id": aca_response.get("name", execution_name),
        "status": "pending",
        "period": period,
        "documentsCount": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def _submit_local_job(upload_id: str, period: str) -> dict:
    resp = httpx.post(
        f"{EXTRACTION_SERVICE_URL}/extract",
        json={"upload_id": upload_id, "period": period},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "id": data["jobId"],
        "status": "running",
        "period": period,
        "documentsCount": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def get_job_status(job_id: str) -> dict:
    """Poll job status from the underlying runner."""
    if JOB_RUNNER_BACKEND == "azure":
        return _get_aca_job_status(job_id)
    if JOB_RUNNER_BACKEND == "local":
        return _get_local_job_status(job_id)
    raise NotImplementedError(f"Job runner '{JOB_RUNNER_BACKEND}' not implemented")


def _get_aca_job_status(execution_name: str) -> dict:
    job_name = os.environ["ACA_EXTRACTION_JOB_NAME"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]

    cmd = [
        "az", "containerapp", "job", "execution", "show",
        "--name", job_name,
        "--resource-group", resource_group,
        "--job-execution-name", execution_name,
        "--output", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    aca_exec = json.loads(result.stdout)

    # Map ACA execution statuses → Archon statuses
    raw_status = aca_exec.get("properties", {}).get("status", "Running")
    status_map = {
        "Running": "running",
        "Succeeded": "completed",
        "Failed": "failed",
        "Stopped": "failed",
        "Degraded": "failed",
        "Processing": "pending",
    }
    status = status_map.get(raw_status, "pending")

    return {
        "id": execution_name,
        "status": status,
        "progress": 100 if status == "completed" else (60 if status == "running" else 10),
        "completedAt": aca_exec.get("properties", {}).get("endTime"),
        "errorMessage": None if status != "failed" else f"ACA job status: {raw_status}",
    }


def _get_local_job_status(job_id: str) -> dict:
    resp = httpx.get(f"{EXTRACTION_SERVICE_URL}/jobs/{job_id}", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    status_map = {"running": "running", "completed": "completed", "failed": "failed"}
    status = status_map.get(data["status"], "pending")
    return {
        "id": job_id,
        "status": status,
        "progress": 100 if status == "completed" else 50,
        "completedAt": data.get("completed_at"),
        "errorMessage": data.get("error") if status == "failed" else None,
    }
