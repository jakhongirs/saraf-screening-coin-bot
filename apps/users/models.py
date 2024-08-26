from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.managers import SoftDeleteUserManager


class User(AbstractUser, BaseModel):
    first_name = None
    last_name = None
    username = models.CharField(
        _("Username"), max_length=150, unique=True, null=True, blank=True
    )
    full_name = models.CharField(_("Full name"), max_length=32)
    is_deleted = models.BooleanField(_("Is deleted"), default=False)
    email = models.EmailField(_("Email"), unique=True)
    objects = SoftDeleteUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "full_name",
    ]  # type: ignore

    def __str__(self):
        if self.full_name:
            return str(self.full_name)
        if self.email:
            return self.email

    def prepare_to_delete(self):
        self.is_deleted = True
        for x in ["email", "full_name"]:
            if getattr(self, x):
                setattr(self, x, f"DELETED_{self.id}_{getattr(self, x)}")
        self.save()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
