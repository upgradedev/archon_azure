"""Entra ID (Azure AD) bearer token validation for Archon API.

When REQUIRE_AUTH=true, endpoints reject requests without a valid Entra ID JWT.
When REQUIRE_AUTH=false (default), a present token is validated but absence is allowed —
allowing the Playwright demo and e2e tests to call without auth while Teams/M365 Copilot
passes the user's Entra ID token and gets it validated.
"""
import logging
import os
import time

import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger("archon.auth")

TENANT_ID = os.getenv("ENTRA_TENANT_ID", "2bcb5033-94ea-4823-aa9d-c945549e3a8a")
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if time.time() - _jwks_fetched_at < _JWKS_TTL and _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


async def validate_entra_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict:
    """FastAPI dependency — validates an Entra ID bearer token.

    Returns the decoded JWT claims on success, or {} when no token is present
    and REQUIRE_AUTH=false. Raises 401 for invalid or expired tokens.
    """
    if not credentials:
        if REQUIRE_AUTH:
            raise HTTPException(status_code=401, detail="Authorization header required")
        return {}

    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        header = jwt.get_unverified_header(token)
        signing_key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == header.get("kid"):
                signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break

        if signing_key is None:
            raise HTTPException(status_code=401, detail="Token signing key not found in Azure AD JWKS")

        claims = jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},
        )
        log.info("Authenticated: oid=%s upn=%s", claims.get("oid"), claims.get("preferred_username"))
        return claims

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Token issuer does not match Archon tenant")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
