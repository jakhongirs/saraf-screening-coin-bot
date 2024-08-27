from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class CoinStatusChoices(models.TextChoices):
    compliant = "compliant", _("Compliant")
    not_screened_yet = "not_screened_yet", _("Not screened yet")
    non_compliant = "non_compliant", _("Non compliant")
    doubtful = "doubtful", _("Doubtful")


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
