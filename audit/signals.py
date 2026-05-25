from __future__ import annotations

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from audit.services import AuditService
from users.models import TenantMembership


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    membership = TenantMembership.objects.filter(user=user, is_active=True).select_related("tenant", "primary_branch").first()
    if not membership:
        return
    AuditService.log_action(
        request=request,
        tenant=membership.tenant,
        branch=membership.primary_branch,
        user=user,
        action="login",
        model="accounts.User",
        object_id=str(user.id),
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", "") if credentials else ""
    membership = (
        TenantMembership.objects.filter(user__username=username, is_active=True)
        .select_related("tenant", "primary_branch", "user")
        .first()
    )
    if not membership:
        return
    AuditService.log_action(
        request=request,
        tenant=membership.tenant,
        branch=membership.primary_branch,
        user=membership.user,
        action="login_failed",
        model="accounts.User",
        object_id=str(membership.user_id),
        metadata={"username": username},
    )
