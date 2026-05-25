from __future__ import annotations

from typing import Any

from django.core.cache import cache

from featureflags.models import FeatureCatalog, PlanFeature, TenantFeatureOverride


class FeatureService:
    CACHE_TTL = 60

    @classmethod
    def _key(cls, tenant_id: int, feature_name: str) -> str:
        return f"feature:{tenant_id}:{feature_name}"

    @classmethod
    def resolve(cls, tenant, feature_name: str, default: Any = False) -> Any:
        if tenant is None:
            return default

        feature = FeatureCatalog.objects.filter(name=feature_name).first()
        if not feature:
            return default

        key = cls._key(tenant.id, feature_name)

        # Always prefer explicit tenant override to avoid stale plan-cache values.
        override = TenantFeatureOverride.objects.filter(tenant=tenant, feature=feature).first()
        if override:
            value = override.value_json.get("value", override.enabled)
            cache.set(key, value, cls.CACHE_TTL)
            return value

        cached = cache.get(key)
        if cached is not None:
            return cached

        plan = getattr(getattr(tenant, "subscription", None), "plan", None)
        if not plan:
            return default

        mapping = PlanFeature.objects.filter(plan=plan, feature=feature).first()
        if not mapping:
            return default

        value = mapping.value_json.get("value", mapping.enabled)
        cache.set(key, value, cls.CACHE_TTL)
        return value

    @classmethod
    def is_enabled(cls, tenant, feature_name: str) -> bool:
        value = cls.resolve(tenant, feature_name, default=False)
        return bool(value)
