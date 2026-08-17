"""Named client identities for repeatable authorization scenarios."""

from enum import StrEnum


class IdentityProfile(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    OTHER_OPERATOR = "other-operator"
    VIEWER = "viewer"
    ANONYMOUS = "anonymous"


DEMO_TOKENS = {
    IdentityProfile.ADMIN: "demo-admin-token",
    IdentityProfile.OPERATOR: "demo-operator-token",
    IdentityProfile.OTHER_OPERATOR: "demo-other-token",
    IdentityProfile.VIEWER: "demo-viewer-token",
}


def authorization_headers(identity: IdentityProfile) -> dict[str, str]:
    token = DEMO_TOKENS.get(identity)
    return {} if token is None else {"Authorization": f"Bearer {token}"}
