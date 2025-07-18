"""Geometry fields for Django."""

from collections.abc import Iterable
import functools
from functools import wraps
import re

from django import forms
from django.core.exceptions import FieldError
from django.db import models


def require_postgres(fn):
    """Ensure the database backend is PostgreSQL or PostGIS."""

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        # Try to find a 'connection' argument either in args or kwargs
        connection = None

        # Check kwargs first
        if "connection" in kwargs:
            connection = kwargs["connection"]
        else:
            # Heuristic: assume first positional argument after self is connection
            if len(args) >= 1:
                connection = args[0]

        if connection is None:
            raise ValueError("No 'connection' argument found to check database engine")

        engine = connection.settings_dict.get("ENGINE", "").lower()
        if not any(db in engine for db in ("postgresql", "postgis", "psycopg2")):
            raise FieldError("Current database is not a PostgreSQL instance")

        return fn(self, *args, **kwargs)

    return wrapper


_FLOAT_RE = r"-?(?:\d+(?:\.\d*)?|\.\d+)"


@functools.total_ordering
class Point:
    """A 2D point with float coordinates."""

    POINT_RE = re.compile(rf"\((?P<x>{_FLOAT_RE}),(?P<y>{_FLOAT_RE})\)")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    @staticmethod
    def from_string(value: str) -> "Point":
        """Parses a string like '(1.0,2.0)' into a Point object."""
        match = Point.POINT_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid point.")
        x = float(match.group("x"))
        y = float(match.group("y"))
        return Point(x, y)

    def __repr__(self) -> str:
        return f"<Point({self.x}, {self.y})>"

    def __str__(self) -> str:
        return f"({self.x},{self.y})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __lt__(self, other) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) < (other.x, other.y)


class Circle:
    """A circle defined by a center point and radius."""

    CIRCLE_RE = re.compile(rf"<\((?P<x>{_FLOAT_RE}),(?P<y>{_FLOAT_RE})\),\s*(?P<r>{_FLOAT_RE})>")

    def __init__(self, *args):
        """Create a Circle.

        - Circle(r): origin (0,0) and radius r
        - Circle(Point, r): center = Point, radius = r
        - Circle(x, y, r): center = (x, y), radius = r
        """
        if len(args) == 1:
            self.center = Point()
            self.radius = float(args[0])
        elif len(args) == 2 and isinstance(args[0], Point):
            self.center = args[0]
            self.radius = float(args[1])
        elif len(args) == 3:
            self.center = Point(float(args[0]), float(args[1]))
            self.radius = float(args[2])
        else:
            raise TypeError(f"Invalid arguments for Circle: {args}")

    @staticmethod
    def from_string(value: str) -> "Circle":
        """Parses a string like '<(x, y), r>' into a Circle object."""
        match = Circle.CIRCLE_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid circle.")

        x = float(match.group("x"))
        y = float(match.group("y"))
        r = float(match.group("r"))
        return Circle(x, y, r)

    def __eq__(self, other) -> bool:
        return isinstance(other, Circle) and self.center == other.center and self.radius == other.radius

    def __repr__(self) -> str:
        return f"<Circle(center={self.center}, radius={self.radius})>"

    def __str__(self) -> str:
        return f"<{self.center}, {self.radius}>"


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


class SegmentPathField(PointMixin, models.Field):
    """Field to store a path; needs at least two points."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "path"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        return super().to_python(value)

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value:
            value = tuple(value)

            if len(value) < 2:
                raise ValueError("Needs at minimum 2 points")

        value = self._get_prep_value(value)
        return f"[{value}]" if value else None

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two or more points as (x1,y1),(x2,y2),...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PolygonField(PointMixin, models.Field):
    """Field to store a polygon; needs at least three points."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "polygon"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        return super().to_python(value)

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value:
            value = tuple(value)
            if len(value) < 3:
                raise ValueError("Needs at minimum 3 points")

        value = self._get_prep_value(value)
        return f"({value})" if value else None

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter three or more points as (x1,y1),(x2,y2),(x3,y3),...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PointField(models.Field):
    """Field to store a single point in space."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "point"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if isinstance(value, Point) or value is None:
            return value
        return Point.from_string(value)

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        return f"({value.x},{value.y})" if value else None

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter a point as (x,y)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class SegmentField(PointMixin, models.Field):
    """Field to store a segment (line segment with exactly two points)."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "lseg"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None:
            return None
        value = super().to_python(value)
        if value and len(value) != 2:
            raise ValueError("Segment needs exactly 2 points")
        return value

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value and len(value) != 2:
            raise ValueError("Segment needs exactly 2 points")
        return self._get_prep_value(value)

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class BoxField(PointMixin, models.Field):
    """Field to store a box, defined by two opposite corner points."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "box"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None:
            return None
        value = super().to_python(value)
        if value and len(value) != 2:
            raise ValueError("Box needs exactly 2 points")
        return value

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value and len(value) != 2:
            raise ValueError("Box needs exactly 2 points")
        return self._get_prep_value(value)

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two opposite corner points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CircleField(models.Field):
    """Custom Django model field to store a PostgreSQL circle."""

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "circle"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None or isinstance(value, Circle):
            return value
        try:
            return Circle.from_string(value)
        except Exception as e:
            raise ValueError(f"Invalid circle value: {value!r}. Error: {e}")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value:
            return f"<({value.center.x},{value.center.y}),{value.radius}>"
        return None

    def get_prep_lookup(self, lookup_type, value):
        """Prepare the value for a lookup operation."""
        raise NotImplementedError(f"Lookup type '{lookup_type}' not implemented.")

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter circle as <(x,y),r>",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
