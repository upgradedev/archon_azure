import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import validate_entra_token

router = APIRouter()

ANALYSIS_ENDPOINT_URL = os.getenv("ANALYSIS_ENDPOINT_URL", "http://analysis:8001")


@router.get("/periods")
async def list_periods(_claims: dict = Depends(validate_entra_token)):
    """List reporting periods that have extracted documents in blob storage."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{ANALYSIS_ENDPOINT_URL}/periods")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc


class AnalyzeRequest(BaseModel):
    period: str


@router.post("/analyze")
async def trigger_analysis(
    req: AnalyzeRequest,
    _claims: dict = Depends(validate_entra_token),
):
    """Trigger the 7-agent analysis pipeline. Validates Entra ID bearer token when present."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{ANALYSIS_ENDPOINT_URL}/analyze",
                json={"period": req.period},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc


@router.get("/documents/{period}")
async def list_documents(
    period: str,
    _claims: dict = Depends(validate_entra_token),
):
    """Return classified extracted documents for a period — used by UI tile drill-down."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{ANALYSIS_ENDPOINT_URL}/documents/{period}")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc


@router.delete("/periods/{period}")
async def delete_period(
    period: str,
    _claims: dict = Depends(validate_entra_token),
):
    """Delete all extracted documents and cached report for a period."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(f"{ANALYSIS_ENDPOINT_URL}/periods/{period}")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc


@router.get("/reports/{period}")
async def get_report(
    period: str,
    _claims: dict = Depends(validate_entra_token),
):
    """Fetch a completed financial report. Validates Entra ID bearer token when present."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.get(f"{ANALYSIS_ENDPOINT_URL}/reports/{period}")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc
