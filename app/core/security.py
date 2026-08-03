"""
Minimal shared-secret auth between the front end and this API.

For a real deployment, replace with OAuth2/JWT (e.g. via your clinic's
identity provider) — this is intentionally simple so the auth layer can be
swapped without touching business logic.
"""
from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
