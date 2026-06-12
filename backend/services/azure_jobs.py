"""
Job runner abstraction — Azure Container Apps Jobs.

Supports Azure Container Apps Jobs in production (via SDK + managed identity)
and a local HTTP extraction service for docker-compose dev.

Switch JOB_RUNNER_BACKEND env var to 'local' for local dev.
"""

import os
import uuid
from datetime import datetime, timezone

import httpx

JOB_RUNNER_BACKEND = os.getenv("JOB_RUNNER_BACKEND", "azure")
EXTRACTION_SERVICE_URL = os.getenv("EXTRACTION_SERVICE_URL", "http://extraction:8002")


def submit_extraction_job(upload_id: str, period: str) -> dict:
    if JOB_RUNNER_BACKEND == "azure":
        return _submit_aca_job(upload_id, period)
    if JOB_RUNNER_BACKEND == "local":
        return _submit_local_job(upload_id, period)
    raise NotImplementedError(f"Job runner '{JOB_RUNNER_BACKEND}' not implemented")


def _submit_aca_job(upload_id: str, period: str) -> dict:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.appcontainers import ContainerAppsAPIClient

    job_name = os.environ["ACA_JOB_NAME"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    execution_name = f"extract-{period}-{uuid.uuid4().hex[:6]}"

    credential = DefaultAzureCredential()
    client = ContainerAppsAPIClient(credential, subscription_id)

    # ACA SDK requires image in template override — read from env var set by Bicep
    extraction_image = os.environ["EXTRACTION_IMAGE"]

    template = {
        "containers": [{
            "name": "archon-extraction",
            "image": extraction_image,
            "env": [
                {"name": "UPLOAD_ID", "value": upload_id},
                {"name": "PERIOD", "value": period},
                {"name": "AZURE_STORAGE_CONNECTION_STRING",
                 "value": os.environ["AZURE_STORAGE_CONNECTION_STRING"]},
                {"name": "AZURE_STORAGE_CONTAINER",
                 "value": os.getenv("AZURE_STORAGE_CONTAINER", "archon")},
                {"name": "AZURE_OPENAI_ENDPOINT",
                 "value": os.environ["AZURE_OPENAI_ENDPOINT"]},
                {"name": "AZURE_OPENAI_API_KEY",
                 "value": os.environ["AZURE_OPENAI_API_KEY"]},
                {"name": "AZURE_OPENAI_API_VERSION",
                 "value": os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")},
                {"name": "AZURE_OPENAI_VISION_DEPLOYMENT",
                 "value": os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "gpt-4o")},
            ],
        }],
    }

    poller = client.jobs.begin_start(
        resource_group_name=resource_group,
        job_name=job_name,
        template=template,
    )
    # timeout=30s: we only need the execution name from the ARM response,
    # not job completion. The actual job runs asynchronously; status is polled separately.
    result = poller.result(timeout=30)

    return {
        "id": result.name if hasattr(result, "name") else execution_name,
        "status": "pending",
        "period": period,
        "documentsCount": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def get_job_status(job_id: str) -> dict:
    if JOB_RUNNER_BACKEND == "azure":
        return _get_aca_job_status(job_id)
    if JOB_RUNNER_BACKEND == "local":
        return _get_local_job_status(job_id)
    raise NotImplementedError(f"Job runner '{JOB_RUNNER_BACKEND}' not implemented")


def _get_aca_job_status(execution_name: str) -> dict:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.appcontainers import ContainerAppsAPIClient

    job_name = os.environ["ACA_JOB_NAME"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

    credential = DefaultAzureCredential()
    client = ContainerAppsAPIClient(credential, subscription_id)

    execution = client.job_execution(
        resource_group_name=resource_group,
        job_name=job_name,
        job_execution_name=execution_name,
    )

    # JobExecution model has status/end_time as direct attributes (not under .properties)
    raw_status = execution.status or "Running"
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
        "completedAt": str(execution.end_time) if execution.end_time else None,
        "errorMessage": None if status != "failed" else f"ACA job status: {raw_status}",
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
