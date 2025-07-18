"""Geometry fields for Django."""

import re

from django import forms
from django.db import models

from .types import Circle, Line, Point
from .utils import PointMixin, require_postgres


class PointField(models.Field):
    """Field to store a single point in space.

    Name = 'point'
    Storage Size = 16 bytes
    Description = Point on a plane
    Representation = (x,y)
    """

    description = "Point on a plane"

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "point"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None or isinstance(value, Point):
            return value
        if isinstance(value, tuple | list) and len(value) == 2:
            return Point(value[0], value[1])
        if isinstance(value, str):
            return Point.from_string(value)
        raise TypeError(f"Cannot convert {value!r} to Point.")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, Point):
            value = self.to_python(value)
        return f"({value.x},{value.y})"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter a point as (x,y)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class LineField(models.Field):
    """Field to store an infinite line defined by coefficients A, B, C.

    Name = 'line'
    Storage Size = 24 bytes
    Description = Infinite line
    Representation = {A,B,C}
    """

    description = "Infinite line"

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "line"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a Line object."""
        if value is None or isinstance(value, Line):
            return value

        if isinstance(value, str):
            try:
                return Line.from_string(value)
            except ValueError as e:
                raise ValueError(f"Invalid line string: {value}. Error: {e}")

        # Accept tuple/list of 3 floats/ints
        if isinstance(value, tuple | list) and len(value) == 3:
            try:
                return Line(*value)
            except Exception as e:
                raise ValueError(f"Invalid line coefficients: {value}. Error: {e}")

        raise ValueError(f"Cannot convert {value!r} to Line.")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, Line):
            # Try to convert tuple/list to Line
            if isinstance(value, tuple | list) and len(value) == 3:
                value = Line(*value)
            else:
                raise ValueError(f"Cannot prepare value {value!r} as Line")

        return str(value)  # Will output as "{A,B,C}"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter line as {A,B,C} representing Ax + By + C = 0",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class LineSegmentField(PointMixin, models.Field):
    """Field to store a segment (line segment with exactly two points).

    Name = 'lseg'
    Storage Size = 32 bytes
    Description = Finite line segment
    Representation = [(x1,y1),(x2,y2)]
    """

    description = "Finite line segment"

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

        if isinstance(value, list) and all(isinstance(p, Point) for p in value):
            if len(value) != 2:
                raise ValueError("Segment needs exactly 2 points")
            return value

        # Accept tuple of tuples, like ((x1,y1),(x2,y2))
        if isinstance(value, list | tuple) and len(value) == 2:
            try:
                return [Point(*value[0]), Point(*value[1])]
            except Exception:
                pass  # fallback to string parsing

        # Parse string: [(1,2),(3,4)]
        segment_re = re.compile(r"\(\s*(-?\d+(?:\.\d*)?)\s*,\s*(-?\d+(?:\.\d*)?)\s*\)")
        matches = segment_re.findall(value) if isinstance(value, str) else []
        if len(matches) == 2:
            return [Point(float(x), float(y)) for x, y in matches]

        raise ValueError(f"Cannot parse line segment from value: {value!r}")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Segment needs exactly 2 points")

        points = []
        for pt in value:
            if not isinstance(pt, Point):
                pt = Point(*pt)  # convert tuple to Point
            points.append(f"({pt.x},{pt.y})")
        return f"[{','.join(points)}]"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter exactly two points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class BoxField(PointMixin, models.Field):
    """Field to store a box, defined by two opposite corner points.

    Name = 'box'
    Storage Size = 32 bytes
    Description = Rectangular box
    Representation = (x1,y1),(x2,y2)
    """

    description = "Rectangular box"

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

        if isinstance(value, list) and all(isinstance(p, Point) for p in value):
            if len(value) != 2:
                raise ValueError("Box needs exactly 2 points")
            return value

        if isinstance(value, list | tuple) and len(value) == 2:
            try:
                return [Point(*value[0]), Point(*value[1])]
            except Exception:
                pass

        # Parse string like: (1,2),(3,4)
        point_re = re.compile(r"\(\s*(-?\d+(?:\.\d*)?)\s*,\s*(-?\d+(?:\.\d*)?)\s*\)")
        matches = point_re.findall(value) if isinstance(value, str) else []
        if len(matches) == 2:
            return [Point(float(x), float(y)) for x, y in matches]

        raise ValueError(f"Cannot parse box from value: {value!r}")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Box needs exactly 2 points")

        points = []
        for pt in value:
            if not isinstance(pt, Point):
                pt = Point(*pt)
            points.append(f"({pt.x},{pt.y})")
        return f"{','.join(points)}"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two opposite corner points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class PathField(PointMixin, models.Field):
    """Field to store a path; needs at least two points.

    Name = 'path'
    Storage Size = 16+16n bytes
    Description = Closed path (similar to polygon)/ Open path
    Representation = [(x1,y1),...]
    """

    description = "Closed path (similar to polygon)/ Open path"

    def __init__(self, *args, closed=False, **kwargs):
        self.closed = closed
        super().__init__(*args, **kwargs)

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "path"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None:
            return None

        if isinstance(value, list) and all(isinstance(p, Point) for p in value):
            if len(value) < 2:
                raise ValueError("Path requires at least 2 points")
            return value

        # Handle list/tuple of tuples
        if isinstance(value, list | tuple) and all(isinstance(p, list | tuple) for p in value):
            if len(value) < 2:
                raise ValueError("Path requires at least 2 points")
            return [Point(*pt) for pt in value]

        # Parse string input like [(1,2),(3,4)] or ((1,2),(3,4))
        point_re = re.compile(r"\(\s*(-?\d+(?:\.\d*)?)\s*,\s*(-?\d+(?:\.\d*)?)\s*\)")
        matches = point_re.findall(value) if isinstance(value, str) else []
        if len(matches) >= 2:
            return [Point(float(x), float(y)) for x, y in matches]

        raise ValueError(f"Cannot parse path from value: {value!r}")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, list | tuple) or len(value) < 2:
            raise ValueError("Needs at minimum 2 points")

        points = []
        for pt in value:
            if not isinstance(pt, Point):
                pt = Point(*pt)
            points.append(f"({pt.x},{pt.y})")

        open_bracket = "(" if self.closed else "["
        close_bracket = ")" if self.closed else "]"
        return f"{open_bracket}{','.join(points)}{close_bracket}"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two or more points as (x1,y1),(x2,y2),...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        if self.closed:
            kwargs["closed"] = self.closed
        return name, path, args, kwargs


class PolygonField(PointMixin, models.Field):
    """Field to store a polygon, needs at least three points.

    Name = 'polygon'
    Storage Size = 40+16n bytes
    Description = Polygon (similar to closed path)
    Representation = ((x1,y1),...)
    """

    description = "Polygon (similar to closed path)"

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "polygon"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a list of Point objects."""
        if value is None:
            return None

        # Already parsed
        if isinstance(value, list) and all(isinstance(p, Point) for p in value):
            if len(value) < 3:
                raise ValueError("Polygon requires at least 3 points")
            return value

        # From list of tuples
        if isinstance(value, list | tuple) and all(isinstance(p, list | tuple) for p in value):
            if len(value) < 3:
                raise ValueError("Polygon requires at least 3 points")
            return [Point(*pt) for pt in value]

        # From string input like ((1,2),(3,4),(5,6))
        point_re = re.compile(r"\(\s*(-?\d+(?:\.\d*)?)\s*,\s*(-?\d+(?:\.\d*)?)\s*\)")
        matches = point_re.findall(value) if isinstance(value, str) else []
        if len(matches) >= 3:
            return [Point(float(x), float(y)) for x, y in matches]

        raise ValueError(f"Cannot parse polygon from value: {value!r}")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None
        if not isinstance(value, list | tuple) or len(value) < 3:
            raise ValueError("Needs at minimum 3 points")

        points = []
        for pt in value:
            if not isinstance(pt, Point):
                pt = Point(*pt)
            points.append(f"({pt.x},{pt.y})")

        return f"({','.join(points)})"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter three or more points as (x1,y1),(x2,y2),(x3,y3),...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class CircleField(models.Field):
    """Field to store a circle defined by a center point and radius.

    Name = 'circle'
    Storage Size = 24 bytes
    Description = Circle
    Representation = <(x,y),r> (center point and radius)
    """

    description = "Circle"

    @require_postgres
    def db_type(self, connection):
        """Return the database type for this field."""
        return "circle"

    def from_db_value(self, value, expression, connection):
        """Convert the value from the database to a Python object."""
        return self.to_python(value)

    def to_python(self, value):
        """Convert a value from the database to a Circle object."""
        if value is None or isinstance(value, Circle):
            return value

        # Accept tuple-like inputs (center, radius)
        if isinstance(value, tuple | list) and len(value) == 2:
            center, radius = value
            if not isinstance(center, Point):
                center = Point(*center)
            return Circle(center, radius)

        # Accept single radius with default center (0,0)
        if isinstance(value, int | float):
            return Circle(value)

        # Only parse string inputs here
        if isinstance(value, str):
            try:
                return Circle.from_string(value)
            except Exception as e:
                raise ValueError(f"Invalid circle value: {value!r}. Error: {e}")

        # If value is none of the above, error out explicitly
        raise ValueError(f"Cannot convert {value!r} to Circle")

    def get_prep_value(self, value):
        """Prepare the value for saving to the database."""
        if value is None:
            return None

        if not isinstance(value, Circle):
            # Try converting from tuple/list
            if isinstance(value, tuple | list) and len(value) == 2:
                center, radius = value
                if not isinstance(center, Point):
                    center = Point(*center)
                value = Circle(center, radius)
            else:
                raise ValueError(f"Cannot prepare value {value!r} as Circle")

        if value.radius < 0:
            raise ValueError("Circle radius cannot be negative")

        return f"<({value.center.x},{value.center.y}),{value.radius}>"

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter a circle as <(x,y),r>",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        """Deconstruct the field for migrations."""
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
