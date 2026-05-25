from __future__ import annotations

from django.conf import settings
from django.utils.translation import get_language

from core.navigation import build_workspace_nav
from core.constants import BRANCH_SCOPED_ROLES
from core.policies import AccessPolicy
from featureflags.services import FeatureService


def layout_context(request):
    language = (get_language() or "ar").split("-")[0]
    tenant = getattr(request, "tenant", None)
    is_system_user = AccessPolicy.is_system_user(getattr(request, "user", None))
    system_path = f"/{str(getattr(settings, 'SYSTEM_PATH', 'system/')).strip('/')}/"
    admin_path = f"/{str(getattr(settings, 'ADMIN_PATH', 'admin/')).strip('/')}/"
    permitted_branches = []
    active_branch = None
    if tenant:
        permitted_branches = list(AccessPolicy.permitted_branches(request, tenant=tenant))
        membership = getattr(request, "membership", None)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES:
            active_branch = membership.primary_branch if membership.primary_branch_id else None
        else:
            session_branch_id = request.session.get("active_branch_id")
            active_branch = next((b for b in permitted_branches if str(b.id) == str(session_branch_id)), None)
            if not active_branch and permitted_branches:
                active_branch = permitted_branches[0]
                request.session["active_branch_id"] = active_branch.id

    return {
        "active_language": language,
        "text_direction": "rtl" if language.startswith("ar") else "ltr",
        "active_tenant": tenant,
        "permitted_branches": permitted_branches,
        "active_branch": active_branch,
        "is_system_user": is_system_user,
        "system_path": system_path,
        "admin_path": admin_path,
        "is_system_path": bool(request.path.startswith(system_path)),
        "kds_enabled": FeatureService.is_enabled(tenant, "kds_screen") if tenant else False,
        "hr_enabled": FeatureService.is_enabled(tenant, "hr_module") if tenant else False,
        "accounting_enabled": FeatureService.is_enabled(tenant, "accounting_module") if tenant else False,
        "workspace_nav": build_workspace_nav(request, language),
    }
