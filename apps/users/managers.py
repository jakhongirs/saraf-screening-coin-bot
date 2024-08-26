from django.contrib.auth.models import UserManager as djUserManager
from django.db.models import QuerySet


class UserManager(djUserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        return super().create_user(
            username=username, email=email, password=password, **extra_fields
        )

    def create_superuser(
            self, username=None, email=None, password=None, **extra_fields
    ):
        return super().create_superuser(
            username=username, email=email, password=password, **extra_fields
        )

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class SoftDeleteUserManager(UserManager):
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(is_deleted=False)
