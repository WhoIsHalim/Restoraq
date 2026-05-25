from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied

from featureflags.services import FeatureService


def feature_required(feature_name: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not FeatureService.is_enabled(getattr(request, "tenant", None), feature_name):
                raise PermissionDenied(f"Feature '{feature_name}' is not enabled for your plan")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
