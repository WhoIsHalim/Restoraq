from __future__ import annotations

import os

from django.contrib.auth import get_user_model


def run() -> None:
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin12345")

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists")
        return

    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created")


run()
