from django.contrib import admin

from apps.bot.models import AllowedUser, Coin


@admin.register(Coin)
class CoinAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "symbol",
        "status",
    )
    search_fields = ("name", "symbol")


@admin.register(AllowedUser)
class AllowedUserAdmin(admin.ModelAdmin):
    list_display = ("username",)
    search_fields = ("username",)
