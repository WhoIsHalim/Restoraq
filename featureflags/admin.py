from django.contrib import admin

from featureflags.models import FeatureCatalog, PlanFeature, TenantFeatureOverride


@admin.register(FeatureCatalog)
class FeatureCatalogAdmin(admin.ModelAdmin):
    list_display = ("name", "value_type")
    search_fields = ("name",)


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("plan", "feature", "enabled")
    list_filter = ("plan", "enabled")


@admin.register(TenantFeatureOverride)
class TenantFeatureOverrideAdmin(admin.ModelAdmin):
    list_display = ("tenant", "feature", "enabled")
    list_filter = ("tenant", "enabled")
