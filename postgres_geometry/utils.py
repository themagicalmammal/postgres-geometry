"""Utility functions for postgres_geometry."""

from collections.abc import Iterable
from functools import wraps
import re

from django.core.exceptions import FieldError

from .types import Point


def require_postgres(fn):
    """Ensure the database backend is PostgreSQL or PostGIS."""

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        connection = kwargs.get("connection") or (args[0] if args else None)
        if connection is None:
            raise ValueError("No 'connection' argument found to check database engine")

        engine = connection.settings_dict.get("ENGINE", "").lower()
        if not any(db in engine for db in ("postgresql", "postgis", "psycopg2")):
            raise FieldError("Current database is not a PostgreSQL instance")

        return fn(self, *args, **kwargs)

    return wrapper


class PointMixin:
    """Mixin for fields that store multiple points."""

    SPLIT_RE = re.compile(r"\((?!\().*?\)")

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None:
            return None

        if isinstance(value, str):
            value = re.findall(self.SPLIT_RE, value)

        if not isinstance(value, Iterable):
            raise TypeError(f"Value {value} is not iterable")

        if all(isinstance(v, Point) for v in value):
            return list(value)

        return [Point.from_string(v) for v in value]

    def _get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        return ",".join(str(v) for v in value) if value else None

