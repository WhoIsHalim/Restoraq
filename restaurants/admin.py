from django.contrib import admin

from restaurants.models import Branch, RestaurantSetting, FloorArea, DiningTable, Reservation


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "code", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("name", "code")


@admin.register(RestaurantSetting)
class RestaurantSettingAdmin(admin.ModelAdmin):
    list_display = ("tenant", "currency")


@admin.register(FloorArea)
class FloorAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "is_active")
    list_filter = ("tenant", "branch", "is_active")
    search_fields = ("name",)


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "capacity", "is_active")
    list_filter = ("tenant", "branch", "is_active")
    search_fields = ("name",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "tenant", "branch", "reservation_time", "status", "party_size")
    list_filter = ("tenant", "branch", "status", "source")
    search_fields = ("customer_name", "customer_phone")
