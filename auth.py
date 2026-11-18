import json
import os
import urllib.error
import urllib.request
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
security = HTTPBearer(auto_error=False)


def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validates a Bearer token against basic_backend's /users/me endpoint.
    Fails closed (401) if the header is missing, invalid, or the backend rejects it.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required",
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token",
        )

    req = urllib.request.Request(
        f"{BACKEND_URL}/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )
            return json.loads(resp.read().decode("utf-8"))
    except HTTPException:
        raise
    except urllib.error.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc


def require_admin(user: dict = Depends(get_current_user_info)) -> dict:
    """Requires the authenticated user to be a global admin."""
    is_admin = bool(
        user.get("is_admin")
        or user.get("is_superuser")
        or user.get("role") == "admin"
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def verify_team_member_or_admin(team_id: int, user: dict) -> None:
    """Ensures the authenticated user is a global admin or belongs to team_id."""
    if bool(user.get("is_admin") or user.get("is_superuser")):
        return
    user_team_ids = {t.get("id") for t in (user.get("teams") or []) if isinstance(t, dict)}
    if team_id not in user_team_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team membership or admin privileges required",
        )
