"""JWT validation. Demo auth only runs when explicitly configured."""
import asyncio
from functools import lru_cache
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import get_settings

bearer = HTTPBearer(auto_error=False)


@lru_cache
def jwks_client(tenant_id: str):
    return PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    settings = get_settings()
    if settings.auth_mode == "demo":
        return {"user_id": "demo-user", "tenant_id": "demo", "groups": []}
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    try:
        key = await asyncio.to_thread(jwks_client(settings.entra_tenant_id).get_signing_key_from_jwt, token)
        claims = jwt.decode(
            token, key.key, algorithms=["RS256"],
            audience=settings.entra_api_audience,
            issuer=f"https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0",
            options={"require": ["exp", "iat", "iss", "aud", "tid", "oid"]},
            leeway=30,
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(401, "Invalid access token", headers={"WWW-Authenticate": "Bearer"}) from exc
    scopes = set(claims.get("scp", "").split())
    if settings.entra_required_scope not in scopes:
        raise HTTPException(403, "Delegated API scope required")
    if claims["tid"] != settings.entra_tenant_id:
        raise HTTPException(403, "Tenant not authorized")
    return {"user_id": claims["oid"], "tenant_id": claims["tid"], "groups": []}
