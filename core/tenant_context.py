from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_current_tenant_id: ContextVar[Optional[int]] = ContextVar("current_tenant_id", default=None)


def set_current_tenant_id(tenant_id: Optional[int]) -> None:
    _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> Optional[int]:
    return _current_tenant_id.get()


def clear_current_tenant_id() -> None:
    _current_tenant_id.set(None)
