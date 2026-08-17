"""Deterministic bearer identities for authorization testing."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vaipex_api_automation.models import Principal, Role

DEMO_IDENTITIES = {
    "demo-admin-token": Principal(subject="admin-001", role=Role.ADMIN),
    "demo-operator-token": Principal(subject="user-001", role=Role.OPERATOR),
    "demo-other-token": Principal(subject="user-002", role=Role.OPERATOR),
    "demo-viewer-token": Principal(subject="user-003", role=Role.VIEWER),
}

bearer = HTTPBearer(auto_error=False, scheme_name="VaipexDemoBearer")


def authenticate(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal = DEMO_IDENTITIES.get(credentials.credentials)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The bearer token is not recognized.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_admin(principal: Annotated[Principal, Depends(authenticate)]) -> Principal:
    if principal.role is not Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role is required.",
        )
    return principal


def require_writer(principal: Annotated[Principal, Depends(authenticate)]) -> Principal:
    if principal.role is Role.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer role cannot modify orders.",
        )
    return principal
