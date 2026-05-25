from __future__ import annotations

from datetime import timedelta

from core.constants import ROLE_CASHIER


def get_user_session_timeout(user) -> timedelta:
    if user.groups.filter(name=ROLE_CASHIER).exists():
        return timedelta(hours=8)
    return timedelta(hours=4)
