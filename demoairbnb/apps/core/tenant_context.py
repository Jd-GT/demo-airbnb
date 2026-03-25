from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID

_current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)


def set_current_tenant_id(tenant_id: UUID | None) -> Token:
    return _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> UUID | None:
    return _current_tenant_id.get()


def reset_current_tenant_id(token: Token) -> None:
    _current_tenant_id.reset(token)
