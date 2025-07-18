"""Tests for postgres_geometry."""

from unittest.mock import Mock

from django.core.exceptions import FieldError
from django.db import connection, models
from django.test import SimpleTestCase, TestCase

from .fields import (
    BoxField,
    CircleField,
    LineSegmentField,
    PathField,
    PointField,
    PolygonField,
)
from .utils import (
    Circle,
    Point,
)


class TestModel(models.Model):
    """Model for testing geometry fields."""

    id = models.BigAutoField(primary_key=True)  # ✅ Explicit primary key
    point = PointField(null=True)
    segment_path = PathField(null=True)
    polygon = PolygonField(null=True)
    segment = LineSegmentField(null=True)
    box = BoxField(null=True)


class CircleTests(SimpleTestCase):
    """Tests for Circle class."""

    def test_from_string(self):
        """Test parsing Circle from string."""
        values = (
            ("<(1,1), 1>", Circle(1, 1, 1)),
            ("<(1,1), -1>", Circle(1, 1, -1)),
            ("<(1,1), 1.5>", Circle(1, 1, 1.5)),
            ("<(1,1), -1.5>", Circle(1, 1, -1.5)),
            ("<(1,1), .5>", Circle(1, 1, 0.5)),
            ("<(1,1), -.5>", Circle(1, 1, -0.5)),
        )

        for value_str, expected in values:
            value = Circle.from_string(value_str)

            self.assertEqual(value, expected, (value_str, value, expected))

    def test_constructor_radius(self):
        """Test Circle constructor with radius only."""
        circle = Circle(1)

        self.assertEqual(circle.center, Point())
        self.assertEqual(circle.radius, 1)

    def test_constructor_point_radius(self):
        """Test Circle constructor with center point and radius."""
        center = Point(1, 2)
        circle = Circle(center, 1)

        self.assertEqual(circle.center, center)
        self.assertEqual(circle.radius, 1)

    def test_constructor_center_radius(self):
        """Test Circle constructor with center coordinates and radius."""
        circle = Circle(1, 2, 3)

        self.assertEqual(circle.center, Point(1, 2))
        self.assertEqual(circle.radius, 3)

    def test_eq(self):
        """Test equality of Circle instances."""
        self.assertTrue(Circle(1, 1, 1) == Circle(1, 1, 1))
        self.assertFalse(Circle(1, 1, 1) != Circle(1, 1, 1))
        self.assertTrue(Circle(1, 1, 1) != Circle(2, 1, 1))
        self.assertTrue(Point(1, 1) != Point(1, 2))
        self.assertTrue(Point(1, 1) != Point(2, 2))
        self.assertTrue(Point(1, 1) == Point(1.0, 1.0))


class PointTests(SimpleTestCase):
    """Tests for Point class."""

    def test_from_string(self):
        """Test parsing Point from string."""
        values = (
            ("(1,1)", Point(1, 1)),
            ("(-1,1)", Point(-1, 1)),
            ("(1,-1)", Point(1, -1)),
            ("(-1,-1)", Point(-1, -1)),
            ("(1.5,1.5)", Point(1.5, 1.5)),
            ("(-1.5,1.5)", Point(-1.5, 1.5)),
            ("(1.5,-1.5)", Point(1.5, -1.5)),
            ("(-1.5,-1.5)", Point(-1.5, -1.5)),
            ("(.5,.5)", Point(0.5, 0.5)),
            ("(-.5,.5)", Point(-0.5, 0.5)),
            ("(.5,-.5)", Point(0.5, -0.5)),
            ("(-.5,-.5)", Point(-0.5, -0.5)),
        )

        for value_str, expected in values:
            value = Point.from_string(value_str)

            self.assertEqual(value, expected, (value_str, value, expected))

    def test_default_values(self):
        """Test default values for Point."""
        point = Point()

        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 0)

    def test_eq(self):
        """Test equality of Point instances."""
        self.assertTrue(Point(1, 1) == Point(1, 1))
        self.assertFalse(Point(1, 1) != Point(1, 1))
        self.assertTrue(Point(1, 1) != Point(2, 1))
        self.assertTrue(Point(1, 1) != Point(1, 2))
        self.assertTrue(Point(1, 1) != Point(2, 2))
        self.assertTrue(Point(1, 1) == Point(1.0, 1.0))

    def test_less_than(self):
        """Test comparison operators for Point."""
        self.assertTrue(Point() < Point(1, 1))
        self.assertTrue(Point() <= Point(1, 1))
        self.assertFalse(Point() > Point(1, 1))
        self.assertFalse(Point() >= Point(1, 1))


