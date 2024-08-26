from django.contrib import admin

from apps.users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "full_name",
    )
    search_fields = ("email", "full_name")
    ordering = ("created_at",)
    readonly_fields = ("created_at", "updated_at")
