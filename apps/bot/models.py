from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


# Crypto Coin Models
class CoinStatusChoices(models.TextChoices):
    compliant = "compliant", _("Compliant")  # Translation in uzbek: Joiz
    not_screened_yet = "not_screened_yet", _("Not screened yet")  # Tekshirilmagan
    non_compliant = "non_compliant", _("Non compliant")  # Joiz emas
    doubtful = "doubtful", _("Doubtful")  # Shubhali


class Coin(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    symbol = models.CharField(_("Symbol"), max_length=255)
    status = models.CharField(
        max_length=20,
        choices=CoinStatusChoices.choices,
        default=CoinStatusChoices.not_screened_yet,
    )
    logo = models.ImageField(_("Logo"), upload_to="coin_logos/", null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Coin")
        verbose_name_plural = _("Coins")


class AllowedUser(models.Model):
    username = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = _("Allowed User")
        verbose_name_plural = _("Allowed Users")


# Stock Market Models
class Symbol(models.Model):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    QUESTIONABLE = "QUESTIONABLE"
    UNKNOWN = "UNKNOWN"

    STATUS_CHOICES = [
        (COMPLIANT, "COMPLIANT"),
        (NON_COMPLIANT, "NON_COMPLIANT"),
        (QUESTIONABLE, "QUESTIONABLE"),
        (UNKNOWN, "UNKNOWN"),
    ]

    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    shariah_status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default=UNKNOWN
    )

    def __str__(self):
        return self.symbol

    class Meta:
        verbose_name = _("Symbol")
        verbose_name_plural = _("Symbols")


class EarningsData(models.Model):
    TIME_PRE_MARKET = "time-pre-market"
    TIME_NOT_SUPPLIED = "time-not-supplied"
    TIME_AFTER_HOURS = "time-after-hours"

    TIME_CHOICES = [
        (TIME_PRE_MARKET, "Pre Market"),
        (TIME_NOT_SUPPLIED, "Not Supplied"),
        (TIME_AFTER_HOURS, "After Hours"),
    ]

    date = models.DateField()
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    time = models.CharField(
        max_length=50, choices=TIME_CHOICES, default=TIME_NOT_SUPPLIED
    )

    class Meta:
        unique_together = ("date", "symbol")
