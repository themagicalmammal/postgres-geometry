"""Utility functions for postgres_geometry."""

from collections.abc import Iterable
import functools
from functools import wraps
import re

from django.core.exceptions import FieldError


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


_FLOAT_RE = r"-?(?:\d+(?:\.\d*)?|\.\d+)"


@functools.total_ordering
class Point:
    """A 2D point with float coordinates."""

    POINT_RE = re.compile(rf"\(\s*(?P<x>{_FLOAT_RE})\s*,\s*(?P<y>{_FLOAT_RE})\s*\)")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    @staticmethod
    def from_string(value: str) -> "Point":
        """Parses a string like '(1.0,2.0)' into a Point object."""
        match = Point.POINT_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid point.")
        return Point(float(match.group("x")), float(match.group("y")))

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
