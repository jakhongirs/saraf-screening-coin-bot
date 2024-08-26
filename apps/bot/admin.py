from django.contrib import admin

from apps.bot.models import Coin


@admin.register(Coin)
class CoinAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "symbol",
        "status",
    )
    search_fields = ("name", "symbol")
