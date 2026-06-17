from dataclasses import dataclass
from typing import Literal

Role = Literal["admin", "analyst", "service"]

# Common role groupings used to protect endpoints.
ALL_ROLES: tuple[Role, ...] = ("admin", "analyst", "service")
PREDICT_ROLES: tuple[Role, ...] = ("service", "admin")
ADMIN_ROLES: tuple[Role, ...] = ("admin",)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller for a request."""

    identity: str
    role: Role
    auth: Literal["api_key", "jwt"]
