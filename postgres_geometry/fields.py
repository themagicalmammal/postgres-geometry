"""Geometry fields for Django."""

from django import forms
from django.db import models

from .utils import Circle, Point, PointMixin, require_postgres


class PointField(models.Field):
    """Field to store a single point in space.

    Name = 'point'
    Storage Size = 16 bytes
    Description = Point on a plane
    Representation = (x,y)
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter a point as (x,y)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class LineSegmentField(PointMixin, models.Field):
    """Field to store a segment (line segment with exactly two points).

    Name = 'lseg'
    Storage Size = 32 bytes
    Description = Finite line segment
    Representation = [(x1,y1),(x2,y2)]
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class BoxField(PointMixin, models.Field):
    """Field to store a box, defined by two opposite corner points.

    Name = 'box'
    Storage Size = 32 bytes
    Description = Rectangular box
    Representation = (x1,y1),(x2,y2)
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two opposite corner points as (x1,y1),(x2,y2)",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PathField(PointMixin, models.Field):
    """Field to store a path; needs at least two points.

    Name = 'path'
    Storage Size = 16+16n bytes
    Description = Closed path (similar to polygon)/ Open path
    Representation = [(x1,y1),...]
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two or more points as (x1,y1),(x2,y2),...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PolygonField(PointMixin, models.Field):
    """Field to store a polygon, needs at least three points.

    Name = 'polygon'
    Storage Size = 40+16n bytes
    Description = Polygon (similar to closed path)
    Representation = ((x1,y1),...)
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter two or more points as (x1,y1),(x2,y2),,...",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CircleField(models.Field):
    """Field to store a circle defined by a center point and radius.

    Name = 'circle'
    Storage Size = 24 bytes
    Description = Circle
    Representation = <(x,y),r> (center point and radius)
    """

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

    def formfield(self, **kwargs):
        """Returns a Django form field for this model field."""
        defaults = {
            "form_class": forms.CharField,
            "help_text": "Enter circle as <(x,y),r>",
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
