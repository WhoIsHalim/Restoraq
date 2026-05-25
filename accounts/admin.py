from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Preferences", {"fields": ("phone", "preferred_language", "is_system_owner")}),)
    list_display = ("username", "email", "is_staff", "is_system_owner")