class GeometryFieldTestsMixin:
    """Mixin for geometry field tests."""

    def test_db_type(self):
        """Test db_type method for geometry fields."""
        self.assertEqual(self.field().db_type(connection), self.db_type)

    def test_postgres_connection(self):
        """Test db_type with a Postgres connection."""
        m_connection = Mock()
        m_connection.settings_dict = {"ENGINE": "psycopg2"}

        self.assertIsInstance(self.field().db_type(m_connection), str)

    def test_non_postgres_connection(self):
        """Test db_type with a non-Postgres connection."""
        m_connection = Mock()
        m_connection.settings_dict = {"ENGINE": "sqlite"}

        self.assertRaises(FieldError, self.field().db_type, m_connection)


class PathFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for PathField."""

    field = PathField
    db_type = "path"

    def test_store_field(self):
        """Test storing a segment path in the field."""
        value = [Point(1, 1), Point(2, 2)]

        model = TestModel()
        model.segment_path = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertIsInstance(model.segment_path, list)
        self.assertEqual(model.segment_path, value)

    def test_minimum_points(self):
        """Test minimum points for segment path."""
        model = TestModel()
        model.segment_path = [Point()]

        with self.assertRaisesRegex(ValueError, "Needs at minimum 2 points"):
            model.save()


class PolygonFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for PolygonField."""

    field = PolygonField
    db_type = "polygon"

    def test_store_field(self):
        """Test storing a polygon in the field."""
        value = [Point(0, 0), Point(1, 0), Point(1, 1)]

        model = TestModel()
        model.polygon = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertIsInstance(model.polygon, list)
        self.assertEqual(model.polygon, value)

    def test_minimum_points(self):
        """Test minimum points for polygon."""
        model = TestModel()
        model.polygon = [Point(), Point()]

        with self.assertRaisesRegex(ValueError, "Needs at minimum 3 points"):
            model.save()


class PointFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for PointField."""

    field = PointField
    db_type = "point"

    def test_store_field(self):
        """Test storing a point in the field."""
        value = Point(1, 1)

        model = TestModel()
        model.point = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertEqual(model.point, value)


class LineSegmentFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for LineSegmentField."""

    field = LineSegmentField
    db_type = "lseg"

    def test_store_field(self):
        """Test storing a segment in the field."""
        value = [Point(1, 1), Point(2, 2)]

        model = TestModel()
        model.segment = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertEqual(model.segment, value)

    def test_less_than_2_points(self):
        """Test storing segment with less than 2 points."""
        model = TestModel()
        model.segment = [Point(1, 1)]

        with self.assertRaisesRegex(ValueError, "Segment needs exactly 2 points"):
            model.save()

    def test_more_than_2_points(self):
        """Test storing segment with more than 2 points."""
        model = TestModel()
        model.segment = [Point(1, 1), Point(2, 2), Point(3, 3)]

        with self.assertRaisesRegex(ValueError, "Segment needs exactly 2 points"):
            model.save()


class BoxFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for BoxField."""

    field = BoxField
    db_type = "box"

    def test_store_field(self):
        """Test storing a box in the field."""
        value = [Point(2, 2), Point(1, 1)]

        model = TestModel()
        model.box = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertEqual(model.box, sorted(value, reverse=True))

    def test_upper_right_lower_left(self):
        """Test storing a box with upper-right and lower-left points."""
        value = [Point(1, 2), Point(2, 1)]  # Upper-left, Lower-right

        model = TestModel()
        model.box = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertEqual(model.box, [Point(2, 2), Point(1, 1)])

    def test_less_than_2_points(self):
        """Test storing box with less than 2 points."""
        model = TestModel()
        model.box = [Point(1, 1)]

        with self.assertRaisesRegex(ValueError, "Box needs exactly 2 points"):
            model.save()

    def test_more_than_2_points(self):
        """Test storing box with more than 2 points."""
        model = TestModel()
        model.box = [Point(1, 1), Point(2, 2), Point(3, 3)]

        with self.assertRaisesRegex(ValueError, "Box needs exactly 2 points"):
            model.save()


class CircleFieldTests(GeometryFieldTestsMixin, TestCase):
    """Tests for CircleField."""

    field = CircleField
    db_type = "circle"

    def test_store_field(self):
        """Test storing a circle in the field."""
        value = [Point(1, 1), Point(2, 2)]

        model = TestModel()
        model.segment = value
        model.save()

        model = TestModel.objects.get(pk=model.pk)

        self.assertEqual(model.segment, value)

    def test_less_than_2_points(self):
        """Test storing segment with less than 2 points."""
        model = TestModel()
        model.segment = [Point(1, 1)]

        self.assertRaisesRegex(ValueError, "Segment needs exactly 2 points", model.save)

    def test_more_than_2_points(self):
        """Test storing segment with more than 2 points."""
        model = TestModel()
        model.segment = [Point(1, 1), Point(2, 2), Point(3, 3)]

        self.assertRaisesRegex(ValueError, "Segment needs exactly 2 points", model.save)
