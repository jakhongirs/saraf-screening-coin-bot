from django.contrib import admin

from apps.bot.models import AllowedUser, Coin, EarningsData, Symbol


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


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "shariah_status")
    search_fields = ("symbol", "name")
    list_filter = ("shariah_status",)


@admin.register(EarningsData)
class EarningsDataAdmin(admin.ModelAdmin):
    list_display = ("date", "symbol", "time")
