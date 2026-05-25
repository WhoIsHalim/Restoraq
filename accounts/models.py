from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=32, blank=True)
    preferred_language = models.CharField(max_length=8, default="ar")
    is_system_owner = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.username
