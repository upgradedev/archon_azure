import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import validate_entra_token
from services import storage

router = APIRouter()

ANALYSIS_ENDPOINT_URL = os.getenv("ANALYSIS_ENDPOINT_URL", "http://analysis:8001")


def _profile_blob(claims: dict) -> str:
    """Blob key for this tenant's company profile.

    Uses the Entra tenant ID ('tid') from the validated JWT so that different
    AAD tenants sharing the same deployment each get their own isolated profile.
    Falls back to 'default' when running in unauthenticated dev/demo mode.
    """
    tid = (claims or {}).get("tid") or "default"
    return f"settings/{tid}/company-profile.json"


def _load_profile(claims: dict) -> dict:
    """Load tenant-specific profile from blob; fall back to empty defaults."""
    try:
        return storage.download_json(_profile_blob(claims))
    except Exception:
        return {"company_name": "", "company_tax_id": ""}


async def _proxy(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    """Shared proxy helper — raises HTTPException on 4xx/5xx or network error."""
    try:
        resp = await client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:300]) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Analysis endpoint error: {exc}") from exc


# ── Read-only proxies ─────────────────────────────────────────────────────────

@router.get("/periods")
async def list_periods(_claims: dict = Depends(validate_entra_token)):
    async with httpx.AsyncClient(timeout=30.0) as c:
        return await _proxy(c, "GET", f"{ANALYSIS_ENDPOINT_URL}/periods")


@router.get("/documents/{period}")
async def list_documents(period: str, claims: dict = Depends(validate_entra_token)):
    profile = _load_profile(claims)
    params: dict[str, str] = {}
    if profile.get("company_name"):
        params["company_name"] = profile["company_name"]
    if profile.get("company_tax_id"):
        params["company_tax_id"] = profile["company_tax_id"]
    async with httpx.AsyncClient(timeout=30.0) as c:
        return await _proxy(c, "GET", f"{ANALYSIS_ENDPOINT_URL}/documents/{period}", params=params)


@router.get("/reports/{period}")
async def get_report(period: str, _claims: dict = Depends(validate_entra_token)):
    async with httpx.AsyncClient(timeout=180.0) as c:
        return await _proxy(c, "GET", f"{ANALYSIS_ENDPOINT_URL}/reports/{period}")


@router.delete("/periods/{period}")
async def delete_period(period: str, _claims: dict = Depends(validate_entra_token)):
    async with httpx.AsyncClient(timeout=30.0) as c:
        return await _proxy(c, "DELETE", f"{ANALYSIS_ENDPOINT_URL}/periods/{period}")


# ── Company profile — tenant-scoped ──────────────────────────────────────────

@router.get("/company-profile")
async def get_company_profile(claims: dict = Depends(validate_entra_token)):
    """Return this tenant's company profile.

    Priority:
      1. Tenant-specific blob  settings/{tid}/company-profile.json
      2. Analysis endpoint env-var defaults (COMPANY_NAME / COMPANY_TAX_ID)
    """
    profile = _load_profile(claims)
    if profile["company_name"] or profile["company_tax_id"]:
        return profile
    # Fall back to the analysis endpoint's env-var defaults
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(f"{ANALYSIS_ENDPOINT_URL}/company-profile")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        return {"company_name": "", "company_tax_id": ""}


class CompanyProfileRequest(BaseModel):
    company_name: str
    company_tax_id: str


@router.put("/company-profile")
async def update_company_profile(
    req: CompanyProfileRequest,
    claims: dict = Depends(validate_entra_token),
):
    """Save this tenant's company identity.

    Stored in blob storage keyed by Entra tenant ID so the setting is
    isolated per AAD tenant without requiring a DB migration or redeployment.
    """
    profile = {
        "company_name": req.company_name.strip(),
        "company_tax_id": req.company_tax_id.strip().replace(" ", ""),
    }
    storage.put_json(_profile_blob(claims), profile)
    return profile


# ── Mutating actions — inject tenant profile ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    period: str


@router.post("/analyze")
async def trigger_analysis(
    req: AnalyzeRequest,
    claims: dict = Depends(validate_entra_token),
):
    """Trigger the 7-agent analysis pipeline.

    Loads the tenant-specific company profile and passes it to the analysis
    endpoint so the classifier can identify sales vs purchase invoices without
    requiring a redeployment or env-var change.
    """
    profile = _load_profile(claims)
    body = {
        "period": req.period,
        "company_name": profile["company_name"],
        "company_tax_id": profile["company_tax_id"],
    }
    async with httpx.AsyncClient(timeout=180.0) as c:
        return await _proxy(c, "POST", f"{ANALYSIS_ENDPOINT_URL}/analyze", json=body)


class DocumentUpdateRequest(BaseModel):
    documents: list


@router.put("/documents/{period}")
async def update_documents(
    period: str,
    req: DocumentUpdateRequest,
    _claims: dict = Depends(validate_entra_token),
):
    async with httpx.AsyncClient(timeout=60.0) as c:
        return await _proxy(c, "PUT", f"{ANALYSIS_ENDPOINT_URL}/documents/{period}",
                            json={"documents": req.documents})
