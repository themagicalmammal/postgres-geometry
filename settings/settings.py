"""Django settings for testing with PostgreSQL geometry types."""

import os

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": 5432,
    },
}

SECRET_KEY = os.environ.get("SECRET_KEY")

INSTALLED_APPS = ("postgres_geometry",)
